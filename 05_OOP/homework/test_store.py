""" Интеграционные тесты работы с хранилищем tarantool, реализованной в store.py """

import unittest

from store import KVStore


class KVStoreTestCase(unittest.TestCase):
    """ Тесты интеграции с хранилищем """
    store = None
    test_uid = 'uid:889898'
    test_cid = 'i:123'

    @classmethod
    def setUpClass(cls):
        """ Настройка подключения и запись тестовых данных """
        cls.store = KVStore(port=3301, host='localhost')
        cls.store.cache_set(cls.test_uid, 1.5)
        cls.store.set(cls.test_cid, [3, 4, 5])

    @classmethod
    def tearDownClass(cls):
        cls.store.connection.close()

    def test_is_alive(self):
        """ Тестируем проверку подключения """
        status = self.store.is_alive
        self.assertTrue(status)

    def test_get(self):
        """ Запрос тестовых данных """
        s = self.store.get(self.test_cid)
        self.assertEqual(s, [3, 4, 5])

    def test_cache_get(self):
        """ Запрос тестовых данных из 'кеша' """
        s = self.store.cache_get(self.test_uid)
        self.assertEqual(s, 1.5)


if __name__ == '__main__':
    unittest.main()
