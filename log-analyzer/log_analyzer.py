#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import gzip
import json
import logging
import os
import re
import statistics
from collections import defaultdict, namedtuple
from datetime import datetime
from string import Template

config = {
    'REPORT_SIZE': 1000,
    'REPORT_DIR': './reports',
    'REPORT_TEMPLATE_PATH': './report.html',
    'LOG_DIR': './log',
    'LOGGING_FILE_PATH': './parser.log',
    'ERROR_LIMIT': 20,
    'REPORT_PRECISION': 3,
}

line_pattern = re.compile(
    '(?P<remote_addr>.*?) '
    '(?P<remote_user>.*?) '
    '(?P<real_ip>.*?) \[(?P<date>.*?)(?= ) (?P<timezone>.*?)\] '
    '"(?P<request_method>.*?) (?P<path>.*?)(?P<request_version> HTTP/.*)?" '
    '(?P<status>.*?) '
    '(?P<length>.*?) '
    '"(?P<referrer>.*?)" '
    '"(?P<user_agent>.*?)" '
    '"(?P<forwarded_for>.*?)" '
    '"(?P<request_id>.*?)" '
    '"(?P<rb_user>.*?)" '
    '(?P<request_time>.*?)$'
)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config')
    return parser.parse_args()


def save_report(report_data, report_file_path, report_template_path):
    with open(report_template_path, 'r') as f:
        file_data = f.read()

    file_data = Template(file_data).safe_substitute({'table_json': json.dumps(report_data)})
    with open(report_file_path, 'w') as f:
        f.write(file_data)


def parse_line(line):
    matched = re.match(line_pattern, line)
    return matched.groupdict() if matched else None


def get_calculated_report_data(report_data, report_size, report_precision):
    template_data = []
    requests_count = sum(map(len, report_data.values()))
    requests_time = sum(map(sum, report_data.values()))

    for url, request_time_list in report_data.items():
        current_request_count = len(request_time_list)
        current_request_time = sum(request_time_list)
        template_data.append({
            'url': url,
            'count': current_request_count,
            'count_perc': round(100 * current_request_count / requests_count, report_precision),
            'time_sum': round(current_request_time, report_precision),
            'time_perc': round(100 * current_request_time / requests_time, report_precision),
            'time_avg': round(current_request_time / current_request_count, report_precision),
            'time_max': round(max(request_time_list), report_precision),
            'time_med': round(statistics.median(request_time_list), report_precision)
        })

    if len(template_data) > int(report_size):
        logging.info('Cutting log size to {}'.format(report_size))
        template_data.sort(key=lambda item: item['time_sum'], reverse=True)
        return template_data[:int(report_size)]

    return template_data


def get_last_log_file(log_dir):
    if not os.path.isdir(log_dir):
        raise NotADirectoryError
    last_log_file = None
    LogFile = namedtuple('LogFile', ['path', 'date'])
    for log_name in os.listdir(log_dir):
        matched = re.match('^nginx-access-ui\.log-(?P<date>\d{8})(\.gz)?$', log_name)
        if not matched:
            continue
        try:
            log_date = datetime.strptime(matched.group('date'), '%Y%m%d')
        except ValueError:
            continue
        if not last_log_file or last_log_file.date < log_date:
            last_log_file = LogFile(os.path.join(log_dir, log_name), log_date)
    return last_log_file


def parse_file(file_path, error_limit):
    open_file = gzip.open if file_path.endswith('.gz') else open
    lines = 0
    errors = 0
    with open_file(file_path, 'rb') as file:
        for line in file:
            lines += 1
            result = parse_line(line.decode('utf-8'))
            if not result:
                errors += 1
                continue
            yield result
    errors_percent = round(errors * 100 / lines)
    if errors_percent > error_limit:
        raise RuntimeError('Percent of errors is more than expected: {}'.format(errors_percent))


def init_logging(file_name=None):
    logging.basicConfig(
        filename=file_name,
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_config_file():
    args = get_args()
    return args.config if args and args.config else None


def get_config(default_config):
    config_file_path = get_config_file()
    if not os.path.isfile(config_file_path):
        raise FileNotFoundError('Config file not found: "{}"'.format(config_file_path))
    try:
        with open(config_file_path, mode='r') as config_file:
            file_config = json.load(config_file)
    except json.decoder.JSONDecodeError:
        raise Exception('Config file is not in json format: "{}"'.format(config_file_path))

    return default_config if not file_config else {**default_config, **file_config}


def get_report_file_path(log_file, report_dir):
    return os.path.join(report_dir, 'report-{}.html'.format(log_file.date.strftime('%Y.%m.%d')))


def run(config):
    init_logging(config.get('LOGGING_FILE_PATH'))
    log_dir = config.get('LOG_DIR')
    log_file = get_last_log_file(log_dir)
    if not log_file:
        logging.error('No nginx log file found in directory: "{}"'.format(log_dir))
        return
    report_file_path = get_report_file_path(log_file, config.get('REPORT_DIR'))
    if os.path.isfile(report_file_path):
        logging.info('Report file "{}" already exists'.format(report_file_path))
        return

    report_data = defaultdict(list)
    try:
        for parsed_line in parse_file(log_file.path, config.get('ERROR_LIMIT', 100)):
            report_data[parsed_line['path']].append(float(parsed_line['request_time']))
    except RuntimeError as e:
        logging.error(str(e))
        return

    report_data = get_calculated_report_data(report_data, config.get('REPORT_SIZE'), config.get('REPORT_PRECISION'))
    save_report(report_data, report_file_path, config.get('REPORT_TEMPLATE_PATH'))


def main():
    try:
        run(get_config(config))
    except BaseException as e:
        logging.exception(e)


if __name__ == '__main__':
    main()
