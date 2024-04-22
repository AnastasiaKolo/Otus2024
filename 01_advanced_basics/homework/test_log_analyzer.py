import datetime
import unittest
import log_analyzer

from collections import namedtuple
from unittest.mock import patch, mock_open

from log_analyzer import DEFAULT_CONFIG, NGINX_LOG_NAME, TMPL_LOG_STRING


class MyTestCase(unittest.TestCase):

    def test_read_config_file(self):
        mock_file_path = "mock/file/path"
        mock_file_content = '{"REPORT_SIZE": 500, "LOG_DIR": "./logs_test"}'

        with patch('log_analyzer.open'.format(__name__, 'rt'), new=mock_open(read_data=mock_file_content)) as mock_file:
            actual = log_analyzer.read_config_file(mock_file_path)
            mock_file.assert_called_once_with(mock_file_path, 'rt')

        expected = {
            "REPORT_SIZE": 500,
            "REPORT_DIR": "./report",
            "LOG_DIR": "./logs_test",
            "LOG_FILE": None,
            "ERROR_LIMIT": 0.8
        }

        self.assertEqual(expected, actual)

    def test_validate_date(self):
        self.assertEqual(log_analyzer.validate_date("20230303"), datetime.date(2023, 3, 3))
        self.assertEqual(log_analyzer.validate_date("20233303"), None)
        self.assertNotEqual(log_analyzer.validate_date("20233303"), datetime.date(2023, 3, 2))

    def test_find_last_nginx_log(self):
        with patch('os.listdir') as mocked_listdir:
            with patch('os.path.isdir') as mocked_isdir:
                mocked_listdir.return_value = ['nginx-access-ui.log-20230303',
                                               'nginx-access-ui.log-20230329.gz',
                                               'nginx-access-ui.log-20240329.bz2']
                mocked_isdir.return_value = True
                actual = log_analyzer.find_last_nginx_log('logs', NGINX_LOG_NAME)
                fname = namedtuple("LogFile", "path, date, ext")
                expected = fname(path="logs\\nginx-access-ui.log-20230329.gz",
                                 date=datetime.date(2023, 3, 29),
                                 ext='gz')

                self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
