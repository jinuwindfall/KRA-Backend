from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appraisals', '0005_appraisal_appraiser_remarks_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='appraisal',
            name='mark_entry_access_open',
            field=models.BooleanField(default=False),
        ),
    ]
