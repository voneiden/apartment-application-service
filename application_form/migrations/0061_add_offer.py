# Generated by Django 3.2.12 on 2022-05-13 12:39

import application_form.enums
from django.db import migrations, models
import django.db.models.deletion
import enumfields.fields


class Migration(migrations.Migration):

    dependencies = [
        (
            "application_form",
            "0060_change_contract_terminated_to_reservation_agreement_canceled",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="Offer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("valid_until", models.DateField(verbose_name="valid until")),
                (
                    "state",
                    enumfields.fields.EnumField(
                        default="pending",
                        enum=application_form.enums.OfferState,
                        max_length=10,
                        verbose_name="state",
                    ),
                ),
                (
                    "concluded_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="concluded at"
                    ),
                ),
                ("comment", models.TextField(blank=True, verbose_name="comment")),
                (
                    "apartment_reservation",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="offer",
                        to="application_form.apartmentreservation",
                        verbose_name="apartment reservation",
                    ),
                ),
            ],
            options={
                "ordering": ("id",),
            },
        ),
    ]