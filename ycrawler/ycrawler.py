import asyncio
import logging
import os

from client import Client
from yparser import YParser


class YCrawler:

    URL = 'https://news.ycombinator.com/'
    CRAWLING_PERIOD = 30
    STORE_DIR = './posts'
    CONC_LEVEL = 3

    def __init__(self, loop):
        self._urls = asyncio.Queue()
        self._processed_urls = []
        self._loop = loop
        self._crawling_period = self.CRAWLING_PERIOD
        self._parser = YParser()
        self._store_dir = self.STORE_DIR
        self._client = Client()
        self._semaphore = asyncio.Semaphore(self.CONC_LEVEL)

    async def parse_urls_forever(self):
        while True:
            logging.info(f'Getting new posts')
            self._loop.create_task(self.parse_urls())
            await asyncio.sleep(self._crawling_period)

    async def parse_urls(self):
        html = await self._client.get(self.URL)
        if not html:
            return
        for post_id in self._parser.get_post_ids(html):
            self.put_url(self.URL + f'item?id={post_id}')

    def put_url(self, url):
        if url in self._processed_urls:
            return
        logging.info(f'New url was put to analysis queue: {url}')
        self._processed_urls.append(url)
        self._urls.put_nowait(url)

    async def process_urls(self):
        while True:
            url = await self._urls.get()
            self._loop.create_task(self.process_url(url))

    async def process_url(self, url):
        html = await self._client.get_with_lock(self._semaphore, url)
        if not html:
            return
        ypost = self._parser.get_ypost(html)
        self._loop.create_task(self.save_in_thread(ypost.url, self.post_dir(ypost), 'post.html'))
        for i, comment_url in enumerate(ypost.comment_urls):
            self._loop.create_task(self.save_in_thread(comment_url, self.post_dir(ypost), f'post-comment-{i}.html'))

    async def save_in_thread(self, url, dir, file_name):
        try:
            html = await self._client.get(url)
            if not html:
                return
            self._loop.run_in_executor(None, self.save, html, dir, file_name)
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
        return os.path.join(self._store_dir, post.id)

    def run(self):
        asyncio.gather(self.parse_urls_forever(), self.process_urls(), loop=self._loop)
        self._loop.run_forever()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    event_loop = asyncio.get_event_loop()
    try:
        crawler = YCrawler(event_loop)
        crawler.run()
    except KeyboardInterrupt:
        event_loop.close()
