import mimetypes
import os
from datetime import datetime
from time import mktime
from urllib import parse
from wsgiref.handlers import format_date_time

CLRF = '\r\n'
ENCODING = 'utf-8'


class Request:

    _method = None
    _query_string = ''
    _query_params = ''
    _http = ''
    _path = '/'
    _headers = []

    def __init__(self, request_bytes):
        self._request_data = request_bytes.decode(ENCODING)
        if not self.is_complete():
            return
        request_string, headers_string = self._request_data.split(CLRF, 1)
        self._method, self._query_string, self._http = request_string.split(' ')
        params = self._query_string.split('?', 1)
        self._path = parse.unquote(params[0])
        self._query_params = params[1] if len(params) > 1 else ''
        self._headers = headers_string.splitlines()[:-1]

    def get_request_data(self):
        return self._request_data

    def is_complete(self):
        return CLRF * 2 in self._request_data

    def get_query_string(self):
        return self._query_string

    def get_path(self):
        return self._path

    def get_method(self):
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
        if not self.has_request_data():
            self.set_bad_request()
            return
        if not self.is_method_allowed():
            self.set_not_allowed()
            return
        self._file_path = self.build_file_path(document_root)
        if not os.path.exists(self._file_path):
            self.set_not_found()
            return
        self._content_type = self.get_content_type()
        self._body = self.get_content()
        self._content_length = len(self._body)
        if self.is_head_request():
            self.clear_body()

    def is_method_allowed(self):
        return self._request.get_method() in self._allowed_methods

    def set_not_allowed(self):
        self._status = self.NOT_ALLOWED
        return self

    def set_not_found(self):
        self._status = self.NOT_FOUND
        return self

    def set_bad_request(self):
        self._status = self.BAD_REQUEST
        return self

    def build_file_path(self, document_root):
        path = self._request.get_path()
        path += 'index.html' if path.endswith('/') else ''
        root = document_root if document_root else os.path.dirname(os.path.abspath(__file__))
        return root + os.path.normpath(path)

    def get_content(self):
        with open(self._file_path, 'rb') as file:
            return file.read()

    def get_content_type(self):
        content_type, encoding = mimetypes.guess_type(self._file_path)
        return content_type

    def has_request_data(self):
        return self._request.get_request_data()

    def clear_body(self):
        self._body = b''
        return self

    def is_head_request(self):
        return self._request.get_method() == 'HEAD'

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
