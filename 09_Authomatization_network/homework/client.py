""" Клиент для тестов """

#import socket

import http.client


HOST = '127.0.0.1'
PORT = 8080

#""" Эхо-клиент для тестов """
# with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
#     s.connect((HOST, PORT))
#     s.sendall(b"Hello, world")
#     data = s.recv(1024)
# print(f"Received reply: {repr(data)}")

conn = http.client.HTTPConnection(HOST, PORT)
conn.request("GET", "/")
r1 = conn.getresponse()
print(r1.status, r1.reason)
