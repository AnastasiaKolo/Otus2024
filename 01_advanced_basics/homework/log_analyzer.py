#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Программа для расчета статистики по логам nginx"""

import argparse
import datetime
import gzip
import json
import logging
import os
import regex

from collections import namedtuple, defaultdict
from statistics import median
from string import Template
from json.decoder import JSONDecodeError

DEFAULT_CONFIG = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./report",
    "LOG_DIR": "./log",
    "LOG_FILE": None,
    "ERROR_LIMIT": 0.8
}

NGINX_LOG_NAME = r"^nginx-access-ui\.log-(\d{8})\.*(gz|log|txt)*$"

TMPL_LOG_STRING = regex.compile(
        r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} .* \"(?:GET|POST|DELETE|PUT|HEAD|OPTIONS|-) "
        r"(.*) HTTP/\d.\d\".* ("
        r"\d+\.\d*)$")


def parse_args():
    """
    Парсит параметры командной строки
    возвращает путь к конфигу
    @return: str
    """

    def is_valid_file(arg):
        """
        проверка что файл переданный в параметрах вызова, существует
        @param arg: аргумент для проверки
        @return: возвращает аргумент, если он корректный. Иначе ошибка
        """
        if not os.path.exists(arg):
            parser.error(f"The file {arg} does not exist!")
        return arg

    parser = argparse.ArgumentParser(description='nginx log analyzer')
    parser.add_argument("--config", "-f", dest="config", default="./log_analyzer.conf",
                        help="path to config file", metavar="FILE",
                        type=lambda x: is_valid_file(x))
    args = parser.parse_args()
    return args.config


def logging_config(log_path=None):
    """
    настройка логирования
    @param log_path: путь к файлу лога
    @return:
    """
    logging.basicConfig(level=logging.INFO, filename=log_path, datefmt='%Y.%m.%d %H:%M:%S',
                        format="[%(asctime)s] %(levelname).1s %(message)s")


def read_config_file(path_to_config: str) -> json:
    """
    читает конфиг из json файла и дополняет дефолтными значениями если необходимо
    @param path_to_config: путь к файлу
    @return: dict возвращает конфиг
    """
    try:
        with open(path_to_config, 'rt') as f_conf:
            config_from_file = json.load(f_conf)
    except JSONDecodeError as e:
        logging.exception(f"Error decoding json config file: {path_to_config}", e)
        raise
    return DEFAULT_CONFIG | config_from_file


def validate_date(date_text):
    """
    проверяет формат даты в строке
    @param date_text: строка с предположительно датой
    @return: date возвращает дату или None если не удалось распарсить
    """
    try:
        dt = datetime.datetime.strptime(date_text, '%Y%m%d').date()
        return dt
    except ValueError:
        return None


def find_last_nginx_log(path: str, reg_name: str) -> namedtuple("LogFile", "path, date, ext"):
    """
    находит имя файла лога по маске с максимальной датой в имени
    :param path: путь к каталогу с логами
    :param reg_name: регулярка для поиска лога
    :return: namedtuple (путь, дата, расширение файла)
    """
    max_date = datetime.date(1, 1, 1)
    last_logfile = None
    fname = namedtuple("LogFile", "path, date, ext")
    if os.path.isdir(path):
        for filename in os.listdir(path):
            get_name = regex.findall(reg_name, filename)
            if get_name:
                dt = validate_date(get_name[0][0])
                if dt and dt > max_date:
                    max_date = dt
                    last_logfile = fname(os.path.join(path, filename), dt, str(get_name[0][1]))
        if last_logfile:
            logging.info(f"last log file is {last_logfile.path}")
        else:
            logging.error(f"log files not found in {path}")
    else:
        logging.error(f"log file directory not found: {path}")
    return last_logfile


