""" Модуль для обращения к key-value хранилищу tarantool """
import tarantool


class KVStore:
    """ Класс для реализации основных функций работы с хранилищем """
    _store_name = 'test_ci'  # space в tarantool где реализован store
    _cache_name = 'test_scoring'  # space в tarantool где реализован cache

    def __init__(self, port=3301, host='localhost',
                 reconnect_attempts=3, timeout=20):
        self._port = port
        self._host = host
        self._reconnect_attempts = reconnect_attempts
        self._timeout = timeout
        self.connection = None
        self.cache_space = None
        self.store_space = None

        self.connect()
        self.init_cache()
        self.init_store()

    def connect(self):
        """ Подключение к хранилищу """
        try:
            self.connection = tarantool.connection.Connection(
                host=self._host, port=self._port,
                reconnect_max_attempts=self._reconnect_attempts,
                connection_timeout=self._timeout)
            print(f"Connected to tarantool service at {self._host, self._port}")
        except tarantool.error.NetworkError:
            print(f"Error connecting to tarantool service at {self._host, self._port}")
            return False
        return True

    def init_cache(self):
        """ Подключение к спейсу в тарантул где живет кеш """
        if self.is_alive:
            try:
                self.cache_space = self.connection.space(self._cache_name)
            except tarantool.error.SchemaError:
                print(f"There's no space with name '{self._cache_name}'")
                return False
            return True
        return False

    def init_store(self):
        """ Подключение к спейсу в тарантул где живет store """
        try:
            self.store_space = self.connection.space(self._store_name)
        except tarantool.error.SchemaError:
            print(f"There's no space with name '{self._store_name}'")
            return False
        return True

    @property
    def is_alive(self):
        """ Проверка подключения """
        if not self.connection:
            return False
        status = self.connection.ping(notime=True)
        if status == "Success":
            return True
        return False

    def cache_set(self, key, value, time=30):
        """ Запись в кеш
        если значение с этим ключом там есть, меняем значение """
        if self.is_alive:
            self.cache_space.upsert((key, value, time), [("=", 1, value), ("=", 2, time)])

    def cache_get(self, key):
        """ Запрос из кеша """
        if not self.is_alive:
            return None
        responce: tarantool.response.Response = self.cache_space.select(key)
        if responce.rowcount == 1:
            return responce.data[0][1]
        return None

    def get(self, key):
        """ Запрос из хранилища """
        responce: tarantool.response.Response = self.store_space.select(key)
        if responce.rowcount == 1:
            return responce.data[0][1]
        return None

    def set(self, key, value):
        """ Запись в хранилище """
        self.store_space.upsert((key, value), [("=", 1, value)])


def main():
    """ Демо работы класса KVStore """
    store = KVStore(port=3301)
    data = store.cache_get(1)
    print("Данные из кеша (1):", data)
    store.cache_set(12, '12', 30)
    data = store.cache_get(12)
    print("Данные из кеша (12):", data)

if __name__ == '__main__':
    main()
