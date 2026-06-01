from django.test import SimpleTestCase
from django.urls import reverse


class MasterUrlsTest(SimpleTestCase):
    def test_master_url_names_exist(self):
        names = [
            'designation_list',
            'department_list',
            'allowances_list',
            'leaves_list',
            'bank_list',
        ]
        for name in names:
            with self.subTest(name=name):
                url = reverse(name)
                self.assertTrue(url)
