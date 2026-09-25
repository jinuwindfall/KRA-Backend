from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appraisals', '0009_period_scoped_template_and_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appraisal',
            name='status',
            field=models.CharField(
                choices=[
                    ('Draft', 'Draft'),
                    ('Appraiser Submitted', 'Appraiser Submitted'),
                    ('Employee Submitted', 'Employee Submitted'),
                    ('Reviewed', 'Reviewed'),
                ],
                default='Draft',
                max_length=20,
            ),
        ),
    ]
