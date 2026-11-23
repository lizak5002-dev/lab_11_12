from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.contrib import messages
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, FloatField, Value, CharField
from .models import Child, Attendance, Parent, Groups, Teacher, ParentChild
from .forms import ChildForm, AttendanceForm, FilterForm, CustomUserCreationForm, TeacherForm, GroupForm, ParentForm, ParentChildForm
from django.http import HttpResponse, JsonResponse
from reportlab.pdfgen import canvas
import openpyxl
from io import BytesIO
from django.contrib.auth import login
from datetime import date, datetime
from django.db.models.functions import Concat, TruncMonth, Cast
from django.core.paginator import Paginator
import json
from .utils.threaded_reports import ReportGeneratorThread
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl.styles import Font, Alignment, PatternFill
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm

# Декораторы для проверки ролей
def is_admin(user):
    return user.groups.filter(name='Admin').exists() or user.is_superuser

def is_user(user):
    return user.groups.filter(name='User').exists()

# Главная страница
def home(request):
    context = {
        'total_children': Child.objects.count(),
        'total_groups': Groups.objects.count(),
        'total_teachers': Teacher.objects.count(),
    }
    return render(request, 'home.html', context)

# Регистрация
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # По умолчанию добавляем в группу User
            user_group = Group.objects.get(name='User')
            user.groups.add(user_group)
            login(request, user)
            messages.success(request, 'Регистрация успешна!')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

# ===== ДЕТИ ================================================================================================

# Список детей
@login_required
def child_list(request):
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'last_name')
    sort_order = request.GET.get('order', 'asc')
    
    # Определяем направление сортировки
    order_by_field = sort_by
    if sort_order == 'desc':
        order_by_field = f'-{sort_by}'
    
    # Начальный запрос
    children = Child.objects.all()
    
    # Применяем сортировку
    if sort_by == 'last_name':
        children = children.order_by(order_by_field, 'first_name', 'second_name')
    elif sort_by == 'group_name':
        # Сортировка по названию группы через внешний ключ
        children = children.order_by(f'{"-" if sort_order == "desc" else ""}group__group_name', 
                                     'last_name', 'first_name')
    else:
        children = children.order_by(order_by_field)
    
    # Фильтрация по группе
    group_filter = request.GET.get('group')
    if group_filter and group_filter.isdigit():
        children = children.filter(group_id=group_filter)
    
    # Поиск
    search_query = request.GET.get('search')
    if search_query:
        search_query = search_query.strip()
        
        # Разбиваем на слова
        words = search_query.split()
        
        if len(words) == 2:
            # Для двух слов Ищем ИМЕННО сочетание
            children = children.filter(
                Q(last_name__icontains=words[0]) & Q(first_name__icontains=words[1])
            )
        else:
            # Для одного или многих слов - обычный поиск
            q_objects = Q()
            for word in words:
                q_objects |= Q(last_name__icontains=word) | \
                             Q(first_name__icontains=word) | \
                             Q(second_name__icontains=word)
            children = children.filter(q_objects)
    
    groups = Groups.objects.all()
    
    # Текстовое описание текущей сортировки для отображения
    sort_options = {
        'last_name_asc': 'По фамилии (А-Я)',
        'last_name_desc': 'По фамилии (Я-А)',
        'start_date_desc': 'По дате поступления (новые)',
        'start_date_asc': 'По дате поступления (старые)',
        'group_name_asc': 'По группе (А-Я)',
        'group_name_desc': 'По группе (Я-А)',
    }
    
    current_sort = f'{sort_by}_{sort_order}'
    current_sort_text = sort_options.get(current_sort, 'Сортировка')
    
    context = {
        'children': children,
        'groups': groups,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'current_sort_text': current_sort_text,
    }
    return render(request, 'children/child_list.html', context)

# Добавить ребенка (только админ)
@login_required
@user_passes_test(is_admin)
def child_create(request):
    if request.method == 'POST':
        form = ChildForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ребенок успешно добавлен!')
            return redirect('child_list')
    else:
        form = ChildForm()
    return render(request, 'children/child_form.html', {'form': form, 'title': 'Добавить ребенка'})

# Редактировать ребенка (только админ)
@login_required
@user_passes_test(is_admin)
def child_edit(request, pk):
    child = get_object_or_404(Child, pk=pk)
    if request.method == 'POST':
        form = ChildForm(request.POST, instance=child)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные ребенка обновлены!')
            return redirect('child_list')
    else:
        form = ChildForm(instance=child)
    return render(request, 'children/child_form.html', {'form': form, 'title': 'Редактировать ребенка'})

@login_required
@user_passes_test(is_admin)
def child_delete(request, pk):
    """Удалить ребенка (только POST)"""
    if request.method == 'POST':
        child = get_object_or_404(Child, pk=pk)
        child.delete()
        messages.success(request, 'Ребенок удален!')
        return redirect('child_list')
    
    # Для GET запроса - редирект на список
    return redirect('child_list')
    

# ===== ПОСЕЩАЕМОСТЬ =============================================================================================================

