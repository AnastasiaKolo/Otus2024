""" Модуль для обращения к key-value хранилищу tarantool """
import tarantool


class KVStore:
    """ Класс для реализации основных функций работы с хранилищем """

    # pylint: disable=too-many-arguments
    def __init__(self, port=3301, host='localhost', spacename='otus',
                 reconnect_attempts=3, timeout=20):
        self._port = port
        self._host = host
        self._spacename = spacename
        self._reconnect_attempts = reconnect_attempts
        self._timeout = timeout

        self.connection = None
        self.space = None

        self.connect()

    def connect(self):
        """ Подключение к хранилищу """
        try:
            self.connection = tarantool.connection.Connection(host=self._host, port=self._port,
                                                reconnect_max_attempts=self._reconnect_attempts,
                                                connection_timeout = self._timeout)
            self.space = self.connection.space(self._spacename)
            print(f"Connected to tarantool service at {self._host, self._port}")
        except tarantool.error.NetworkError:
            print(f"Error connecting to tarantool service at {self._host, self._port}")
            return False
        except tarantool.error.SchemaError:
            print(f"There's no space with name '{self._spacename}'")
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
            self.space.upsert((key, value, time), [("=", 1, value), ("=", 2, time)])

    def cache_get(self, key):
        """ Запрос из кеша """
        print(f"!!!!!store cache_get request, key {key}")
        if not self.is_alive:
            return None
        responce: tarantool.response.Response = self.space.select(key)
        if responce.rowcount == 1:
            return responce.data[0][1]
        return None

    def get(self, key):
        """ Запрос из хранилища """
        print(f"!!!!!store get request, key {key}, type {type(key)}")
        # responce: tarantool.response.Response = self.space.select(key)
        # if responce.rowcount == 1:
        #     return responce.data[0][1]
        return None

    def set(self, key, value):
        """ Запись в хранилище """
        self.space.upsert((key, value), [("=", 1, value)])


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
    # connection = tarantool.connect('localhost', 3303)
    # tester = connection.space('tester')
    #
    # # tester.insert((4, 'ABBA', 1972))
    # s = tester.select(4)
    # p = tester.select('Scorpions', index=1)
    # print(s, p)
    #
    # s = tester.select()
    # print(s)
    #
    # tester.update(4, [('=', 1, 'New group'), ('+', 2, 2)])
    #
    # s = tester.select(4)
    # print(s)
