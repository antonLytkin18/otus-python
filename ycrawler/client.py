import logging
from functools import wraps

import aiohttp
import asyncio


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
