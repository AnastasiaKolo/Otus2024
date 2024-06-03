""" Модуль реализует web server c многопоточной архитектурой """

import argparse
import logging
import mimetypes
import os

import threading
import time

from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from urllib.parse import unquote


LOGGING_FORMAT = "[%(asctime)s] %(levelname).1s %(message)s"
LOGGING_DATEFMT = "%Y.%m.%d %H:%M:%S"
LOGGING_LEVEL = logging.DEBUG
LOGGING_FILE = None

logging.basicConfig(filename=LOGGING_FILE, level=LOGGING_LEVEL,
                    format=LOGGING_FORMAT, datefmt=LOGGING_DATEFMT)

HOST = "127.0.0.1"
PORT = 8080
DOCUMENT_ROOT = "09_Authomatization_network\\homework\\www"
INDEX = "index.html"
ENCODING = "utf-8"

OK = 200
NOT_FOUND = 404
FORBIDDEN = 403
BAD_REQUEST = 400
NOT_ALLOWED = 405
INTERNAL_SERVER_ERROR = 500
HTTP_VERSION_NOT_SUPPORTED = 505
MESSAGES = {
    OK: "OK",
    NOT_FOUND: "NOT_FOUND",
    FORBIDDEN: "FORBIDDEN",
    BAD_REQUEST: "BAD_REQUEST",
    NOT_ALLOWED: "NOT_ALLOWED",
    INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
    HTTP_VERSION_NOT_SUPPORTED: "HTTP_VERSION_NOT_SUPPORTED"
}
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


class EchoServer:
    """ Base class TCP Echo Server """
    def __init__(self, host: str, port: int, workers: int, stop_event: threading.Event):
        self.address = (host, port)
        self.read_size = 1024
        self.workers = workers
        self.opened_threads = []
        self.sock: socket = None
        self.stop_event = stop_event

    def start(self):
        """ Try to open the socket and start server threads"""
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        try:
            logging.info("Starting HTTP server on %s...", self.address)
            self.sock.bind(self.address)
        except OSError:
            logging.exception("Failed to bind socket")
            return
        logging.info("Listening port %s", str(self.address[1]))
        logging.info("Press Ctrl+C to shut down the server and exit.")
        for key in range(self.workers):
            logging.info("Starting worker thread %s", key)
            t = threading.Thread(target=self.listen, args=(key,))
            t.start()
            self.opened_threads.append(t)
        logging.debug("All threads started")

    def listen(self, worker_key):
        """ Listen to incoming connections """
        self.sock.listen(5)
        self.sock.settimeout(1)
        while not self.stop_event.is_set():
            # logging.debug("Worker %s: accepting connections", worker_key)
            try:
                client, _ = self.sock.accept()
                client.settimeout(1)
                self.serve_client(client, worker_key)
            except OSError:
                pass  # timeout expired

    def serve_client(self, client, worker_key):
        """ Responding to client request """
        try:
            data = self.read(client)
            logging.debug("Worker %s received: %s", worker_key, data)
            if data:
                response = self.get_response(data)
                client.sendall(response)
                logging.debug("Worker %s has sent response %s", worker_key, response)
                client.close()
            else:
                logging.debug("Worker %s: Client disconnected", worker_key)
        except TimeoutError:
            logging.info("Worker %s: timed out waiting for request", worker_key)
            client.close()
        except OSError:
            logging.exception("Error serving client in worker thread %s", worker_key)
            client.close()

    def read(self, client):
        """ Receive data from socket"""
        data = client.recv(self.read_size)
        return data

    def get_response(self, data: bytes) -> bytes:
        """ Simple version returning echo response """
        return data

    def shutdown(self):
        """ Stop all threads and close the socket """
        try:
            logging.info("Shutting down the server")
            for th in self.opened_threads:
                th.join(timeout=2)
                logging.debug("Joined thread %s", th.name)
        except OSError:
            logging.exception("Could not shut down the socket. Maybe it was already closed")


