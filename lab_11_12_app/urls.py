from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Главная
    path('', views.home, name='home'),
    
    # Аутентификация
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    
    # Дети
    path('children/', views.child_list, name='child_list'),
    path('children/create/', views.child_create, name='child_create'),
    path('children/<int:pk>/edit/', views.child_edit, name='child_edit'),
    path('children/<int:pk>/delete/', views.child_delete, name='child_delete'),
    
    # Посещаемость
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('attendance/create/', views.attendance_create, name='attendance_create'),
    path('attendance/<int:pk>/edit/', views.attendance_edit, name='attendance_edit'),
    path('attendance/<int:pk>/delete/', views.attendance_delete, name='attendance_delete'),
    path('children/<int:child_id>/attendance/', views.child_attendance_page, name='child_attendance'),
    path('attendance/mark-all/', views.mark_all_attendance, name='mark_all_attendance'),
    
    # Отчеты
    path('reports/groups/', views.report_groups, name='report_groups'),
    path('reports/groups/pdf/', views.report_groups_pdf, name='report_groups_pdf'),
    path('reports/groups/excel/', views.report_groups_excel, name='report_groups_excel'),
    path('reports/attendance/', views.report_attendance, name='report_attendance'),
    path('reports/start-generation/', views.start_report_generation, name='start_report_generation'),
    path('reports/attendance/pdf/', views.report_attendance_pdf, name='report_attendance_pdf'),
    path('reports/attendance/excel/', views.report_attendance_excel, name='report_attendance_excel'),
    path('reports/start-attendance-generation/', views.start_attendance_report_generation, name='start_attendance_report_generation'),

    
    # Дашборд
    path('dashboard/', views.dashboard, name='dashboard'),

    # Воспитатели
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/create/', views.teacher_create, name='teacher_create'),
    path('teachers/<int:pk>/edit/', views.teacher_edit, name='teacher_edit'),
    path('teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),
    
    # Группы
    path('groups/', views.group_list, name='group_list'),
    path('groups/create/', views.group_create, name='group_create'),
    path('groups/<int:pk>/edit/', views.group_edit, name='group_edit'),
    path('groups/<int:pk>/delete/', views.group_delete, name='group_delete'),
    
    # Родители
    path('parents/', views.parent_list, name='parent_list'),
    path('parents/create/', views.parent_create, name='parent_create'),
    path('parents/<int:pk>/edit/', views.parent_edit, name='parent_edit'),
    path('parents/<int:pk>/delete/', views.parent_delete, name='parent_delete'),
    
    # Родитель-ребёнок
    path('parent-child/', views.parentchild_list, name='parentchild_list'),
    path('parent-child/create/', views.parentchild_create, name='parentchild_create'),
    path('parent-child/<int:pk>/edit/', views.parentchild_edit, name='parentchild_edit'),
    path('parent-child/<int:pk>/delete/', views.parentchild_delete, name='parentchild_delete'),
]