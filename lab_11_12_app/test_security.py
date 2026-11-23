from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('Admin', 'admin@test.com', 'password123')

    # N: POST без CSRF → 403
    def test_post_without_csrf_forbidden(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username='Admin', password='password123')
        response = client.post(reverse('child_create'), {'last_name': 'X'})
        self.assertEqual(response.status_code, 403)

    # N: SQL-инъекция в поиске не ломает
    def test_sql_injection_in_search(self):
        self.client.login(username='Admin', password='password123')
        response = self.client.get(reverse('child_list'), {'search': "' OR 1=1--"})
        self.assertIn(response.status_code, [200])

    # N: XSS в поиске экранируется
    def test_xss_in_search_escaped(self):
        self.client.login(username='Admin', password='password123')
        response = self.client.get(reverse('child_list'), {'search': '<script>alert(1)</script>'})
        self.assertNotIn(b'<script>alert(1)</script>', response.content)
        self.assertIn(b'&lt;script&gt;', response.content)

    # N: пароль хранится в хеше
    def test_password_is_hashed(self):
        u = User.objects.get(username='Admin')
        self.assertNotEqual(u.password, 'password123')
        self.assertTrue(u.check_password('password123'))

    # N: аноним не имеет доступа к админке
    def test_anonymous_cannot_access_admin(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)