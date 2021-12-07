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


def init_config(config):
    parser = ArgumentParser(description='nginx log analyzer')
    parser.add_argument('--config',
                        dest='config_path',
                        type=pathlib.Path,
                        help='path to the config file')
    args = parser.parse_args()
    if args.config_path:
        try:
            with open(args.config_path) as f:
                try:
                    config_from_file = json.load(f)
                    config.update(config_from_file)
                except json.JSONDecodeError:
                    print(f'Config file "{f.name}" could not be converted to JSON or empty')
        except FileNotFoundError:
            print(f'No such file or directory: "{args.config_path}"')


def get_logs_dir(config):
    logs_dir = pathlib.Path(config.get('LOG_DIR'))
    if logs_dir.is_dir():
        logging.info(f'Directory for log analyze: {logs_dir}')
        return logs_dir
    else:
        logging.error("LOG_DIR in config isn't a directory")
        return None


def get_report_path(config, date):
    report_dir = pathlib.Path(config.get('REPORT_DIR'))
    try:
        report_dir.mkdir(parents=True)
        logging.info(f'Directory "{report_dir}" created')
    except FileExistsError:
        logging.info(f'REPORT_DIR "{report_dir}" is already exist')
    report_name = f'report-{date:%Y.%m.%d}.html'
    report_path = report_dir.joinpath(report_name)
    try:
        report_path.touch(exist_ok=False)
        logging.info(f'Report file "{report_path.name}" created in dir "{report_path.parent}"')
        return report_path
    except FileExistsError:
        logging.error(f'The last log file has already been processed. The report "{report_path}" is exist')
        return None


def get_last_log(logs_dir: pathlib.Path):
    if logs_dir.is_dir():
        last_log = last_date = last_ext = None
        pattern = re.compile(r'^nginx-access-ui\.log-(?P<date>\d{8})(?P<ext>\.gz$|$)')
        for path in logs_dir.iterdir():
            m = pattern.match(path.name)
            if m:
                date = datetime.strptime(m.group('date'), '%Y%m%d').date()
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
    else:
        logging.error("LOG_DIR in config isn't a directory")
        return None


def line_generator(log: LastLog, pattern, open_function):
    with open_function(log.path, 'rt', encoding='utf-8') as file:
        logging.info(f'The log {log.path} is open for parsing')
        for line in file:
            parsed_result = re.search(pattern, line)
            if parsed_result:
                yield parsed_result.group('url', 'time')
            else:
                yield None, None


def analyze_log(log: LastLog, config):
    nginx_pattern = re.compile(r'^.+?"\w+ (?P<url>\S+) .* (?P<time>\d+.\d+)$')
    urls = defaultdict(list)
    open_function = gzip.open if log.extension else open
    total = processed = total_time_sum = 0
    generator = line_generator(log, nginx_pattern, open_function)
    for url, time in generator:
        total += 1
        if url and time:
            processed += 1
            time = float(time)
            total_time_sum += time
            urls[url].append(time)
    check_errors(total, processed)
    report_size = config.get('REPORT_SIZE')
    data = get_statistics(urls, total, total_time_sum, report_size)
    return data


def check_errors(total, processed):
    error_limit = 0.5
    if processed / total >= error_limit:
        logging.info(f'{processed} of {total} lines processed')
    else:
        logging.error(f'Failed to process more than {error_limit * 100}% of the log - exit')
        raise Exception


def get_statistics(urls: defaultdict, total_requests, total_time_sum, report_size):
    stats = []
    for url, request_times in urls.items():
        count = len(request_times)
        time_sum = round(sum(request_times), 3)
        stats.append({
            'url': url,
            'count': count,
            'count_perc': round(count / total_requests * 100, 3),
            'time_avg': round(time_sum / count, 3),
            'time_max': max(request_times),
            'time_med': round(median(request_times), 3),
            'time_perc': round(time_sum / total_time_sum * 100, 3),
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
    init_config(config)
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname).1s %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
        filename=config.get('LOG_FILE') if 'LOG_FILE' in config else None
    )
    logging.info(f'Config "{config}" was applied')
    logs_dir = get_logs_dir(config)
    log_file = get_last_log(logs_dir)
    if not log_file:
        logging.info('No logs for analyze, exit')
        sys.exit()
    report_path = get_report_path(config, log_file.date)
    if report_path:
        table_json = analyze_log(log_file, config)
        generate_report(report_path, table_json)


if __name__ == "__main__":
    try:
        main(config)
    except KeyboardInterrupt:
        logging.error('Log Analyzer Program was interrupted')
    except Exception as err:
        logging.exception(err)
