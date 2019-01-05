import functools
import unittest

import ip2w


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)
        return wrapper
    return decorator


class Ip2wTest(unittest.TestCase):
    @cases([
        '176.14.221.123',
        '192.200.18.23',
    ])
    def test_ip_is_valid(self, ip):
        self.assertEqual(ip, ip2w.validate_ip(ip))

    @cases([
        'some-str',
        '266.189.591.789',
    ])
    def test_ip_is_invalid(self, ip):
        with self.assertRaises(Exception):
            ip2w.validate_ip(ip)

    @cases([
        {'loc': '50.2,60.7'},
        {'loc': '11.5,58.12'},
        {'loc': '17.512,9.126'},
    ])
    def test_coords_is_valid(self, location_info):
        weather_info = ip2w.get_weather_info(location_info)
        self.assertIsNotNone(weather_info.get('temp'))

    @cases([
        {'loc': '123, 11'},
        {'loc': 'one, two'},
        {'loc': 'three'},
        {'loc': '17.512,9.126,7.251'},
    ])
    def test_coords_is_invalid(self, location_info):
        with self.assertRaises(Exception):
            ip2w.get_weather_info(location_info)


if __name__ == '__main__':
    unittest.main()
