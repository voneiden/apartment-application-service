# Generated by Django 3.2.6 on 2022-01-20 12:20

from django.db import migrations, models
import enumfields.fields
import invoicing.enums


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ApartmentInstallment",
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
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="created at"),
                ),
                (
                    "type",
                    enumfields.fields.EnumField(
                        enum=invoicing.enums.InstallmentType,
                        max_length=32,
                        verbose_name="type",
                    ),
                ),
                (
                    "value",
                    models.DecimalField(
                        decimal_places=2, max_digits=16, verbose_name="value"
                    ),
                ),
                (
                    "unit",
                    enumfields.fields.EnumField(
                        enum=invoicing.enums.InstallmentUnit,
                        max_length=32,
                        verbose_name="unit",
                    ),
                ),
                (
                    "percentage_specifier",
                    enumfields.fields.EnumField(
                        blank=True,
                        enum=invoicing.enums.InstallmentPercentageSpecifier,
                        max_length=32,
                        null=True,
                        verbose_name="percentage specifier",
                    ),
                ),
                (
                    "account_number",
                    models.CharField(max_length=255, verbose_name="account number"),
                ),
                (
                    "due_date",
                    models.DateField(blank=True, null=True, verbose_name="due date"),
                ),
                ("apartment_uuid", models.UUIDField(verbose_name="apartment UUID")),
                (
                    "reference_number",
                    models.CharField(
                        blank=True, max_length=64, verbose_name="reference number"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ProjectInstallmentTemplate",
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
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="created at"),
                ),
                (
                    "type",
                    enumfields.fields.EnumField(
                        enum=invoicing.enums.InstallmentType,
                        max_length=32,
                        verbose_name="type",
                    ),
                ),
                (
                    "value",
                    models.DecimalField(
                        decimal_places=2, max_digits=16, verbose_name="value"
                    ),
                ),
                (
                    "unit",
                    enumfields.fields.EnumField(
                        enum=invoicing.enums.InstallmentUnit,
                        max_length=32,
                        verbose_name="unit",
                    ),
                ),
                (
                    "percentage_specifier",
                    enumfields.fields.EnumField(
                        blank=True,
                        enum=invoicing.enums.InstallmentPercentageSpecifier,
                        max_length=32,
                        null=True,
                        verbose_name="percentage specifier",
                    ),
                ),
                (
                    "account_number",
                    models.CharField(max_length=255, verbose_name="account number"),
                ),
                (
                    "due_date",
                    models.DateField(blank=True, null=True, verbose_name="due date"),
                ),
                ("project_uuid", models.UUIDField(verbose_name="project UUID")),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
