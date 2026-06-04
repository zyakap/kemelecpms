"""
REST API viewsets for CPMS mobile and external integrations.
"""

from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.dsr.models import DailySiteReport
from apps.ipc.models import IPC
from apps.procurement.models import GoodsReceivedNote, MaterialRequisition, PurchaseOrder
from apps.projects.models import Project
from apps.safety.models import Incident, ToolboxTalk

from .serializers import (
    DSRCreateSerializer,
    DSRDetailSerializer,
    DSRListSerializer,
    GRNListSerializer,
    IPCDetailSerializer,
    IPCListSerializer,
    IncidentSerializer,
    MRListSerializer,
    POListSerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
    ToolboxTalkSerializer,
)


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only project list and detail.
    Users see only projects they are associated with (PM, supervisor, or all for MD/admin).
    """

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "project_id", "province", "description"]
    ordering_fields = ["name", "status", "start_date", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = Project.objects.select_related("client", "project_manager", "funder")
        if user.role in ("MANAGING_DIRECTOR", "ADMIN", "SYSTEM_ADMIN"):
            return qs
        return qs.filter(
            models_Q(project_manager=user) | models_Q(site_supervisor=user)
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectListSerializer


def models_Q(*args, **kwargs):
    from django.db.models import Q
    return Q(*args, **kwargs)


class DSRViewSet(viewsets.ModelViewSet):
    """DSR CRUD — site supervisors can create, PMs can approve."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["dsr_number", "project__name"]
    ordering_fields = ["date", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        user = self.request.user
        qs = DailySiteReport.objects.select_related("project", "prepared_by")
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return DSRCreateSerializer
        if self.action == "retrieve":
            return DSRDetailSerializer
        return DSRListSerializer

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        dsr = self.get_object()
        if dsr.status != DailySiteReport.STATUS_DRAFT:
            return Response({"detail": "Only draft DSRs can be submitted."}, status=status.HTTP_400_BAD_REQUEST)
        dsr.status = DailySiteReport.STATUS_SUBMITTED
        dsr.save(update_fields=["status"])
        from apps.dsr.tasks import notify_dsr_submitted
        notify_dsr_submitted.delay(dsr.pk)
        return Response({"status": "submitted"})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        dsr = self.get_object()
        if dsr.status != DailySiteReport.STATUS_SUBMITTED:
            return Response({"detail": "Only submitted DSRs can be approved."}, status=status.HTTP_400_BAD_REQUEST)
        dsr.status = DailySiteReport.STATUS_APPROVED
        dsr.approved_by = request.user
        dsr.save(update_fields=["status", "approved_by"])
        from apps.dsr.tasks import notify_dsr_approved
        notify_dsr_approved.delay(dsr.pk)
        return Response({"status": "approved"})


class IPCViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only IPC list and detail."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = IPC.objects.select_related("project")
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return IPCDetailSerializer
        return IPCListSerializer


class MRViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only Material Requisition list."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MRListSerializer
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = MaterialRequisition.objects.all()
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs


class POViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only Purchase Order list."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = POListSerializer
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related("supplier")
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs


class GRNViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only GRN list."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GRNListSerializer
    ordering = ["-received_date"]

    def get_queryset(self):
        qs = GoodsReceivedNote.objects.select_related("purchase_order")
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(purchase_order__project_id=project_pk)
        return qs


class IncidentViewSet(viewsets.ModelViewSet):
    """Incident reporting — can create from mobile."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IncidentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["incident_number", "description", "project__name"]
    ordering = ["-date"]

    def get_queryset(self):
        qs = Incident.objects.select_related("project")
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user, created_by=self.request.user)


class ToolboxTalkViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only Toolbox Talk list."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ToolboxTalkSerializer
    ordering = ["-date"]

    def get_queryset(self):
        qs = ToolboxTalk.objects.select_related("project")
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs
