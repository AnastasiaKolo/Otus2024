""" Инициализация БД tarantool, используемой для тестов """

import tarantool


def main():
    """ Создание спейсов в БД """
    lua_code = r"""
        s = box.schema.space.create('test_scoring')
        s:format({
                 {name = 'key', type = 'string'},
                 {name = 'value', type = 'double'}
                 })
        s:create_index('primary', {type = 'tree', parts = {'key'}})
        
        s = box.schema.space.create('test_ci')
        s:format({
                 {name = 'key', type = 'string'},
                 {name = 'value', type = 'array'}
                 })
        s:create_index('primary', {type = 'tree', parts = {'key'}})
        """
    conn = tarantool.Connection('localhost', 3301)
    print("Connected to tarantool instance port 3301")
    conn.eval(lua_code, (1, 2))
    print("Initialized DB")


if __name__ == '__main__':
    main()
