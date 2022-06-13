# Generated by Django 3.2.12 on 2022-05-17 12:46

from django.db import migrations


forwards_sql = """
UPDATE application_form_apartmentreservationstatechangeevent
SET cancellation_reason = 'reservation_agreement_canceled'
WHERE cancellation_reason = 'contract_terminated';
"""

backwards_sql = """
UPDATE application_form_apartmentreservationstatechangeevent
SET cancellation_reason = 'contract_terminated'
WHERE cancellation_reason = 'reservation_agreement_canceled';
"""


class Migration(migrations.Migration):

    dependencies = [
        ("application_form", "0059_apartmentreservationstatechangeevent_replaced_by"),
    ]

    operations = [migrations.RunSQL(forwards_sql, backwards_sql)]