@login_required
def attendance_list(request):
    # Получаем записи с сортировкой по умолчанию (новые сначала)
    attendances_queryset = Attendance.objects.select_related('child', 'child__group').all()
    
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'date')
    sort_order = request.GET.get('order', 'desc')
    
    # Применяем сортировку
    if sort_by == 'date':
        if sort_order == 'asc':
            attendances_queryset = attendances_queryset.order_by('date', 'child__last_name')
        else:
            attendances_queryset = attendances_queryset.order_by('-date', 'child__last_name')
    elif sort_by == 'child':
        if sort_order == 'asc':
            attendances_queryset = attendances_queryset.order_by('child__last_name', 'child__first_name', '-date')
        else:
            attendances_queryset = attendances_queryset.order_by('-child__last_name', '-child__first_name', '-date')
    
    # Фильтрация
    form = FilterForm(request.GET)
    if form.is_valid():
        if form.cleaned_data['group']:
            attendances_queryset = attendances_queryset.filter(child__group=form.cleaned_data['group'])
        if form.cleaned_data['date_from']:
            attendances_queryset = attendances_queryset.filter(date__gte=form.cleaned_data['date_from'])
        if form.cleaned_data['date_to']:
            attendances_queryset = attendances_queryset.filter(date__lte=form.cleaned_data['date_to'])
    
    # Считаем статистику после фильтрации, но до пагинации
    total_count = attendances_queryset.count()
    present_count = attendances_queryset.filter(status='присутствовал').count()
    absent_count = attendances_queryset.filter(status='отсутствовал').count()
    
    # Добавляем пагинацию (по 50 записей на страницу)
    paginator = Paginator(attendances_queryset, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Получаем всех детей для фильтра в модальном окне
    all_children = Child.objects.select_related('group').all()
    
    # Передаем текущую дату для отображения "Сегодня"
    from datetime import date

    today = date.today()
    
    context = {
        'attendances': page_obj, 
        'total_count': total_count,  # Общее количество записей
        'present_count': present_count,
        'absent_count': absent_count,
        'all_children': all_children,
        'today': today,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'form': form,
        'page_obj': page_obj,  # Добавляем page_obj для удобства
        'paginator': paginator,  # Добавляем paginator
    }
    return render(request, 'attendance/attendance_list.html', context)

@login_required
def child_attendance_page(request, child_id):
    """Страница посещаемости конкретного ребенка"""
    child = get_object_or_404(Child, pk=child_id)
    attendances = Attendance.objects.filter(child=child).order_by('-date')
    
    context = {
        'child': child,
        'attendances': attendances,
    }
    return render(request, 'child_attendance_page.html', context)

@login_required
def mark_all_attendance(request):
    """Отметить всех детей в выбранной группе за сегодня"""
    if request.method == 'POST':
        try:
            group_id = request.POST.get('group_id')
            status = request.POST.get('status', 'присутствовал')
            attendance_date = request.POST.get('date', date.today())
            
            if not group_id:
                messages.error(request, 'Не выбрана группа')
                return redirect('child_list')
            
            group = get_object_or_404(Groups, pk=group_id)
            children = Child.objects.filter(group=group)
            
            created_count = 0
            updated_count = 0
            
            for child in children:
                # Проверяем, есть ли уже запись за сегодня
                existing_attendance = Attendance.objects.filter(
                    child=child,
                    date=attendance_date
                ).first()
                
                if existing_attendance:
                    # Обновляем существующую запись
                    if existing_attendance.status != status:
                        existing_attendance.status = status
                        existing_attendance.save()
                        updated_count += 1
                else:
                    # Создаем новую запись
                    Attendance.objects.create(
                        child=child,
                        date=attendance_date,
                        status=status
                    )
                    created_count += 1
            
            total_count = created_count + updated_count
            messages.success(request, 
                f'Успешно отмечено {total_count} детей в группе "{group.group_name}"! '
                f'(Добавлено: {created_count}, Обновлено: {updated_count})'
            )
            
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
    
    return redirect('child_list')

@login_required
def attendance_create(request):
    if request.method == 'POST':
        child_id = request.POST.get('child')
        date_str = request.POST.get('date')
        status = request.POST.get('status')
        
        try:
            child = Child.objects.get(pk=child_id)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Проверяем, существует ли уже запись за эту дату
            existing_attendance = Attendance.objects.filter(
                child=child,
                date=date_obj
            ).first()
            
            if existing_attendance:
                # Обновляем существующую запись
                existing_attendance.status = status
                existing_attendance.save()
                messages.success(request, f'Запись о посещаемости обновлена! (было: {existing_attendance.status})')
            else:
                # Создаем новую запись
                Attendance.objects.create(
                    child=child,
                    date=date_obj,
                    status=status
                )
                messages.success(request, 'Запись о посещаемости добавлена!')
                
        except ValueError:
            messages.error(request, 'Неверный формат даты')
        except Child.DoesNotExist:
            messages.error(request, 'Ребенок не найден')
        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')
        
        return redirect('attendance_list')
    
    return redirect('attendance_list')

# изменить запись о посещаемости
@login_required
def attendance_edit(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)
    
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Запись обновлена!')
            return redirect('attendance_list')
    else:
        form = AttendanceForm(instance=attendance)
    
    return render(request, 'attendance/attendance_form.html', {'form': form})

# удалить запись о посещаемости
@login_required
def attendance_delete(request, pk):
    attendance = get_object_or_404(Attendance, pk=pk)
    
    if request.method == 'POST':
        attendance.delete()
        messages.success(request, 'Запись удалена!')
        return redirect('attendance_list')
    
    return render(request, 'attendance_confirm_delete.html', {'attendance': attendance})


# ===== ВОСПИТАТЕЛИ =================================================================================================

@login_required
@user_passes_test(is_admin)
def teacher_list(request):
    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'last_name')
    sort_order = request.GET.get('order', 'asc')
    
    # Определяем направление сортировки
    order_by_field = sort_by
    if sort_order == 'desc':
        order_by_field = f'-{sort_by}'
    
    # Начальный запрос
    teachers = Teacher.objects.all()
    
    # Применяем сортировку
    if sort_by == 'last_name':
        teachers = teachers.order_by(order_by_field, 'first_name', 'second_name')
    else:
        children = children.order_by(order_by_field)
    
    # Поиск
    search_query = request.GET.get('search')
    if search_query:
        search_query = search_query.strip()
        
        # Разбиваем на слова
        words = search_query.split()
        
        if len(words) == 2:
            # Для двух слов Ищем ИМЕННО сочетание
            children = children.filter(
                Q(last_name__icontains=words[0]) & Q(first_name__icontains=words[1])
            )
        else:
            # Для одного или многих слов - обычный поиск
            q_objects = Q()
            for word in words:
                q_objects |= Q(last_name__icontains=word) | \
                             Q(first_name__icontains=word) | \
                             Q(second_name__icontains=word)
            teachers = teachers.filter(q_objects)
    
    # Текстовое описание текущей сортировки для отображения
    sort_options = {
        'last_name_asc': 'По фамилии (А-Я)',
        'last_name_desc': 'По фамилии (Я-А)'
    }
    
    current_sort = f'{sort_by}_{sort_order}'
    current_sort_text = sort_options.get(current_sort, 'Сортировка')
    
    context = {
        'teachers': teachers,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'current_sort_text': current_sort_text,
    }
    return render(request, 'teachers/list.html', context)


@login_required
@user_passes_test(is_admin)
def teacher_create(request):
    """Добавить воспитателя"""
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Воспитатель успешно добавлен!')
            return redirect('teacher_list')
    else:
        form = TeacherForm()
    return render(request, 'teachers/form.html', {'form': form, 'title': 'Добавить воспитателя'})

