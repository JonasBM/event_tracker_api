# Generated by Django 3.1.3 on 2023-03-05 16:01

from django.db import migrations
import eventtracker.custom_fields


class Migration(migrations.Migration):

    dependencies = [
        ('eventapp', '0026_auto_20230305_1124'),
    ]

    operations = [
        migrations.AddField(
            model_name='imovel',
            name='cnpj_cpf',
            field=eventtracker.custom_fields.NumberCharField(default=None, max_length=14, null=True),
        ),
    ]
