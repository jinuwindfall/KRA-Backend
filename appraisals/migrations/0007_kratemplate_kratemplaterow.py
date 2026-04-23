from django.db import migrations, models
import django.db.models.deletion
import appraisals.models


class Migration(migrations.Migration):

    dependencies = [
        ('appraisals', '0006_appraisal_mark_entry_access_open'),
        ('appraisals', '0008_appraisal_extra_appraiser_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='KRATemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('frame_config', models.JSONField(blank=True, default=appraisals.models.default_frame_config)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'KRA Template',
            },
        ),
        migrations.CreateModel(
            name='KRATemplateRow',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('section', models.CharField(max_length=30)),
                ('sl_no', models.PositiveIntegerField(default=1)),
                ('max_mark', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rows', to='appraisals.kratemplate')),
            ],
            options={
                'ordering': ['section', 'sl_no'],
            },
        ),
    ]
