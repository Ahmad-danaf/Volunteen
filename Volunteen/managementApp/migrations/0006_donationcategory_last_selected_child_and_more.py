# Generated by Django 5.0.1 on 2025-04-30 06:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('childApp', '0005_child_campaign_ban_until'),
        ('managementApp', '0005_donationspending_shop'),
    ]

    operations = [
        migrations.AddField(
            model_name='donationcategory',
            name='last_selected_child',
            field=models.ForeignKey(blank=True, help_text='Round-robin pointer: child picked last in the most recent spending; used to rotate queue on the next one', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='childApp.child'),
        ),
        migrations.AddIndex(
            model_name='donationtransaction',
            index=models.Index(fields=['category', 'date_donated'], name='managementA_categor_d59f24_idx'),
        ),
    ]
