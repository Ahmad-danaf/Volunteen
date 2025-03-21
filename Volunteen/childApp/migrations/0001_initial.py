# Generated by Django 5.0.1 on 2025-02-27 06:00

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Child',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('points', models.IntegerField(default=0, verbose_name='Points')),
                ('identifier', models.CharField(max_length=5, unique=True, verbose_name='Identifier')),
                ('secret_code', models.CharField(max_length=3, verbose_name='Secret Code')),
                ('streak_count', models.IntegerField(default=0, verbose_name='Streak Count')),
                ('last_streak_date', models.DateField(blank=True, null=True, verbose_name='Last Streak Date')),
                ('city', models.CharField(blank=True, choices=[('TLV', 'תל אביב יפו'), ('TAM', 'טמרה')], max_length=3, null=True, verbose_name='City')),
            ],
        ),
        migrations.CreateModel(
            name='Medal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Medal Name')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('points_reward', models.IntegerField(default=0, verbose_name='Points Reward')),
                ('criterion', models.CharField(max_length=255, verbose_name='Criterion Function')),
            ],
        ),
    ]
