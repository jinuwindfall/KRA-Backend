from django.db import migrations
import re


def _normalize_username_base(name, emp_id):
    merged = ''.join((name or '').split()).lower()
    merged = re.sub(r'[^a-z0-9@.+_-]', '', merged)
    if merged:
        return merged
    fallback = ''.join(str(emp_id or '').split()).lower()
    fallback = re.sub(r'[^a-z0-9@.+_-]', '', fallback)
    return fallback or 'user'


def _unique_username(User, base, emp_id, current_user_id):
    candidate = base
    suffix = 1
    while True:
        exists = User.objects.filter(username=candidate).exclude(id=current_user_id).exists()
        if not exists:
            return candidate
        if suffix == 1:
            candidate = f"{base}{_normalize_username_base('', emp_id)}"
        else:
            candidate = f"{base}{suffix}"
        suffix += 1


def normalize_all_usernames(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Employee = apps.get_model('employees', 'Employee')

    for employee in Employee.objects.select_related('user').all():
        user = employee.user
        full_name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
        base = _normalize_username_base(full_name, employee.emp_id)
        username = _unique_username(User, base, employee.emp_id, user.id)
        if user.username != username:
            user.username = username
            user.save(update_fields=['username'])


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0006_add_gender_to_employee'),
    ]

    operations = [
        migrations.RunPython(normalize_all_usernames, migrations.RunPython.noop),
    ]