class HTTPServer(EchoServer):
    """ Added methods to read and parse requests, prepare and send responses """
    maxsize = 65536
    supported_methods = ("GET", "HEAD")

    # pylint: disable=too-many-arguments
    def __init__(self, host, port, workers, stop_event, document_root):
        super().__init__(host, port, workers, stop_event)
        self.method = ""
        self.path = ""
        self.status = 0
        self.document_root = document_root
        self.response_headers = b"empty_header"  # for debug
        self.response_body = b"empty_body"

    def read(self, client):
        data = bytearray()
        while b"\r\n\r\n" not in data:
            data += client.recv(self.read_size)
            if not data or len(data) > self.maxsize:
                self.status = BAD_REQUEST
                break
        return data

    def get_response(self, data: bytes) -> bytes:
        if self.parse_request(data):
            self.analyze_request()
        if self.status == OK and self.method == "GET":
            self.get_html_file()
        logging.debug("Preparing headers... Status=%s", self.status)
        self.get_response_headers()
        if self.method == "GET":
            return self.response_headers + self.response_body + b"\r\n\r\n"
        return self.response_headers  # HEAD request

    def parse_request(self, data: bytes) -> bool:
        """ Парсинг запроса """
        request_str = data.decode("iso-8859-1")
        try:
            request_str, _ = request_str.split("\r\n", maxsplit=1)
            method, path, protocol = request_str.strip().split(" ")
        except ValueError:
            logging.error("Unable to parse request headers '%s'", request_str)
            self.status = BAD_REQUEST
            return False
        self.method = method.upper()
        path = unquote(path)
        self.path = os.path.join(os.path.abspath(os.getcwd()),
                                 self.document_root,
                                 path.lstrip("/"))
        logging.debug("Path %s", self.path)
        logging.info("Parsed request method=%s, path=%s, protocol=%s",
                     self.method, self.path, protocol)
        return True

    def analyze_request(self):
        """ Подготовка ответа """
        if self.method not in self.supported_methods:
            logging.error("Method not supported: %s", self.method)
            self.status = NOT_ALLOWED
        else:
            if os.path.isdir(self.path):
                logging.debug("Found requested dir")
                self.path = os.path.join(self.path, INDEX)
            if os.path.isfile(self.path):
                logging.debug("Found requested file")
                self.status = OK
            else:
                self.status = NOT_FOUND
        logging.debug("Analyzed request. Status=%s", self.status)

    def get_html_file(self) :
        """ Read file for GET request """
        logging.debug("Reading file...Status=%s", self.status)
        try:
            with open(self.path, "rb") as f:
                self.response_body = f.read()
        except OSError:
            logging.exception("Error reading file %s", self.path)
            self.status = INTERNAL_SERVER_ERROR

    def get_response_headers(self):
        """ Упаковка заголовков ответа для отправки """
        response_headers = {
            "Date": time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()),
            "Server": "Otus homework web server",
            "Connection": "close",
            "Content-Type": "text/html; charset='utf8'",
            "Content-Length": 0
        }
        message = MESSAGES.get(self.status)
        if self.status != OK:
            self.response_body = HTML_ERROR.format(status=self.status,
                                                   text=message).encode("utf-8")
        else:
            response_headers["Content-Length"] = os.path.getsize(self.path)
            _, extension = os.path.splitext(self.path)
            response_headers["Content-Type"] = mimetypes.types_map.get(extension)
        headers = f"HTTP/1.1 {self.status} {message}\r\n"
        for name, value in response_headers.items():
            headers += f"{name}: {value}\r\n"
        headers += "\r\n"
        self.response_headers = headers.encode("utf-8")


def get_params() -> argparse.Namespace:
    """ Get and parse command string parameters """
    parser = argparse.ArgumentParser(description="Web Server")
    parser.add_argument("--ip", "-i", default=HOST, type=str)
    parser.add_argument("--port", "-p", default=PORT, type=int)
    parser.add_argument("--workers", "-w", default=2, type=int)
    parser.add_argument("--documentroot", "-r", default=DOCUMENT_ROOT)
    args = parser.parse_args()
    return args


def main():
    """ Get parameters and start server """
    params = get_params()
    stop_event = threading.Event()
    server = HTTPServer(params.ip, params.port, params.workers, stop_event, params.documentroot)
    try:
        server.start()
        while not stop_event.is_set():
            time.sleep(0.5)
            # logging.debug("Main thread")
    except KeyboardInterrupt:
        logging.debug("KeyboardInterrupt signal received!")
        stop_event.set()
        time.sleep(0.5)
        server.shutdown()
        logging.info("Server was stopped by user")
    except:  # pylint: disable=bare-except
        logging.exception("Unexpected error")


if __name__ == "__main__":
    main()