@login_required
@user_passes_test(is_admin)
def teacher_edit(request, pk):
    """Редактировать воспитателя"""
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        form = TeacherForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные воспитателя обновлены!')
            return redirect('teacher_list')
    else:
        form = TeacherForm(instance=teacher)
    return render(request, 'teachers/form.html', {'form': form, 'title': 'Редактировать воспитателя'})

@login_required
@user_passes_test(is_admin)
def teacher_delete(request, pk):
    """Удалить воспитателя"""
    teacher = get_object_or_404(Teacher, pk=pk)
    
    # Проверяем, есть ли у воспитателя группы
    has_groups = Groups.objects.filter(teacher=teacher).exists()
    
    if has_groups:
        messages.error(request, 'Нельзя удалить воспитателя, так как он привязан к группе!')
        return redirect('teacher_list')
    
    if request.method == 'POST':
        teacher.delete()
        messages.success(request, 'Воспитатель удален!')
        return redirect('teacher_list')

# ===== ГРУППЫ ============================================================================================================

@login_required
@user_passes_test(is_admin)
def group_list(request):
    """Список групп"""
    groups = Groups.objects.all()
    teachers = Teacher.objects.order_by('last_name').all()

    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'group_name')
    sort_order = request.GET.get('order', 'asc')
    
    # Определяем направление сортировки
    order_by_field = sort_by
    if sort_order == 'desc':
        order_by_field = f'-{sort_by}'
    
    # Применяем сортировку
    if sort_by == 'group_name':
        groups = groups.order_by(order_by_field, 'group_name')
    else:
        groups = groups.order_by(order_by_field)
    
    # Фильтрация по воспитателю
    teacher_filter = request.GET.get('teacher')
    if teacher_filter:
        groups = groups.filter(teacher_id=teacher_filter)
    
    # Поиск
    search_query = request.GET.get('search')
    if search_query:
        search_query = search_query.strip()
        
        # Разбиваем на слова
        words = search_query.split()
        
        q_objects = Q()
        for word in words:
            q_objects |= Q(group_name__icontains=word)
        groups = groups.filter(q_objects)
    
    paginator = Paginator(groups, 20)  # 20 групп на страницу
    page_number = request.GET.get('page')
    groups_page = paginator.get_page(page_number)
    
    # Текстовое описание текущей сортировки для отображения
    sort_options = {
        'group_name_asc': 'По названию (А-Я)',
        'group_name_desc': 'По названию (Я-А)',
        'start_year_desc': 'По дате начала обучения (новые)',
        'start_year_asc': 'По дате начала обучения (старые)'
    }
    
    current_sort = f'{sort_by}_{sort_order}'
    current_sort_text = sort_options.get(current_sort, 'Сортировка')
    
    context = {
        'groups': groups_page,
        'teachers': teachers,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'current_sort_text': current_sort_text,
    }
    return render(request, 'groups/list.html', context)

@login_required
@user_passes_test(is_admin)
def group_create(request):
    """Добавить группу"""
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Группа успешно добавлена!')
            return redirect('group_list')
    else:
        form = GroupForm()
    return render(request, 'groups/form.html', {'form': form, 'title': 'Добавить группу'})

@login_required
@user_passes_test(is_admin)
def group_edit(request, pk):
    """Редактировать группу"""
    group = get_object_or_404(Groups, pk=pk)
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные группы обновлены!')
            return redirect('group_list')
    else:
        form = GroupForm(instance=group)
    return render(request, 'groups/form.html', {'form': form, 'title': 'Редактировать группу'})

@login_required
@user_passes_test(is_admin)
def group_delete(request, pk):
    """Удалить группу"""
    group = get_object_or_404(Groups, pk=pk)
    
    # Проверяем, есть ли дети в группе
    has_children = Child.objects.filter(group=group).exists()
    
    if has_children:
        messages.error(request, 'Нельзя удалить группу, так как в ней есть дети!')
        return redirect('group_list')
    
    if request.method == 'POST':
        group.delete()
        messages.success(request, 'Группа удалена!')
        return redirect('group_list')


# ===== РОДИТЕЛИ ====================================================================================================================

@login_required
@user_passes_test(is_admin)
def parent_list(request):
    """Список родителей"""
    parents = Parent.objects.all()

    # Получаем параметры сортировки
    sort_by = request.GET.get('sort', 'first_name')
    sort_order = request.GET.get('order', 'asc')
    
    # Определяем направление сортировки
    order_by_field = sort_by
    if sort_order == 'desc':
        order_by_field = f'-{sort_by}'
    
    # Применяем сортировку
    if sort_by == 'first_name':
        parents = parents.order_by(order_by_field, 'first_name', 'second_name')
    else:
        parents = parents.order_by(order_by_field)
    
    # Поиск
    search_query = request.GET.get('search')
    if search_query:
        search_query = search_query.strip()
        
        # Разбиваем на слова
        words = search_query.split()
        
        if len(words) == 2:
            # Для двух слов Ищем ИМЕННО сочетание
            parents = parents.filter(
                Q(last_name__icontains=words[0]) & Q(first_name__icontains=words[1])
            )
        else:
            # Для одного или многих слов - обычный поиск
            q_objects = Q()
            for word in words:
                q_objects |= Q(last_name__icontains=word) | \
                             Q(first_name__icontains=word) | \
                             Q(second_name__icontains=word)
            parents = parents.filter(q_objects)
    
    # Текстовое описание текущей сортировки для отображения
    sort_options = {
        'last_name_asc': 'По фамилии (А-Я)',
        'last_name_desc': 'По фамилии (Я-А)'
    }
    
    current_sort = f'{sort_by}_{sort_order}'
    current_sort_text = sort_options.get(current_sort, 'Сортировка')
    
    context = {
        'parents': parents,
        'sort_by': sort_by,
        'sort_order': sort_order,
        'current_sort_text': current_sort_text,
    }
    return render(request, 'parents/list.html', context)


@login_required
@user_passes_test(is_admin)
def parent_create(request):
    """Добавить родителя"""
    if request.method == 'POST':
        form = ParentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Родитель успешно добавлен!')
            return redirect('parent_list')
    else:
        form = ParentForm()
    return render(request, 'parents/form.html', {'form': form, 'title': 'Добавить родителя'})

