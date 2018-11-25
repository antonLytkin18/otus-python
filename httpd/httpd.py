#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import socket
from multiprocessing import Process

from lib import Request, Response


class Server:

    CHUNK_SIZE = 1024
    HOST = ''
    PORT = 8080
    CLIENT_TIMEOUT = 10

    def __init__(self, root, port):
        self._document_root = root
        if self.is_document_root_invalid():
            raise Exception('Invalid document root')
        self._socket = socket.socket()
        self._socket.bind((self.HOST, port))
        self._socket.listen()

    def is_document_root_invalid(self):
        return self._document_root and not os.path.isdir(self._document_root)

    def create_request(self, client_socket):
        request_bytes = b''
        expected_size = 0
        request = None
        while len(request_bytes) >= expected_size:
            chunk_bytes = client_socket.recv(self.CHUNK_SIZE)
            request_bytes += chunk_bytes
            request = Request(request_bytes)
            if request.is_complete():
                break
            expected_size += self.CHUNK_SIZE
        return request

    def serve(self):
        client_socket, address_info = self._socket.accept()
        client_socket.settimeout(self.CLIENT_TIMEOUT)
        with client_socket:
            request = self.create_request(client_socket)
            response = Response(request, self._document_root)
            client_socket.sendall(response.to_bytes())

    def serve_forever(self):
        while True:
            self.serve()


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--workers', help='workers count', default=1, type=int)
    parser.add_argument('-r', '--document_root', help='document root path', default='', type=str)
    parser.add_argument('-p', '--port', help='port', default=Server.PORT, type=int)
    args = parser.parse_args()
    workers_count = args.workers if args.workers > 0 else 1
    try:
        server = Server(args.document_root, args.port)
    except Exception as e:
        logging.error(e)
        exit()
    workers = []
    worker = Process(target=server.serve_forever)

    for _ in range(workers_count):
        worker = Process(target=server.serve_forever)
        worker.start()
        workers.append(worker)
    try:
        for worker in workers:
            worker.join()
    except KeyboardInterrupt:
        for worker in workers:
            worker.terminate()
            logging.info(f'Worker {worker.pid} was terminated')

