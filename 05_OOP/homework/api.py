#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль реализует декларативный язык описания и систему валидации запросов
к HTTP API сервиса скоринга
"""

import argparse
import json
import datetime
import logging
import hashlib
import re
import typing
import uuid

from http.server import BaseHTTPRequestHandler, HTTPServer

from scoring import get_score, get_interests

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

# pylint: disable=too-few-public-methods


class BaseField:
    """Базовый класс, реализующий проверки для разных типов полей """
    __template__ = None

    def __init__(self, required: bool = False, nullable: bool = True):
        self.required = required
        self.nullable = nullable

    def validate(self, value):
        """ Валидация объекта """
        if not value and not self.nullable:
            raise ValueError(f"Not nullable field {self.__class__.__name__} is empty!")

        if self.__template__ and value:
            if not re.match(self.__template__, str(value)):
                raise ValueError(f"Invalid value format {self.__class__.__name__}")

        return value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class CharField(BaseField):
    """ Проверка поля со строковыми значениями """
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, str):
            raise TypeError(f"Field {self.__class__.__name__} must be 'str' type.")

        return value


class EmailField(CharField):
    """ Строка, в которой есть @, опционально, может быть пустым """
    __template__ = r"^[a-zA-Z0-9\.\-\_]+@[a-zA-Z0-9\.\-\_]+\.[a-zA-Z0-9]+$"


class PhoneField(CharField):
    """ Строка или число, длиной 11, начинается с 7, опционально, может быть пустым """
    __template__ = r"^7\d{10}$"


class DateField(BaseField):
    """ Проверяет поле, в котором содержится дата """

    def validate(self, value):
        super().validate(value)
        if value:
            try:
                value = datetime.datetime.strptime(value, "%d.%m.%Y")
            except ValueError as exc:
                raise ValueError(f"Invalid date value in "
                                 f"{self.__class__.__name__}, 'dd.mm.yyyy' expected") from exc
        return value


class BirthDayField(DateField):
    """ Дата в формате DD.MM.YYYY,
    с которой прошло не больше 70 лет, опционально, может быть пустым """
    __valid_days_count__ = 365 * 70

    def validate(self, value):
        """ проверка валидности дня рождения """
        dt = super().validate(value)
        if dt:
            valid_age = datetime.timedelta(days=self.__valid_days_count__)
            diff = datetime.datetime.now() - dt

            if diff > valid_age or diff < datetime.timedelta(0):
                raise ValueError(f"Invalid {self.__class__.__name__} value! "
                                 f"Must be between 0 and 70 years ago")

        return dt


class GenderField(BaseField):
    """ Число 0, 1 или 2, опционально, может быть пустым """
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, int):
            raise TypeError(f"Field {self.__class__.__name__} must be 'int' type.")
        if value not in (0, 1, 2):
            raise ValueError(f"Number 0, 1 or 2 expected in {self.__class__.__name__}")

        return value


class ClientIDsField(BaseField):
    """ Массив чисел, обязательно, не пустое """

    def validate(self, value):
        super().validate(value)
        if not isinstance(value, list):
            raise ValueError(f"A list of integers expected, got {value}")
        for item in value:
            if not isinstance(item, int):
                raise ValueError(f"Integer value expected, got {item}")
        return value


class ArgumentsField(BaseField):
    """
    Словарь с аргументами вызываемого метода (объект в терминах json),
    обязательно, может быть пустым
    """
    def validate(self, value):
        super().validate(value)
        if not isinstance(value, dict):
            raise ValueError("A dict expected in " + self.__class__.__name__)
        return value


class BaseRequest:
    """ Вызов проверки и Заполнение аргументов базового запроса к серверу """
    def __init__(self, src_dict: dict):
        if not isinstance(src_dict, dict):
            raise ValueError("A Dict expected in " + self.__class__.__name__)

        class_fields = self.__class__.__dict__
        for key, field in class_fields.items():

            if isinstance(field, BaseField):
                # поля запросов сохраняются в словаре экземпляра этого класса
                if key not in src_dict:
                    if field.required:
                        raise ValueError(f"Required field {key} not found in "
                                         f"{self.__class__.__name__}")
                    self.__dict__[key] = None
                else:
                    self.__dict__[key] = self.__class__.__dict__[key].validate(src_dict[key])

    def __repr__(self) -> str:
        attrs_list: list[str] = [f"{key}: {value}" for key, value in self.__dict__.items()]
        attrs: str = ", ".join(attrs_list)
        return f"{self.__class__.__name__}({attrs})"

    @property
    def non_empty_fields_lst(self) -> typing.List[str]:
        """ Список непустых полей объекта """
        # print("non_empty_fields_lst", self.__dict__)
        return [key for key, value in self.__dict__.items() if value]


class ClientsInterestsRequest(BaseRequest):
    """ Аргументы метода clients_interests """
    client_ids = ClientIDsField(required=True)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(BaseRequest):
    """ Аргументы метода online_score """
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def is_valid(self):
        """ Аргументы валидны, если валидны все поля по отдельности
        и если присутствует хоть одна пара
        phone-email,
        first name-last name,
        gender-birthday с непустыми значениями """
        if any([self.phone and self.email,
                self.first_name and self.last_name,
                self.gender and self.birthday]):
            return True
        return False


class MethodRequest(BaseRequest):
    """ Основной запрос метода """
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=False)

    @property
    def is_admin(self):
        """ Проверка, что запрос от админа """
        return self.login == ADMIN_LOGIN

    def check_auth(self):
        """ Аутентификация """

        if self.is_admin:
            digest_data = datetime.datetime.now().strftime("%Y%m%d") + ADMIN_SALT
        else:
            digest_data = self.account + self.login + SALT
        digest = hashlib.sha512(digest_data.encode()).hexdigest()
        if digest == self.token:
            return True
        return False

    # pylint: disable=not-an-iterable
    def get_response_by_method(self, context, store) -> dict:
        """ Вызов одного из методов скоринга """
        if self.method == "online_score":
            online_score = OnlineScoreRequest(src_dict=self.arguments)
            if not online_score.is_valid():
                raise ValueError("Invalid online_score request arguments")
            score = 42 if self.is_admin else get_score(**online_score.__dict__, store=store)
            context["has"] = online_score.non_empty_fields_lst
            return {"score": score}

        if self.method == "clients_interests":
            interests = ClientsInterestsRequest(src_dict=self.arguments)
            context["nclients"] = len(interests.client_ids)
            return {cid: get_interests(store=store, cid=cid) for cid in interests.client_ids}

        raise ValueError(f"Invalid method {self.method}")


def method_handler(request, context, store):
    """ Обработчик вызываемых методов """
    try:
        request_body = request.get("body", {})
        method_request = MethodRequest(src_dict=request_body)
        if method_request.check_auth():
            response = method_request.get_response_by_method(context, store)
            code = OK
        else:
            response, code = "Invalid authorization", FORBIDDEN
    except ValueError as err:
        response, code = err, INVALID_REQUEST
    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    """ Обработчик http запросов к сервису """
    router = {
        "method": method_handler
    }
    store = None

    def get_request_id(self, headers):
        """ get_request_id """
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    # pylint: disable=invalid-name
    def do_POST(self):
        """ пользователи дергают методы POST запросами """
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        data_string = ""
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logging.exception("BAD_REQUEST: %s", exc)
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s", self.path, data_string, context["request_id"])
            if path in self.router:
                try:
                    response, code = self.router[path](
                        {"body": request,
                         "headers": self.headers},
                        context,
                        self.store)
                except ValueError as value_error:
                    response = str(value_error)
                    code = INVALID_REQUEST
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logging.exception("INTERNAL_ERROR: %s", e)
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


def main():
    """
    Читает параметры и вызывает дальнейшие действия в программе
    @return:
    """
    parser = argparse.ArgumentParser(description='Scoring API')
    parser.add_argument("--port", "-p", dest="port", default=8080, type=int)
    parser.add_argument("--log", "-l", dest="log", default=None, type=str)
    args = parser.parse_args()

    logging.basicConfig(filename=args.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')

    server = HTTPServer(("localhost", args.port), MainHTTPHandler)
    logging.info("Starting server at %s", args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server was stopped by user")
    except:  # pylint: disable=bare-except
        logging.exception("Unexpected error")
    server.server_close()


if __name__ == "__main__":
    main()
