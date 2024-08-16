# Generated by Django 5.0.1 on 2024-05-31 21:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teenApp', '0021_task_total_bonus_points'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='completed_date',
            field=models.DateTimeField(blank=True, help_text='The date when the task was completed', null=True, verbose_name='Completed Date'),
        ),
    ]