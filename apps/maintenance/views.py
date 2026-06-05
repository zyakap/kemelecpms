from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.core.permissions import accessible_projects, can_manage_project

from .forms import (
    AssetForm,
    BreakdownTicketForm,
    PreventiveMaintenanceScheduleForm,
    ServiceRecordForm,
    SparePartForm,
    WorkOrderForm,
)
from .models import (
    Asset,
    BreakdownTicket,
    PreventiveMaintenanceSchedule,
    ServiceRecord,
    SparePart,
    WorkOrder,
)


class ProjectMixin(LoginRequiredMixin):
    def get_project(self):
        if not hasattr(self, "_project"):
            self._project = get_object_or_404(
                accessible_projects(self.request.user),
                pk=self.kwargs["project_pk"],
            )
        return self._project

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.get_project()
        return ctx


class MaintenanceDashboardView(ProjectMixin, TemplateView):
    template_name = "maintenance/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = self.get_project()
        assets = project.maintenance_assets.all()
        work_orders = project.maintenance_work_orders.all()
        ctx.update(
            {
                "asset_count": assets.count(),
                "down_assets": assets.filter(status=Asset.STATUS_OUT_OF_SERVICE).count(),
                "due_pm": PreventiveMaintenanceSchedule.objects.filter(
                    asset__project=project,
                    is_active=True,
                    next_due_date__lte=timezone.now().date(),
                ).count(),
                "open_work_orders": work_orders.exclude(
                    status__in=[
                        WorkOrder.STATUS_COMPLETED,
                        WorkOrder.STATUS_SIGNED_OFF,
                        WorkOrder.STATUS_CANCELLED,
                    ]
                ).count(),
                "recent_work_orders": work_orders.select_related("asset", "assigned_to").order_by("-requested_date")[:10],
                "service_due_assets": [asset for asset in assets if asset.is_service_due][:10],
                "low_spares": [part for part in project.maintenance_spares.all() if part.is_low_stock][:10],
            }
        )
        return ctx


class AssetListView(ProjectMixin, ListView):
    model = Asset
    template_name = "maintenance/asset_list.html"
    context_object_name = "assets"

    def get_queryset(self):
        qs = Asset.objects.filter(project=self.get_project())
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("asset_code")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Asset.STATUS_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class AssetCreateView(ProjectMixin, CreateView):
    model = Asset
    form_class = AssetForm
    template_name = "maintenance/asset_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create maintenance assets for this project.")
            return redirect(self.get_success_url())
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Maintenance asset created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("maintenance:asset-list", kwargs={"project_pk": self.get_project().pk})


class AssetUpdateView(ProjectMixin, UpdateView):
    model = Asset
    form_class = AssetForm
    template_name = "maintenance/asset_form.html"

    def get_queryset(self):
        return Asset.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update maintenance assets for this project.")
            return redirect(self.object.get_absolute_url())
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Maintenance asset updated.")
        return super().form_valid(form)


