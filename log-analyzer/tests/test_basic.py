import datetime
import os
from collections import namedtuple
from unittest import TestCase, mock
from log_analyzer import get_config, get_last_log_file, get_config_file, run


class TestLogAnalyzer(TestCase):
    @mock.patch('log_analyzer.get_config_file', return_value='./tests/fixtures/config.json')
    def test_file_config(self, mocked_config_file):
        config = get_config({
            'REPORT_SIZE': 1000,
            'REPORT_DIR': './tests/reports',
            'REPORT_TEMPLATE_PATH': './report.html',
            'LOG_DIR': './tests/log',
            'ERROR_LIMIT': 20,
        })
        self.assertEqual(config['REPORT_SIZE'], 10)

    @mock.patch('log_analyzer.get_config_file', return_value='./tests/fixtures/short_config.json')
    def test_default_config(self, mocked_config_file):
        config = get_config({
            'REPORT_SIZE': 1000,
            'REPORT_DIR': './tests/reports',
            'REPORT_TEMPLATE_PATH': './report.html',
            'LOG_DIR': './tests/fixtures/log',
            'ERROR_LIMIT': 20,
        })
        self.assertEqual(config['REPORT_SIZE'], 1000)

    def test_get_last_log(self):
        self.assertEqual(get_last_log_file('./tests/fixtures/log').date.strftime('%Y.%m.%d'), '2017.08.26')

    @mock.patch('log_analyzer.get_last_log_file')
    def test_invalid_log(self, mocked_log_file):
        LogFile = namedtuple('LogFile', ['path', 'date'])
        mocked_log_file.return_value = LogFile('./tests/fixtures/log/invalid.log', datetime.datetime.now())

        self.assertRaises(RuntimeError, run({
            'REPORT_SIZE': 20,
            'REPORT_DIR': './tests/reports',
            'REPORT_TEMPLATE_PATH': './report.html',
            'LOG_DIR': './tests/fixtures/log',
            'ERROR_LIMIT': 99,
        }))

    def test_valid_log(self):
        config = {
            'REPORT_SIZE': 20,
            'REPORT_DIR': './tests/reports',
            'REPORT_TEMPLATE_PATH': './report.html',
            'LOG_DIR': './tests/fixtures/log',
            'ERROR_LIMIT': 10,
        }
        run(config)
        report_dir = config['REPORT_DIR']
        self.assertIsNotNone(os.listdir(report_dir))
        self.remove_files_from_dir(report_dir)

    @staticmethod
    def remove_files_from_dir(dir):
        filelist = [file for file in os.listdir(dir) if file.endswith('.html')]
        for file in filelist:
            os.remove(os.path.join(dir, file))
