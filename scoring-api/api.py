#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import json
import datetime
import logging
import hashlib
import re
import uuid
from optparse import OptionParser
from http.server import HTTPServer, BaseHTTPRequestHandler

import scoring
from store import Store, RedisCache

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}
PHONE_FORMAT = r'^7\d{10}$'
DATE_FORMAT = '%d.%m.%Y'
MAX_USER_AGE = 70
DAYS_IN_YEAR = 365


class Field:
    def __init__(self, required=False, nullable=True):
        self.required = required
        self.nullable = nullable

    def validate(self, value):
        if self.required and value is None:
            raise ValueError('value is required')
        if not self.nullable and self.is_nullable(value):
            raise ValueError('value can not be null')

    @staticmethod
    def is_nullable(value):
        return len(value) == 0 if isinstance(value, collections.Iterable) else value is None


class CharField(Field):
    def validate(self, value):
        super().validate(value)
        if not value:
            return
        if not isinstance(value, str):
            raise ValueError('invalid value type')


class ArgumentsField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, dict):
            raise ValueError('invalid value type')


class EmailField(CharField):
    def validate(self, value):
        super().validate(value)
        if not value:
            return
        if '@' not in value:
            raise ValueError('invalid value format')


class PhoneField(Field):
    def validate(self, value):
        super().validate(value)
        if not value:
            return
        if not isinstance(value, str) and not isinstance(value, int):
            raise ValueError('invalid value type')
        if not re.compile(PHONE_FORMAT).match(str(value)):
            raise ValueError('invalid value format')


class DateField(CharField):
    def validate(self, value):
        super().validate(value)
        if not value:
            return
        try:
            datetime.datetime.strptime(value, DATE_FORMAT)
        except ValueError:
            raise ValueError('invalid value format')


class BirthDayField(DateField):
    def validate(self, value):
        super().validate(value)
        if not value:
            return
        start_datetime = datetime.datetime.now() - datetime.timedelta(days=MAX_USER_AGE * DAYS_IN_YEAR)
        if datetime.datetime.strptime(value, '%d.%m.%Y') <= start_datetime:
            raise ValueError(f'Years count more than expected: {MAX_USER_AGE}')


class GenderField(Field):
    def validate(self, value):
        super().validate(value)
        if not value:
            return
        if not isinstance(value, int):
            raise ValueError('invalid field type')
        if value not in [UNKNOWN, MALE, FEMALE]:
            raise ValueError('invalid field value')


class ClientIDsField(Field):
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, list):
            raise ValueError('value must be list type')
        for clientId in value:
            if not isinstance(clientId, int):
                raise ValueError('clientId must be integer type')


class RequestMeta(type):
    def __new__(mcs, name, bases, attributes):
        fields = {}
        for key, val in attributes.items():
            if isinstance(val, Field):
                fields[key] = val

        cls = super().__new__(mcs, name, bases, attributes)
        cls.fields = fields
        return cls


class Request(metaclass=RequestMeta):

    def __init__(self, request_params):
        self.errors = []
        for name, field in self.fields.items():
            value = request_params[name] if name in request_params else None
            try:
                field.validate(value)
                setattr(self, name, value)
            except ValueError as e:
                self.errors.append(f'field "{name}": {str(e)}')

    def is_valid(self):
        return not self.errors


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True, nullable=False)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, request_params):
        super().__init__(request_params)
        if not self.is_valid():
            return

        for first_pair, second_pair in self.get_valid_field_pairs():
            if getattr(self, first_pair) is not None and getattr(self, second_pair) is not None:
                return

        self.errors.append('there are no valid pairs')

    @staticmethod
    def get_valid_field_pairs():
        return [
            ['phone', 'email'],
            ['first_name', 'last_name'],
            ['gender', 'birthday']
        ]

    def get_not_empty_fields(self):
        result = []
        for name in self.fields:
            if getattr(self, name) is not None:
                result.append(name)
        return result


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        salt = datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT
        digest = hashlib.sha512(salt.encode('utf-8')).hexdigest()
    else:
        salt = request.account + request.login + SALT
        digest = hashlib.sha512(salt.encode('utf-8')).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    method_request = MethodRequest(request['body'])
    if not method_request.is_valid():
        return method_request.errors, INVALID_REQUEST
    if not check_auth(method_request):
        return ERRORS[FORBIDDEN], FORBIDDEN
    return process_scoring(method_request, ctx, store)


def process_scoring(method_request, ctx, store):
    method_name = method_request.method
    if not method_name:
        return ERRORS[INVALID_REQUEST], INVALID_REQUEST

    scoring_methods = {
        'online_score': get_online_score,
        'clients_interests': get_clients_interests
    }
    try:
        method = scoring_methods[method_name]
    except KeyError:
        return ERRORS[FORBIDDEN], FORBIDDEN

    return method(method_request, ctx, store)


def get_online_score(method_request, ctx, store):
    if method_request.is_admin:
        return  {'score': int(ADMIN_SALT)}, OK
    request = OnlineScoreRequest(method_request.arguments)
    if not request.is_valid():
        return request.errors, INVALID_REQUEST
    ctx['has'] = request.get_not_empty_fields()

    score = scoring.get_score(store, request.phone, request.email, request.birthday, request.gender, request.first_name, request.last_name)
    return {'score': score}, OK


def get_clients_interests(method_request, ctx, store):
    request = ClientsInterestsRequest(method_request.arguments)
    if not request.is_valid():
        return request.errors, INVALID_REQUEST
    client_ids = request.client_ids
    ctx['nclients'] = len(client_ids)
    clients_interests = {}
    for cid in client_ids:
        clients_interests[cid] = scoring.get_interests(store, cid)
    return clients_interests, OK


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        'method': method_handler
    }
    store = Store(RedisCache())

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string.decode("utf-8"))
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r).encode())
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
