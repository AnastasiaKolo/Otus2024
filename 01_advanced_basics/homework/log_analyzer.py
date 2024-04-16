#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import json
import logging

import os.path


from json.decoder import JSONDecodeError

# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '  
#                     '$request_time';

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LOG_FILE": None
}

logger = logging.getLogger(__name__)


def logging_config(log_path=None):
    """
    настройка логирования
    @param log_path: путь к файлу лога
    @return:
    """
    logging.basicConfig(level=logging.INFO, filename=log_path, datefmt='%Y.%m.%d %H:%M:%S',
                        format="[%(asctime)s] %(levelname).1s %(message)s")


def is_valid_file(parser, arg):
    """
    проверка что файл переданный в параметрах вызова, существует
    @param parser: ссылка на парсер аргументов
    @param arg: аргумент для проверки
    @return: возвращает аргумент, если он корректный. Иначе ошибка
    """
    if not os.path.exists(arg):
        parser.error(f"The file {arg} does not exist!")
    return arg


def read_config_file(path_to_config: str):
    """
    читает конфиг из json файла и дополняет дефолтными значениями если необходимо
    @param path_to_config: путь к файлу
    @return: dict возвращает конфиг
    """
    try:
        with open(path_to_config, 'rt') as f_conf:
            config_from_file = json.load(f_conf)
    except Exception as err:
        print(f"Error decoding json config file: {path_to_config}")
        raise
    return config | config_from_file


def main():
    """
    Получает параметры командной строки и в зависимости от них вызывает дальнейшие действия в программе
    @return:
    """
    parser = argparse.ArgumentParser(description='nginx log analyzer')
    parser.add_argument("--config", "-f", dest="config", default="./log_analyzer.conf",
                        help="path to config file", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))
    args = parser.parse_args()
    work_config = read_config_file(args.config)
    logging_config(work_config["LOG_FILE"])
    logger.info(f"Starting Log Analyzer. Config file is {args.config}")
    print(work_config)


if __name__ == "__main__":
    main()
