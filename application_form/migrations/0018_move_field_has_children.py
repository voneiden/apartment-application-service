# Generated by Django 2.2.21 on 2021-06-03 13:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("application_form", "0017_add_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="applicant",
            name="has_children",
        ),
        migrations.AddField(
            model_name="application",
            name="has_children",
            field=models.BooleanField(default=False, verbose_name="has children"),
        ),
    ]
