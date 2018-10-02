from time import sleep

import redis
from redis import ConnectionError, TimeoutError
import functools
import logging

MAX_RECONNECT_TRIES = 2
RECONNECT_TIMEOUT_RATE = 2


class StoreCacheError(Exception):
    pass


def reconnect(max_tries=MAX_RECONNECT_TRIES, timeout_rate=RECONNECT_TIMEOUT_RATE):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tries = 0
            while tries < max_tries:
                try:
                    return func(*args, **kwargs)
                except StoreCacheError:
                    logging.info(f'Cache is unavailable. Trying to reconnect {tries + 1} times')
                    tries += 1
                    sleep(tries + tries * timeout_rate)
            return False
        return wrapper
    return decorator


class RedisCache:
    def __init__(self, port=6379, timeout=10):
        self._cache = redis.StrictRedis(
            host='localhost',
            port=port,
            decode_responses=True,
            socket_timeout=timeout,
            socket_connect_timeout=timeout
        )

    def get(self, key):
        try:
            return self._cache.get(key)
        except (ConnectionError, TimeoutError):
            raise StoreCacheError

    def set(self, key, value, time=None):
        try:
            self._cache.set(key, value, time)
        except (ConnectionError, TimeoutError):
            raise StoreCacheError
        return self


class Store:
    def __init__(self, cache_driver):
        self._cache_driver = cache_driver

    def get(self, key):
        return self._cache_driver.get(key)

    def set(self, key, value, time=None):
        self._cache_driver.set(key, value, time)
        return self

    @reconnect()
    def cache_get(self, key):
        return self.get(key)

    @reconnect()
    def cache_set(self, key, value, time=None):
        self.set(key, value, time)
        return self

