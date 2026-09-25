from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appraisals', '0010_rename_appraisal_statuses'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appraisal',
            name='status',
            field=models.CharField(
                choices=[
                    ('Draft', 'Draft'),
                    ('Employee Submitted', 'Employee Submitted'),
                    ('Appraiser Submitted', 'Appraiser Submitted'),
                    ('Reviewed', 'Reviewed'),
                ],
                default='Draft',
                max_length=20,
            ),
        ),
    ]
