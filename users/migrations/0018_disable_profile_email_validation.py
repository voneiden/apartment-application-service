# Generated by Django 3.2.15 on 2022-08-25 11:40

from django.db import migrations
import pgcrypto.fields


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0017_add_salesperson_group"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="email",
            field=pgcrypto.fields.CharPGPPublicKeyField(
                blank=True, max_length=254, verbose_name="email address"
            ),
        ),
    ]
