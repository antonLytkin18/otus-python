import json
import logging
import os
import socket
from functools import wraps
from time import sleep

import requests

IPINFO_API_URL = os.environ.get('IPINFO_API_URL')
WEATHER_API_URL = os.environ.get('WEATHER_API_URL')
WEATHER_APP_ID = os.environ.get('WEATHER_APP_ID')
MAX_RECONNECT_TRIES = int(os.environ.get('MAX_RECONNECT_TRIES'))
BACKOFF_FACTOR = float(os.environ.get('BACKOFF_FACTOR'))
REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT'))

STATUS_OK = '200 OK'
STATUS_BAD_REQUEST = '400 Bad Request'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname).1s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def reconnect(max_tries=MAX_RECONNECT_TRIES, backoff_factor=BACKOFF_FACTOR):
    def wrappy(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            tries = 0
            while tries < max_tries:
                try:
                    return fn(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    logging.exception(e)
                    tries += 1
                    timeout = backoff_factor * (2 ** tries)
                    sleep(timeout)
                    raise Exception(str(e))

        return wrapper

    return wrappy


@reconnect()
def get_location_info(ip=''):
    response = requests.get(IPINFO_API_URL + '/' + ip, timeout=REQUEST_TIMEOUT)
    return response.json()


@reconnect()
def get_weather_info(location_info):
    lat, lon = location_info.get('loc').split(',')
    response = requests.get(WEATHER_API_URL, params={
        'lat': lat,
        'lon': lon,
        'appid': WEATHER_APP_ID,
        'units': 'metric',
    }, timeout=REQUEST_TIMEOUT)
    info = response.json()
    return {
        'city': location_info.get('city'),
        'temp': info['main']['temp'],
        'conditions': ', '.join([item['description'] for item in info['weather']])
    }


def validate_ip(ip):
    try:
        socket.inet_aton(ip)
    except socket.error:
        raise Exception('ipv4 is invalid')
    return ip


def get_ip_from_request(environment):
    uri = environment.get('REQUEST_URI', '')
    ip = uri.split('/')[-1]
    return validate_ip(ip) if ip else ''


def application(environment, start_response):
    status = STATUS_OK
    errors = []
    weather_info = {}
    try:
        ip = get_ip_from_request(environment)
        location_info = get_location_info(ip)
        weather_info = get_weather_info(location_info)
    except Exception as e:
        logging.exception(e)
        status = STATUS_BAD_REQUEST
        errors.append('Unable to get weather info')

    response_body = json.dumps({**weather_info, 'errors': errors}).encode('utf-8')
    start_response(status, [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(response_body)))
    ])
    return [response_body]
