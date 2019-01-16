import argparse
import os
import logging
import asyncio
import aiohttp

from functools import wraps
from collections import namedtuple
from bs4 import BeautifulSoup

MAX_RECONNECT_TRIES = 5
BACKOFF_FACTOR = 0.4


def reconnect(max_tries=MAX_RECONNECT_TRIES, backoff_factor=BACKOFF_FACTOR):
    def wrappy(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            tries = 0
            url = args[1]
            while tries < max_tries:
                try:
                    return await fn(*args, **kwargs)
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    tries += 1
                    timeout = backoff_factor * (2 ** tries)
                    logging.info(f'Recconnect ({tries}): {url}')
                    await asyncio.sleep(timeout)
            logging.error(f'Unable to load url: {url}')
            return None
        return wrapper
    return wrappy


YPost = namedtuple('YPost', ['id', 'url', 'comment_urls'])


class YParser:
    def get_post_ids(self, main_html):
        soup = self._soup(main_html)
        items = soup.select('tr.athing')
        return [item.attrs['id'] for item in items]

    def get_ypost(self, post_html):
        soup = self._soup(post_html)
        item = soup.select_one('tr.athing')
        link = item.select_one('a.storylink')
        ypost = YPost(id=item.attrs['id'], url=link.attrs['href'], comment_urls=set())
        comments_links = soup.select('div.comment a[rel=nofollow]')
        for link in comments_links:
            ypost.comment_urls.add(link.attrs['href'])

        return ypost

    def _soup(self, html):
        return BeautifulSoup(html, features='html.parser')


class Client:

    READ_TIMEOUT = 5
    SUCCESS_STATUS = 200

    @reconnect()
    async def get(self, url):
        connector = aiohttp.TCPConnector(verify_ssl=False)
        async with aiohttp.ClientSession(connector=connector, read_timeout=self.READ_TIMEOUT) as session:
            async with session.get(url) as response:
                if response.status != self.SUCCESS_STATUS:
                    return None
                return await response.read()

    async def get_with_lock(self, semaphore, url):
        with (await semaphore):
            return await self.get(url)


class YCrawler:

    URL = 'https://news.ycombinator.com/'

    def __init__(self, loop, client, parser, period, store_dir, conc_level):
        self.loop = loop
        self.client = client
        self.parser = parser
        self.urls = asyncio.Queue()
        self.crawling_period = period
        self.store_dir = store_dir
        self.processed_urls = []
        self.semaphore = asyncio.Semaphore(conc_level)

    async def parse_urls_forever(self):
        while True:
            logging.info(f'Getting new posts')
            self.loop.create_task(self.parse_urls())
            await asyncio.sleep(self.crawling_period)

    async def parse_urls(self):
        html = await self.client.get(self.URL)
        if not html:
            return
        for post_id in self.parser.get_post_ids(html):
            self.put_url(self.URL + f'item?id={post_id}')

    def put_url(self, url):
        if url in self.processed_urls:
            return
        logging.info(f'New url was put to analysis queue: {url}')
        self.processed_urls.append(url)
        self.urls.put_nowait(url)

    async def process_urls(self):
        while True:
            url = await self.urls.get()
            self.loop.create_task(self.process_url(url))

    async def process_url(self, url):
        html = await self.client.get_with_lock(self.semaphore, url)
        if not html:
            return
        ypost = self.parser.get_ypost(html)
        self.loop.create_task(self.save_in_thread(ypost.url, self.post_dir(ypost), 'post.html'))
        for i, comment_url in enumerate(ypost.comment_urls):
            self.loop.create_task(self.save_in_thread(comment_url, self.post_dir(ypost), f'post-comment-{i}.html'))

    async def save_in_thread(self, url, dir, file_name):
        try:
            html = await self.client.get(url)
            if not html:
                return
            self.loop.run_in_executor(None, self.save, html, dir, file_name)
            logging.info(f'{url} page has been saved to {dir}')
        except Exception:
            logging.error(f'Unable to save page: {url}')

    def save(self, html, dir, file_name):
        if not os.path.exists(dir):
            os.makedirs(dir, exist_ok=True)
        path = os.path.join(dir, file_name)
        with open(path, 'wb') as f:
            f.write(html)

    def post_dir(self, post):
        return os.path.join(self.store_dir, post.id)

    def run(self):
        asyncio.gather(self.parse_urls_forever(), self.process_urls(), loop=self.loop)
        self.loop.run_forever()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-p', '--period', help='Crawling period', default=30, type=int)
    arg_parser.add_argument('-d', '--store_dir', help='Destination dir', default='./posts', type=str)
    arg_parser.add_argument('-c', '--conc_level', help='Concurrency level', default=3, type=int)
    args = arg_parser.parse_args()

    event_loop = asyncio.get_event_loop()
    try:
        crawler = YCrawler(
            loop=event_loop,
            client=Client(),
            parser=YParser(),
            period=args.period,
            store_dir=args.store_dir,
            conc_level=args.conc_level
        )
        crawler.run()
    except KeyboardInterrupt:
        event_loop.close()
