import logging
from datetime import date
from django.db import transaction
from django.db.models import QuerySet
from typing import Iterable, List, Optional

from apartment.enums import IdentifierSchemaType
from apartment.models import Apartment, Identifier
from application_form.enums import ApartmentQueueChangeEventType, ApplicationState
from application_form.models import Applicant, Application, ApplicationApartment
from application_form.services.queue import (
    add_application_to_queues,
    remove_application_from_queue,
)
from connections.service.elastic import get_and_update_apartment, get_and_update_project

_logger = logging.getLogger(__name__)


def cancel_haso_application(application_apartment: ApplicationApartment) -> None:
    """
    Mark the application as canceled and remove it from the apartment queue.

    If the application has already won the apartment, then the winner for the apartment
    will be recalculated.
    """
    was_reserved = application_apartment.state in [
        ApplicationState.RESERVED,
        ApplicationState.REVIEW,
    ]
    apartment = application_apartment.apartment
    remove_application_from_queue(application_apartment)
    if was_reserved:
        _reserve_haso_apartment(apartment)


def cancel_hitas_application(application_apartment: ApplicationApartment) -> None:
    """
    Cancel a HITAS application for a specific apartment. If the application has already
    won an apartment, then the winner for that apartment must be recalculated.
    """
    apartment = application_apartment.apartment
    was_reserved = application_apartment.state in [
        ApplicationState.RESERVED,
        ApplicationState.OFFERED,
    ]
    remove_application_from_queue(application_apartment)
    if was_reserved:
        _reserve_apartments([apartment], False)


@transaction.atomic
def create_application(application_data: dict) -> Application:
    _logger.debug(
        "Creating a new application with external UUID %s",
        application_data["external_uuid"],
    )
    data = application_data.copy()
    profile = data.pop("profile")
    project_id = data.pop("project_id")
    project = get_and_update_project(project_id)
    Identifier.objects.get_or_create(
        schema_type=IdentifierSchemaType.ATT_PROJECT_ES,
        identifier=project_id,
        defaults={"project": project},
    )
    additional_applicant_data = data.pop("additional_applicant")
    application = Application.objects.create(
        external_uuid=data.pop("external_uuid"),
        applicants_count=2 if additional_applicant_data else 1,
        type=data.pop("type"),
        has_children=data.pop("has_children"),
        right_of_residence=data.pop("right_of_residence"),
        profile=profile,
    )
    Applicant.objects.create(
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email,
        phone_number=profile.phone_number,
        street_address=profile.street_address,
        city=profile.city,
        postal_code=profile.postal_code,
        age=_calculate_age(profile.date_of_birth),
        date_of_birth=profile.date_of_birth,
        ssn_suffix=application_data["ssn_suffix"],
        contact_language=profile.contact_language,
        is_primary_applicant=True,
        application=application,
    )
    if additional_applicant_data:
        Applicant.objects.create(
            first_name=additional_applicant_data["first_name"],
            last_name=additional_applicant_data["last_name"],
            email=additional_applicant_data["email"],
            phone_number=additional_applicant_data["phone_number"],
            street_address=additional_applicant_data["street_address"],
            city=additional_applicant_data["city"],
            postal_code=additional_applicant_data["postal_code"],
            age=_calculate_age(additional_applicant_data["date_of_birth"]),
            date_of_birth=additional_applicant_data["date_of_birth"],
            ssn_suffix=additional_applicant_data["ssn_suffix"],
            application=application,
        )
    apartment_data = data.pop("apartments")
    for apartment_item in apartment_data:
        apartment = get_and_update_apartment(apartment_item["identifier"])
        ApplicationApartment.objects.create(
            application=application,
            apartment=apartment,
            priority_number=apartment_item["priority"],
        )
        Identifier.objects.get_or_create(
            schema_type=IdentifierSchemaType.ATT_PROJECT_ES,
            identifier=apartment_item["identifier"],
            defaults={"apartment": apartment},
        )
    _logger.debug(
        "Application created with external UUID %s", application_data["external_uuid"]
    )
    add_application_to_queues(application)
    return application


def get_ordered_applications(apartment: Apartment) -> QuerySet:
    """
    Returns a list of all applications for the given apartment, ordered by their
    position in the queue.
    """
    return apartment.applications.filter(
        application_apartments__in=apartment.application_apartments.exclude(
            queue_application__change_events__type=ApartmentQueueChangeEventType.REMOVED
        )
    ).order_by("application_apartments__queue_application__queue_position")


