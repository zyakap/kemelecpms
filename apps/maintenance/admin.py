from django.contrib import admin

from .models import (
    Asset,
    BreakdownTicket,
    PreventiveMaintenanceSchedule,
    ServiceRecord,
    SparePart,
    SparePartUsage,
    WorkOrder,
)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("asset_code", "name", "project", "category", "status", "criticality", "next_service_due")
    list_filter = ("project", "category", "status", "criticality")
    search_fields = ("asset_code", "name", "serial_number")


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("work_order_number", "project", "asset", "work_type", "priority", "status", "due_date", "assigned_to")
    list_filter = ("project", "work_type", "priority", "status")
    search_fields = ("work_order_number", "title", "asset__asset_code")


@admin.register(PreventiveMaintenanceSchedule)
class PreventiveMaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ("title", "asset", "frequency", "next_due_date", "is_active")
    list_filter = ("frequency", "is_active", "next_due_date", "asset__project")
    search_fields = ("title", "asset__asset_code", "asset__name")


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    list_display = ("work_order", "service_date", "technician", "downtime_hours", "cost")
    list_filter = ("service_date", "work_order__project")
    search_fields = ("work_order__work_order_number", "technician", "work_performed")


@admin.register(SparePartUsage)
class SparePartUsageAdmin(admin.ModelAdmin):
    list_display = ("description", "service_record", "quantity", "unit_cost", "total_cost")
    search_fields = ("description", "service_record__work_order__work_order_number")


@admin.register(BreakdownTicket)
class BreakdownTicketAdmin(admin.ModelAdmin):
    list_display = ("asset", "reported_at", "restored_at", "downtime_hours", "status")
    list_filter = ("status", "asset__project")
    search_fields = ("asset__asset_code", "asset__name", "cause")


@admin.register(SparePart)
class SparePartAdmin(admin.ModelAdmin):
    list_display = ("part_number", "description", "project", "quantity_on_hand", "minimum_quantity", "is_low_stock")
    list_filter = ("project",)
    search_fields = ("part_number", "description")
