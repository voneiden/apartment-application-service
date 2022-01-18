from django.views.decorators.http import require_http_methods
from rest_framework import permissions, status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apartment.elastic.queries import get_projects
from application_form.api.sales.serializers import (
    ProjectUUIDSerializer,
    SalesApplicationSerializer,
)
from application_form.api.views import ApplicationViewSet
from application_form.exceptions import ProjectDoesNotHaveApplicationsException
from application_form.services.lottery.machine import distribute_apartments
from users.permissions import IsSalesperson


@api_view(http_method_names=["POST"])
@permission_classes([permissions.AllowAny])
@authentication_classes([])
@require_http_methods(["POST"])  # For SonarCloud
def execute_lottery_for_project(request):
    """
    Run the lottery for the given project.
    """
    serializer = ProjectUUIDSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    project_uuid = serializer.data.get("project_uuid")

    if not get_projects(project_uuid):
        raise NotFound(detail="Project not found.")

    try:
        distribute_apartments(project_uuid)
    except ProjectDoesNotHaveApplicationsException as ex:
        raise ValidationError(detail="Project does not have applications.") from ex

    return Response({"status": "success"}, status=status.HTTP_200_OK)


class SalesApplicationViewSet(ApplicationViewSet):
    serializer_class = SalesApplicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsSalesperson]
