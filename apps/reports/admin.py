from django.contrib import admin

from .models import (
    BackupRun,
    BoQImportBatch,
    IntegrationExportLog,
    PortalAccess,
    ProductionReadinessItem,
    ScheduledExport,
    SyncConflict,
)


@admin.register(PortalAccess)
class PortalAccessAdmin(admin.ModelAdmin):
    list_display = ["project", "portal_type", "organisation", "contact_email", "is_active", "expires_at"]
    list_filter = ["portal_type", "is_active", "project"]
    search_fields = ["organisation", "contact_email", "project__name"]


@admin.register(SyncConflict)
class SyncConflictAdmin(admin.ModelAdmin):
    list_display = ["model_name", "object_reference", "project", "user", "status", "created_at"]
    list_filter = ["status", "model_name"]
    search_fields = ["model_name", "object_reference", "device_id"]


@admin.register(BoQImportBatch)
class BoQImportBatchAdmin(admin.ModelAdmin):
    list_display = ["project", "revision", "status", "rows_total", "rows_valid", "rows_rejected", "created_at"]
    list_filter = ["status", "project"]
    search_fields = ["revision", "project__name"]


@admin.register(ScheduledExport)
class ScheduledExportAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "report_type", "frequency", "next_run", "is_active"]
    list_filter = ["report_type", "frequency", "is_active"]
    search_fields = ["name", "recipients", "project__name"]


@admin.register(IntegrationExportLog)
class IntegrationExportLogAdmin(admin.ModelAdmin):
    list_display = ["export_type", "project", "status", "external_reference", "created_at"]
    list_filter = ["export_type", "status"]
    search_fields = ["external_reference", "message", "project__name"]


@admin.register(BackupRun)
class BackupRunAdmin(admin.ModelAdmin):
    list_display = ["started_at", "finished_at", "status", "storage_location", "size_mb"]
    list_filter = ["status"]


@admin.register(ProductionReadinessItem)
class ProductionReadinessItemAdmin(admin.ModelAdmin):
    list_display = ["area", "title", "is_complete", "owner", "due_date"]
    list_filter = ["area", "is_complete"]
    search_fields = ["title", "description"]
