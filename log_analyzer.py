#!/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
import gzip
import json
import logging
import pathlib
import re
import sys
import string
from argparse import ArgumentParser
from datetime import datetime
from collections import namedtuple, defaultdict
from statistics import median

config = {
    'REPORT_SIZE': 1000,
    'REPORT_DIR': './reports',
    'LOG_DIR': './log'
}

LastLog = namedtuple('LastLog', ['path', 'date', 'extension'])
Urls = namedtuple('Urls', ['urls_dict', 'total', 'total_time_sum'])


def get_config_path():
    parser = ArgumentParser(description='nginx log analyzer')
    parser.add_argument('--config',
                        dest='config_path',
                        type=pathlib.Path,
                        default='./conf',
                        help='path to the config file')
    args = parser.parse_args()
    return args.config_path


def init_config(config_path, config):
    try:
        with open(config_path) as f:
            try:
                config_from_file = json.load(f)
                config.update(config_from_file)
                return True
            except json.JSONDecodeError:
                print(f'Config file "{f.name}" could not be converted to JSON or empty')
                return False
    except FileNotFoundError:
        print(f'No such file or directory: "{config_path}"')
        return False


def get_report_path(report_dir: pathlib.Path, date):
    report_name = f'report-{date:%Y.%m.%d}.html'
    report_path = report_dir.joinpath(report_name)
    if report_path.exists():
        logging.error(f'The last log file has already been processed. The report "{report_path}" is exist')
        return None
    else:
        try:
            report_dir.mkdir(parents=True)
            logging.info(f'Directory "{report_dir}" created')
        except FileExistsError:
            logging.info(f'Report dir "{report_dir}" is already exist')
        logging.info(f'Report file "{report_path.name}" will be created in dir "{report_path.parent}"')
        return report_path


def get_last_log(logs_dir: pathlib.Path):
    logging.info(f'Directory for log analyze: {logs_dir}')
    last_log = last_date = last_ext = None
    pattern = re.compile(r'^nginx-access-ui\.log-(?P<date>\d{8})(?P<ext>\.gz$|$)')
    for path in logs_dir.iterdir():
        m = pattern.match(path.name)
        if m:
            try:
                date = datetime.strptime(m.group('date'), '%Y%m%d').date()
            except ValueError:
                continue
            extension = m.group('ext')
            if last_date is None or date > last_date:
                last_date = date
                last_ext = extension
                last_log = path
        else:
            continue
    if last_date:
        logging.info(f'Last logfile: {last_log}')
        return LastLog(path=last_log, date=last_date, extension=last_ext)


def line_generator(log: LastLog, pattern, open_function):
    with open_function(log.path, 'rt', encoding='utf-8') as file:
        logging.info(f'The log {log.path} is open for parsing')
        for line in file:
            parsed_result = re.search(pattern, line)
            if parsed_result:
                yield parsed_result.group('url', 'time')
            else:
                yield None, None


def get_urls(generator, total=0, processed=0, total_time_sum=0):
    urls = defaultdict(list)
    for url, time in generator:
        total += 1
        if url and time:
            processed += 1
            time = float(time)
            total_time_sum += time
            urls[url].append(time)
    check_errors(total, processed)
    return Urls(urls, total, total_time_sum)


def analyze_log(log: LastLog):
    nginx_pattern = re.compile(r'^.+?"\w+ (?P<url>\S+) .* (?P<time>\d+.\d+)$')
    open_function = gzip.open if log.extension else open
    generator = line_generator(log, nginx_pattern, open_function)
    return get_urls(generator)


def check_errors(total, processed):
    error_limit = 0.5
    if processed / total >= error_limit:
        logging.info(f'{processed} of {total} lines processed')
    else:
        raise RuntimeError(f'Failed to process more than {error_limit * 100}% of the log - exit')


def get_statistics(urls: Urls, report_size):
    stats = []
    for url, request_times in urls.urls_dict.items():
        count = len(request_times)
        time_sum = round(sum(request_times), 3)
        stats.append({
            'url': url,
            'count': count,
            'count_perc': round(count / urls.total * 100, 3),
            'time_avg': round(time_sum / count, 3),
            'time_max': max(request_times),
            'time_med': round(median(request_times), 3),
            'time_perc': round(time_sum / urls.total_time_sum * 100, 3),
            'time_sum': time_sum,
        })
    stats = sorted(stats, key=lambda key: key['time_sum'], reverse=True)[:report_size]
    return stats


def generate_report(report_path: pathlib.Path, table_json):
    report_template_path = pathlib.Path('./report.html')
    if report_template_path.exists():
        with report_template_path.open(encoding='utf-8') as file:
            template = string.Template(file.read())
        report = template.safe_substitute(table_json=json.dumps(table_json))
        with report_path.open(mode='w', encoding='utf-8') as file:
            file.write(report)
        logging.info(f'The report was successfully generated in {report_path}')
    else:
        logging.error("The template of report isn't exist. Impossible to generate a report")


def main(config):
    config_path = get_config_path()
    if not init_config(config_path, config):
        sys.exit()
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        filename=config.get('LOG_FILE') if 'LOG_FILE' in config else None
    )
    logging.info(f'Config "{config}" was applied')
    logs_dir = pathlib.Path(config.get('LOG_DIR'))
    log_file = get_last_log(logs_dir)
    if not log_file:
        logging.info('No logs for analyze, exit')
        sys.exit()
    report_dir = pathlib.Path(config.get('REPORT_DIR'))
    report_path = get_report_path(report_dir, log_file.date)
    if report_path:
        urls = analyze_log(log_file)
        report_size = config.get('REPORT_SIZE')
        table_json = get_statistics(urls, report_size)
        generate_report(report_path, table_json)


if __name__ == "__main__":
    try:
        main(config)
    except KeyboardInterrupt:
        logging.error('Log Analyzer Program was interrupted')
    except Exception as err:
        logging.exception(err)
