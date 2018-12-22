#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import sys
import glob
import logging
import collections
from functools import partial
from optparse import OptionParser
import queue
from time import sleep

import appsinstalled_pb2
import memcache
import multiprocessing
import threading

NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple('AppsInstalled', ['dev_type', 'dev_id', 'lat', 'lon', 'apps'])

MAX_TASK_QUEUE_SIZE = 0
MAX_RESULT_QUEUE_SIZE = 0
WORKER_COUNT = multiprocessing.cpu_count()
THREADS_PER_WORKER = 5
MEMCACHE_TIMEOUT = 15
MEMCACHE_RETRIES_COUNT = 1
MEMCACHE_BACKOFF_FACTOR = 1


class AppsInsertPool:
    def __init__(self, threads_count, task_queue, result_queue):
        self.threads_count = threads_count
        self.threads = []
        self.tasks_queue = task_queue
        self.result_queue = result_queue
        self.memc_pool = collections.defaultdict(queue.Queue)

    def run_threads(self):
        for _ in range(self.threads_count):
            thread = threading.Thread(target=self._run)
            self.threads.append(thread)
            thread.start()

    def _run(self):
        processed = errors = 0
        while True:
            try:
                memc_addr, appsinstalled, dry_run = self.tasks_queue.get(timeout=1)
                memc_client = self._get_memc_client(memc_addr)
                is_success = insert_appsinstalled(memc_client, memc_addr, appsinstalled, dry_run)
                self.memc_pool[memc_addr].put(memc_client)
                if is_success:
                    processed += 1
                else:
                    errors += 1
            except queue.Empty:
                try:
                    self.result_queue.put((processed, errors), timeout=0.1)
                except queue.Full:
                    logging.error('Result queue is overflew')
                return

    def _get_memc_client(self, memc_addr):
        try:
            return self.memc_pool[memc_addr].get(timeout=0.1)
        except queue.Empty:
            return memcache.Client([memc_addr], socket_timeout=MEMCACHE_TIMEOUT)

    def wait(self):
        for thread in self.threads:
            thread.join()


class AppsParser:
    def __init__(self, task_queue, result_queue):
        self.tasks_queue = task_queue
        self.result_queue = result_queue

    def run(self, path, device_memc, dry):
        processed = errors = 0
        logging.info('Processing %s' % path)
        with gzip.open(path) as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                appsinstalled = parse_appsinstalled(line)
                if not appsinstalled:
                    errors += 1
                    continue
                memc_addr = device_memc.get(appsinstalled.dev_type)
                if not memc_addr:
                    errors += 1
                    logging.error('Unknown device type: %s' % appsinstalled.dev_type)
                    continue
                self.tasks_queue.put((memc_addr, appsinstalled, dry))
        try:
            self.result_queue.put((processed, errors), timeout=0.1)
        except queue.Full:
            logging.error('Result queue is overflew')
        return


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, '.' + fn))


def insert_appsinstalled(memc_client, memc_addr, appsinstalled, dry_run=False):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = '%s:%s' % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    try:
        if not dry_run:
            is_success = False
            for attempt in range(MEMCACHE_RETRIES_COUNT + 1):
                is_success = memc_client.set(key, packed)
                if is_success:
                    break
                sleep(MEMCACHE_BACKOFF_FACTOR * (2 ** attempt))
            return is_success
        logging.debug('%s - %s -> %s' % (memc_addr, key, str(ua).replace('\n', ' ')))
    except Exception as e:
        logging.exception('Cannot write to memc %s: %s' % (memc_addr, e))
        return False
    return True


def parse_appsinstalled(line):
    line_parts = line.decode('utf-8').strip().split('\t')
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(',')]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(',') if a.isidigit()]
        logging.info('Not all user apps are digits: `%s`' % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info('Invalid geo coords: `%s`' % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def log_result(result_queue):
    processed = errors = 0
    while not result_queue.empty():
        processed_per_worker, errors_per_worker = result_queue.get()
        processed += processed_per_worker
        errors += errors_per_worker
    if not processed:
        logging.info('There are no processed files. Did you forget to start a memcache server?')
        return
    err_rate = float(errors) / processed
    if err_rate < NORMAL_ERR_RATE:
        logging.info('Acceptable error rate (%s). Successfull load' % err_rate)
    else:
        logging.error('High error rate (%s > %s). Failed load' % (err_rate, NORMAL_ERR_RATE))


def process_file(path, device_memc, dry):
    task_queue = queue.Queue(maxsize=MAX_TASK_QUEUE_SIZE)
    result_queue = queue.Queue(maxsize=MAX_RESULT_QUEUE_SIZE)

    pool = AppsInsertPool(THREADS_PER_WORKER, task_queue, result_queue)
    pool.run_threads()

    parser = AppsParser(task_queue, result_queue)
    parser.run(path, device_memc, dry)

    pool.wait()

    log_result(result_queue)

    return path


def prototest():
    sample = 'idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424'
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split('\t')
        apps = [int(a) for a in raw_apps.split(',') if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


def main(options):
    device_memc = {
        'idfa': options.idfa,
        'gaid': options.gaid,
        'adid': options.adid,
        'dvid': options.dvid,
    }
    pool = multiprocessing.Pool(processes=WORKER_COUNT)
    path_list = sorted(path for path in glob.iglob(options.pattern))
    for path in pool.imap(partial(process_file, device_memc=device_memc, dry=options.dry), path_list):
        dot_rename(path)


if __name__ == '__main__':
    op = OptionParser()
    op.add_option('-t', '--test', action='store_true', default=False)
    op.add_option('-l', '--log', action='store', default=None)
    op.add_option('--dry', action='store_true', default=False)
    op.add_option('--pattern', action='store', default='data/*.tsv.gz')
    op.add_option('--idfa', action='store', default='127.0.0.1:33013')
    op.add_option('--gaid', action='store', default='127.0.0.1:33014')
    op.add_option('--adid', action='store', default='127.0.0.1:33015')
    op.add_option('--dvid', action='store', default='127.0.0.1:33016')
    (opts, args) = op.parse_args()
    logging.basicConfig(
        filename=opts.log,
        level=logging.INFO if not opts.dry else logging.DEBUG,
        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S'
    )
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info('Memc loader started with options: %s' % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception('Unexpected error: %s' % e)
        sys.exit(1)
