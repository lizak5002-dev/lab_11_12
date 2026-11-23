from django.db import models
from django.core.exceptions import ValidationError

class Groups(models.Model):
    group_id = models.AutoField(primary_key=True)
    group_name = models.CharField(unique=True, max_length=50)
    start_year = models.IntegerField()
    age_category = models.CharField(max_length=10)
    teacher = models.ForeignKey('Teacher', on_delete=models.PROTECT)  
    
    class Meta:
        db_table = 'groups'
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'
    
    def __str__(self):
        return self.group_name


class Teacher(models.Model):
    teacher_id = models.AutoField(primary_key=True)
    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    second_name = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    experience = models.IntegerField()
    
    class Meta:
        db_table = 'teacher'
        verbose_name = 'Воспитатель'
        verbose_name_plural = 'Воспитатели'
    
    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.second_name or ''}".strip()
    
    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.second_name:
            parts.append(self.second_name)
        return ' '.join(parts)


class Child(models.Model):
    child_id = models.AutoField(primary_key=True)
    last_name = models.CharField(max_length=50, verbose_name="Фамилия")
    first_name = models.CharField(max_length=50, verbose_name="Имя")
    second_name = models.CharField(max_length=50, blank=True, null=True, verbose_name="Отчество")
  
    GENDER_CHOICES = [
        ('Мужской', 'Мужской'),
        ('Женский', 'Женский'),
    ]
    
    gender = models.CharField(max_length=7, choices=GENDER_CHOICES, verbose_name="Пол")
    address = models.CharField(max_length=150, verbose_name="Адрес")
    birth_date = models.DateField(verbose_name="Дата рождения")
    allergies = models.TextField(blank=True, null=True, verbose_name="Аллергии")
    start_date = models.DateField(verbose_name="Дата поступления")
    group = models.ForeignKey('Groups', on_delete=models.PROTECT, verbose_name="Группа")  
    
    class Meta:
        db_table = 'child'
        verbose_name = 'Ребенок'
        verbose_name_plural = 'Дети'
    
    def __str__(self):
        if self.second_name:
            return f"{self.last_name} {self.first_name} {self.second_name}"
        return f"{self.last_name} {self.first_name}"

    def clean(self):
        super().clean()
        from datetime import date

        # Дата рождения не может быть в будущем
        if self.birth_date and self.birth_date > date.today():
            raise ValidationError({
                'birth_date': 'Дата рождения не может быть в будущем.'
            })

        # Дата поступления не может быть в будущем
        if self.start_date and self.start_date > date.today():
            raise ValidationError({
                'start_date': 'Дата поступления не может быть в будущем.'
            })

        # Дата поступления должна быть строго позже даты рождения
        if self.birth_date and self.start_date and self.birth_date >= self.start_date:
            raise ValidationError({
                'start_date': 'Дата поступления должна быть позже даты рождения.'
            })
    
    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.second_name:
            parts.append(self.second_name)
        return ' '.join(parts)
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        age = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            age -= 1
        return age


class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    child = models.ForeignKey('Child', on_delete=models.CASCADE, verbose_name="Ребёнок")  
    date = models.DateField(verbose_name="Дата")
    
    STATUS_CHOICES = [
        ('присутствовал', 'Присутствовал'),
        ('отсутствовал', 'Отсутствовал'),
    ]
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, verbose_name="Статус")
    
    class Meta:
        db_table = 'attendance'
        unique_together = (('child', 'date'),)
        verbose_name = 'Посещаемость'
        verbose_name_plural = 'Посещаемость'
    
    def __str__(self):
        return f"{self.child} - {self.date}: {self.get_status_display()}"


class Parent(models.Model):
    parent_id = models.AutoField(primary_key=True)
    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    second_name = models.CharField(max_length=50, blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    email = models.CharField(max_length=100)
    
    class Meta:
        db_table = 'parent'
        verbose_name = 'Родитель'
        verbose_name_plural = 'Родители'
    
    def __str__(self):
        if self.second_name:
            return f"{self.last_name} {self.first_name} {self.second_name}"
        return f"{self.last_name} {self.first_name}"
    
    @property
    def full_name(self):
        parts = [self.last_name, self.first_name]
        if self.second_name:
            parts.append(self.second_name)
        return ' '.join(parts)


class ParentChild(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, db_column='parent_id')
    child = models.ForeignKey(Child, on_delete=models.CASCADE, db_column='child_id')
    
    RELATIONSHIP_CHOICES = [
        ('Мать', 'Мать'),
        ('Отец', 'Отец'),
        ('Бабушка', 'Бабушка'),
        ('Дедушка', 'Дедушка'),
        ('Опекун', 'Опекун'),
        ('Другой', 'Другой'),
    ]
    
    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES,
        verbose_name='Тип связи'
    )
    
    class Meta:
        db_table = 'parent_child'
        verbose_name = 'Связь родитель-ребенок'
        verbose_name_plural = 'Связи родитель-ребенок'
        unique_together = [['parent_id', 'child_id']]
    
    def __str__(self):
        return f"{self.parent} → {self.child} ({self.relationship})"
