from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


class ReportsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('Admin', 'admin@test.com', 'password123')
        self.client.login(username='Admin', password='password123')

    # P: HTML-отчёт по группам → 200
    def test_report_groups_html(self):
        response = self.client.get(reverse('report_groups'))
        self.assertEqual(response.status_code, 200)

    # P: PDF по группам → 200 + Content-Type
    def test_report_groups_pdf(self):
        response = self.client.get(reverse('report_groups_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    # P: Excel по группам → 200 + Content-Type
    def test_report_groups_excel(self):
        response = self.client.get(reverse('report_groups_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml', response['Content-Type'])

    # N: PDF с невалидным year → не 500
    def test_report_pdf_invalid_year(self):
        response = self.client.get(reverse('report_groups_pdf'), {'year': 'abc'})
        self.assertIn(response.status_code, [200, 400])

    # N: PDF без логина → редирект на логин
    def test_report_pdf_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('report_groups_pdf'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)