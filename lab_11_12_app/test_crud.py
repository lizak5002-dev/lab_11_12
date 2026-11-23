from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.urls import reverse
from .models import Child, Groups, Teacher


class CrudTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('Admin', 'admin@test.com', 'password123')
        self.client.login(username='Admin', password='password123')

        self.teacher = Teacher.objects.create(
            last_name='Иванова', first_name='Мария',
            phone_number='+79000000000', experience=5,
        )
        self.group = Groups.objects.create(
            group_name='Группа A', start_year=2020,
            age_category='младшая', teacher=self.teacher,
        )
        self.child = Child.objects.create(
            last_name='Петров', first_name='Иван', gender='Мужской',
            address='ул. 1', birth_date=date(2020, 1, 1),
            start_date=date(2021, 9, 1), group=self.group,
        )

    # P: создание ребёнка через ORM
    def test_create_child_via_orm(self):
        Child.objects.create(
            last_name='Сидоров', first_name='Пётр', gender='Мужской',
            address='ул. 2', birth_date=date(2019, 5, 5),
            start_date=date(2021, 9, 1), group=self.group,
        )
        self.assertEqual(Child.objects.count(), 2)

    # P: создание через view → 302 и запись в БД
    def test_create_child_via_view(self):
        response = self.client.post(reverse('child_create'), {
            'last_name': 'Сидоров', 'first_name': 'Пётр', 'gender': 'Мужской',
            'address': 'ул. 2', 'birth_date': '2019-05-05',
            'start_date': '2021-09-01', 'group': self.group.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Child.objects.filter(last_name='Сидоров').exists())

    # P: редактирование через view
    def test_edit_child_via_view(self):
        response = self.client.post(reverse('child_edit', args=[self.child.pk]), {
            'last_name': 'Петров-Изменённый', 'first_name': 'Иван', 'gender': 'Мужской',
            'address': 'ул. 1', 'birth_date': '2020-01-01',
            'start_date': '2021-09-01', 'group': self.group.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.last_name, 'Петров-Изменённый')

    # N: редактирование несуществующего → 404
    def test_edit_nonexistent_child_returns_404(self):
        response = self.client.get(reverse('child_edit', args=[999999]))
        self.assertEqual(response.status_code, 404)

    # N: удаление группы с детьми → ProtectedError
    def test_delete_group_with_children_protected(self):
        with self.assertRaises(ProtectedError):
            self.group.delete()