"""
DRF serializers for the CPMS REST API.

Provides read-optimised serializers for mobile app and analytics consumption.
"""

from rest_framework import serializers

from apps.dsr.models import DailySiteReport, DSRActivity, DSRPhoto
from apps.ipc.models import IPC, Payment
from apps.procurement.models import MaterialRequisition, PurchaseOrder, GoodsReceivedNote
from apps.projects.models import Project
from apps.safety.models import Incident, ToolboxTalk


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class ProjectListSerializer(serializers.ModelSerializer):
    project_manager_name = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    contract_value = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "project_id",
            "name",
            "project_type",
            "status",
            "province",
            "contract_value",
            "start_date",
            "target_completion_date",
            "project_manager_name",
            "client_name",
        ]

    def get_project_manager_name(self, obj):
        pm = getattr(obj, "project_manager", None)
        if pm:
            return pm.get_full_name() or pm.email
        return None

    def get_client_name(self, obj):
        return obj.client.name if obj.client else None

    def get_contract_value(self, obj):
        return obj.contract_value


class ProjectDetailSerializer(ProjectListSerializer):
    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + [
            "description",
            "district",
            "site_address",
            "gps_lat",
            "gps_lng",
            "actual_completion_date",
            "created_at",
            "updated_at",
        ]


# ---------------------------------------------------------------------------
# DSR
# ---------------------------------------------------------------------------


class DSRActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DSRActivity
        fields = ["id", "description", "location", "progress_pct", "crew_size", "notes"]


class DSRPhotoSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = DSRPhoto
        fields = ["id", "caption", "tag", "photo_url", "uploaded_at"]

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None


class DSRListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    prepared_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DailySiteReport
        fields = [
            "id",
            "dsr_number",
            "project",
            "project_name",
            "date",
            "status",
            "weather_am",
            "weather_pm",
            "prepared_by_name",
        ]

    def get_prepared_by_name(self, obj):
        return obj.prepared_by.get_full_name() or obj.prepared_by.email


class DSRDetailSerializer(DSRListSerializer):
    activities = DSRActivitySerializer(many=True, read_only=True)
    photos = DSRPhotoSerializer(many=True, read_only=True)

    class Meta(DSRListSerializer.Meta):
        fields = DSRListSerializer.Meta.fields + [
            "day_number",
            "summary",
            "activities",
            "photos",
        ]


class DSRCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailySiteReport
        fields = [
            "project",
            "date",
            "weather_am",
            "weather_pm",
            "summary",
        ]

    def create(self, validated_data):
        request = self.context.get("request")
        if request:
            validated_data["prepared_by"] = request.user
            validated_data["created_by"] = request.user
        return super().create(validated_data)


# ---------------------------------------------------------------------------
# IPC
# ---------------------------------------------------------------------------


class IPCListSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = IPC
        fields = [
            "id",
            "ipc_number",
            "project",
            "project_name",
            "claim_period_from",
            "claim_period_to",
            "status",
            "submitted_date",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "payment_date", "amount", "payment_reference", "notes"]


class IPCDetailSerializer(IPCListSerializer):
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta(IPCListSerializer.Meta):
        fields = IPCListSerializer.Meta.fields + ["notes", "payments"]


# ---------------------------------------------------------------------------
# Procurement
# ---------------------------------------------------------------------------


class MRListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialRequisition
        fields = ["id", "mr_number", "project", "date_required", "status", "created_at"]


class POListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = ["id", "po_number", "project", "supplier_name", "order_date", "status", "total_amount"]


class GRNListSerializer(serializers.ModelSerializer):
    po_number = serializers.CharField(source="purchase_order.po_number", read_only=True)

    class Meta:
        model = GoodsReceivedNote
        fields = ["id", "grn_number", "purchase_order", "po_number", "received_date", "received_by"]


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------


class IncidentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id",
            "project",
            "project_name",
            "incident_number",
            "date",
            "incident_type",
            "description",
            "persons_involved",
            "is_lti",
            "status",
            "created_at",
        ]


class ToolboxTalkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToolboxTalk
        fields = [
            "id",
            "project",
            "date",
            "topic",
            "presenter",
            "attendee_count",
        ]
