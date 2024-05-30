"""
Модуль реализует web server
"""

import argparse
import json
import logging
import mimetypes
import os
import select

#from os.path import isfile, isdir, join, getsize, splitext, normpath
from socket import socket, AF_INET, SOCK_STREAM
from time import strftime, localtime

LOGGING_FORMAT = "[%(asctime)s] %(levelname).1s %(message)s"
LOGGING_DATEFMT = "%Y.%m.%d %H:%M:%S"
LOGGING_LEVEL = logging.INFO
LOGGING_FILE = None

logging.basicConfig(filename=LOGGING_FILE, level=LOGGING_LEVEL,
                    format=LOGGING_FORMAT, datefmt=LOGGING_DATEFMT)

HOST = "127.0.0.1"
PORT = 8080
DOCUMENT_ROOT = "www"
INDEX = 'index.html'

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

# class Request:
#     """ Парсинг запроса """
#     maxsize = 65536


# pylint: disable=too-many-instance-attributes
class Worker:
    """ Обработчик запросов """
    maxsize = 65536
    supported_methods = ('GET', 'HEAD')

    def __init__(self, document_root: str):
        self.raw_out = b''  # outgoing message to the client
        self.raw_in = b''
        self.method = ''
        self.path = ''
        self.request_protocol = ''
        self.status = 0
        self.document_root = document_root
        self.response_body = b''
        logging.info('Initialized worker')

    def __str__(self):
        """ Представление в виде строки """
        return f"raw_out ({self.raw_out}), raw_in ({self.raw_in})"

    def work(self):
        """ Обработка запросов """
        if self.raw_in:
            if self.parse_request():
                self.make_response()
            self.raw_out = self.pack_response()
            self.raw_in = b''
        else:
            logging.debug("Empty request given")

    def parse_request(self) -> bool:
        """ Парсинг запроса """
        request_str = str(self.raw_in, "iso-8859-1")
        if len(request_str) > self.maxsize:
            self.status = BAD_REQUEST
            return False
        request_str, _ = request_str.split("\r\n", maxsplit=1)
        try:
            method, path, protocol = request_str.strip().split(' ')
        except ValueError:
            logging.error("Unable to parse request headers '%s'", request_str)
            self.status = BAD_REQUEST
            return False
        self.method = method.upper()
        self.path = os.path.join(self.document_root, os.path.normpath(path.strip("?").lstrip("/")))
        self.request_protocol = protocol
        logging.info("Incoming request method=%s, path=%s, protocol=%s",
                     self.method, self.path, protocol)
        return True

    def make_response(self):
        """ Подготовка ответа """
        if self.method not in self.supported_methods:
            logging.error("Method not supported: %s", self.method)
            self.status = NOT_ALLOWED
        elif os.path.isfile(self.path):
            self.response_body = self.path
            self.status = OK
            logging.debug("Sending file: %s", self.path)
        elif os.path.isdir(self.path):
            index_file = os.path.join(self.path, INDEX)
            if os.path.isfile(index_file):
                self.response_body = index_file
                self.status = OK
        self.status = NOT_FOUND

    def pack_response(self) -> bytes:
        """ Упаковка ответа для отправки """
        response_headers = {
            'Date': strftime("%a, %d %b %Y %H:%M:%S", localtime()),
            'Server': 'Otus homework web server',
            'Connection': 'close',
            'Content-Type': 'text/html; charset="utf8"',
            'Content-Length': 0
        }
        if self.response_body:
            response_headers['Content-Length'] = os.path.getsize(self.response_body)
            _, extension = os.path.splitext(self.path)
            content_type = mimetypes.types_map.get(extension)
            if content_type:
                response_headers['Content-Type'] = content_type
        response = json.dumps(response_headers)
        return response.encode('utf-8') + self.response_body


