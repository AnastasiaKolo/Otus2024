""" Клиент для тестов """

import argparse
import http.client
import socket


HOST = "127.0.0.1"
PORT = 80


def echo_client():
    """ Эхо-клиент для тестов """
    msg = b"Hello, world"
    print("starting echo client")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(msg)
        print(f"Sent message: {repr(msg)}")
        data = s.recv(1024)
    print(f"Received reply: {repr(data)}")


def http_client():
    """ http-клиент для тестов """
    print("starting http client")
    conn = http.client.HTTPConnection(HOST, PORT)
    conn.request("GET", "test%20space.html")
    r1 = conn.getresponse()
    print(r1.status, r1.reason)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Echo or http client")
    parser.add_argument("--type", "-t", default="echo", choices=["echo", "http"])
    args = parser.parse_args()
    if args.type == "echo":
        echo_client()
    else:
        http_client()
