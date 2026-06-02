"""
Procurement views for kemelecpms.

All views require authentication. Covers:
  - Supplier CRUD
  - Material catalogue CRUD
  - Material Requisition (MR) list / create / detail / approve / reject
  - Purchase Order (PO) list / create / detail / update / approve
  - Goods Received Note create / detail
  - Supplier Invoice list / create
  - Stock Ledger (on-site stock view)
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
)

from apps.projects.models import Project

from .forms import (
    GoodsReceivedNoteForm,
    GRNItemForm,
    MaterialForm,
    MaterialRequisitionForm,
    MRItemFormSet,
    MRRejectForm,
    POItemFormSet,
    PurchaseOrderForm,
    StockLedgerForm,
    SupplierForm,
    SupplierInvoiceForm,
)
from .models import (
    GoodsReceivedNote,
    GRNItem,
    Material,
    MaterialCategory,
    MaterialRequisition,
    MRItem,
    POItem,
    PurchaseOrder,
    StockLedger,
    Supplier,
    SupplierInvoice,
)


# ---------------------------------------------------------------------------
# Supplier views
# ---------------------------------------------------------------------------


class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = "procurement/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 25

    def get_queryset(self):
        qs = Supplier.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(contact_person__icontains=q)
                | Q(email__icontains=q)
                | Q(irc_tin__icontains=q)
            )
        if self.request.GET.get("preferred"):
            qs = qs.filter(is_preferred=True)
        if self.request.GET.get("blacklisted"):
            qs = qs.filter(is_blacklisted=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class SupplierCreateView(LoginRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "procurement/supplier_form.html"
    success_url = reverse_lazy("procurement:supplier_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Supplier created successfully.")
        return super().form_valid(form)


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = "procurement/supplier_form.html"

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Supplier updated successfully.")
        return super().form_valid(form)


class SupplierDetailView(LoginRequiredMixin, DetailView):
    model = Supplier
    template_name = "procurement/supplier_detail.html"
    context_object_name = "supplier"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["purchase_orders"] = self.object.purchase_orders.select_related(
            "project"
        ).order_by("-date")[:10]
        ctx["invoices"] = self.object.invoices.order_by("-invoice_date")[:10]
        return ctx


# ---------------------------------------------------------------------------
# Material views
# ---------------------------------------------------------------------------


class MaterialListView(LoginRequiredMixin, ListView):
    model = Material
    template_name = "procurement/material_list.html"
    context_object_name = "materials"
    paginate_by = 30

    def get_queryset(self):
        qs = Material.objects.select_related("category").order_by("item_code")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(item_code__icontains=q) | Q(description__icontains=q)
            )
        cat = self.request.GET.get("category")
        if cat:
            qs = qs.filter(category_id=cat)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = MaterialCategory.objects.all()
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class MaterialCreateView(LoginRequiredMixin, CreateView):
    model = Material
    form_class = MaterialForm
    template_name = "procurement/material_form.html"
    success_url = reverse_lazy("procurement:material_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Material added to catalogue.")
        return super().form_valid(form)


class MaterialUpdateView(LoginRequiredMixin, UpdateView):
    model = Material
    form_class = MaterialForm
    template_name = "procurement/material_form.html"
    success_url = reverse_lazy("procurement:material_list")

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Material updated.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Material Requisition views
# ---------------------------------------------------------------------------


class MRListView(LoginRequiredMixin, ListView):
    model = MaterialRequisition
    template_name = "procurement/mr_list.html"
    context_object_name = "requisitions"
    paginate_by = 20

    def get_queryset(self):
        qs = MaterialRequisition.objects.select_related(
            "project", "requested_by"
        ).order_by("-date", "-mr_number")
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = Project.objects.all()
        ctx["status_choices"] = MaterialRequisition.STATUS_CHOICES
        return ctx


class MRCreateView(LoginRequiredMixin, CreateView):
    model = MaterialRequisition
    form_class = MaterialRequisitionForm
    template_name = "procurement/mr_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["item_formset"] = MRItemFormSet(self.request.POST)
        else:
            ctx["item_formset"] = MRItemFormSet()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        item_formset = ctx["item_formset"]
        if item_formset.is_valid():
            with transaction.atomic():
                form.instance.created_by = self.request.user
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()
            messages.success(self.request, f"Requisition {self.object.mr_number} created.")
            return redirect(self.object.get_absolute_url())
        return self.form_invalid(form)


class MRDetailView(LoginRequiredMixin, DetailView):
    model = MaterialRequisition
    template_name = "procurement/mr_detail.html"
    context_object_name = "mr"

    def get_queryset(self):
        return MaterialRequisition.objects.select_related(
            "project", "requested_by", "approved_by"
        ).prefetch_related("items__material")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_approve"] = self.object.status == MaterialRequisition.STATUS_SUBMITTED
        ctx["can_submit"] = self.object.status == MaterialRequisition.STATUS_DRAFT
        return ctx


class MRApproveView(LoginRequiredMixin, View):
    """POST-only: approve a submitted MR."""

    def post(self, request, pk):
        mr = get_object_or_404(MaterialRequisition, pk=pk)
        if mr.status != MaterialRequisition.STATUS_SUBMITTED:
            messages.error(request, "Only submitted requisitions can be approved.")
            return redirect(mr.get_absolute_url())
        mr.status = MaterialRequisition.STATUS_APPROVED
        mr.approved_by = request.user
        mr.approved_at = timezone.now()
        mr.updated_by = request.user
        mr.save(update_fields=["status", "approved_by", "approved_at", "updated_by", "updated_at"])
        messages.success(request, f"{mr.mr_number} approved.")
        return redirect(mr.get_absolute_url())


class MRSubmitView(LoginRequiredMixin, View):
    """POST-only: submit a draft MR for approval."""

    def post(self, request, pk):
        mr = get_object_or_404(MaterialRequisition, pk=pk)
        if mr.status != MaterialRequisition.STATUS_DRAFT:
            messages.error(request, "Only draft requisitions can be submitted.")
            return redirect(mr.get_absolute_url())
        if not mr.items.exists():
            messages.error(request, "Cannot submit an MR with no items.")
            return redirect(mr.get_absolute_url())
        mr.status = MaterialRequisition.STATUS_SUBMITTED
        mr.updated_by = request.user
        mr.save(update_fields=["status", "updated_by", "updated_at"])
        messages.success(request, f"{mr.mr_number} submitted for approval.")
        return redirect(mr.get_absolute_url())


class MRRejectView(LoginRequiredMixin, FormView):
    """POST-only: reject a submitted MR with a reason."""

    form_class = MRRejectForm
    template_name = "procurement/mr_reject.html"

    def get_mr(self):
        return get_object_or_404(MaterialRequisition, pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mr"] = self.get_mr()
        return ctx

    def form_valid(self, form):
        mr = self.get_mr()
        if mr.status != MaterialRequisition.STATUS_SUBMITTED:
            messages.error(self.request, "Only submitted requisitions can be rejected.")
            return redirect(mr.get_absolute_url())
        mr.status = MaterialRequisition.STATUS_REJECTED
        mr.rejection_reason = form.cleaned_data["rejection_reason"]
        mr.updated_by = self.request.user
        mr.save(update_fields=["status", "rejection_reason", "updated_by", "updated_at"])
        messages.warning(self.request, f"{mr.mr_number} has been rejected.")
        return redirect(mr.get_absolute_url())


# ---------------------------------------------------------------------------
# Purchase Order views
# ---------------------------------------------------------------------------


class POListView(LoginRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = "procurement/po_list.html"
    context_object_name = "purchase_orders"
    paginate_by = 20

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related(
            "project", "supplier"
        ).order_by("-date", "-po_number")
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        supplier = self.request.GET.get("supplier")
        if supplier:
            qs = qs.filter(supplier_id=supplier)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = Project.objects.all()
        ctx["suppliers"] = Supplier.objects.filter(is_blacklisted=False)
        ctx["status_choices"] = PurchaseOrder.STATUS_CHOICES
        return ctx


class POCreateView(LoginRequiredMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = "procurement/po_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["item_formset"] = POItemFormSet(self.request.POST)
        else:
            ctx["item_formset"] = POItemFormSet()
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        item_formset = ctx["item_formset"]
        if item_formset.is_valid():
            with transaction.atomic():
                form.instance.created_by = self.request.user
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()
                self.object.recalculate_total()
            messages.success(self.request, f"Purchase Order {self.object.po_number} created.")
            return redirect(self.object.get_absolute_url())
        return self.form_invalid(form)


class PODetailView(LoginRequiredMixin, DetailView):
    model = PurchaseOrder
    template_name = "procurement/po_detail.html"
    context_object_name = "po"

    def get_queryset(self):
        return PurchaseOrder.objects.select_related(
            "project", "supplier", "mr", "approved_by"
        ).prefetch_related("items__material", "grns__items", "invoices")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_approve"] = self.object.status == PurchaseOrder.STATUS_PENDING_APPROVAL
        ctx["can_create_grn"] = self.object.status in (
            PurchaseOrder.STATUS_APPROVED,
            PurchaseOrder.STATUS_SENT,
            PurchaseOrder.STATUS_PARTIALLY_DELIVERED,
        )
        return ctx


class POUpdateView(LoginRequiredMixin, UpdateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = "procurement/po_form.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.status not in (
            PurchaseOrder.STATUS_DRAFT,
            PurchaseOrder.STATUS_PENDING_APPROVAL,
        ):
            return None
        return obj

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object is None:
            messages.error(request, "Only draft or pending-approval POs can be edited.")
            return redirect("procurement:po_list")
        return super(UpdateView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["item_formset"] = POItemFormSet(self.request.POST, instance=self.object)
        else:
            ctx["item_formset"] = POItemFormSet(instance=self.object)
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        item_formset = ctx["item_formset"]
        if item_formset.is_valid():
            with transaction.atomic():
                form.instance.updated_by = self.request.user
                self.object = form.save()
                item_formset.instance = self.object
                item_formset.save()
                self.object.recalculate_total()
            messages.success(self.request, f"Purchase Order {self.object.po_number} updated.")
            return redirect(self.object.get_absolute_url())
        return self.form_invalid(form)


class POApproveView(LoginRequiredMixin, View):
    """POST-only: approve a PO that is pending approval."""

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if po.status != PurchaseOrder.STATUS_PENDING_APPROVAL:
            messages.error(request, "Only pending-approval POs can be approved.")
            return redirect(po.get_absolute_url())
        po.status = PurchaseOrder.STATUS_APPROVED
        po.approved_by = request.user
        po.approved_at = timezone.now()
        po.updated_by = request.user
        po.save(update_fields=["status", "approved_by", "approved_at", "updated_by", "updated_at"])
        messages.success(request, f"{po.po_number} approved.")
        return redirect(po.get_absolute_url())


class POSubmitView(LoginRequiredMixin, View):
    """POST-only: move a draft PO to pending approval."""

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        if po.status != PurchaseOrder.STATUS_DRAFT:
            messages.error(request, "Only draft POs can be submitted for approval.")
            return redirect(po.get_absolute_url())
        if not po.items.exists():
            messages.error(request, "Cannot submit a PO with no line items.")
            return redirect(po.get_absolute_url())
        po.status = PurchaseOrder.STATUS_PENDING_APPROVAL
        po.updated_by = request.user
        po.save(update_fields=["status", "updated_by", "updated_at"])
        messages.success(request, f"{po.po_number} submitted for approval.")
        return redirect(po.get_absolute_url())


# ---------------------------------------------------------------------------
# GRN views
# ---------------------------------------------------------------------------


class GRNCreateView(LoginRequiredMixin, CreateView):
    """Create a GRN from an approved/sent PO."""

    model = GoodsReceivedNote
    form_class = GoodsReceivedNoteForm
    template_name = "procurement/grn_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.po = get_object_or_404(
            PurchaseOrder,
            pk=self.kwargs["po_pk"],
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["po"] = self.po
        ctx["po_items"] = self.po.items.select_related("material")
        return ctx

    def form_valid(self, form):
        if self.po.status not in (
            PurchaseOrder.STATUS_APPROVED,
            PurchaseOrder.STATUS_SENT,
            PurchaseOrder.STATUS_PARTIALLY_DELIVERED,
        ):
            messages.error(
                self.request,
                "GRNs can only be created for approved or sent POs.",
            )
            return redirect(self.po.get_absolute_url())

        with transaction.atomic():
            form.instance.po = self.po
            form.instance.created_by = self.request.user
            self.object = form.save()

            # Create GRN items for each PO item from POST data
            for po_item in self.po.items.all():
                qty_key = f"qty_{po_item.pk}"
                disc_key = f"disc_{po_item.pk}"
                disc_notes_key = f"disc_notes_{po_item.pk}"
                qty_str = self.request.POST.get(qty_key, "0").strip()
                try:
                    qty = float(qty_str)
                except ValueError:
                    qty = 0
                if qty > 0:
                    has_disc = self.request.POST.get(disc_key) == "on"
                    GRNItem.objects.create(
                        grn=self.object,
                        po_item=po_item,
                        quantity_delivered=qty,
                        has_discrepancy=has_disc,
                        discrepancy_notes=self.request.POST.get(disc_notes_key, ""),
                    )

            # Update PO status
            total_ordered = sum(
                item.quantity for item in self.po.items.all()
            )
            total_delivered = sum(
                grn_item.quantity_delivered
                for grn in self.po.grns.all()
                for grn_item in grn.items.all()
            )
            if total_delivered >= total_ordered:
                self.po.status = PurchaseOrder.STATUS_DELIVERED
            else:
                self.po.status = PurchaseOrder.STATUS_PARTIALLY_DELIVERED
            self.po.updated_by = self.request.user
            self.po.save(update_fields=["status", "updated_by", "updated_at"])

        messages.success(
            self.request, f"GRN {self.object.grn_number} created successfully."
        )
        return redirect(self.object.get_absolute_url())


class GRNDetailView(LoginRequiredMixin, DetailView):
    model = GoodsReceivedNote
    template_name = "procurement/grn_detail.html"
    context_object_name = "grn"

    def get_queryset(self):
        return GoodsReceivedNote.objects.select_related(
            "po__project", "po__supplier", "received_by"
        ).prefetch_related("items__po_item__material")


# ---------------------------------------------------------------------------
# Invoice views
# ---------------------------------------------------------------------------


class InvoiceListView(LoginRequiredMixin, ListView):
    model = SupplierInvoice
    template_name = "procurement/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        qs = SupplierInvoice.objects.select_related(
            "supplier", "po__project"
        ).order_by("-invoice_date")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        supplier = self.request.GET.get("supplier")
        if supplier:
            qs = qs.filter(supplier_id=supplier)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = SupplierInvoice.STATUS_CHOICES
        ctx["suppliers"] = Supplier.objects.all()
        return ctx


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = SupplierInvoice
    form_class = SupplierInvoiceForm
    template_name = "procurement/invoice_form.html"
    success_url = reverse_lazy("procurement:invoice_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Invoice recorded.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Stock Ledger view
# ---------------------------------------------------------------------------


class StockLedgerView(LoginRequiredMixin, ListView):
    """
    Shows stock ledger entries, with optional filtering by project and material.
    Also computes net on-site stock for a material on a project.
    """

    model = StockLedger
    template_name = "procurement/stock_ledger.html"
    context_object_name = "entries"
    paginate_by = 30

    def get_queryset(self):
        qs = StockLedger.objects.select_related(
            "project", "material", "recorded_by"
        ).order_by("-date", "-pk")
        project_pk = self.request.GET.get("project")
        if project_pk:
            qs = qs.filter(project_id=project_pk)
        material_pk = self.request.GET.get("material")
        if material_pk:
            qs = qs.filter(material_id=material_pk)
        tx_type = self.request.GET.get("type")
        if tx_type:
            qs = qs.filter(transaction_type=tx_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = Project.objects.all()
        ctx["materials"] = Material.objects.order_by("item_code")
        ctx["tx_types"] = StockLedger.TRANSACTION_TYPE_CHOICES

        # Compute on-site stock for current filter combination
        project_pk = self.request.GET.get("project")
        material_pk = self.request.GET.get("material")
        if project_pk and material_pk:
            try:
                project = Project.objects.get(pk=project_pk)
                material = Material.objects.get(pk=material_pk)
                ctx["stock_quantity"] = material.stock_on_site(project)
                ctx["selected_project"] = project
                ctx["selected_material"] = material
            except (Project.DoesNotExist, Material.DoesNotExist):
                pass

        return ctx


class StockLedgerCreateView(LoginRequiredMixin, CreateView):
    model = StockLedger
    form_class = StockLedgerForm
    template_name = "procurement/stock_ledger_form.html"
    success_url = reverse_lazy("procurement:stock_ledger")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Stock ledger entry recorded.")
        return super().form_valid(form)