@login_required
@user_passes_test(is_admin)
def parent_edit(request, pk):
    """Редактировать родителя"""
    parent = get_object_or_404(Parent, pk=pk)
    if request.method == 'POST':
        form = ParentForm(request.POST, instance=parent)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные родителя обновлены!')
            return redirect('parent_list')
    else:
        form = ParentForm(instance=parent)
    return render(request, 'parents/form.html', {'form': form, 'title': 'Редактировать родителя'})

@login_required
@user_passes_test(is_admin)
def parent_delete(request, pk):
    """Удалить родителя"""
    parent = get_object_or_404(Parent, pk=pk)
    
    # Проверяем, есть ли связи с детьми
    has_children = ParentChild.objects.filter(parent=parent).exists()
    
    if has_children:
        messages.error(request, 'Нельзя удалить родителя, так как у него есть дети в системе!')
        return redirect('parent_list')
    
    if request.method == 'POST':
        parent.delete()
        messages.success(request, 'Родитель удален!')
        return redirect('parent_list')


# ===== СВЯЗИ РОДИТЕЛЬ-РЕБЕНОК ==========================================================================================================

@login_required
@user_passes_test(is_admin)
def parentchild_list(request):
    """Список связей родитель-ребенок"""
    relationships = ParentChild.objects.select_related('parent', 'child').all()
    
    # Поиск
    search_query = request.GET.get('search')
    if search_query:
        search_query = search_query.strip()
        
        # Разбиваем на слова
        words = search_query.split()
        
        q_objects = Q()
        for word in words:
            q_objects |= Q(parent__last_name__icontains=word) | \
                         Q(parent__first_name__icontains=word) | \
                         Q(parent__second_name__icontains=word) | \
                         Q(child__last_name__icontains=word) | \
                         Q(child__first_name__icontains=word) | \
                         Q(child__second_name__icontains=word)
        
        relationships = relationships.filter(q_objects)
    
    # Сортировка
    sort_by = request.GET.get('sort', 'parent__last_name')
    sort_order = request.GET.get('order', 'asc')
    
    # Определяем направление сортировки
    if sort_order == 'desc':
        sort_by = f'-{sort_by}'
    
    relationships = relationships.order_by(sort_by)
    
    # Пагинация
    paginator = Paginator(relationships, 20)
    page_number = request.GET.get('page')
    relationships_page = paginator.get_page(page_number)
    
    # Текстовое описание текущей сортировки
    sort_options = {
        'parent__last_name_asc': 'По фамилии родителя (А-Я)',
        'parent__last_name_desc': 'По фамилии родителя (Я-А)',
        'child__last_name_asc': 'По фамилии ребенка (А-Я)',
        'child__last_name_desc': 'По фамилии ребенка (Я-А)',
        'relationship_asc': 'По типу связи (А-Я)',
        'relationship_desc': 'По типу связи (Я-А)',
    }
    
    current_sort = f"{sort_by.lstrip('-')}_{sort_order}"
    current_sort_text = sort_options.get(current_sort, 'Сортировка')
    
    context = {
        'relationships': relationships_page,
        'sort_by': sort_by.lstrip('-'),
        'sort_order': sort_order,
        'current_sort_text': current_sort_text,
    }
    return render(request, 'parentchild/list.html', context)

@login_required
@user_passes_test(is_admin)
def parentchild_create(request):
    """Добавить связь родитель-ребенок"""
    if request.method == 'POST':
        form = ParentChildForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Связь успешно добавлена!')
            return redirect('parentchild_list')
    else:
        form = ParentChildForm()
    
    return render(request, 'parentchild/form.html', {
        'form': form,
        'title': 'Добавить связь родитель-ребенок',
    })

@login_required
@user_passes_test(is_admin)
def parentchild_edit(request, pk):
    """Редактирование связи родитель-ребенок"""
    relationship = get_object_or_404(ParentChild, pk=pk)
    
    if request.method == 'POST':
        form = ParentChildForm(request.POST, instance=relationship)
        if form.is_valid():
            form.save()
            messages.success(request, 'Связь успешно обновлена!')
            return redirect('parentchild_list')
    else:
        form = ParentChildForm(instance=relationship)
    
    context = {'form': form, 'relationship': relationship}
    return render(request, 'parentchild/form.html', context)

@login_required
@user_passes_test(is_admin)
def parentchild_delete(request, pk):
    """Удаление связи родитель-ребенок"""
    relationship = get_object_or_404(ParentChild, pk=pk)
    
    if request.method == 'POST':
        relationship.delete()
        messages.success(request, 'Связь успешно удалена!')
        return redirect('parentchild_list')
    
# ===== ОТЧЕТ ПО ПОСЕЩАЕМОСТИ 1: Статистика по группам ===============================================================================================

@login_required
def report_groups(request):
    """Показать отчет по группам в HTML"""
    groups_data, context = get_groups_report_data(request)
    return render(request, 'reports/groups.html', context)

@login_required
def report_groups_pdf(request):
    """Скачать отчет по группам в PDF"""
    groups_data, _ = get_groups_report_data(request)
    return generate_groups_pdf(groups_data)

@login_required
def report_groups_excel(request):
    """Скачать отчет по группам в Excel"""
    groups_data, _ = get_groups_report_data(request)
    return generate_groups_excel(groups_data)

