import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0010_alter_employee_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeememo',
            name='period_from',
            field=models.DateField(default=datetime.date.today),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='employeememo',
            name='period_to',
            field=models.DateField(default=datetime.date.today),
            preserve_default=False,
        ),
    ]
