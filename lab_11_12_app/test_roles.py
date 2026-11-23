from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from .views import is_admin, is_user


class RolesTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('Admin', 'admin@test.com', 'password123')
        self.user = User.objects.create_user('user', 'user@test.com', 'password123')
        user_group, _ = Group.objects.get_or_create(name='User')
        self.user.groups.add(user_group)

    # P: is_admin для суперпользователя
    def test_is_admin_superuser(self):
        self.assertTrue(is_admin(self.admin))

    # N: is_admin для обычного пользователя
    def test_is_admin_regular_user_false(self):
        self.assertFalse(is_admin(self.user))

    # P: is_user для пользователя в группе User
    def test_is_user_true(self):
        self.assertTrue(is_user(self.user))

    # # P: админ может открыть форму создания
    # def test_admin_can_access_create_form(self):
    #     self.client.login(username='Admin', password='password123')
    #     response = self.client.get(reverse('child_create'))
    #     self.assertEqual(response.status_code, 200)

    # N: обычный пользователь не может открыть форму создания
    def test_regular_user_cannot_access_create_form(self):
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('child_create'))
        self.assertEqual(response.status_code, 302)  # редирект на логин