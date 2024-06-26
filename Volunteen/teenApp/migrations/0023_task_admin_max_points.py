# Generated by Django 5.0.1 on 2024-05-31 19:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teenApp', '0022_task_completed_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='admin_max_points',
            field=models.IntegerField(default=0, help_text='Max bonus points assigned to this task', verbose_name='Max Bonus Points'),
        ),
    ]
