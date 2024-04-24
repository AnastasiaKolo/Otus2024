"""Тесты для модуля log_analyzer.py"""

import datetime
import os
import unittest

from collections import namedtuple
from unittest.mock import patch, mock_open

import log_analyzer

from log_analyzer import NGINX_LOG_NAME


class MyTestCase(unittest.TestCase):
    """Тесты отдельных функций скрипта"""

    def test_read_config_file(self):
        """Тестирует функцию в которой читается конфиг из файла и объединяется с дефолтным"""
        mock_file_path = "mock/file/path"
        mock_file_content = '{"REPORT_SIZE": 500, "LOG_DIR": "./logs_test"}'
        # pylint: disable=format-string-without-interpolation
        # pylint: disable=consider-using-f-string
        patched_file = patch('log_analyzer.open'.format(__name__, 'rt'),
                             new=mock_open(read_data=mock_file_content))

        with patched_file as mock_file:
            actual = log_analyzer.read_config_file(mock_file_path)
            mock_file.assert_called_once_with(mock_file_path, 'rt', encoding='utf-8')

        expected = {
            "REPORT_SIZE": 500,
            "REPORT_DIR": "./report",
            "LOG_DIR": "./logs_test",
            "LOG_FILE": None,
            "ERROR_LIMIT": 0.8
        }

        self.assertEqual(expected, actual)

    def test_validate_date(self):
        """Тестирует функцию проверки даты в текстовом формате"""
        self.assertEqual(log_analyzer.validate_date("20230303"), datetime.date(2023, 3, 3))
        self.assertEqual(log_analyzer.validate_date("20233303"), None)
        self.assertNotEqual(log_analyzer.validate_date("20233303"), datetime.date(2023, 3, 2))

    def test_find_last_nginx_log(self):
        """
        Тестирует функцию нахождения последнего по дате лога,
        проверяя что дата в имени файла корректная
        """
        with patch('os.listdir') as mocked_listdir:
            with patch('os.path.isdir') as mocked_isdir:
                mocked_listdir.return_value = ['nginx-access-ui.log-20230303',
                                               'nginx-access-ui.log-20230329.gz',
                                               'nginx-access-ui.log-20240329.bz2']
                mocked_isdir.return_value = True
                actual = log_analyzer.find_last_nginx_log('logs', NGINX_LOG_NAME)
                fname = namedtuple("LogFile", "path, date, ext")
                expected = fname(path=os.path.join("logs", "nginx-access-ui.log-20230329.gz"),
                                 date=datetime.date(2023, 3, 29),
                                 ext='gz')

                self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
