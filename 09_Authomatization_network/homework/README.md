Задание по курсу Python
Web-сервер, частично реализующий протокол HTTP

## Использование

Запуск сервера: python httpd.py

Опциональные параметры конфигурации:

| Имя                     | Описание                                     | Значение по умолчанию |
|-------------------------|----------------------------------------------|-----------------------|
| --ip, -i                | ip адрес на котором будет запущен веб сервер | 127.0.0.1             |
| --port, -p              | порт на котором будет запущен веб сервер     | 8080                  |
| --workers, -w           | количество воркеров запускаемых веб сервером | 4                     |
| --documentroot, -r      | корневая директория для веб сервера          | www                   |

Пример запроса для проверки работы приложения:
curl -X GET http://127.0.0.1:8080/

# Использованная архитектура
Multithreading

# Результаты теста httptest.py
directory index file exists ... ok
document root escaping forbidden ... ok
Send bad http headers ... ok
file located in nested folders ... ok
absent file returns 404 ... ok
urlencoded filename ... ok
file with two dots in name ... ok
query string after filename ... ok
slash after filename ... ok
filename with spaces ... ok
Content-Type for .css ... ok
Content-Type for .gif ... ok
Content-Type for .html ... ok
Content-Type for .jpeg ... ok
Content-Type for .jpg ... ok
Content-Type for .js ... ok
Content-Type for .png ... ok
Content-Type for .swf ... ok
head method support ... ok
directory index file absent ... ok
large file downloaded correctly ... ok
post method forbidden ... ok
Server header exists ... ok

----------------------------------------------------------------------
Ran 23 tests in 42.938s

# Результаты нагрузочного тестирования

c:\Apache24\bin>ab -n 50000 -c 100 -r http://localhost:80/index.html
This is ApacheBench, Version 2.3 <$Revision: 1913912 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        Otus
Server Hostname:        localhost
Server Port:            80

Document Path:          /index.html
Document Length:        142 bytes

Concurrency Level:      100
Time taken for tests:   1526.102 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      14650000 bytes
HTML transferred:       7100000 bytes
Requests per second:    32.76 [#/sec] (mean)
Time per request:       3052.203 [ms] (mean)
Time per request:       30.522 [ms] (mean, across all concurrent requests)
Transfer rate:          9.37 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0   30 119.4      0     545
Processing:     0 3015 389.5   3161    5181
Waiting:        0 1660 833.8   1612    4220
Total:          0 3045 391.0   3176    5181

Percentage of the requests served within a certain time (ms)
  50%   3176
  66%   3213
  75%   3228
  80%   3239
  90%   3623
  95%   3719
  98%   3757
  99%   4136
 100%   5181 (longest request)

c:\Apache24\bin>
