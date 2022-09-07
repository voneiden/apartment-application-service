# Generated by Django 3.2.12 on 2022-07-13 11:40

import enumfields.fields
import pgcrypto.fields
from django.db import migrations, models

from apartment_application_service.settings import (
    METADATA_HANDLER_INFORMATION,
    METADATA_HASO_PROCESS_NUMBER,
    METADATA_HITAS_PROCESS_NUMBER,
)
from application_form.enums import ApplicationArrivalMethod, ApplicationType


def populate_metadata(apps, schema_editor):
    Application = apps.get_model("application_form", "Application")
    for instance in Application.objects.all():
        instance.handler_information = METADATA_HANDLER_INFORMATION
        if instance.type == ApplicationType.HASO:
            instance.process_number = METADATA_HASO_PROCESS_NUMBER
        else:
            # Puolihitas and hitas using the same process number
            instance.process_number = METADATA_HITAS_PROCESS_NUMBER
        instance.method_of_arrival = ApplicationArrivalMethod.ELECTRONICAL_SYSTEM
        instance.sender_names = f"{instance.customer.primary_profile.first_name} {instance.customer.primary_profile.last_name}"
        instance.save()


class Migration(migrations.Migration):

    dependencies = [
        ("application_form", "0064_add_missing_hitas_and_haso_fields_to_reservation"),
    ]

    operations = [
        migrations.AddField(
            model_name="apartmentreservation",
            name="handler",
            field=pgcrypto.fields.CharPGPPublicKeyField(
                blank=True, null=True, max_length=200, verbose_name="handler"
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="handler_information",
            preserve_default=False,
            field=models.CharField(
                default="", max_length=100, verbose_name="handler information"
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="method_of_arrival",
            field=enumfields.fields.EnumField(
                default="electronical_system",
                enum=ApplicationArrivalMethod,
                max_length=50,
                verbose_name="method of arrival",
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="process_number",
            preserve_default=False,
            field=models.CharField(
                default="", max_length=32, verbose_name="process number"
            ),
        ),
        migrations.AddField(
            model_name="application",
            name="sender_names",
            field=pgcrypto.fields.CharPGPPublicKeyField(
                blank=True, null=True, max_length=200, verbose_name="sender names"
            ),
        ),
        migrations.AddField(
            model_name="lotteryevent",
            name="handler",
            field=pgcrypto.fields.CharPGPPublicKeyField(
                blank=True, null=True, max_length=200, verbose_name="handler"
            ),
        ),
        migrations.AddField(
            model_name="offer",
            name="handler",
            field=pgcrypto.fields.CharPGPPublicKeyField(
                blank=True, null=True, max_length=200, verbose_name="handler"
            ),
        ),
        migrations.RunPython(populate_metadata, reverse_code=migrations.RunPython.noop),
    ]
