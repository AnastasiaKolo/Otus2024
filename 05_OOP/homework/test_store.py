""" Интеграционные тесты работы с хранилищем tarantool, реализованной в store.py """

import unittest

from store import KVStore


class KVStoreTestCase(unittest.TestCase):
    """ Тесты интеграции с хранилищем """
    store = None

    @classmethod
    def setUpClass(cls):
        """ Настройка подключения и запись тестовых данных """
        cls.store = KVStore(port=3301, host='localhost', spacename='test')
        cls.store.cache_set(1, '1')

    @classmethod
    def tearDownClass(cls):
        cls.store.connection.close()

    def test_is_alive(self):
        """ Тестируем проверку подключения """
        status = self.store.is_alive
        self.assertTrue(status)

    def test_get(self):
        """ Запрос тестовых данных """
        s = self.store.get(1)
        self.assertEqual(s, '1')

    def test_cache_get(self):
        """ Запрос тестовых данных из 'кеша' """
        s = self.store.cache_get(1)
        self.assertEqual(s, '1')


if __name__ == '__main__':
    unittest.main()
