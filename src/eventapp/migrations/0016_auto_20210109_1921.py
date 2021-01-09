# Generated by Django 3.1.3 on 2021-01-09 22:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventapp', '0015_imovelupdatelog_datetime_started'),
    ]

    operations = [
        migrations.AddField(
            model_name='imovelupdatelog',
            name='progresso',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name='imovelupdatelog',
            name='state',
            field=models.SmallIntegerField(default=0),
        ),
    ]
