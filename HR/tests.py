from django.test import SimpleTestCase
from django.urls import reverse


class RecruitmentUrlsTest(SimpleTestCase):
    def test_recruitment_url_names_exist(self):
        urls = [
            ('recruiter_dashboard', None),
            ('job_creation', None),
            ('job_list', None),
            ('job_detail', {'pk': 1}),
            ('job_edit', {'pk': 1}),
            ('job_delete', {'pk': 1}),
            ('candidate_list', None),
            ('candidate_create', None),
            ('candidate_detail', {'pk': 1}),
            ('candidate_delete', {'pk': 1}),
            ('candidate_convert_to_employee', {'pk': 1}),
            ('offer_list', None),
            ('offer_create', None),
            ('offer_detail', {'pk': 1}),
            ('offer_delete', {'pk': 1}),
            ('offer_convert_to_employee', {'pk': 1}),
            ('recruitment_reports', None),
        ]
        for name, kwargs in urls:
            with self.subTest(name=name):
                self.assertTrue(reverse(name, kwargs=kwargs))
