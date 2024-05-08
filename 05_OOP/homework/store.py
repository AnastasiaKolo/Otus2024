""" Модуль для обращения к key-value хранилищу tarantool """
import tarantool


class KVStore:
    """ Класс для реализации основных функций работы с хранилищем """
    def __init__(self, port=3301, host='localhost', spacename='otus'):
        self._port = port
        self._host = host
        self._spacename = spacename
        self.connection = None
        self.space = None
        self.connect()

    def connect(self):
        try:
            self.connection = tarantool.connect(self._host, self._port)
            self.space = self.connection.space(self._spacename)
        except tarantool.error.NetworkError:
            print(f"Error connecting to tarantool service at {self._host, self._port}")
        except tarantool.error.SchemaError:
            print(f"There's no space with name '{self._spacename}'")

    def cache_set(self, key, value, time):
        pass

    def cache_get(self, key):
        pass

    def get(self, key):
        pass

    def set(self. key, value):
        pass


def main():
    """ Демо работы класса KVStore """
    store = KVStore(port=3301)



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



