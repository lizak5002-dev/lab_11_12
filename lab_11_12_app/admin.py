from django.contrib import admin
from .models import Groups, Teacher, Child, Attendance, Parent, ParentChild

@admin.register(Groups)
class GroupsAdmin(admin.ModelAdmin):
    list_display = ['group_name', 'age_category', 'start_year', 'teacher']
    list_filter = ['age_category', 'start_year']
    search_fields = ['group_name']

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'phone_number', 'experience']
    search_fields = ['last_name', 'first_name']

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'gender', 'birth_date', 'group']
    list_filter = ['gender', 'group', 'birth_date']
    search_fields = ['last_name', 'first_name']
    date_hierarchy = 'birth_date'

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['child', 'date', 'status']
    list_filter = ['date', 'status']
    search_fields = ['child__last_name', 'child__first_name']
    date_hierarchy = 'date'

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'phone_number', 'email']
    search_fields = ['last_name', 'first_name', 'phone_number']

@admin.register(ParentChild)
class ParentChildAdmin(admin.ModelAdmin):
    list_display = ['parent', 'child', 'relationship']
    list_filter = ['relationship']