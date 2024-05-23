"""
Модуль реализует web server
"""

import argparse
import logging

LOGGING_FORMAT = '[%(asctime)s] %(levelname).1s %(message)s'
LOGGING_DATEFMT = '%Y.%m.%d %H:%M:%S'
LOGGING_LEVEL = logging.INFO
LOGGING_FILE = None

logging.basicConfig(filename=LOGGING_FILE, level=LOGGING_LEVEL,
                    format=LOGGING_FORMAT, datefmt=LOGGING_DATEFMT)

HOST = '127.0.0.1'
PORT = 8080
DOCUMENT_ROOT = 'www'

OK = 200
NOT_FOUND = 404
FORBIDDEN = 403
BAD_REQUEST = 400
NOT_ALLOWED = 405
INTERNAL_SERVER_ERROR = 500
HTTP_VERSION_NOT_SUPPORTED = 505
HTML_ERROR = """<html>
<head>
<meta charset="UTF-8"> 
<title>{status} - {text}</title>
</head>
<body>
<h1>Error loading page</h1>
<h2>{status}</h2>
<p>{text}</p>
</body>
</html>
"""


class HTTPServer:
    """ Реализация веб сервера """
    def __init__(self, host, port, workers, document_root):
        self.host = host
        self.port = port
        self.workers = workers
        self.document_root = document_root

    def serve_forever(self):
        """ Обслуживание запросов """
        pass

    def server_close(self):
        pass


def get_params() -> dict:
    """ Обработка параметров командной строки """
    parser = argparse.ArgumentParser(description='Web Server')
    parser.add_argument("--host", "-h", dest="host", default=HOST, type=str)
    parser.add_argument("--port", "-p", dest="port", default=PORT, type=int)
    parser.add_argument('--workers', '-w', default=4, type=int)
    parser.add_argument('--documentroot', '-r', default=DOCUMENT_ROOT)
    args = parser.parse_args()
    return {
        'host': args.host,
        'port': args.port,
        'workers': args.workers,
        'document_root': args.documentroot,
    }


def main():
    """
    Читает параметры и вызывает дальнейшие действия в программе
    @return:
    """
    params = get_params()

    server = HTTPServer(**params)
    logging.info("Starting server at %s:%s", params.host, params.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server was stopped by user")
    except:  # pylint: disable=bare-except
        logging.exception("Unexpected error")
    server.server_close()


if __name__ == "__main__":
    main()