class AssetDetailView(ProjectMixin, DetailView):
    model = Asset
    template_name = "maintenance/asset_detail.html"
    context_object_name = "asset"

    def get_queryset(self):
        return Asset.objects.filter(project=self.get_project()).prefetch_related(
            "preventive_schedules", "work_orders", "spare_parts"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        asset = self.object
        ctx["pm_plans"] = asset.preventive_schedules.order_by("next_due_date")
        ctx["work_orders"] = asset.work_orders.order_by("-requested_date")
        ctx["service_records"] = ServiceRecord.objects.filter(work_order__asset=asset).order_by("-service_date")
        ctx["spare_parts"] = asset.spare_parts.order_by("part_number")
        return ctx


class PreventiveMaintenancePlanCreateView(ProjectMixin, CreateView):
    model = PreventiveMaintenanceSchedule
    form_class = PreventiveMaintenanceScheduleForm
    template_name = "maintenance/pm_form.html"

    def get_asset(self):
        return get_object_or_404(Asset, pk=self.kwargs["asset_pk"], project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["asset"] = self.get_asset()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["asset"] = self.get_asset()
        return ctx

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create preventive maintenance plans for this project.")
            return redirect(self.get_success_url())
        form.instance.asset = self.get_asset()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Preventive maintenance plan created.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.get_asset().get_absolute_url()


class WorkOrderListView(ProjectMixin, ListView):
    model = WorkOrder
    template_name = "maintenance/workorder_list.html"
    context_object_name = "work_orders"
    paginate_by = 30

    def get_queryset(self):
        qs = WorkOrder.objects.filter(project=self.get_project()).select_related("asset", "assigned_to")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-requested_date", "-work_order_number")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = WorkOrder.STATUS_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class WorkOrderCreateView(ProjectMixin, CreateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = "maintenance/workorder_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create maintenance work orders for this project.")
            return redirect(self.get_success_url())
        form.instance.project = self.get_project()
        form.instance.requested_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Maintenance work order created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("maintenance:workorder-list", kwargs={"project_pk": self.get_project().pk})


class WorkOrderUpdateView(ProjectMixin, UpdateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = "maintenance/workorder_form.html"

    def get_queryset(self):
        return WorkOrder.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update maintenance work orders for this project.")
            return redirect(self.object.get_absolute_url())
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Maintenance work order updated.")
        return super().form_valid(form)


class WorkOrderDetailView(ProjectMixin, DetailView):
    model = WorkOrder
    template_name = "maintenance/workorder_detail.html"
    context_object_name = "work_order"

    def get_queryset(self):
        return WorkOrder.objects.filter(project=self.get_project()).select_related(
            "asset", "assigned_to", "signed_off_by"
        ).prefetch_related("service_records")


class BreakdownTicketCreateView(ProjectMixin, CreateView):
    model = BreakdownTicket
    form_class = BreakdownTicketForm
    template_name = "maintenance/breakdown_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create breakdown tickets for this project.")
            return redirect(self.get_success_url())
        form.instance.created_by = self.request.user
        messages.success(self.request, "Breakdown ticket recorded.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("maintenance:dashboard", kwargs={"project_pk": self.get_project().pk})


class ServiceRecordCreateView(ProjectMixin, CreateView):
    model = ServiceRecord
    form_class = ServiceRecordForm
    template_name = "maintenance/service_form.html"

    def get_work_order(self):
        work_order_pk = self.kwargs.get("work_order_pk")
        if not work_order_pk:
            return None
        if not hasattr(self, "_work_order"):
            self._work_order = get_object_or_404(WorkOrder, pk=work_order_pk, project=self.get_project())
        return self._work_order

    def get_initial(self):
        initial = super().get_initial()
        work_order = self.get_work_order()
        if work_order:
            initial["work_order"] = work_order
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["work_order"] = self.get_work_order()
        return ctx

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create service records for this project.")
            return redirect(self.get_success_url())
        work_order = self.get_work_order()
        if work_order:
            form.instance.work_order = work_order
        form.instance.created_by = self.request.user
        messages.success(self.request, "Service record created.")
        return super().form_valid(form)

    def get_success_url(self):
        work_order = self.get_work_order()
        if work_order:
            return work_order.get_absolute_url()
        return reverse_lazy("maintenance:dashboard", kwargs={"project_pk": self.get_project().pk})


class SparePartListView(ProjectMixin, ListView):
    model = SparePart
    template_name = "maintenance/spare_list.html"
    context_object_name = "spares"

    def get_queryset(self):
        return SparePart.objects.filter(project=self.get_project()).select_related("asset")


class SparePartCreateView(ProjectMixin, CreateView):
    model = SparePart
    form_class = SparePartForm
    template_name = "maintenance/spare_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_project(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create maintenance spares for this project.")
            return redirect(self.get_success_url())
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Spare part recorded.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("maintenance:spare-list", kwargs={"project_pk": self.get_project().pk})
