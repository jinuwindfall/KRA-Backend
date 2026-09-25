from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0008_employeememo'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeememo',
            name='deduction',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
    ]