def get_groups_report_data(request):
    """Общая функция для получения данных отчета (используется во всех форматах)"""
    # Получаем все группы
    groups_list = Groups.objects.all()
    
    # Применяем фильтры из GET-параметров
    year_filter = request.GET.get('year')
    age_category_filter = request.GET.get('age_category')
    
    if year_filter and year_filter.isdigit():
        groups_list = groups_list.filter(start_year=int(year_filter))
    
    if age_category_filter and age_category_filter != '':
        groups_list = groups_list.filter(age_category=age_category_filter)
    
    # Получаем уникальные значения для фильтров
    years = sorted(set(g.start_year for g in Groups.objects.all() if g.start_year), reverse=True)
    age_categories = sorted(set(g.age_category for g in Groups.objects.all() if g.age_category))
    
    # Создаем список для передачи в шаблон
    groups_data = []
    total_children = 0
    total_teachers = Teacher.objects.count()
    
    for group in groups_list:
        # Считаем детей в группе
        child_count = Child.objects.filter(group=group).count()
        total_children += child_count
        
        # Вычисляем средний возраст детей в группе
        children = Child.objects.filter(group=group)
        avg_age = 0
        if child_count > 0:
            total_age = 0
            today = date.today()
            for child in children:
                age = today.year - child.birth_date.year
                # Корректировка если день рождения еще не наступил
                if (today.month, today.day) < (child.birth_date.month, child.birth_date.day):
                    age -= 1
                total_age += age
            avg_age = total_age / child_count
        
        # Собираем данные группы
        group_data = {
            'pk': group.pk,
            'group_name': group.group_name,
            'age_category': group.age_category,
            'start_year': group.start_year,
            'teacher': group.teacher,
            'child_count': child_count,
            'avg_age': round(avg_age, 1) if avg_age > 0 else None,
        }
        groups_data.append(group_data)
    
    # Рассчитываем среднее количество детей в группе
    avg_children_per_group = total_children / len(groups_data) if groups_data else 0
    
    context = {
        'groups': groups_data,
        'years': years,
        'age_categories': age_categories,
        'total_children': total_children,
        'total_teachers': total_teachers,
        'avg_children_per_group': avg_children_per_group,
    }
    
    return groups_data, context

