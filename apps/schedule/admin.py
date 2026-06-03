from django.contrib import admin

from .models import Activity, LookAhead, LookAheadTask, Programme, ProgressEntry, WBSActivity


class WBSActivityInline(admin.TabularInline):
    model = WBSActivity
    fk_name = "parent"
    fields = ("wbs_code", "name", "level", "responsible")
    extra = 0
    ordering = ("wbs_code",)
    show_change_link = True


@admin.register(WBSActivity)
class WBSActivityAdmin(admin.ModelAdmin):
    list_display = ("wbs_code", "name", "level", "project", "parent", "responsible")
    list_filter = ("project", "level")
    search_fields = ("wbs_code", "name")
    autocomplete_fields = ("responsible", "cost_code")
    inlines = [WBSActivityInline]
    ordering = ("project", "wbs_code")


class ActivityInline(admin.TabularInline):
    model = Activity
    fields = ("name", "start_date", "end_date", "duration", "planned_percent", "actual_percent", "is_critical")
    extra = 0
    ordering = ("start_date",)
    show_change_link = True


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "version",
        "baseline_start",
        "baseline_end",
        "current_start",
        "current_end",
        "is_baseline",
    )
    list_filter = ("is_baseline",)
    search_fields = ("project__name",)
    inlines = [ActivityInline]
    readonly_fields = ("duration_days", "baseline_duration_days")


class ProgressEntryInline(admin.TabularInline):
    model = ProgressEntry
    fields = ("date", "percent_complete", "recorded_by", "notes")
    extra = 0
    ordering = ("-date",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "programme",
        "start_date",
        "end_date",
        "duration",
        "planned_percent",
        "actual_percent",
        "is_critical",
        "responsible",
    )
    list_filter = ("programme__project", "is_critical", "dependency_type")
    search_fields = ("name", "description")
    autocomplete_fields = ("responsible", "predecessor", "wbs_activity")
    readonly_fields = ("spi", "is_on_schedule")
    inlines = [ProgressEntryInline]


@admin.register(ProgressEntry)
class ProgressEntryAdmin(admin.ModelAdmin):
    list_display = ("activity", "date", "percent_complete", "recorded_by")
    list_filter = ("activity__programme__project", "date")
    search_fields = ("activity__name",)
    date_hierarchy = "date"


class LookAheadTaskInline(admin.TabularInline):
    model = LookAheadTask
    fields = ("description", "activity", "assigned_to", "planned_start", "planned_end", "is_completed")
    extra = 0
    ordering = ("planned_start",)
    autocomplete_fields = ("activity", "assigned_to")


@admin.register(LookAhead)
class LookAheadAdmin(admin.ModelAdmin):
    list_display = ("project", "period_start", "period_end", "created_by", "completion_rate")
    list_filter = ("project",)
    search_fields = ("project__name", "notes")
    inlines = [LookAheadTaskInline]
    readonly_fields = ("completion_rate",)


@admin.register(LookAheadTask)
class LookAheadTaskAdmin(admin.ModelAdmin):
    list_display = ("description", "look_ahead", "assigned_to", "planned_start", "planned_end", "is_completed")
    list_filter = ("look_ahead__project", "is_completed")
    search_fields = ("description",)
    autocomplete_fields = ("activity", "assigned_to")
