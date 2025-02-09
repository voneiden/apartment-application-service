import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status
from rest_framework.reverse import reverse

from application_form.enums import ApartmentReservationState
from application_form.tests.factories import ApartmentReservationFactory
from cost_index.api.serializers import ApartmentRevaluationSerializer
from cost_index.models import CostIndex
from cost_index.tests.factories import ApartmentRevaluationFactory


@pytest.mark.django_db
def test_cost_index_viewset(
    sales_ui_salesperson_api_client,
):
    response = sales_ui_salesperson_api_client.get(
        reverse("cost_index:sales-cost-index-list"), format="json"
    )

    default_count = 393
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == default_count

    response = sales_ui_salesperson_api_client.post(
        reverse("cost_index:sales-cost-index-list"),
        format="json",
        data={"valid_from": "2022-11-25", "value": "250.00"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert CostIndex.objects.all().count() == default_count + 1
    created_id = response.data["id"]
    response = sales_ui_salesperson_api_client.get(
        reverse("cost_index:sales-cost-index-detail", kwargs={"pk": created_id}),
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["value"] == "250.00"

    response = sales_ui_salesperson_api_client.put(
        reverse("cost_index:sales-cost-index-detail", kwargs={"pk": created_id}),
        format="json",
        data={"valid_from": "2022-11-25", "value": "260.00"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert CostIndex.objects.all().count() == default_count + 1
    assert CostIndex.objects.first().value == Decimal("260.00")

    response = sales_ui_salesperson_api_client.delete(
        reverse("cost_index:sales-cost-index-detail", kwargs={"pk": created_id}),
        format="json",
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert CostIndex.objects.all().count() == default_count
    assert CostIndex.objects.filter(pk=created_id).exists() is False

    response = sales_ui_salesperson_api_client.patch(
        reverse("cost_index:sales-cost-index-detail", kwargs={"pk": created_id}),
        format="json",
    )
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


@pytest.mark.django_db
def test_get_apartment_revaluation_summary_unauthorized(
    api_client, user_api_client, profile_api_client, drupal_salesperson_api_client
):
    response = api_client.get(reverse("cost_index:apartment-revaluation-summary"))
    assert response.status_code == 403

    response = user_api_client.get(reverse("cost_index:apartment-revaluation-summary"))
    assert response.status_code == 403

    response = profile_api_client.get(
        reverse("cost_index:apartment-revaluation-summary")
    )
    assert response.status_code == 403

    response = drupal_salesperson_api_client.get(
        reverse("cost_index:apartment-revaluation-summary")
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_apartment_revaluation_summary_api(
    drupal_server_api_client, elastic_haso_project_with_5_apartments
):
    response = drupal_server_api_client.get(
        reverse("cost_index:apartment-revaluation-summary")
    )
    assert response.status_code == 200
    assert response.data == []

    _, haso_apartments = elastic_haso_project_with_5_apartments

    haso_0 = haso_apartments[0]
    haso_0_reservation_0 = ApartmentReservationFactory(
        apartment_uuid=haso_0.uuid,
        state=ApartmentReservationState.CANCELED,
        list_position=1,
    )
    haso_0_reservation_1 = ApartmentReservationFactory(
        apartment_uuid=haso_0.uuid,
        state=ApartmentReservationState.CANCELED,
        list_position=2,
    )

    haso_1 = haso_apartments[1]
    haso_1_reservation_0 = ApartmentReservationFactory(
        apartment_uuid=haso_1.uuid,
        state=ApartmentReservationState.CANCELED,
        list_position=1,
    )

    haso_2 = haso_apartments[2]
    haso_2_reservation_0 = ApartmentReservationFactory(
        apartment_uuid=haso_2.uuid,
        state=ApartmentReservationState.CANCELED,
        list_position=1,
    )

    now = timezone.now()
    with freeze_time(now - timedelta(hours=2000)):
        haso_0_revaluation_0 = ApartmentRevaluationFactory(
            apartment_reservation=haso_0_reservation_0,
        )
    with freeze_time(now - timedelta(minutes=20)):
        haso_0_revaluation_1 = ApartmentRevaluationFactory(
            apartment_reservation=haso_0_reservation_1,
        )
    with freeze_time(now - timedelta(minutes=5)):
        haso_1_revaluation_0 = ApartmentRevaluationFactory(
            apartment_reservation=haso_1_reservation_0,
        )
    with freeze_time(now - timedelta(minutes=61)):
        ApartmentRevaluationFactory(
            apartment_reservation=haso_2_reservation_0,
        )

    response = drupal_server_api_client.get(
        reverse("cost_index:apartment-revaluation-summary")
    )
    assert response.status_code == 200
    assert len(response.data) == 2

    haso_0_data = [
        row for row in response.data if str(row["apartment_uuid"]) == haso_0.uuid
    ][0]
    haso_1_data = [
        row for row in response.data if str(row["apartment_uuid"]) == haso_1.uuid
    ][0]

    haso_0_expected_roop = haso_0_revaluation_1.end_right_of_occupancy_payment
    haso_0_expected_alteration_work = (
        haso_0_revaluation_0.alteration_work + haso_0_revaluation_1.alteration_work
    )
    haso_1_expected_roop = haso_1_revaluation_0.end_right_of_occupancy_payment
    haso_1_expected_alteration_work = haso_1_revaluation_0.alteration_work

    assert haso_0_expected_roop == haso_0_data["adjusted_right_of_occupancy_payment"]
    assert haso_0_expected_alteration_work == haso_0_data["alteration_work_total"]
    assert haso_1_expected_roop == haso_1_data["adjusted_right_of_occupancy_payment"]
    assert haso_1_expected_alteration_work == haso_1_data["alteration_work_total"]

    # Test start after end
    response = drupal_server_api_client.get(
        reverse("cost_index:apartment-revaluation-summary")
        + "?start_time=2022-12-27T10:00:00Z&end_time=2022-12-27T09:00:00Z"
    )
    assert response.status_code == 400
    assert "start_time must be less than end_time" in str(response.data)


@pytest.mark.django_db
def test_revaluation_and_haso_payment_api(
    sales_ui_salesperson_api_client,
    elastic_haso_project_with_5_apartments,
    elastic_hitas_project_with_5_apartments,
):
    _, haso_apartments = elastic_haso_project_with_5_apartments
    _, hitas_apartments = elastic_hitas_project_with_5_apartments
    haso_0 = haso_apartments[0]
    haso_0_reservation_0 = ApartmentReservationFactory(
        apartment_uuid=haso_0.uuid,
        state=ApartmentReservationState.CANCELED,
        list_position=1,
    )

    haso_0_revaluation_template = ApartmentRevaluationFactory(
        apartment_reservation=haso_0_reservation_0
    )
    template_data = ApartmentRevaluationSerializer(haso_0_revaluation_template).data
    haso_0_revaluation_template.delete()

    # Check that request fails with invalid cost index values
    # Invalid start cost index
    start_cost_index_value = template_data["start_cost_index_value"]
    end_cost_index_value = template_data["end_cost_index_value"]
    template_data["start_cost_index_value"] = (
        Decimal(template_data["start_cost_index_value"]) + 5
    )

    response = sales_ui_salesperson_api_client.post(
        reverse("cost_index:sales-apartment-revaluation-list"),
        format="json",
        data=template_data,
    )

    assert response.status_code == 400

    # Invalid end cost index
    template_data["start_cost_index_value"] = start_cost_index_value
    template_data["end_cost_index_value"] = (
        Decimal(template_data["end_cost_index_value"]) + 5
    )

    response = sales_ui_salesperson_api_client.post(
        reverse("cost_index:sales-apartment-revaluation-list"),
        format="json",
        data=template_data,
    )

    assert response.status_code == 400

    template_data["end_cost_index_value"] = end_cost_index_value

    # Finally check that we get success with correct values
    response = sales_ui_salesperson_api_client.post(
        reverse("cost_index:sales-apartment-revaluation-list"),
        format="json",
        data=template_data,
    )

    assert response.status_code == 201
    created_id = response.data["id"]

    # No duplicates
    response = sales_ui_salesperson_api_client.post(
        reverse("cost_index:sales-apartment-revaluation-list"),
        format="json",
        data=template_data,
    )

    assert response.status_code == 400

    # Retrieve test
    response = sales_ui_salesperson_api_client.get(
        reverse(
            "cost_index:sales-apartment-revaluation-detail", kwargs={"pk": created_id}
        ),
        format="json",
    )
    assert response.status_code == 200

    # List view tests
    response = sales_ui_salesperson_api_client.get(
        reverse("cost_index:sales-apartment-revaluation-list"), format="json"
    )
    assert response.status_code == 200

    # HASO payment API
    response = sales_ui_salesperson_api_client.get(
        reverse(
            "cost_index:apartment-haso-payment", kwargs={"apartment_uuid": haso_0.uuid}
        ),
        format="json",
    )
    assert response.status_code == 200

    # HASO payment API
    response = sales_ui_salesperson_api_client.get(
        reverse(
            "cost_index:apartment-haso-payment",
            kwargs={"apartment_uuid": hitas_apartments[0].uuid},
        ),
        format="json",
    )
    assert response.status_code == 400
