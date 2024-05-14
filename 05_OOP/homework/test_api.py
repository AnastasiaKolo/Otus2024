"""Тесты для модуля api.py"""

import datetime
import functools
import hashlib
import unittest

import api
from store import KVStore


def cases(testcases):
    """ Декоратор для запуска кейса с разными тест-векторами """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in testcases:
                # tuple в случае нескольких аргументов функции
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)
        return wrapper
    return decorator


# @unittest.SkipTest
class RequestsTestCase(unittest.TestCase):
    """ Тесты запросов к API """
    store = None

    @classmethod
    def setUpClass(cls):
        """ Настройка подключения и запись тестовых данных """
        cls.store = KVStore(port=3301, host='localhost', spacename='test')
        cls.store.cache_set(1, '1')

    @classmethod
    def tearDownClass(cls):
        cls.store.connection.close()

    def setUp(self):
        self.headers = {}
        self.context = {}

    @staticmethod
    def add_auth(request, login):
        """ Добавляет поля аутентификации в запрос """
        account = "test"
        request["login"] = login
        if login == api.ADMIN_LOGIN:
            digest_data = datetime.datetime.now().strftime("%Y%m%d") + api.ADMIN_SALT
        else:
            request["account"] = account
            digest_data = account + login + api.SALT

        request["token"] = hashlib.sha512(digest_data.encode()).hexdigest()

    def get_response(self, request):
        """ Вызов обработчика запроса """
        return api.method_handler({"body": request, "headers": self.headers},
                                  self.context,
                                  self.store)

    def test_empty_request(self):
        """ Тестируем пустой запрос """
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)

    @cases([
        "123456",
        {"user": "admin"},
        {"aaa": "bbb"}
    ])
    def test_wrong_request(self, request):
        """ Тестируем неверный формат запроса """
        _, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)

    @unittest.SkipTest
    @cases([({"phone": "79001234567", "birthday": "01.01.2023", "gender": 1},
             3.0, ["phone", "birthday", "gender"]),
            ({"first_name": "Jack", "last_name": "Smith", "gender": 1},
             0.5, ["first_name", "last_name", "gender"]),
            ])
    def test_online_score_request(self, arguments, expected_score, expected_has):
        """ Тестируем корректный запрос онлайн скоринга """
        request = {"method": "online_score",
                   "arguments": arguments}
        self.add_auth(request, "user")
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        self.assertEqual(response["score"], expected_score)
        self.assertTrue(response["score"] > 0)
        self.assertEqual(self.context["has"], expected_has)

    @cases([{"phone": "71234567890", "birthday": "01.02.2022", "gender": 1}])
    def test_admin_request(self, arguments):
        """ Тестируем корректный запрос онлайн-скоринга с админским логином """
        request = {"method": "online_score",
                   "arguments": arguments}
        self.add_auth(request, api.ADMIN_LOGIN)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        # print("test_admin_request", request, response, code)
        self.assertEqual(response["score"], 42)
        self.assertEqual(self.context["has"], ["phone", "birthday", "gender"])

    @cases([{"client_ids": [1, 2, 3, 4, 5]},
           {"client_ids": [0]},
           {"client_ids": [3, 4, 5]}])
    def test_clients_interests_request(self, arguments):
        """ Тестируем запрос интересов клиентов """
        request = {"method": "clients_interests",
                   "arguments": arguments}
        self.add_auth(request, "user")
        _, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        self.assertEqual(self.context["nclients"], len(arguments["client_ids"]))


# pylint: disable=invalid-name
class FieldClassesTestCase(unittest.TestCase):
    """Тесты классов задающих разные типы полей """

    @cases(["01.01.2023", "01.01.2025", "31.12.1931"])
    def test_DateField_valid(self, date_to_check):
        """Тестирует функцию проверки даты в текстовом формате"""
        api.DateField().validate(date_to_check)

    @cases(["01.31.2023", "21.13.2023"])
    def test_DateField_invalid(self, date_to_check):
        """Тестирует функцию проверки даты в текстовом формате"""
        with self.assertRaises(expected_exception=ValueError):
            api.DateField().validate(date_to_check)

    @cases(["01.01.2023", "31.01.2000"])
    def test_BirthdayField_valid(self, date_to_check):
        """Тестирует функцию проверки даты в текстовом формате"""
        api.BirthDayField().validate(date_to_check)

    @cases(["01.01.1923", "01.01.2033"])
    def test_BirthdayField_invalid(self, date_to_check):
        """Тестирует функцию проверки дня рождения
        не принимает даты старше 70 лет назад
        не принимает даты в будущем"""
        with self.assertRaises(expected_exception=ValueError):
            api.BirthDayField().validate(date_to_check)

    @cases(["_usernam-123@server.mail.ru", "user@mail.ru"])
    def test_EmailField_valid(self, email):
        """Тестирует функцию проверки email"""
        api.EmailField().validate(email)

    @cases(["@server.mail.ru", "@@@@@mail.ru"])
    def test_EmailField_invalid(self, email):
        """Тестирует выдачу ошибок насчет некорректного email"""
        with self.assertRaises(expected_exception=ValueError):
            api.EmailField().validate(email)

    @cases(["", [], {}, None])
    def test_BaseField_nullable(self, value):
        """Тестирует проверку атрибута nullable,
        должна появляться ошибка """
        with self.assertRaises(expected_exception=ValueError):
            api.BaseField(nullable=False).validate(value)

        api.BaseField(nullable=True).validate(value)


class RequestsClassesTestCase(unittest.TestCase):
    """ Тесты классов, задающих разные типы запросов """

    def test_BaseRequest(self):
        """ Тест создания класса базового запроса """
        src_dict = {}
        req = api.BaseRequest(src_dict=src_dict)
        self.assertEqual(src_dict, req.__dict__)

    def test_ClientsInterestsRequest(self):
        """ Тест создания класса запроса интересов """
        req = api.ClientsInterestsRequest(src_dict={"client_ids": [1, 2, 3, 4]})
        self.assertEqual(req.client_ids, [1, 2, 3, 4])


if __name__ == '__main__':
    unittest.main()
