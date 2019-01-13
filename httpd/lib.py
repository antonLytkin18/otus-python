import mimetypes
import os
from datetime import datetime
from time import mktime
from urllib import parse
from wsgiref.handlers import format_date_time

CLRF = '\r\n'
ENCODING = 'utf-8'


class Request:

    MAX_LENGTH = 1000

    _request_data = ''
    _method = None
    _query_string = ''
    _query_params = ''
    _http = ''
    _path = '/'
    _headers = []

    def __init__(self, request_bytes):
        if self.is_length_exceeded(request_bytes) or not self.is_complete(request_bytes):
            return
        self._request_data = request_bytes.decode(ENCODING)
        request_string, headers_string = self._request_data.split(CLRF, 1)
        self._method, self._query_string, self._http = request_string.split(' ')
        params = self._query_string.split('?', 1)
        self._path = parse.unquote(params[0])
        self._query_params = params[1] if len(params) > 1 else ''
        self._headers = headers_string.splitlines()[:-1]

    @staticmethod
    def is_complete(request_bytes):
        return CLRF * 2 in request_bytes.decode(ENCODING)

    @staticmethod
    def is_length_exceeded(request_bytes):
        return len(request_bytes.decode(ENCODING)) > Request.MAX_LENGTH

    @property
    def request_data(self):
        return self._request_data

    @property
    def path(self):
        return self._path

    @property
    def method(self):
        return self._method


class Response:

    OK = 200
    BAD_REQUEST = 400
    NOT_FOUND = 404
    NOT_ALLOWED = 405
    STATUS_REASON_PHRASES = {
        OK: 'OK',
        BAD_REQUEST: 'Bad Request',
        NOT_FOUND: 'Not Found',
        NOT_ALLOWED: 'Not allowed',
    }

    _allowed_methods = ['GET', 'HEAD']
    _status = OK
    _body = b''
    _content_type = 'text/html'
    _content_length = 0

    def __init__(self, request, document_root):
        self._request = request
        if not self._request.request_data:
            self._status = self.BAD_REQUEST
            return
        if self._request.method not in self._allowed_methods:
            self._status = self.NOT_ALLOWED
            return
        self._file_path = self.build_file_path(document_root)
        if not os.path.exists(self._file_path):
            self._status = self.NOT_FOUND
            return
        self._content_type = self.get_content_type()
        if request.method == 'HEAD':
            self._content_length = len(self.get_content())
            return
        self._body = self.get_content()
        self._content_length = len(self._body)

    def build_file_path(self, document_root):
        path = self._request.path
        path += 'index.html' if path.endswith('/') else ''
        root = document_root if document_root else os.path.dirname(os.path.abspath(__file__))
        return root + os.path.normpath(path)

    def get_content(self):
        with open(self._file_path, 'rb') as file:
            return file.read()

    def get_content_type(self):
        content_type, encoding = mimetypes.guess_type(self._file_path)
        return content_type

    def get_headers(self):
        return [
            f'HTTP/1.1 {self._status} {self.get_reason_phrase()}',
            f'Date: {format(format_date_time(mktime(datetime.now().timetuple())))}',
            f'Content-Type: {self._content_type}',
            f'Content-Length: {self._content_length}',
            'Server: Poor man\'s server',
            'Connection: close',
        ]

    def get_reason_phrase(self):
        return self.STATUS_REASON_PHRASES[self._status]

    def to_bytes(self):
        return (CLRF.join(self.get_headers()) + CLRF * 2).encode(ENCODING) + self._body
