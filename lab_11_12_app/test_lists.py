from datetime import date
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Child, Groups, Teacher


class ListTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('Admin', 'admin@test.com', 'password123')
        self.client.login(username='Admin', password='password123')

        self.teacher = Teacher.objects.create(
            last_name='Иванова', first_name='Мария',
            phone_number='+79000000000', experience=5,
        )
        self.g1 = Groups.objects.create(
            group_name='A', start_year=2020, age_category='младшая', teacher=self.teacher,
        )
        self.g2 = Groups.objects.create(
            group_name='B', start_year=2021, age_category='средняя', teacher=self.teacher,
        )
        self.c1 = Child.objects.create(
            last_name='Петров', first_name='Иван', gender='Мужской',
            address='ул. 1', birth_date=date(2020, 1, 1),
            start_date=date(2021, 9, 1), group=self.g1,
        )
        self.c2 = Child.objects.create(
            last_name='Сидорова', first_name='Анна', gender='Женский',
            address='ул. 2', birth_date=date(2019, 5, 10),
            start_date=date(2021, 9, 1), group=self.g2,
        )

    # P: сортировка по фамилии asc
    def test_sort_by_last_name_asc(self):
        response = self.client.get(reverse('child_list'), {'sort': 'last_name', 'order': 'asc'})
        children = list(response.context['children'])
        self.assertEqual(children[0].last_name, 'Петров')
        self.assertEqual(children[-1].last_name, 'Сидорова')

    # P: фильтр по группе
    def test_filter_by_group(self):
        response = self.client.get(reverse('child_list'), {'group': self.g1.pk})
        children = list(response.context['children'])
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].last_name, 'Петров')

    # N: фильтр по несуществующей группе → пусто
    def test_filter_by_nonexistent_group(self):
        response = self.client.get(reverse('child_list'), {'group': 99999})
        self.assertEqual(len(list(response.context['children'])), 0)

    # P: поиск по одному слову
    def test_search_by_single_word(self):
        response = self.client.get(reverse('child_list'), {'search': 'Петров'})
        children = list(response.context['children'])
        self.assertEqual(len(children), 1)

    # N: поиск с нечисловым group → не 500
    def test_search_with_non_numeric_group_does_not_crash(self):
        response = self.client.get(reverse('child_list'), {'group': 'abc'})
        self.assertIn(response.status_code, [200, 400])