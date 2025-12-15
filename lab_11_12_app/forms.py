from django import forms
from .models import Child, Attendance, Parent, Groups, Teacher, Groups, Parent, Child, ParentChild
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# Форма для создания/редактирования ребенка
class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = '__all__'
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'allergies': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем классы Bootstrap ко всем полям
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput', 'RadioSelect']:
                field.widget.attrs['class'] = 'form-control'

# Форма для посещаемости
class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['child', 'date', 'status']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'child': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

# Форма для фильтрации
class FilterForm(forms.Form):
    group = forms.ModelChoiceField(
        queryset=Groups.objects.all(),
        required=False,
        label='Группа',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_from = forms.DateField(
        required=False,
        label='С даты',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_to = forms.DateField(
        required=False,
        label='По дату',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

# Форма для регистрации пользователей
class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['last_name', 'first_name', 'second_name', 'phone_number', 'experience']
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите фамилию'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите имя'}),
            'second_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите отчество'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (XXX) XXX-XX-XX'}),
            'experience': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Опыт работы в годах'}),
        }
        labels = {
            'last_name': 'Фамилия',
            'first_name': 'Имя',
            'second_name': 'Отчество',
            'phone_number': 'Телефон',
            'experience': 'Опыт работы (лет)',
        }

class GroupForm(forms.ModelForm):
    class Meta:
        model = Groups
        fields = ['group_name', 'start_year', 'age_category', 'teacher']
        widgets = {
            'group_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Солнышко'}),
            'start_year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Год открытия'}),
            'age_category': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('', 'Выберите категорию'),
                ('ясли', 'Ясельная (1-2 года)'),
                ('младшая', 'Младшая (3-4 года)'),
                ('средняя', 'Средняя (4-5 лет)'),
                ('старшая', 'Старшая (5-6 лет)'),
            ]),
            'teacher': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'group_name': 'Название группы',
            'start_year': 'Год открытия',
            'age_category': 'Возрастная категория',
            'teacher': 'Воспитатель',
        }

class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ['last_name', 'first_name', 'second_name', 'phone_number', 'email']
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'second_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}) 
            }
        labels = {
            'last_name': 'Фамилия',
            'first_name': 'Имя',
            'second_name': 'Отчество',
            'phone_number': 'Телефон',
            'email': 'Email'
        }

class ParentChildForm(forms.ModelForm):
    class Meta:
        model = ParentChild
        fields = ['parent', 'child', 'relationship']
        widgets = {
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'child': forms.Select(attrs={'class': 'form-select'}),
            'relationship': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'parent': 'Родитель',
            'child': 'Ребенок',
            'relationship': 'Тип связи',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Сортируем родителей и детей по алфавиту
        self.fields['parent'].queryset = Parent.objects.all().order_by('last_name', 'first_name')
        self.fields['child'].queryset = Child.objects.all().order_by('last_name', 'first_name')
        
        # Настраиваем отображение для полей select
        self.fields['parent'].label_from_instance = lambda obj: f"{obj.last_name} {obj.first_name} {obj.second_name or ''}".strip()
        self.fields['child'].label_from_instance = lambda obj: f"{obj.last_name} {obj.first_name} {obj.second_name or ''}".strip()
        
        # Добавляем пустой вариант для типа связи (если нужно)
        self.fields['relationship'].empty_label = 'Выберите тип связи'

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        child = cleaned_data.get('child')
        
        if parent and child:
            # Проверяем, существует ли уже такая связь
            exists = ParentChild.objects.filter(
                parent=parent, 
                child=child
            ).exists()
            
            if exists and not self.instance.pk:  # Только для создания, не для редактирования
                raise forms.ValidationError('Такая связь уже существует!')
        
        return cleaned_data