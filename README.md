# NGINX Log Analyzer

The script analyzes the log with the most recent date and generates a html-report with statistics on the time of requests

## Getting Started

You need to install Python 3 to run log analyzer script

### Installing

Download files in one directory:
* log_analyzer.py, 
* report.html, 
* jquery.tablesorter.min.js,
* conf, tests.py (if you need it)

### Running

To get help about running log analyzer: 
```
python3 log_analyzer.py -h
```
Run with default args:
```
python3 log_analyzer.py
```
Run with config file:
```
python3 log_analyzer.py --config filename
```
Run tests:
```
python3 tests.py
```

## Examples

NGINX log format:
```
# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
```
Example log filename: 
```
nginx-access-ui.log-20211025.gz
nginx-access-ui.log-20211025
```
Example report filename:
```
report-2021.10.25.html
```
Example JSON config file:
```
{
    "REPORT_SIZE": 500, # count of urls with max sum time in report
    "REPORT_DIR": "./reports", # path to report directory
    "LOG_DIR": "./log", # path to log directory
    "LOG_FILE": "log_analyzer.log" # if not specified, then the log of script is written to stdout
}
```
Example script run log:
```
[2021.12.08 23:28:31] I Config "{'REPORT_SIZE': 1000, 'REPORT_DIR': './reports', 'LOG_DIR': './log'}" was applied
[2021.12.08 23:28:31] I Directory for log analyze: log
[2021.12.08 23:28:31] I Last logfile: log/nginx-access-ui.log-20211010
[2021.12.08 23:28:31] I REPORT_DIR "reports" is already exist
[2021.12.08 23:28:31] I Report file "report-2021.10.10.html" created in dir "reports"
[2021.12.08 23:28:31] I The log log/nginx-access-ui.log-20211010 is open for parsing
[2021.12.08 23:28:31] I 15 of 21 lines processed
[2021.12.08 23:28:31] I The report was successfully generated in reports/report-2021.10.10.html
```

