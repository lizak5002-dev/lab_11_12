from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Child, Groups, Teacher


class ChildModelTest(TestCase):
    def setUp(self):
        self.teacher = Teacher.objects.create(
            last_name='Воспитателева', first_name='Мария',
            phone_number='+79000000000', experience=5,
        )
        self.group = Groups.objects.create(
            group_name='Тест', start_year=2020,
            age_category='младшая', teacher=self.teacher,
        )

    def _make_child(self, **overrides):
        """Хелпер: создаёт валидного ребёнка, позволяя переопределить поля."""
        defaults = dict(
            last_name='Иванов', first_name='Пётр', gender='Мужской',
            address='ул. Тестовая, 1',
            birth_date=date(2020, 1, 1),
            start_date=date(2021, 9, 1),
            group=self.group,
        )
        defaults.update(overrides)
        return Child(**defaults)

    # ---------- тест 1: валидация дат  ----------

    def test_clean_rejects_birth_after_start(self):
        child = self._make_child(
            birth_date=date(2020, 1, 1),
            start_date=date(2019, 1, 1),
        )
        with self.assertRaises(ValidationError):
            child.full_clean()

    # ---------- тест 2: валидный ребёнок проходит full_clean ----------

    def test_valid_child_passes_full_clean(self):
        """Корректные данные не вызывают ValidationError."""
        child = self._make_child()
        # Не должно бросить исключение
        child.full_clean()

    # ---------- тест 3: дата рождения в будущем ----------

    def test_clean_rejects_future_birth_date(self):
        tomorrow = date.today() + timedelta(days=1)
        child = self._make_child(
            birth_date=tomorrow,
            start_date=tomorrow + timedelta(days=365),
        )
        with self.assertRaises(ValidationError) as ctx:
            child.full_clean()
        # Проверяем, что ошибка привязана именно к birth_date
        self.assertIn('birth_date', ctx.exception.message_dict)

    # ---------- тест 4: свойство age ----------

    def test_age_property(self):
        """Свойство age корректно считает возраст с учётом дня рождения."""
        today = date.today()
        # Ребёнок, родившийся ровно 5 лет назад (день рождения уже был)
        five_years_ago = today.replace(year=today.year - 5)
        child = self._make_child(
            birth_date=five_years_ago,
            start_date=today,
        )
        self.assertEqual(child.age, 5)

    # ---------- тест 5: full_name с отчеством и без ----------

    def test_full_name_with_and_without_second_name(self):
        """full_name возвращает ФИО с отчеством, если оно есть, иначе ФИ."""
        with_second = self._make_child(
            last_name='Иванов', first_name='Пётр', second_name='Сергеевич',
        )
        without_second = self._make_child(
            last_name='Петров', first_name='Иван', second_name=None,
        )
        self.assertEqual(with_second.full_name, 'Иванов Пётр Сергеевич')
        self.assertEqual(without_second.full_name, 'Петров Иван')