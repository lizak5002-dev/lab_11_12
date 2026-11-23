from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth.models import User
from datetime import date

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

from .models import Groups, Child, Teacher


class TestUserFlow(StaticLiveServerTestCase):
    def setUp(self):
        options = webdriver.FirefoxOptions()
        options.add_argument('--headless')
        options.binary_location = "/snap/firefox/current/usr/lib/firefox/firefox"
        self.driver = webdriver.Firefox(options=options)

        # Пользователи
        self.admin = User.objects.create_superuser('Admin', 'admin@test.com', 'password123')
        self.regular_user = User.objects.create_user('user', 'user@test.com', 'password123')

        # Воспитатель и группы
        self.teacher = Teacher.objects.create(
            last_name='Воспитателева',
            first_name='Мария',
            second_name='Ивановна',
            phone_number='+79000000000',
            experience=5,
        )
        self.group1 = Groups.objects.create(
            group_name='Группа 1', start_year=2020,
            age_category='младшая', teacher=self.teacher,
        )
        self.group2 = Groups.objects.create(
            group_name='Группа 2', start_year=2021,
            age_category='средняя', teacher=self.teacher,
        )

        # Дети — для проверки фильтрации и списка
        self.child1 = Child.objects.create(
            last_name='Петров', first_name='Иван', gender='Мужской',
            address='ул. Первая, 1', birth_date=date(2020, 1, 1),
            start_date=date(2021, 9, 1), group=self.group1,
        )
        self.child2 = Child.objects.create(
            last_name='Сидорова', first_name='Анна', gender='Женский',
            address='ул. Вторая, 2', birth_date=date(2019, 5, 10),
            start_date=date(2021, 9, 1), group=self.group2,
        )

    def tearDown(self):
        self.driver.quit()

    # ---------- хелперы ----------

    def _login(self, username='Admin', password='password123'):
        self.driver.get(f'{self.live_server_url}/login/')
        self.driver.find_element(By.NAME, 'username').send_keys(username)
        self.driver.find_element(By.NAME, 'password').send_keys(password + Keys.ENTER)
        WebDriverWait(self.driver, 5).until(
            lambda d: '/login/' not in d.current_url
        )

    # ---------- тесты ----------

    def test_admin_can_open_create_form(self):
        self._login()
        self.driver.get(f'{self.live_server_url}/children/create/')

        self.assertIn('/children/create/', self.driver.current_url)

        for field in ['last_name', 'first_name', 'gender', 'address',
                      'birth_date', 'start_date', 'group']:
            self.assertIsNotNone(
                self.driver.find_element(By.NAME, field),
                f"Поле {field} не найдено на форме"
            )

    def test_regular_user_cannot_see_add_button(self):
        """Обычный пользователь не должен видеть кнопку добавления ребёнка."""
        self._login(username='user', password='password123')

        self.driver.get(f'{self.live_server_url}/children/')
        self.assertIn('Петров', self.driver.page_source)
        self.assertNotIn('/children/create/', self.driver.page_source)
        self.assertNotIn('/children/add/', self.driver.page_source)

        self.driver.get(f'{self.live_server_url}/children/create/')
        self.assertNotIn('name="last_name"', self.driver.page_source)

    def test_filter_by_group(self):
        """Фильтр по группе показывает только детей этой группы."""
        self._login()

        self.driver.get(f'{self.live_server_url}/children/?group={self.group1.pk}')
        self.assertIn('Петров', self.driver.page_source)
        self.assertNotIn('Сидорова', self.driver.page_source)

        self.driver.get(f'{self.live_server_url}/children/?group={self.group2.pk}')
        self.assertIn('Сидорова', self.driver.page_source)
        self.assertNotIn('Петров', self.driver.page_source)