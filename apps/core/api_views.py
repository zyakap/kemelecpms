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
from apps.core.permissions import (
    accessible_projects,
    can_approve_dsr,
    can_submit_dsr,
)

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
        return (
            accessible_projects(user)
            .select_related("client", "project_manager", "funder")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectListSerializer


class DSRViewSet(viewsets.ModelViewSet):
    """DSR CRUD — site supervisors can create, PMs can approve."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["dsr_number", "project__name"]
    ordering_fields = ["date", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        qs = DailySiteReport.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related("project", "prepared_by")
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
        if not can_submit_dsr(request.user, dsr):
            return Response({"detail": "You do not have permission to submit this DSR."}, status=status.HTTP_403_FORBIDDEN)
        if dsr.status != DailySiteReport.STATUS_DRAFT:
            return Response({"detail": "Only draft DSRs can be submitted."}, status=status.HTTP_400_BAD_REQUEST)
        dsr.status = DailySiteReport.STATUS_SUBMITTED
        dsr.updated_by = request.user
        dsr.save(update_fields=["status", "updated_by", "updated_at"])
        from apps.core.models import AuditLog
        AuditLog.log(request.user, AuditLog.ACTION_SUBMIT, dsr, request=request)
        from apps.core.utils import queue_task
        from apps.dsr.tasks import notify_dsr_submitted
        queue_task(notify_dsr_submitted, dsr.pk)
        return Response({"status": "submitted"})

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        dsr = self.get_object()
        if not can_approve_dsr(request.user, dsr):
            return Response({"detail": "You do not have permission to approve this DSR."}, status=status.HTTP_403_FORBIDDEN)
        if dsr.status != DailySiteReport.STATUS_SUBMITTED:
            return Response({"detail": "Only submitted DSRs can be approved."}, status=status.HTTP_400_BAD_REQUEST)
        dsr.status = DailySiteReport.STATUS_APPROVED
        dsr.approved_by = request.user
        dsr.is_locked = True
        dsr.updated_by = request.user
        from django.utils import timezone
        dsr.approved_at = timezone.now()
        dsr.save(update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "is_locked",
            "updated_by",
            "updated_at",
        ])
        from apps.core.models import AuditLog
        AuditLog.log(request.user, AuditLog.ACTION_APPROVE, dsr, request=request)
        from apps.core.utils import queue_task
        from apps.dsr.tasks import notify_dsr_approved
        queue_task(notify_dsr_approved, dsr.pk)
        return Response({"status": "approved"})


class IPCViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only IPC list and detail."""

    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = IPC.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related("project")
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
        qs = MaterialRequisition.objects.filter(
            project__in=accessible_projects(self.request.user)
        )
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
        qs = PurchaseOrder.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related("supplier")
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs


class GRNViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only GRN list."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GRNListSerializer
    ordering = ["-delivery_date"]

    def get_queryset(self):
        qs = GoodsReceivedNote.objects.filter(
            po__project__in=accessible_projects(self.request.user)
        ).select_related("po")
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(po__project_id=project_pk)
        return qs


class IncidentViewSet(viewsets.ModelViewSet):
    """Incident reporting — can create from mobile."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IncidentSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["incident_number", "description", "project__name"]
    ordering = ["-date"]

    def get_queryset(self):
        qs = Incident.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related("project")
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
        qs = ToolboxTalk.objects.filter(
            project__in=accessible_projects(self.request.user)
        ).select_related("project")
        project_pk = self.request.query_params.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        return qs
