import datetime
import pathlib
import unittest
from log_analyzer import get_last_log, get_statistics, Urls

config = {
    'REPORT_SIZE': 10,
    'REPORT_DIR': './reports',
    'LOG_DIR': './log'
}

config_wrong = {
    'REPORT_SIZE': 10,
    'REPORT_DIR': 'фывап',
    'LOG_DIR': 'йцукен'
}

urls = {
    '/export/appinstall_raw/2017-06-29/': [0.01, 0.017],
    '/api/1/campaigns/?id=3884027': [0.142],
    '/api/1/campaigns/?id=637948': [0.161],
    '/upload_file/ajax/': [2.495],
    '/api/v2/group/7049889/banners': [0.13, 5.04],
    '/api/1/mailruspy/?n=5016917': [0.012],
    '/banners/26625439/edit/': [4.091],
    '/api/1/campaigns/?id=1166322': [0.239, 0.532, 10.146],
    '/api/v2/internal/mobile_app': [0.021],
    '/export/appinstall_raw/2017-06-30/': [0.001],
    '/api/1/campaigns/?id=6074491': [0.146],
    '/api/v2/group/6991994/banners': [0.135]
}


class StatisticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.urls = Urls(urls, 30, 20)

    def test_statistics_size(self):
        report_size = 8
        stat = get_statistics(self.urls, report_size)
        self.assertEqual(len(stat), report_size)

    def test_stat_size_from_config(self):
        report_size = config.get('REPORT_SIZE')
        stat = get_statistics(self.urls, report_size)
        self.assertEqual(len(stat), report_size)

    def test_stat_count(self):
        stat = get_statistics(self.urls, 1)
        self.assertEqual(stat[0]['count'], 3)

    def test_stat_time_sum(self):
        stat = get_statistics(self.urls, 5)
        self.assertEqual(stat[0]['time_sum'], 10.917)

    def test_url_in_stat(self):
        stat = get_statistics(self.urls, 5)
        stat_urls = [stat[x]['url'] for x in range(5)]
        self.assertIn('/upload_file/ajax/', stat_urls)

    def test_url_not_in_stat(self):
        stat = get_statistics(self.urls, 5)
        stat_urls = [stat[x]['url'] for x in range(5)]
        self.assertNotIn('/api/1/mailruspy/?n=5016917', stat_urls)


class LogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.logs_dir = pathlib.Path(config.get('LOG_DIR'))
        cls.logs_dir_wrong = pathlib.Path(config_wrong.get('LOG_DIR'))

    def test_get_last_log(self):
        log = get_last_log(self.logs_dir)
        self.assertTrue(log)
        self.assertEqual(log.path.name, 'nginx-access-ui.log-20210630')
        self.assertEqual(log.extension, '')
        self.assertEqual(log.date, datetime.date(2021, 6, 30))

    def test_get_log_invalid_config(self):
        with self.assertRaises(FileNotFoundError):
            get_last_log(self.logs_dir_wrong)


if __name__ == '__main__':
    unittest.main()
