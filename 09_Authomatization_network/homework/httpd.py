"""
Модуль реализует web server
"""

import argparse
import logging
import select

import http.server

from socket import socket, AF_INET, SOCK_STREAM


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


class Worker:
    """ Обработчик запросов """

    def __init__(self):
        self.raw_out = b""  # outgoing message to the client
        self.raw_in = b""

    def __str__(self):
        """ Представление в виде строки """
        return f"raw_out ({self.raw_out}), raw_in ({self.raw_in})"

    def work(self):
        """ Обработка запросов """
        if self.raw_in:
            self.parse_request()
            self.raw_out = self.raw_in
            self.raw_in = b''


    def parse_request(self):
        request_str = str(self.raw_in, 'iso-8859-1')
        words = request_str.split('\r\n')
        for c in words:
            print(c)


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
                    self.workers[client] = Worker()

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
                logging.info("'%s' sent to client",
                             worker.raw_out)
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
        pass


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
