from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('appraisals', '0008_appraisal_status_appraiser_reviewed'),
    ]

    operations = [
        migrations.AddField(
            model_name='kratemplate',
            name='period_from',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='kratemplate',
            name='period_to',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='appraisal',
            index=models.Index(fields=['period_from'], name='appraisals_a_period__2af2dc_idx'),
        ),
        migrations.AddIndex(
            model_name='appraisal',
            index=models.Index(fields=['period_to'], name='appraisals_a_period__1987e4_idx'),
        ),
        migrations.AddIndex(
            model_name='appraisal',
            index=models.Index(fields=['employee', 'period_from', 'period_to'], name='appraisals_a_employe_3fbf00_idx'),
        ),
    ]
