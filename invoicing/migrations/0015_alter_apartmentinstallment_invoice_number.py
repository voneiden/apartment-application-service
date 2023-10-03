# Generated by Django 3.2.15 on 2023-01-12 12:27
import logging

import django.core.validators
from django.db import migrations, models


def fix_empty_invoice_numbers(apps, schema_editor):
    # noinspection PyPep8Naming
    ApartmentInstallment = apps.get_model("invoicing", "ApartmentInstallment")
    empty_invoice_numbers = ApartmentInstallment.objects.filter(invoice_number="")
    if empty_invoice_numbers:
        highest_invoice_number = (
            int(
                (
                    ApartmentInstallment.objects.exclude(invoice_number="")
                    .order_by("-invoice_number")
                    .first()
                ).invoice_number
            )
            + 1
        )
        for installment in empty_invoice_numbers:
            if installment.sent_to_sap_at is not None:
                raise ValueError(
                    f"Can not update installment {installment.id} because it is already sent to SAP!"
                )
            installment.invoice_number = highest_invoice_number

            highest_invoice_number += 1
            installment.save(update_fields=("invoice_number",))


class Migration(migrations.Migration):

    dependencies = [
        ("invoicing", "0014_add_payment_batch"),
    ]

    operations = [
        migrations.RunPython(fix_empty_invoice_numbers),
        migrations.AlterField(
            model_name="apartmentinstallment",
            name="invoice_number",
            field=models.IntegerField(
                unique=True,
                validators=[
                    django.core.validators.MinValueValidator(730000001),
                    django.core.validators.MaxValueValidator(999999999),
                ],
                verbose_name="invoice number",
            ),
        ),
    ]