@login_required
def start_report_generation(request):
    """Запустить генерацию отчета в отдельном потоке"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            report_type = data.get('type')  # 'pdf' или 'excel'
            year_filter = data.get('year')
            age_category_filter = data.get('age_category')
            
            # Получаем данные для отчета
            groups_data, _ = get_groups_report_data(request)
            
            # Запускаем в отдельном потоке
            def report_callback(report_url, error=None):
                if error:
                    print(f"Ошибка: {error}")
                else:
                    print(f"Отчет сохранен: {report_url}")
            
            thread = ReportGeneratorThread(
                groups_data, 
                report_type, 
                callback=report_callback
            )
            thread.start()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Генерация {report_type} отчета запущена в фоновом режиме'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

import os
import platform
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def _find_font(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"Не найден ни один из шрифтов: {candidates}")


def generate_groups_pdf(groups):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="groups_report.pdf"'

    if platform.system() == 'Windows':
        regular_candidates = [
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/DejaVuSans.ttf',
        ]
        bold_candidates = [
            'C:/Windows/Fonts/arialbd.ttf',
            'C:/Windows/Fonts/DejaVuSans-Bold.ttf',
        ]
    else:
        regular_candidates = [
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        ]
        bold_candidates = [
            '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]

    regular_font = _find_font(regular_candidates)
    bold_font = _find_font(bold_candidates)

    pdfmetrics.registerFont(TTFont('Arial', regular_font))
    pdfmetrics.registerFont(TTFont('Arial-Bold', bold_font))

    font_name = 'Arial'
          
    # Используем BytesIO для создания PDF в памяти
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # Устанавливаем русский шрифт
    p.setFont(font_name, 16)
    p.drawString(100, 800, "Отчет по группам")
    
    p.setFont(font_name, 10)
    p.drawString(400, 800, f"Дата: {date.today().strftime('%d.%m.%Y')}")
    
    p.setFont(font_name, 12)
    y = 750
    
    # Заголовки таблицы
    p.drawString(50, y, "№")
    p.drawString(100, y, "Группа")
    p.drawString(250, y, "Возрастная категория")
    p.drawString(400, y, "Год открытия")
    p.drawString(480, y, "Кол-во детей")
    y -= 20
    p.line(50, y, 550, y)
    y -= 10
    
    # Данные
    for i, group in enumerate(groups, 1):
        if y < 50:
            p.showPage()
            y = 800
            p.setFont(font_name, 12)
        
        p.drawString(50, y, str(i))
        p.drawString(100, y, str(group.get('group_name', '')))
        p.drawString(250, y, str(group.get('age_category', '')))
        p.drawString(400, y, str(group.get('start_year', '')))
        p.drawString(480, y, str(group.get('child_count', 0)))
        y -= 20
    
    p.save()
    
    # Получаем значение из буфера и записываем в ответ
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

def generate_groups_excel(groups):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="groups_report.xlsx"'
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Группы"
    
    # Заголовки
    headers = ['№', 'Группа', 'Возрастная категория', 'Год открытия', 
               'Воспитатель', 'Количество детей', 'Средний возраст']
    
    for col, header in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=header)
    
    # Данные
    for row, group in enumerate(groups, 2):
        ws.cell(row=row, column=1, value=row-1)
        ws.cell(row=row, column=2, value=group.get('group_name', ''))
        ws.cell(row=row, column=3, value=group.get('age_category', ''))
        ws.cell(row=row, column=4, value=group.get('start_year', ''))
        
        teacher = group.get('teacher')
        if teacher:
            ws.cell(row=row, column=5, value=f"{teacher.last_name} {teacher.first_name}")
        
        ws.cell(row=row, column=6, value=group.get('child_count', 0))
        ws.cell(row=row, column=7, value=group.get('avg_age', ''))
    
    # Автоширина колонок
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width
    
    wb.save(response)
    return response

# ===== ОТЧЕТ ПО ПОСЕЩАЕМОСТИ 2: Статистика по посещаемости ===============================================================================================

@login_required
def report_attendance(request):
    """Показать отчет по посещаемости в HTML"""
    stats, groups_stats, totals = get_attendance_report_data(request)
    
    # Для фильтров
    months = [
        (1, 'Январь'), (2, 'Февраль'), (3, 'Март'), (4, 'Апрель'),
        (5, 'Май'), (6, 'Июнь'), (7, 'Июль'), (8, 'Август'),
        (9, 'Сентябрь'), (10, 'Октябрь'), (11, 'Ноябрь'), (12, 'Декабрь')
    ]
    
    # Получаем уникальные годы из записей посещаемости
    years = list(set(Attendance.objects.values_list('date__year', flat=True).distinct()))
    years.sort(reverse=True)
    
    all_groups = Groups.objects.all()
    
    # Добавляем тренды для отображения в HTML
    previous_percentage = None
    for stat in stats:
        if previous_percentage is not None:
            if stat['percentage'] > previous_percentage + 2:
                stat['trend'] = 'up'
            elif stat['percentage'] < previous_percentage - 2:
                stat['trend'] = 'down'
            else:
                stat['trend'] = 'same'
        else:
            stat['trend'] = 'same'
        previous_percentage = stat['percentage']
    
    context = {
        'stats': stats,
        'months': months,
        'years': years,
        'all_groups': all_groups,
        'total_present': totals['present'],
        'total_absent': totals['absent'],
        'total_days': totals['days'],
        'avg_attendance': totals['avg_attendance'],
        'best_group': totals['best_group'],
        'best_day': {'date': datetime.now()},  # Для шаблона
        'groups_stats': groups_stats,
    }
    
    return render(request, 'reports/attendance.html', context)

@login_required
def report_attendance_pdf(request):
    """Скачать отчет по посещаемости в PDF"""

    if platform.system() == 'Windows':
        regular_candidates = [
                'C:/Windows/Fonts/arial.ttf',
                'C:/Windows/Fonts/DejaVuSans.ttf',
            ]
        bold_candidates = [
                'C:/Windows/Fonts/arialbd.ttf',
                'C:/Windows/Fonts/DejaVuSans-Bold.ttf',
            ]
    else:
        regular_candidates = [
                '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            ]
        bold_candidates = [
                '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            ]
    
    regular_font = _find_font(regular_candidates)
    bold_font = _find_font(bold_candidates)
    
    pdfmetrics.registerFont(TTFont('Arial', regular_font))
    pdfmetrics.registerFont(TTFont('Arial-Bold', bold_font))
    font_name = 'Arial'
    # Получаем данные отчета
    stats, groups_stats, totals = get_attendance_report_data(request)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.pdf"'
    
    # Создаем PDF документ
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # Создаем стили
    styles = getSampleStyleSheet()
    
    # Русский стиль
    russian_style = ParagraphStyle(
        'RussianStyle',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,
        leading=12
    )
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontName=font_name,
        fontSize=16,
        spaceAfter=20
    )
    
    elements = []
    
    # Заголовок
    elements.append(Paragraph("Отчет по посещаемости", title_style))
    
    # Параметры отчета
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    group_filter = request.GET.get('group', '')
    
    params = []
    if month_filter:
        months_dict = dict([
            (1, 'Январь'), (2, 'Февраль'), (3, 'Март'), (4, 'Апрель'),
            (5, 'Май'), (6, 'Июнь'), (7, 'Июль'), (8, 'Август'),
            (9, 'Сентябрь'), (10, 'Октябрь'), (11, 'Ноябрь'), (12, 'Декабрь')
        ])
        params.append(f"Месяц: {months_dict.get(int(month_filter), month_filter)}")
    if year_filter:
        params.append(f"Год: {year_filter}")
    if group_filter:
        try:
            group = Groups.objects.get(pk=group_filter)
            params.append(f"Группа: {group.group_name}")
        except:
            params.append(f"Группа ID: {group_filter}")
    
    if params:
        elements.append(Paragraph("Параметры: " + "; ".join(params), russian_style))
    
    elements.append(Paragraph(f"Дата формирования: {date.today().strftime('%d.%m.%Y')}", russian_style))
    elements.append(Spacer(1, 20))
    
    # Сводная статистика
    summary_data = [
        ["Показатель", "Значение"],
        ["Всего дней в отчете", str(totals['days'])],
        ["Всего присутствовали", str(totals['present'])],
        ["Всего отсутствовали", str(totals['absent'])],
        ["Средняя посещаемость", f"{totals['avg_attendance']:.1f}%"],
        ["Лучшая группа", totals.get('best_group', 'Нет данных')],
        ["Лучший день", totals.get('best_day', 'Нет данных')],
    ]
    
    summary_table = Table(summary_data, colWidths=[4*cm, 4*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#4B8BBE')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (1, -1), font_name),
        ('FONTSIZE', (0, 0), (1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (1, -1), colors.HexColor('#F0F0F0')),
        ('GRID', (0, 0), (1, -1), 1, colors.black)
    ]))
    
    elements.append(Paragraph("Сводная статистика", russian_style))
    elements.append(Spacer(1, 10))
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # Детализированный отчет по месяцам
    if stats:
        elements.append(Paragraph("Посещаемость по месяцам", russian_style))
        elements.append(Spacer(1, 10))
        
        table_data = [["Месяц", "Присут.", "Отсут.", "Всего", "Посещаемость"]]
        
        for stat in stats:
            month_str = stat['month'].strftime("%B %Y") if stat['month'] else "Не указано"
            percentage = stat.get('percentage', 0)
            
            table_data.append([
                month_str,
                str(stat.get('present_count', 0)),
                str(stat.get('absent_count', 0)),
                str(stat.get('total_count', 0)),
                f"{percentage:.1f}%"
            ])
        
        table = Table(table_data, colWidths=[3*cm, 2*cm, 2*cm, 2*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4B8BBE')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0F0F0')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('TEXTCOLOR', (1, 1), (1, -1), colors.green),
            ('TEXTCOLOR', (2, 1), (2, -1), colors.red),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
    
    # Статистика по группам
    if groups_stats:
        elements.append(Paragraph("Статистика по группам", russian_style))
        elements.append(Spacer(1, 10))
        
        group_data = [["Группа", "Присут.", "Всего", "Посещаемость"]]
        
        for group in groups_stats[:10]:  # Ограничим 10 группами
            percentage = getattr(group, 'percentage', 0)
            group_data.append([
                getattr(group, 'group_name', ''),
                str(getattr(group, 'present', 0)),
                str(getattr(group, 'total', 0)),
                f"{percentage:.1f}%"
            ])
        
        group_table = Table(group_data, colWidths=[4*cm, 2*cm, 2*cm, 3*cm])
        group_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E8F5E8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(group_table)
    
    # Подпись
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(f"Отчет сформирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}", russian_style))
    elements.append(Paragraph(f"Пользователь: {request.user.username}", russian_style))
    
    # Собираем документ
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

@login_required
def report_attendance_excel(request):
    """Скачать отчет по посещаемости в Excel"""
    # Получаем данные отчета
    stats, groups_stats, totals = get_attendance_report_data(request)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.xlsx"'
    
    wb = openpyxl.Workbook()
    
    # Лист 1: Сводная статистика
    ws_summary = wb.active
    ws_summary.title = "Сводная статистика"
    
    # Заголовок
    ws_summary['A1'] = "Отчет по посещаемости"
    ws_summary['A1'].font = Font(size=16, bold=True)
    
    # Параметры
    row = 3
    month_filter = request.GET.get('month', '')
    year_filter = request.GET.get('year', '')
    group_filter = request.GET.get('group', '')
    
    if month_filter or year_filter or group_filter:
        ws_summary[f'A{row}'] = "Параметры отчета:"
        row += 1
        
        if month_filter:
            months_dict = dict([
                (1, 'Январь'), (2, 'Февраль'), (3, 'Март'), (4, 'Апрель'),
                (5, 'Май'), (6, 'Июнь'), (7, 'Июль'), (8, 'Август'),
                (9, 'Сентябрь'), (10, 'Октябрь'), (11, 'Ноябрь'), (12, 'Декабрь')
            ])
            ws_summary[f'A{row}'] = f"Месяц: {months_dict.get(int(month_filter), month_filter)}"
            row += 1
        
        if year_filter:
            ws_summary[f'A{row}'] = f"Год: {year_filter}"
            row += 1
        
        if group_filter:
            try:
                group = Groups.objects.get(pk=group_filter)
                ws_summary[f'A{row}'] = f"Группа: {group.group_name}"
            except:
                ws_summary[f'A{row}'] = f"Группа ID: {group_filter}"
            row += 1
    
    # Сводная статистика
    row += 1
    ws_summary[f'A{row}'] = "Сводная статистика"
    ws_summary[f'A{row}'].font = Font(size=14, bold=True)
    row += 1
    
    summary_data = [
        ["Показатель", "Значение"],
        ["Всего дней в отчете", totals['days']],
        ["Всего присутствовали", totals['present']],
        ["Всего отсутствовали", totals['absent']],
        ["Средняя посещаемость", f"{totals['avg_attendance']:.1f}%"],
        ["Лучшая группа", totals.get('best_group', 'Нет данных')],
        ["Лучший день", totals.get('best_day', 'Нет данных')],
    ]
    
    for i, (label, value) in enumerate(summary_data):
        ws_summary[f'A{row+i}'] = label
        ws_summary[f'B{row+i}'] = value
        
        if i == 0:  # Заголовок
            ws_summary[f'A{row+i}'].font = Font(bold=True)
            ws_summary[f'B{row+i}'].font = Font(bold=True)
            ws_summary[f'A{row+i}'].fill = PatternFill(start_color="4B8BBE", end_color="4B8BBE", fill_type="solid")
            ws_summary[f'B{row+i}'].fill = PatternFill(start_color="4B8BBE", end_color="4B8BBE", fill_type="solid")
    
    row += len(summary_data) + 2
    
    # Лист 2: Детализированный отчет
    ws_details = wb.create_sheet("По месяцам")
    
    ws_details['A1'] = "Посещаемость по месяцам"
    ws_details['A1'].font = Font(size=14, bold=True)
    
    headers = ["Месяц", "Присутствовали", "Отсутствовали", "Всего записей", "Посещаемость %"]
    for col, header in enumerate(headers, 1):
        cell = ws_details.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="4B8BBE", end_color="4B8BBE", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
    
    data_row = 4
    for stat in stats:
        month_str = stat['month'].strftime("%B %Y") if stat['month'] else "Не указано"
        percentage = stat.get('percentage', 0)
        
        ws_details.cell(row=data_row, column=1, value=month_str)
        ws_details.cell(row=data_row, column=2, value=stat.get('present_count', 0))
        ws_details.cell(row=data_row, column=3, value=stat.get('absent_count', 0))
        ws_details.cell(row=data_row, column=4, value=stat.get('total_count', 0))
        ws_details.cell(row=data_row, column=5, value=percentage)
        
        # Форматируем проценты
        percent_cell = ws_details.cell(row=data_row, column=5)
        percent_cell.number_format = '0.0"%"'
        
        data_row += 1
    
    # Лист 3: Статистика по группам
    ws_groups = wb.create_sheet("По группам")
    
    ws_groups['A1'] = "Статистика по группам"
    ws_groups['A1'].font = Font(size=14, bold=True)
    
    group_headers = ["Группа", "Присутствовали", "Всего записей", "Посещаемость %"]
    for col, header in enumerate(group_headers, 1):
        cell = ws_groups.cell(row=3, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
        cell.alignment = Alignment(horizontal='center')
    
    group_row = 4
    for group in groups_stats:
        percentage = getattr(group, 'percentage', 0)
        
        ws_groups.cell(row=group_row, column=1, value=getattr(group, 'group_name', ''))
        ws_groups.cell(row=group_row, column=2, value=getattr(group, 'present', 0))
        ws_groups.cell(row=group_row, column=3, value=getattr(group, 'total', 0))
        ws_groups.cell(row=group_row, column=4, value=percentage)
        
        # Форматируем проценты
        percent_cell = ws_groups.cell(row=group_row, column=4)
        percent_cell.number_format = '0.0"%"'
        
        group_row += 1
    
    # Автоширина колонок
    for ws in [ws_summary, ws_details, ws_groups]:
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    # Лист с метаданными
    ws_meta = wb.create_sheet("Информация")
    ws_meta['A1'] = "Информация об отчете"
    ws_meta['A1'].font = Font(size=14, bold=True)
    ws_meta['A3'] = f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    ws_meta['A4'] = f"Пользователь: {request.user.username}"
    ws_meta['A5'] = f"Всего записей: {totals['present'] + totals['absent']}"
    
    wb.save(response)
    return response

def get_attendance_report_data(request):
    
    # Применяем фильтры из запроса
    month_filter = request.GET.get('month')
    year_filter = request.GET.get('year')
    group_filter = request.GET.get('group')
    
    # Базовый QuerySet с фильтрацией
    attendance_qs = Attendance.objects.all()
    
    if month_filter and month_filter != '':
        attendance_qs = attendance_qs.filter(date__month=month_filter)
    
    if year_filter and year_filter != '':
        attendance_qs = attendance_qs.filter(date__year=year_filter)
    
    if group_filter and group_filter != '':
        attendance_qs = attendance_qs.filter(child__group_id=group_filter)
    
    # Статистика по месяцам
    stats = attendance_qs.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        present_count=Count('attendance_id', filter=Q(status='присутствовал')),
        absent_count=Count('attendance_id', filter=Q(status='отсутствовал')),
        total_count=Count('attendance_id')
    ).order_by('month')
    
    # Рассчитываем проценты
    for stat in stats:
        if stat['total_count'] > 0:
            stat['percentage'] = (stat['present_count'] / stat['total_count']) * 100
        else:
            stat['percentage'] = 0
    
    # Статистика по группам
    group_stats_qs = Groups.objects.all()
    
    if month_filter and month_filter != '':
        group_stats_qs = group_stats_qs.filter(child__attendance__date__month=month_filter)
    
    if year_filter and year_filter != '':
        group_stats_qs = group_stats_qs.filter(child__attendance__date__year=year_filter)
    
    if group_filter and group_filter != '':
        group_stats_qs = group_stats_qs.filter(pk=group_filter)
    
    group_stats = group_stats_qs.annotate(
        present=Count('child__attendance', filter=Q(child__attendance__status='присутствовал')),
        total=Count('child__attendance')
    ).filter(total__gt=0).annotate(
        percentage=ExpressionWrapper(
            F('present') * 100.0 / F('total'),
            output_field=FloatField()
        )
    ).order_by('-percentage')
    
    # Сводные данные
    total_present = attendance_qs.filter(status='присутствовал').count()
    total_absent = attendance_qs.filter(status='отсутствовал').count()
    total_days = attendance_qs.dates('date', 'day').distinct().count()
    
    total_records = total_present + total_absent
    avg_attendance = (total_present / total_records * 100) if total_records > 0 else 0
    
    # Лучшая группа
    best_group = group_stats.first()
    
    # Лучший день
    best_day_qs = attendance_qs.values('date').annotate(
        present=Count('attendance_id', filter=Q(status='присутствовал')),
        total=Count('attendance_id')
    ).filter(total__gt=0).annotate(
        percentage=ExpressionWrapper(
            F('present') * 100.0 / F('total'),
            output_field=FloatField()
        )
    ).order_by('-percentage').first()
    
    best_day_str = ""
    if best_day_qs:
        best_day_date = best_day_qs['date']
        best_day_percentage = best_day_qs.get('percentage', 0)
        best_day_str = f"{best_day_date.strftime('%d.%m.%Y')} ({best_day_percentage:.1f}%)"
    
    totals = {
        'days': total_days,
        'present': total_present,
        'absent': total_absent,
        'avg_attendance': avg_attendance,
        'best_group': getattr(best_group, 'group_name', 'Нет данных') if best_group else 'Нет данных',
        'best_day': best_day_str,
    }
    
    return list(stats), list(group_stats), totals

@login_required
def start_attendance_report_generation(request):
    """Запустить генерацию отчета по посещаемости в отдельном потоке"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            report_type = data.get('type')  # 'pdf' или 'excel'
            
            # Получаем параметры фильтрации
            month_filter = data.get('month')
            year_filter = data.get('year')
            group_filter = data.get('group')
            
            # Получаем данные для отчета
            stats, groups_stats, totals = get_attendance_report_data(request)
            
            # Запускаем в отдельном потоке
            def report_callback(report_url, error=None):
                if error:
                    print(f"Ошибка генерации отчета по посещаемости: {error}")
                else:
                    print(f"Отчет по посещаемости сохранен: {report_url}")
            
            thread = ReportGeneratorThread(
                stats, groups_stats, totals, report_type, 
                callback=report_callback
            )
            thread.start()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Генерация {report_type} отчета по посещаемости запущена'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

