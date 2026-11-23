from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.test import TestCase
from .models import Child, Groups, Teacher


class ValidationTest(TestCase):
    def setUp(self):
        self.teacher = Teacher.objects.create(
            last_name='Иванова', first_name='Мария',
            phone_number='+79000000000', experience=5,
        )
        self.group = Groups.objects.create(
            group_name='Группа A', start_year=2020,
            age_category='младшая', teacher=self.teacher,
        )

    def _make_child(self, **overrides):
        defaults = dict(
            last_name='Иванов', first_name='Пётр', gender='Мужской',
            address='ул. Тестовая, 1',
            birth_date=date(2020, 1, 1),
            start_date=date(2021, 9, 1),
            group=self.group,
        )
        defaults.update(overrides)
        return Child(**defaults)

    # # N: дата рождения в будущем → ошибка
    # def test_future_birth_date_rejected(self):
    #     tomorrow = date.today() + timedelta(days=1)
    #     child = self._make_child(
    #         birth_date=tomorrow,
    #         start_date=tomorrow + timedelta(days=365),
    #     )
    #     with self.assertRaises(ValidationError) as ctx:
    #         child.full_clean()
    #     self.assertIn('birth_date', ctx.exception.message_dict)

    # N: дата поступления в будущем → ошибка
    def test_future_start_date_rejected(self):
        tomorrow = date.today() + timedelta(days=1)
        child = self._make_child(start_date=tomorrow)
        with self.assertRaises(ValidationError) as ctx:
            child.full_clean()
        self.assertIn('start_date', ctx.exception.message_dict)

    # # N: birth_date >= start_date → ошибка
    # def test_birth_after_start_rejected(self):
    #     child = self._make_child(
    #         birth_date=date(2021, 1, 1),
    #         start_date=date(2020, 1, 1),
    #     )
    #     with self.assertRaises(ValidationError):
    #         child.full_clean()

    # N: пустая фамилия → ошибка
    def test_empty_last_name_rejected(self):
        child = self._make_child(last_name='')
        with self.assertRaises(ValidationError):
            child.full_clean()

    def test_duplicate_group_name_rejected(self):
        try:
            Groups.objects.create(
                group_name='Группа A', start_year=2021,
                age_category='средняя', teacher=self.teacher,
            )
            self.fail("Ожидалось исключение, но группа создалась")
        except Exception as e:
            print(f"[DEBUG] Тип исключения: {type(e).__name__}")
            print(f"[DEBUG] Модуль: {type(e).__module__}")
            print(f"[DEBUG] Сообщение: {e}")
            raise   