def _cancel_lower_priority_apartments(
    application_apartment: ApplicationApartment,
    cancel_reserved: bool = True,
) -> List[ApplicationApartment]:
    """
    Given the winning apartment application, cancel each apartment application for the
    same project that has a lower priority than the reserved apartment, no matter what
    position they are in the queue. The canceled application is removed from the queue
    of the corresponding apartment.

    An applicant can only have one apartment reserved at a time. If the applicant has,
    for example, priority 2 apartment reserved, then the lower priority apartments will
    be given to other applicants. However, the applicant will still be queuing for the
    first-priority apartment.
    """
    states_to_cancel = [ApplicationState.SUBMITTED]
    if cancel_reserved:
        states_to_cancel.append(ApplicationState.RESERVED)
    app_apartments = application_apartment.application.application_apartments.all()
    lower_priority_app_apartments = app_apartments.filter(
        priority_number__gt=application_apartment.priority_number,
        state__in=states_to_cancel,
    )
    canceled_winners = []
    for app_apartment in lower_priority_app_apartments:
        if app_apartment.queue_application.queue_position == 0:
            canceled_winners.append(app_apartment)
        cancel_hitas_application(app_apartment)
    return canceled_winners


def _calculate_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _reserve_apartments(
    apartments: Iterable[Apartment],
    cancel_lower_priority_reserved: bool = True,
) -> None:
    apartments_to_process = set(list(apartments))
    while apartments_to_process:
        for apartment in apartments_to_process.copy():
            apartments_to_process.remove(apartment)
            # Mark the winner as "RESERVED"
            winner = _reserve_apartment(apartment)
            if winner is None:
                continue
            # If the winner has lower priority applications, we should cancel them.
            # This will modify the queues of other apartments, and if the apartment's
            # winner gets canceled, that apartment must be processed again.
            canceled_winners = _cancel_lower_priority_apartments(
                winner, cancel_lower_priority_reserved
            )
            apartments_to_process.update(app.apartment for app in canceled_winners)


def _reserve_haso_apartment(apartment: Apartment) -> None:
    """
    Declare a winner for the given apartment.

    The application with the smallest right of residence number will be the winner.
    If there is a single winner, the state of that application will be changed to
    "RESERVED". If there are multiple winner candidates with the same right of residence
    number, their state will be changed to "REVIEW".

    If a winner has applied to other apartments in the same project with lower priority,
    then the applications with lower priority will be canceled and removed from their
    respective queues, unless their state is already "RESERVED".
    """
    # Get the applications in the queue, ordered by their queue position
    applications = get_ordered_applications(apartment)

    # There can be a single winner, or multiple winners if there are several
    # winning candidates with the same right of residence number.
    winning_applications = _find_winning_candidates(applications)

    # Set the reservation state to either "RESERVED" or "REVIEW"
    _update_reservation_state(winning_applications, apartment)

    # At this point the winner has been decided, but the winner may have outstanding
    # applications to other apartments. If they are lower priority, they should be
    # marked as "CANCELED" and deleted from the respective queues.
    _cancel_lower_priority_haso_applications(winning_applications, apartment)


def _update_reservation_state(applications: QuerySet, apartment: Apartment) -> None:
    """
    Update the state of the apartment application to either "RESERVED" or "REVIEW",
    depending on whether there is one or more winning candidates.
    """
    application_state = ApplicationState.RESERVED
    if applications.count() > 1:
        application_state = ApplicationState.REVIEW
    for app in applications:
        app_apartment = app.application_apartments.get(apartment=apartment)
        app_apartment.state = application_state
        app_apartment.save(update_fields=["state"])


def _reserve_apartment(apartment: Apartment) -> Optional[ApplicationApartment]:
    # The winning application is whoever is at first position in the queue
    winning_application = get_ordered_applications(apartment).first()
    if winning_application is None:
        return None
    app_apartment = winning_application.application_apartments.get(apartment=apartment)
    app_apartment.state = ApplicationState.RESERVED
    app_apartment.save(update_fields=["state"])
    return app_apartment


def _cancel_lower_priority_haso_applications(
    winning_applications: QuerySet,
    reserved_apartment: Apartment,
) -> None:
    """
    Go through the given winning applications, and cancel each application made for
    an apartment that has a lower priority than the reserved apartment and is not in
    the first place in the queue. The canceled application is removed from the queue of
    the corresponding apartment.
    """
    for app in winning_applications:
        app_apartments = app.application_apartments.all()
        priority = app_apartments.get(apartment=reserved_apartment).priority_number
        low_priority_app_apartments = app_apartments.filter(
            priority_number__gt=priority,
            state=ApplicationState.SUBMITTED,
            queue_application__queue_position__gt=0,
        )
        for app_apartment in low_priority_app_apartments:
            cancel_haso_application(app_apartment)


def _find_winning_candidates(applications: QuerySet) -> QuerySet:
    """Return all applications that have the smallest right of residence number."""
    if not applications.exists():
        return applications.none()
    min_right_of_residence = applications.first().right_of_residence
    return applications.filter(right_of_residence=min_right_of_residence)