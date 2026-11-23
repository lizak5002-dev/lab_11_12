from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date


class NoGroupsTest(TestCase):
    """
    Тест-кейс: Попытка создания ребёнка, когда в БД нет ни одной группы.
    Ожидаемый результат: Создание невозможно, форма возвращает ошибку валидации по полю 'group'.
    """

    def setUp(self):
        # Создаем админа, так как страница создания требует прав администратора
        self.admin = User.objects.create_superuser('Admin', 'admin@test.com', 'password123')
        self.client.login(username='Admin', password='password123')

    def test_create_child_fails_without_groups(self):
        # 1. Проверяем, что БД действительно пуста по группам (предусловие)
        from .models import Groups
        self.assertEqual(Groups.objects.count(), 0, "В БД уже есть группы, тест не чистый!")

        # 2. Пытаемся открыть форму и отправить её
        # Данные валидные по всем остальным полям, кроме group
        form_data = {
            'last_name': 'Иванов',
            'first_name': 'Пётр',
            'second_name': 'Сергеевич',
            'gender': 'Мужской',
            'address': 'ул. Тестовая, д. 1',
            'birth_date': date(2020, 1, 1),
            'start_date': date(2021, 9, 1),
            'group': '',  # Оставляем пустым, так как групп нет
        }

        response = self.client.post(reverse('child_create'), data=form_data)

        # 3. Проверяем, что форма не сохранилась (статус 200, а не 302 редирект)
        self.assertEqual(response.status_code, 200, "Форма не должна была пройти (ожидался редирект 302 при успехе)")
        
        # 4. Проверяем, что в контексте ответа есть форма с ошибками
        form = response.context['form']
        self.assertFalse(form.is_valid(), "Форма не должна быть валидной")
        
        # 5. Проверяем, что ошибка привязана именно к полю 'group' и связана с его обязательностью
        self.assertIn('group', form.errors, "Ожидалась ошибка валидации по полю group")
        
        # 6. Проверяем, что запись не появилась в БД
        from .models import Child
        self.assertEqual(Child.objects.count(), 0, "Ребёнок не должен был создаться")
