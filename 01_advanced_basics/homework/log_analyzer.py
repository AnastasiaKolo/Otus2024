#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import datetime
import json
import logging
import regex

import os.path

from collections import namedtuple


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


def find_last_nginx_log(path: str):
    """
    находит имя файла лога по маске с максимальной датой в имени
    @param path: путь к каталогу с логами
    @return: namedtuple (путь, дата, расширение файла)
    """
    max_date = datetime.date(1, 1, 1)
    log_name = None
    reg_name = r"^nginx-access-ui\.log-(\d{8})\.*(gz|log|txt)*$"
    fname = namedtuple("Log_filename", ['name', 'date', 'ext'])
    if os.path.isdir(path):
        for filename in os.listdir(path):
            get_name = regex.findall(reg_name, filename)
            if get_name:
                dt = validate_date(get_name[0][0])
                if dt and dt > max_date:
                    max_date = dt
                    log_name = fname(os.path.join(path, filename), dt, str(get_name[0][1]))
        if log_name:
            logging.info(f"last log file is {log_name.name}")
        else:
            logging.error(f"log files not found in {path}")
        return log_name
    else:
        logging.error(f"log file directory not found: {path}")
        return None


def gen_report_name(path, rep_date):
    """
    проверяет что файла с отчетом за эту дату нет
    @param path: путь к каталогу с отчетами
    @param rep_date: дата отчета
    @return: (путь к файлу или None если файл уже есть)
    """
    rep_name = os.path.join(path, rep_date.strftime("report-%Y.%m.%d.html"))
    if os.path.exists(rep_name):
        logging.info(f"report {rep_name} already exists")
        return None
    return rep_name


def logfile_read(log_name):
    """
    читает файл выдавая строки по запросу
    @param log_name: namedtuple("Log_filename", ['name', 'date', 'ext'])
    @return: str
    """
    if log_name.ext == "gz":
        log = gzip.open(logf, 'rt')
    else:
        log = open(logf, 'rt')
    with log as l_file:
        for line in l_file:
            yield line


def log_string_parse(log_str: str):
    global log_req_time_total
    url, time = "", 0.0
    tmpl = regex.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3} .* \"(?:GET|POST|DELETE|PUT|HEAD|OPTIONS|-) (.*) HTTP/\d.\d\".* (\d+\.\d*)$")

    try:
        url, time = regex.findall(tmpl, log_str)[0]
        url = str(url)
        time = float(time)
        log_req_time_total += time
        log.info("Log string: " + log_str)
        log.info("Log parse url string: " + url + " access time:" + str(time))
    except IndexError:
        log.warning("Wrong string format: " + log_str)
    return url, time


def log_statistics(log_limit: int):
    url_stat = []
    for key, val in log_counter.items():
        times = val
        log.info("Log stats. URL: " + str(key) + " list time: " + str(times))
        url_stat.append(
            {
                'url': key,
                'count': len(times),
                'count_perc': (1 / len(log_counter)) * 100,
                'time_max': max(times),
                'time_sum': sum(times),
                'time_avg': sum(times) / len(times),
                'time_med': median(times),
                'time_perc': (sum(times) / log_req_time_total) * 100
            })
    url_stat.sort(key=lambda x: x['time_sum'], reverse=True)

    if len(url_stat) < log_limit:
        log_limit = len(url_stat)

    return url_stat[0:log_limit]


def log_report(stat, file_date, report_dir):
    template_path = Path("./template.html")
    if not Path(report_dir).exists():
        Path(report_dir).mkdir()
    report_file_name = Path(f"{report_dir}/report-{file_date}.html")

    tmpl_ex = ""
    with open(template_path, "rt") as f_rep:
        for line in f_rep:
            tmpl_ex += line

    tmpl = Template(str(tmpl_ex))
    tmpl_sub = dict(table_json=json.dumps(stat))
    with open(report_file_name, "wt") as f_rep_fresh:
        f_rep_fresh.write(tmpl.safe_substitute(tmpl_sub))


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
    log_name = find_last_nginx_log(work_config["LOG_DIR"])
    rep_name = None
    if log_name:
        rep_name = gen_report_name(work_config["REPORT_DIR"], log_name.date)
    if rep_name:
        print(rep_name)




if __name__ == "__main__":
    main()
