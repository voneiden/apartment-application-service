# Generated by Django 2.2.21 on 2021-06-03 13:08

import django.db.models.deletion
import enumfields.fields
import uuid
from django.db import migrations, models

import application_form.enums


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_auto_20210527_0953"),
        ("apartment", "0004_apartment_identifier_project"),
        ("application_form", "0014_delete_application"),
    ]

    operations = [
        migrations.CreateModel(
            name="Application",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        verbose_name="application identifier",
                    ),
                ),
                (
                    "applicants_count",
                    models.PositiveSmallIntegerField(verbose_name="applicants count"),
                ),
                (
                    "type",
                    enumfields.fields.EnumField(
                        enum=application_form.enums.ApplicationType,
                        max_length=15,
                        verbose_name="application type",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="ApplicationApartment",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "priority_number",
                    models.PositiveSmallIntegerField(verbose_name="priority number"),
                ),
                (
                    "apartment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="apartment.Apartment",
                    ),
                ),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="application_form.Application",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="application",
            name="apartments",
            field=models.ManyToManyField(
                through="application_form.ApplicationApartment",
                to="apartment.Apartment",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="users.Profile"
            ),
        ),
    ]
