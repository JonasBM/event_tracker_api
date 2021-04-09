# Generated by Django 3.1.3 on 2021-04-08 22:16

from django.db import migrations, models
import eventapp.models


class Migration(migrations.Migration):

    dependencies = [
        ('eventapp', '0021_auto_20210407_0933'),
    ]

    operations = [
        migrations.AlterField(
            model_name='noticeeventtypefile',
            name='file_doc',
            field=models.FileField(upload_to=eventapp.models.auto_directory_path),
        ),
        migrations.AlterField(
            model_name='noticeeventtypefile',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AddConstraint(
            model_name='noticeeventtypefile',
            constraint=models.UniqueConstraint(fields=('name', 'notice_event_type'), name='unique_name_per_type'),
        ),
    ]
