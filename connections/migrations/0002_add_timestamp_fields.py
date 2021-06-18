# Generated by Django 2.2.21 on 2021-06-09 13:22

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("connections", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mappedapartment",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="mappedapartment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
