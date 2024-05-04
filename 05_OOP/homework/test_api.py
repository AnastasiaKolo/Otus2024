"""Тесты для модуля api.py"""

import datetime
import hashlib
import unittest

import api


#@unittest.skip("temporary does not work")
class RequestsTestCase(unittest.TestCase):
    """ Тесты запросов к API """

    request_account = "test"
    user_login = "user"
    store = None

    @classmethod
    def setUpClass(cls):
        """ Настойка параметров для запросов """
        admin_data = datetime.datetime.now().strftime("%Y%m%d") + api.ADMIN_SALT
        cls.admin_token = hashlib.sha512(admin_data.encode()).hexdigest()
        user_data = cls.request_account + cls.user_login + api.SALT
        cls.user_token = hashlib.sha512(user_data.encode()).hexdigest()

    def setUp(self):
        self.headers = {}
        self.context = {}

    def get_response(self, request):
        """ Вызов обработчика запроса """
        return api.method_handler({"body": request, "headers": self.headers},
                                  self.context,
                                  self.store)

    def test_empty_request(self):
        """ Тестируем пустой запрос """
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)
        print("empty_request", self.context)

    def test_wrong_request(self):
        """ Тестируем неверный формат запроса """
        _, code = self.get_response("123456")
        self.assertEqual(api.INVALID_REQUEST, code)
        print("wrong_request", self.context)

    def test_online_score_request(self):
        """ Тестируем запрос онлайн скоринга """
        arguments = {"phone": "79001234567",
                     "email": "",
                     "first_name": "",
                     "last_name": "",
                     "birthday": "01.01.2023",
                     "gender": 1}
        request = {"account": self.request_account,
                   "login": self.user_login,
                   "method": "online_score",
                   "token": self.user_token,
                   "arguments": arguments}
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        self.assertEqual(response["score"], 3.0)
        self.assertEqual(self.context["has"], ["phone", "birthday", "gender"])

    def test_admin_request(self):
        """ Тестируем запрос с админским логином """
        arguments = {"phone": "",
                     "email": "",
                     "first_name": "",
                     "last_name": "",
                     "birthday": "",
                     "gender": 1}
        request = {"login": api.ADMIN_LOGIN,
                   "method": "online_score",
                   "token": self.admin_token,
                   "arguments": arguments}
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        self.assertEqual(response["score"], 42)
        self.assertEqual(self.context["has"], ["gender"])

    def test_clients_interests_request(self):
        """ Тестируем запрос интересов клиентов """
        arguments = {"client_ids": [1, 2, 3, 4, 5]}
        request = {"account": self.request_account,
                   "login": self.user_login,
                   "method": "clients_interests",
                   "token": self.user_token,
                   "arguments": arguments}
        _, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        self.assertEqual(self.context["nclients"], 5)

# pylint: disable=invalid-name
class FieldClassesTestCase(unittest.TestCase):
    """Тесты классов задающих разные типы полей """

    def test_DateField_valid(self):
        """Тестирует функцию проверки даты в текстовом формате"""
        dates_to_check = ["01.01.2023", "01.01.2025", "31.12.1931"]
        for dt in dates_to_check:
            api.DateField().validate(dt)

    def test_DateField_invalid(self):
        """Тестирует функцию проверки даты в текстовом формате"""
        with self.assertRaises(expected_exception=ValueError):
            api.DateField().validate("01.31.2023")

    def test_BirthdayField_valid(self):
        """Тестирует функцию проверки даты в текстовом формате"""
        dates_to_check = ["01.01.2023", "31.01.2000"]
        for dt in dates_to_check:
            api.BirthDayField().validate(dt)

    def test_BirthdayField_invalid(self):
        """Тестирует функцию проверки дня рождения
        не принимает даты старше 70 лет назад
        не принимает даты в будущем"""
        with self.assertRaises(expected_exception=ValueError):
            api.BirthDayField().validate("01.01.1923")
            api.BirthDayField().validate("01.01.2033")

    def test_EmailField_valid(self):
        """Тестирует функцию проверки email"""
        emails = ["_usernam-123@server.mail.ru", "user@mail.ru"]
        for email in emails:
            api.EmailField().validate(email)

    def test_EmailField_invalid(self):
        """Тестирует выдачу ошибок насчет некорректного email"""
        emails = ["@server.mail.ru", "@@@@@mail.ru"]
        with self.assertRaises(expected_exception=ValueError):
            for email in emails:
                api.EmailField().validate(email)

    def test_BaseField_nullable(self):
        """Тестирует проверку атрибута nullable """
        null_values = ["", [], {}, None]
        not_null_values = ["1", [1], {1: 2}]

        with self.assertRaises(expected_exception=ValueError):
            for value in null_values:
                api.BaseField(nullable=False).validate(value)

        for value in null_values:
            api.BaseField(nullable=True).validate(value)

        for value in not_null_values:
            api.BaseField(nullable=False).validate(value)


class RequestsClassesTestCase(unittest.TestCase):
    """ Тесты классов, задающих разные типы запросов """

    def test_BaseRequest(self):
        """ Тест создания класса базового запроса """
        src_dict = {}
        baserec = api.BaseRequest(src_dict=src_dict)
        self.assertEqual(src_dict, baserec.__dict__)

    def test_ClientsInterestsRequest(self):
        """ Тест создания класса запроса интересов """
        rec = api.ClientsInterestsRequest(src_dict={"client_ids": [1, 2, 3, 4]})
        print("ClientsInterestsRequest", str(rec))


if __name__ == '__main__':
    unittest.main()