# ===== ДАШБОРД ==============================================================================================================================================

@login_required
def dashboard(request):
    today = date.today()
    
    # Посещаемость за сегодня
    today_attendances = Attendance.objects.filter(date=today)
    total_children_today = Child.objects.count()
    
    if today_attendances.exists():
        present_today = today_attendances.filter(status='присутствовал').count()
        percent_today = round((present_today / total_children_today) * 100) if total_children_today > 0 else 0
    else:
        # Если нет записей за сегодня, считаем всех присутствующими
        percent_today = 100
    
    today_attendance = {
        'percent': percent_today,
        'present': present_today if 'present_today' in locals() else total_children_today,
        'total': total_children_today }
    
    # Статистика для графиков
    children_by_group = list(Child.objects.values('group__group_name').annotate(
        count=Count('child_id')
    ))
    
    attendance_by_status = list(Attendance.objects.values('status').annotate(
        count=Count('attendance_id')
    ))
    
    # Последние посещения
    recent_attendances = Attendance.objects.select_related('child', 'child__group').order_by('-date')[:10]
    
    # Статистика по возрасту
    age_stats = []
    today = date.today()
    
    # Простая группировка по возрасту
    for child in Child.objects.all():
        age = today.year - child.birth_date.year
        # Корректировка если день рождения еще не наступил
        if (today.month, today.day) < (child.birth_date.month, child.birth_date.day):
            age -= 1
        
        # увеличиваем счетчик
        found = False
        for stat in age_stats:
            if stat['age'] == age:
                stat['count'] += 1
                found = True
                break
        
        if not found:
            age_stats.append({'age': age, 'count': 1})
    
    # Сортируем по возрасту
    age_stats = sorted(age_stats, key=lambda x: x['age'])
    
    # Если нет данных, создаем тестовые для демонстрации
    if not children_by_group:
        children_by_group = [{'group__group_name': 'Младшая группа', 'count': 12},
                           {'group__group_name': 'Средняя группа', 'count': 15},
                           {'group__group_name': 'Старшая группа', 'count': 18}]
    
    if not attendance_by_status:
        attendance_by_status = [{'status': 'присутствовал', 'count': 120},
                              {'status': 'отсутствовал', 'count': 25}]
    
    if not age_stats:
        age_stats = [{'age': 3, 'count': 5},
                     {'age': 4, 'count': 8},
                     {'age': 5, 'count': 6},
                     {'age': 6, 'count': 4}]
    
    
    # Подготовка данных для передачи в шаблон
    
    context = {
        'today_attendance': today_attendance,
        'children_by_group_json': json.dumps(children_by_group),  
        'attendance_by_status_json': json.dumps(attendance_by_status),  
        'age_stats_json': json.dumps(age_stats),
        'children_by_group': children_by_group,  # также передаем как список для отладки
        'attendance_by_status': attendance_by_status,
        'age_stats': age_stats,
        'recent_attendances': recent_attendances,
        'total_children': Child.objects.count(),
        'total_groups': Groups.objects.count(),
        'total_teachers': Teacher.objects.count(),
    }
    
    return render(request, 'dashboard.html', context)







