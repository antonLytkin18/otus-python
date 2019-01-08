from collections import namedtuple

from bs4 import BeautifulSoup

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
