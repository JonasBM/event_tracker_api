# Generated by Django 3.1.3 on 2023-03-05 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventapp', '0027_imovel_cnpj_cpf'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='imovel',
            name='filedatetime',
        ),
        migrations.AddField(
            model_name='imovelupdatelog',
            name='falhas',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='imovel',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
