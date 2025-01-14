from datetime import date, datetime, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import UniqueConstraint
from django.utils import timezone
from django.utils.timezone import localdate, now
from django.utils.translation import gettext_lazy as _
from enumfields import EnumField
from pgcrypto.fields import CharPGPPublicKeyField
from uuid import uuid4

from application_form.models import ApartmentReservation
from invoicing.enums import (
    InstallmentPercentageSpecifier,
    InstallmentType,
    InstallmentUnit,
    PaymentStatus,
)
from invoicing.utils import (
    generate_reference_number,
    get_euros_from_cents,
    get_rounded_price,
)

User = get_user_model()


class AlreadyAddedToBeSentToSapError(Exception):
    pass


class InstallmentBase(models.Model):
    # we are not inheriting TimestampedModel because we want to be able to set values
    # for these manually to get exactly the same values for installments that are
    # created / updated on the same request
    created_at = models.DateTimeField(
        verbose_name=_("created at"), default=now, editable=False
    )
    updated_at = models.DateTimeField(
        verbose_name=_("updated at"), default=now, editable=False
    )

    type = EnumField(InstallmentType, verbose_name=_("type"), max_length=32)
    value = models.DecimalField(
        verbose_name=_("value"), max_digits=16, decimal_places=2
    )
    account_number = models.CharField(max_length=255, verbose_name=_("account number"))
    due_date = models.DateField(verbose_name=_("due date"), blank=True, null=True)

    class Meta:
        abstract = True


class ApartmentInstallmentQuerySet(models.QuerySet):
    def sending_to_sap_needed(self):
        max_due_date = timezone.localdate() + timedelta(
            days=settings.SAP_DAYS_UNTIL_INSTALLMENT_DUE_DATE
        )
        return self.filter(
            added_to_be_sent_to_sap_at__isnull=False,
            sent_to_sap_at__isnull=True,
            due_date__lt=max_due_date,
        )

    def set_sent_to_sap_at(self, dt: datetime = None):
        self.update(sent_to_sap_at=dt or timezone.now())


class ApartmentInstallment(InstallmentBase):
    INVOICE_NUMBER_PREFIX_LENGTH: int = 3

    apartment_reservation = models.ForeignKey(
        ApartmentReservation,
        verbose_name=_("apartment reservation"),
        related_name="apartment_installments",
        on_delete=models.PROTECT,
    )
    invoice_number = models.CharField(max_length=9, verbose_name=_("invoice number"))
    reference_number = models.CharField(
        max_length=64, verbose_name=_("reference number"), unique=True
    )
    added_to_be_sent_to_sap_at = models.DateTimeField(
        verbose_name=_("added to be sent to SAP at"), null=True, blank=True
    )
    sent_to_sap_at = models.DateTimeField(
        verbose_name=_("sent to SAP at"), null=True, blank=True
    )
    # Metadata fields
    handler = CharPGPPublicKeyField(
        verbose_name=_("handler"), max_length=200, blank=True
    )

    objects = ApartmentInstallmentQuerySet.as_manager()

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["apartment_reservation", "type"], name="unique_reservation_type"
            )
        ]

    @property
    def is_overdue(self) -> bool:
        if not self.due_date or localdate() <= self.due_date:
            return False

        return (
            sum(
                payment.amount
                for payment in self.payments.filter(payment_date__lte=self.due_date)
            )
            < self.value
        )

    @property
    def payment_status(self) -> PaymentStatus:
        paid_amount = sum(payment.amount for payment in self.payments.all())
        if not paid_amount:
            return PaymentStatus.UNPAID
        elif paid_amount == self.value:
            return PaymentStatus.PAID
        elif paid_amount < self.value:
            return PaymentStatus.UNDERPAID
        else:
            return PaymentStatus.OVERPAID

    def _get_next_invoice_number(self):
        if self.invoice_number:
            return self.invoice_number

        invoice_number_prefix = settings.INVOICE_NUMBER_PREFIX or ""

        if len(invoice_number_prefix) != self.INVOICE_NUMBER_PREFIX_LENGTH:
            raise ValueError(
                f"INVOICE_NUMBER_PREFIX setting has invalid length "
                f"({self.INVOICE_NUMBER_PREFIX_LENGTH}): {len(invoice_number_prefix)} "
            )

        apartment_installment = (
            ApartmentInstallment.objects.filter(
                invoice_number__istartswith=invoice_number_prefix,
                created_at__year=date.today().year,
            )
            .order_by("-invoice_number")
            .first()
        )

        last_invoice_number = 1
        if apartment_installment:
            last_invoice_number = apartment_installment.invoice_number
            removeable_prefix_length = self.INVOICE_NUMBER_PREFIX_LENGTH
            last_invoice_number = int(last_invoice_number[removeable_prefix_length:])
            last_invoice_number += 1

        next_invoice_number = invoice_number_prefix + str(last_invoice_number).zfill(6)
        return next_invoice_number

    def set_reference_number(self, force=False):
        if self.reference_number and not force:
            return

        self.reference_number = generate_reference_number(self.id)
        self.save(update_fields=("reference_number",))

    @transaction.atomic
    def save(self, *args, **kwargs):
        creating = not self.id

        self.invoice_number = self._get_next_invoice_number()

        if creating:
            generate_reference_number = not self.reference_number

            if generate_reference_number:
                # set a temporary unique reference number to please the unique
                # constraint
                self.reference_number = str(f"TEMP-{uuid4()}")

            super().save(*args, **kwargs)

            if generate_reference_number:
                self.set_reference_number(force=True)
        else:
            super().save(*args, **kwargs)

    def add_to_be_sent_to_sap(self, force=False):
        if self.added_to_be_sent_to_sap_at and not force:
            raise AlreadyAddedToBeSentToSapError()
        self.added_to_be_sent_to_sap_at = timezone.now()
        self.save(update_fields=("added_to_be_sent_to_sap_at",))


