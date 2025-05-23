# Generated by Django 5.0.1 on 2025-05-04 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shopApp', '0010_shop_address_shop_latitude_shop_longitude'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='shop',
            name='latitude',
        ),
        migrations.RemoveField(
            model_name='shop',
            name='longitude',
        ),
        migrations.AddField(
            model_name='shop',
            name='google_maps_link',
            field=models.URLField(blank=True, null=True, verbose_name='Google Maps Link'),
        ),
        migrations.AddField(
            model_name='shop',
            name='waze_link',
            field=models.URLField(blank=True, null=True, verbose_name='Waze Link'),
        ),
    ]