class HTTPServer:
    """ Реализация веб сервера """
    def __init__(self, host, port, workers, document_root):
        self.address = (host, port)
        self.workers = workers
        self.document_root = document_root
        self.sock = self.listen_socket()
        self.clients = []  # list of currently connected client sockets
        self.workers = {}  # dictionary, key = client, value = worker workers for each socket

    def serve_forever(self):
        """ Обслуживание запросов """
        try:
            while True:
                try:
                    client, addr = self.sock.accept()  # connect new clients
                except OSError:
                    pass  # timeout expired
                else:
                    logging.info("Incoming connection %s",  str(addr))
                    self.clients.append(client)
                    self.workers[client] = Worker(self.document_root)

                finally:
                    r, w, e = [], [], []
                    try:
                        r, w, e = select.select(self.clients, self.clients, [], 0)
                    except OSError:
                        pass  # timeout
                    for sock in e:  # sockets disconnected
                        self.disconnect_client(sock)
                    for sock in r:  # sockets that can be read
                        self.receive_data(sock)
                    for sock in self.clients:  # serving current clients
                        self.process_data(sock)
                    for sock in w:  # sockets that can be written to
                        self.send_data(sock)
        except KeyboardInterrupt:
            logging.info("Shutting down")
            self.server_close()

    def disconnect_client(self, client_socket):
        """ Отсоединение клиента """
        client_socket.close()
        if client_socket in self.clients:
            self.clients.remove(client_socket)
        if client_socket in self.workers:
            self.workers.pop(client_socket)

    def process_data(self, client_socket):
        """ Вызов обработчика для клиента """
        if self.workers[client_socket].raw_in:
            self.workers[client_socket].work()

    def receive_data(self, client_socket):
        """ Получение данных """
        try:
            total_data = b''
            while True:
                data = client_socket.recv(1024)
                total_data += data
                if not data or len(data) < 1024:
                    break
            if total_data:
                self.workers[client_socket].raw_in = total_data
        except ConnectionError:
            logging.error("Client disconnected in receive_data")
            self.disconnect_client(client_socket)

    def send_data(self, client_socket):
        """ Отправка данных """
        try:
            worker = self.workers[client_socket]
        except KeyError:
            # client has already disconnected, nobody to send data
            logging.debug("Worker not found for %s", client_socket)
            return
        if worker.raw_out:
            logging.debug("Sending Worker raw_out")
            try:
                client_socket.send(worker.raw_out)
                logging.info("Response sent to client")
                worker.raw_out = b""
            except ConnectionError:  # Сокет недоступен, клиент отключился
                logging.info("Client %s disconnected in send_data",
                             self.workers[client_socket])
                self.disconnect_client(client_socket)

    def listen_socket(self):
        """ Открытие сокета """
        sock = socket(AF_INET, SOCK_STREAM)
        sock.bind(self.address)
        sock.listen(5)
        # Таймаут для операций с сокетом
        # Таймаут необходим, чтобы не ждать появления данных в сокете
        sock.settimeout(0.2)
        logging.info("Listening port %s", str(self.address[1]))
        return sock

    def server_close(self):
        """ Остановка сервера """
        for client in self.clients:
            self.disconnect_client(client)


def get_params() -> argparse.Namespace:
    """ Обработка параметров командной строки """
    parser = argparse.ArgumentParser(description='Web Server')
    parser.add_argument("--ip", "-i", default=HOST, type=str)
    parser.add_argument("--port", "-p", default=PORT, type=int)
    parser.add_argument('--workers', '-w', default=4, type=int)
    parser.add_argument('--documentroot', '-r', default=DOCUMENT_ROOT)
    args = parser.parse_args()
    return args


def main():
    """
    Читает параметры и вызывает дальнейшие действия в программе
    @return:
    """
    params = get_params()

    server = HTTPServer(params.ip, params.port, params.workers, params.documentroot)
    logging.info("Starting server at %s:%s", params.ip, params.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server was stopped by user")
    except:  # pylint: disable=bare-except
        logging.exception("Unexpected error")
    server.server_close()


if __name__ == "__main__":
    main()