class ProjectInstallmentTemplate(InstallmentBase):
    project_uuid = models.UUIDField(verbose_name=_("project UUID"))
    unit = EnumField(InstallmentUnit, verbose_name=_("unit"), max_length=32)
    percentage_specifier = EnumField(
        InstallmentPercentageSpecifier,
        verbose_name=_("percentage specifier"),
        max_length=32,
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["project_uuid", "type"], name="unique_project_type"
            )
        ]

    def get_amount(self):
        return self.value if self.unit == InstallmentUnit.EURO else None

    def get_percentage(self):
        return self.value if self.unit == InstallmentUnit.PERCENT else None

    def get_corresponding_apartment_installment(self, apartment_data):
        apartment_installment = ApartmentInstallment()

        field_names = [
            f.name for f in InstallmentBase._meta.get_fields() if f.name != "created_at"
        ]
        for field_name in field_names:
            setattr(apartment_installment, field_name, getattr(self, field_name))

        if self.unit == InstallmentUnit.PERCENT:
            if not self.percentage_specifier:
                raise ValueError(
                    f"Cannot calculate apartment installment value, {self} "
                    f"has no percentage_specifier"
                )
            if self.percentage_specifier == InstallmentPercentageSpecifier.SALES_PRICE:
                price_in_cents = apartment_data["sales_price"]
            elif (
                self.percentage_specifier
                == InstallmentPercentageSpecifier.RIGHT_OF_OCCUPANCY_PAYMENT
            ):
                price_in_cents = apartment_data["right_of_occupancy_payment"]
            else:
                price_in_cents = apartment_data["debt_free_sales_price"]

            price = get_euros_from_cents(price_in_cents)
            percentage_multiplier = self.value / 100
            apartment_installment.value = get_rounded_price(
                price * percentage_multiplier
            )
        else:
            apartment_installment.value = self.value

        return apartment_installment


class Payment(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    apartment_installment = models.ForeignKey(
        ApartmentInstallment,
        verbose_name=_("apartment installment"),
        related_name="payments",
        on_delete=models.PROTECT,
    )
    amount = models.DecimalField(
        verbose_name=_("amount"), max_digits=16, decimal_places=2
    )
    payment_date = models.DateField(verbose_name=_("payment date"))

    class Meta:
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering = ("id",)