def logfile_parse(logfile: namedtuple("LogFile", "path, date, ext"), tmpl, error_limit=0.8):
    """
    читает файл выдавая распарсенные строки
    если превышено кол-во ошибок, пишет в лог и выходит
    :param tmpl: результат regex.compile регулярного выражения строки лога
    :param logfile: namedtuple("LogFile", "path, date, ext")
    :param error_limit: допустимая часть ошибок от общего кол-ва обработанных строк
    :return: str
    """
    total, errors = 0, 0
    opener = gzip.open(logfile.path, 'rt') if logfile.ext == "gz" else open(logfile.path, 'rt')
    with opener as log:
        try:
            for line in log:
                total += 1
                try:
                    url, time = regex.findall(tmpl, line)[0]
                    url = str(url)
                    time = float(time)
                    yield url, time
                except IndexError:
                    errors += 1
        except (FileNotFoundError, PermissionError, OSError):
            logging.error(f"Error opening file {logfile.path}")

    logging.info(f"{total} lines parsed with {errors} errors")

    if total > 0 and errors / total > error_limit:
        raise Warning(f"Errors limit {error_limit} exceeded!")


def generate_report(logfile_data, report_size: int) -> list:
    """
    Обрабатывает iterable logfile_data, вычисляет статистику посещения url-ов
    и выдает отчет
    :param logfile_data:
    :param report_size:
    :return: (массив заданного размера отсортированный по времени затраченному на посещение url)
    """
    log_counter = defaultdict(list)
    total_time = 0.0
    for url, time in logfile_data:
        log_counter[url].append(time)
        total_time += time

    url_stat = []
    for url, times in log_counter.items():
        url_stat.append(
            {
                'url': url,
                'count': len(times),
                'count_perc': (1 / len(log_counter)) * 100,
                'time_max': max(times),
                'time_sum': sum(times),
                'time_avg': sum(times) / len(times),
                'time_med': median(times),
                'time_perc': (sum(times) / total_time) * 100
            })
    url_stat.sort(key=lambda x: x['time_sum'], reverse=True)

    if len(url_stat) < report_size:
        report_size = len(url_stat)

    return url_stat[0:report_size]


def make_report(stat, report_file_name, report_dir):
    """
    сохраняет отчет в формате html
    :param stat: массив значений отчета
    :param report_file_name: имя файла куда сохранить отчет
    :param report_dir: каталог для отчетов
    :return:
    """
    template_path = "./report/report.html"
    if not os.path.exists(report_dir):
        os.mkdir(report_dir)

    with open(template_path, "rt") as file:
        tmpl = Template(file.read())

    tmpl_sub = dict(table_json=json.dumps(stat))
    with open(report_file_name, "wt") as file:
        file.write(tmpl.safe_substitute(tmpl_sub))
        logging.info(f"Report saved to {report_file_name}")


def main():
    """
    Получает рабочий конфиг и вызывает дальнейшие действия в программе
    @return:
    """
    work_config = read_config_file(parse_args())
    logging_config(work_config["LOG_FILE"])
    logging.info(f"Starting Log Analyzer. Work_config is {work_config}")
    last_log = find_last_nginx_log(work_config["LOG_DIR"], NGINX_LOG_NAME)

    if not last_log:
        logging.info(f"nginx log file not found in directory {work_config['LOG_DIR']}")
    else:
        new_rep_name = os.path.join(work_config["REPORT_DIR"],
                                    last_log.date.strftime("report-%Y.%m.%d.html"))

        if os.path.exists(new_rep_name):
            logging.info(f"report {new_rep_name} already exists")
            print(f"report {new_rep_name} already exists")
        else:
            print(f"generating report {new_rep_name}...")
            url_stat = generate_report(logfile_parse(last_log, TMPL_LOG_STRING),
                                       work_config["REPORT_SIZE"])
            make_report(url_stat, new_rep_name, work_config["REPORT_DIR"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("User requested cancel of current operation!")
    except:
        logging.exception("Exception occurred!")
