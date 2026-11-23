from django.test import TestCase, Client
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.urls import reverse


class AuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('Admin', 'admin@test.com', 'password123')
        self.user = User.objects.create_user('user', 'user@test.com', 'password123')

    # P: верные учётные данные → пользователь
    def test_authenticate_valid_credentials(self):
        u = authenticate(username='Admin', password='password123')
        self.assertIsNotNone(u)
        self.assertEqual(u.username, 'Admin')

    # N: неверный пароль → None
    def test_authenticate_wrong_password(self):
        self.assertIsNone(authenticate(username='Admin', password='wrong'))

    # N: несуществующий пользователь → None
    def test_authenticate_nonexistent_user(self):
        self.assertIsNone(authenticate(username='nobody', password='password123'))

    # P: логин через /login/ → редирект на /
    def test_login_view_redirects(self):
        response = self.client.post(reverse('login'), {
            'username': 'Admin', 'password': 'password123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

    # N: защищённая страница без логина → редирект на /login/
    def test_anonymous_redirected_from_children(self):
        response = self.client.get(reverse('child_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)