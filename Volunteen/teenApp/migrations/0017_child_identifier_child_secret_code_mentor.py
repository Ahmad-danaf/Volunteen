# Generated by Django 5.0.1 on 2024-05-02 14:14

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teenApp', '0016_remove_reward_qr_code_url'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='child',
            name='identifier',
            field=models.CharField(default=11111, max_length=5, verbose_name='Identifier'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='child',
            name='secret_code',
            field=models.CharField(default=100, max_length=3, verbose_name='Secret Code'),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='Mentor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]