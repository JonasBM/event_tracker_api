# Generated by Django 3.1.3 on 2021-05-03 21:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventapp', '0022_auto_20210408_1916'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='user_type',
            field=models.CharField(choices=[('AU', 'Auditor'), ('AS', 'Assistente'), ('PA', 'Particular')], default='PA', max_length=2),
        ),
    ]
