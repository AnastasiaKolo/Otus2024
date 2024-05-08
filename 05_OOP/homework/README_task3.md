# 05.OOP homework - Scoring API

Программа реализует декларативный язык описания и систему валидации запросов к HTTP API сервиса скоринга.

## Использование

Укажите параметры конфигурации командной строке. 

python api.py --port PORT --log LOG

| Name        | Description                           | Default value          |
|-------------|---------------------------------------|------------------------|
| PORT        | Порт для запуска сервиса              | 8080                   |
| LOG         | Имя файла лога работы данного скрипта | None (вывод в консоль) |

Пример запроса для проверки работы приложения:
curl -X POST http://127.0.0.1:8080/method/ -H "Content-Type: application/json"  -d "{\"account\": \"test\", \"login\": \"user\", \"method\": \"clients_interests\",\"token\": \"b82cd0fc71ab4c300d0a36ed8d570d64d0292ad317035be13142aa737a2190493a80cde46ae01961e1fbad1250fe6877c391a6631d232a0b723c9cd168c6c5aa\", \"arguments\": {\"client_ids\": [1,2,3,4], \"date\": \"20.07.2017\"}}"
{"response": {"1": ["pets", "cinema"], "2": ["music", "otus"], "3": ["otus", "pets"], "4": ["music", "geek"]}, "code": 200}

## Тестирование

```bash
python test_api.py
```
