from django.db import migrations


def create_user_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='User')


def delete_user_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='User').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('lab_11_12_app', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_user_group, delete_user_group),
    ]