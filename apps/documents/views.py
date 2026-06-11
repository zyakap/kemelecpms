import csv

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.accounts.models import User
from apps.core.permissions import accessible_projects, can_manage_documents
from apps.core.models import AuditLog
from apps.projects.models import Project

from .forms import (
    CorrespondenceForm,
    DistributionContactForm,
    DocumentControlSettingsForm,
    DocumentTransmittalForm,
    DrawingForm,
    DrawingRevisionForm,
    ProjectDocumentForm,
    ProjectDocumentRevisionForm,
    RFIForm,
    SubmittalForm,
)
from .models import (
    Correspondence,
    DistributionContact,
    DocumentAccessLog,
    DocumentControlSettings,
    DocumentTransmittal,
    Drawing,
    DrawingRevision,
    ProjectDocument,
    ProjectDocumentRevision,
    RFI,
    Submittal,
)
from .services import get_document_settings


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------


class ProjectMixin(LoginRequiredMixin):
    """Resolves the current project from the ``project_pk`` URL kwarg."""

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


# ---------------------------------------------------------------------------
# Drawing views
# ---------------------------------------------------------------------------


class DrawingListView(ProjectMixin, ListView):
    model = Drawing
    template_name = "documents/drawing_list.html"
    context_object_name = "drawings"

    def get_queryset(self):
        qs = Drawing.objects.filter(project=self.get_project())
        discipline = self.request.GET.get("discipline")
        status = self.request.GET.get("status")
        if discipline:
            qs = qs.filter(discipline=discipline)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("discipline", "drawing_number")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["discipline_choices"] = Drawing.DISCIPLINE_CHOICES
        ctx["status_choices"] = Drawing.STATUS_CHOICES
        ctx["selected_discipline"] = self.request.GET.get("discipline", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class LatestIFCDrawingListView(DrawingListView):
    template_name = "documents/latest_ifc_list.html"

    def get_queryset(self):
        return Drawing.objects.filter(
            project=self.get_project(),
            status=Drawing.STATUS_IFC,
        ).order_by("discipline", "drawing_number")


class DrawingCreateView(ProjectMixin, CreateView):
    model = Drawing
    form_class = DrawingForm
    template_name = "documents/drawing_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to register drawings for this project.")
            return redirect(reverse_lazy("documents:drawing-list", kwargs={"project_pk": self.get_project().pk}))
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Drawing registered successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("documents:drawing-list", kwargs={"project_pk": self.get_project().pk})


class DrawingUpdateView(ProjectMixin, UpdateView):
    model = Drawing
    form_class = DrawingForm
    template_name = "documents/drawing_form.html"

    def get_queryset(self):
        return Drawing.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update drawings for this project.")
            return redirect(self.object.get_absolute_url())
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Drawing updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "documents:drawing-detail",
            kwargs={"project_pk": self.get_project().pk, "pk": self.object.pk},
        )


class DrawingDetailView(ProjectMixin, DetailView):
    model = Drawing
    template_name = "documents/drawing_detail.html"
    context_object_name = "drawing"

    def get_queryset(self):
        return Drawing.objects.filter(project=self.get_project()).prefetch_related(
            "revisions__uploaded_by", "rfis"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["revisions"] = self.object.revisions.order_by("-date")
        ctx["revision_form"] = DrawingRevisionForm(drawing=self.object, user=self.request.user)
        return ctx


# ---------------------------------------------------------------------------
# Drawing Revision views
# ---------------------------------------------------------------------------


class DrawingRevisionCreateView(LoginRequiredMixin, CreateView):
    model = DrawingRevision
    form_class = DrawingRevisionForm
    template_name = "documents/drawingrevision_form.html"

    def get_drawing(self):
        if not hasattr(self, "_drawing"):
            self._drawing = get_object_or_404(
                Drawing,
                pk=self.kwargs["drawing_pk"],
                project__in=accessible_projects(self.request.user),
            )
        return self._drawing

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["drawing"] = self.get_drawing()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        drawing = self.get_drawing()
        ctx["drawing"] = drawing
        ctx["project"] = drawing.project
        return ctx

    def form_valid(self, form):
        drawing = self.get_drawing()
        if not can_manage_documents(self.request.user, drawing.project):
            messages.error(self.request, "You do not have permission to upload revisions for this drawing.")
            return redirect(drawing.get_absolute_url())
        form.instance.drawing = drawing
        form.instance.uploaded_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Drawing revision uploaded.")
        return super().form_valid(form)

    def get_success_url(self):
        drawing = self.get_drawing()
        return reverse_lazy(
            "documents:drawing-detail",
            kwargs={"project_pk": drawing.project_id, "pk": drawing.pk},
        )


# ---------------------------------------------------------------------------
# RFI views
# ---------------------------------------------------------------------------


class RFIListView(ProjectMixin, ListView):
    model = RFI
    template_name = "documents/rfi_list.html"
    context_object_name = "rfis"
    paginate_by = 25

    def get_queryset(self):
        qs = RFI.objects.filter(project=self.get_project()).select_related("raised_by", "drawing")
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-date_raised")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = RFI.STATUS_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class RFICreateView(ProjectMixin, CreateView):
    model = RFI
    form_class = RFIForm
    template_name = "documents/rfi_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.raised_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "RFI raised successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("documents:rfi-list", kwargs={"project_pk": self.get_project().pk})


class RFIUpdateView(ProjectMixin, UpdateView):
    model = RFI
    form_class = RFIForm
    template_name = "documents/rfi_form.html"

    def get_queryset(self):
        return RFI.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update this RFI.")
            return redirect(
                reverse_lazy("documents:rfi-detail", kwargs={"project_pk": self.get_project().pk, "pk": self.object.pk})
            )
        old_status = self.object.status
        form.instance.updated_by = self.request.user
        messages.success(self.request, "RFI updated.")
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"RFI status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        return response

    def get_success_url(self):
        return reverse_lazy(
            "documents:rfi-detail",
            kwargs={"project_pk": self.get_project().pk, "pk": self.object.pk},
        )


class RFIDetailView(ProjectMixin, DetailView):
    model = RFI
    template_name = "documents/rfi_detail.html"
    context_object_name = "rfi"

    def get_queryset(self):
        return RFI.objects.filter(project=self.get_project()).select_related(
            "raised_by", "drawing"
        )


# ---------------------------------------------------------------------------
# Submittal views
# ---------------------------------------------------------------------------


class SubmittalListView(ProjectMixin, ListView):
    model = Submittal
    template_name = "documents/submittal_list.html"
    context_object_name = "submittals"
    paginate_by = 25

    def get_queryset(self):
        qs = Submittal.objects.filter(project=self.get_project()).select_related(
            "submitted_by", "reviewed_by"
        )
        submittal_type = self.request.GET.get("type")
        status = self.request.GET.get("status")
        if submittal_type:
            qs = qs.filter(submittal_type=submittal_type)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-submitted_date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["submittal_type_choices"] = Submittal.SUBMITTAL_TYPE_CHOICES
        ctx["status_choices"] = Submittal.STATUS_CHOICES
        ctx["selected_type"] = self.request.GET.get("type", "")
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class SubmittalCreateView(ProjectMixin, CreateView):
    model = Submittal
    form_class = SubmittalForm
    template_name = "documents/submittal_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.project = self.get_project()
        form.instance.submitted_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Submittal lodged successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "documents:submittal-list", kwargs={"project_pk": self.get_project().pk}
        )


class SubmittalUpdateView(ProjectMixin, UpdateView):
    model = Submittal
    form_class = SubmittalForm
    template_name = "documents/submittal_form.html"

    def get_queryset(self):
        return Submittal.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update this submittal.")
            return redirect(
                reverse_lazy("documents:submittal-list", kwargs={"project_pk": self.get_project().pk})
            )
        old_status = self.object.status
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Submittal updated.")
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"Submittal status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        return response

    def get_success_url(self):
        return reverse_lazy(
            "documents:submittal-list", kwargs={"project_pk": self.get_project().pk}
        )


# ---------------------------------------------------------------------------
# Correspondence views
# ---------------------------------------------------------------------------


class CorrespondenceListView(ProjectMixin, ListView):
    model = Correspondence
    template_name = "documents/correspondence_list.html"
    context_object_name = "correspondences"
    paginate_by = 25

    def get_queryset(self):
        qs = Correspondence.objects.filter(project=self.get_project())
        direction = self.request.GET.get("direction")
        action = self.request.GET.get("action")
        if direction:
            qs = qs.filter(direction=direction)
        if action == "required":
            qs = qs.filter(action_required=True, is_responded=False)
        return qs.order_by("-date")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["direction_choices"] = Correspondence.DIRECTION_CHOICES
        ctx["selected_direction"] = self.request.GET.get("direction", "")
        ctx["selected_action"] = self.request.GET.get("action", "")
        return ctx


class CorrespondenceCreateView(ProjectMixin, CreateView):
    model = Correspondence
    form_class = CorrespondenceForm
    template_name = "documents/correspondence_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to register correspondence for this project.")
            return redirect(
                reverse_lazy("documents:correspondence-list", kwargs={"project_pk": self.get_project().pk})
            )
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Correspondence registered.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "documents:correspondence-list", kwargs={"project_pk": self.get_project().pk}
        )


class CorrespondenceUpdateView(ProjectMixin, UpdateView):
    model = Correspondence
    form_class = CorrespondenceForm
    template_name = "documents/correspondence_form.html"

    def get_queryset(self):
        return Correspondence.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update correspondence for this project.")
            return redirect(
                reverse_lazy("documents:correspondence-list", kwargs={"project_pk": self.get_project().pk})
            )
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Correspondence updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "documents:correspondence-list", kwargs={"project_pk": self.get_project().pk}
        )


# ---------------------------------------------------------------------------
# ProjectDocument views
# ---------------------------------------------------------------------------


class ProjectDocumentListView(ProjectMixin, ListView):
    model = ProjectDocument
    template_name = "documents/projectdocument_list.html"
    context_object_name = "documents"

    def get_queryset(self):
        return ProjectDocument.objects.filter(
            project=self.get_project()
        ).select_related("uploaded_by").order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["selected_type"] = self.request.GET.get("type", "")
        return ctx


class ProjectDocumentTemplatesView(LoginRequiredMixin, ListView):
    """Company-wide document templates (project=None)."""

    model = ProjectDocument
    template_name = "documents/projectdocument_templates.html"
    context_object_name = "documents"

    def get_queryset(self):
        return ProjectDocument.objects.filter(project__isnull=True).select_related(
            "uploaded_by"
        ).order_by("-created_at")


class ProjectDocumentCreateView(ProjectMixin, CreateView):
    model = ProjectDocument
    form_class = ProjectDocumentForm
    template_name = "documents/projectdocument_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to upload documents for this project.")
            return redirect(
                reverse_lazy("documents:projectdoc-list", kwargs={"project_pk": self.get_project().pk})
            )
        form.instance.project = self.get_project()
        form.instance.uploaded_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Document uploaded successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            "documents:projectdoc-list", kwargs={"project_pk": self.get_project().pk}
        )


class DistributionContactListView(ProjectMixin, ListView):
    model = DistributionContact
    template_name = "documents/distribution_contact_list.html"
    context_object_name = "contacts"

    def get_queryset(self):
        return DistributionContact.objects.filter(project=self.get_project()).order_by(
            "organization", "name"
        )


class DistributionContactCreateView(ProjectMixin, CreateView):
    model = DistributionContact
    form_class = DistributionContactForm
    template_name = "documents/distribution_contact_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create distribution contacts for this project.")
            return redirect(self.get_success_url())
        form.instance.project = self.get_project()
        form.instance.created_by = self.request.user
        messages.success(self.request, "Distribution contact created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("documents:distribution-contact-list", kwargs={"project_pk": self.get_project().pk})


class DistributionContactUpdateView(ProjectMixin, UpdateView):
    model = DistributionContact
    form_class = DistributionContactForm
    template_name = "documents/distribution_contact_form.html"

    def get_queryset(self):
        return DistributionContact.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update distribution contacts for this project.")
            return redirect(self.get_success_url())
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Distribution contact updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("documents:distribution-contact-list", kwargs={"project_pk": self.get_project().pk})


class DocumentTransmittalListView(ProjectMixin, ListView):
    model = DocumentTransmittal
    template_name = "documents/transmittal_list.html"
    context_object_name = "transmittals"

    def get_queryset(self):
        qs = DocumentTransmittal.objects.filter(project=self.get_project()).select_related("sent_by").prefetch_related(
            "recipients", "drawings", "submittals", "documents"
        )
        status = self.request.GET.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = DocumentTransmittal.STATUS_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class DocumentTransmittalCreateView(ProjectMixin, CreateView):
    model = DocumentTransmittal
    form_class = DocumentTransmittalForm
    template_name = "documents/transmittal_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to create transmittals for this project.")
            return redirect(self.get_success_url())
        form.instance.project = self.get_project()
        form.instance.sent_by = self.request.user
        form.instance.created_by = self.request.user
        messages.success(self.request, "Document transmittal created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("documents:transmittal-list", kwargs={"project_pk": self.get_project().pk})


class DocumentTransmittalUpdateView(ProjectMixin, UpdateView):
    model = DocumentTransmittal
    form_class = DocumentTransmittalForm
    template_name = "documents/transmittal_form.html"

    def get_queryset(self):
        return DocumentTransmittal.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update transmittals for this project.")
            return redirect(self.object.get_absolute_url())
        old_status = self.object.status
        if not form.instance.sent_by_id:
            form.instance.sent_by = self.request.user
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        if old_status != self.object.status:
            AuditLog.log(
                self.request.user,
                AuditLog.ACTION_UPDATE,
                self.object,
                changes=f"Transmittal status changed from {old_status} to {self.object.status}.",
                request=self.request,
            )
        messages.success(self.request, "Document transmittal updated.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class DocumentTransmittalDetailView(ProjectMixin, DetailView):
    model = DocumentTransmittal
    template_name = "documents/transmittal_detail.html"
    context_object_name = "transmittal"

    def get_queryset(self):
        return DocumentTransmittal.objects.filter(project=self.get_project()).select_related("sent_by").prefetch_related(
            "recipients", "drawings", "submittals", "documents"
        )


# ---------------------------------------------------------------------------
# Document Control hub, settings, and controlled-document workflow
# ---------------------------------------------------------------------------


SETTINGS_MANAGER_ROLES = {User.ROLE_DOC_CTRL, User.ROLE_ADMIN, User.ROLE_MD}


def can_manage_company_document_settings(user):
    return user.is_authenticated and (
        user.is_superuser or user.role in SETTINGS_MANAGER_ROLES
    )


class DocumentControlHomeView(LoginRequiredMixin, TemplateView):
    """Landing page for the documents module: per-project register summary."""

    template_name = "documents/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        projects = (
            accessible_projects(self.request.user)
            .annotate(
                drawing_count=Count("drawings", distinct=True),
                open_rfi_count=Count(
                    "rfis", filter=Q(rfis__status=RFI.STATUS_OPEN), distinct=True
                ),
                pending_submittal_count=Count(
                    "submittals",
                    filter=Q(submittals__status=Submittal.STATUS_SUBMITTED),
                    distinct=True,
                ),
                document_count=Count("project_documents", distinct=True),
                transmittal_count=Count("transmittals", distinct=True),
            )
            .order_by("name")
        )
        ctx["projects"] = projects
        ctx["can_manage_settings"] = can_manage_company_document_settings(
            self.request.user
        )
        return ctx


class CompanyDocumentSettingsView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Company-wide document control settings (the fallback for all projects)."""

    model = DocumentControlSettings
    form_class = DocumentControlSettingsForm
    template_name = "documents/settings_form.html"
    success_url = reverse_lazy("documents:company-settings")

    def test_func(self):
        return can_manage_company_document_settings(self.request.user)

    def get_object(self, queryset=None):
        obj, _ = DocumentControlSettings.objects.get_or_create(project=None)
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["settings_scope"] = "Company-wide defaults"
        return ctx

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        AuditLog.log(
            self.request.user,
            AuditLog.ACTION_UPDATE,
            self.object,
            changes="Company document control settings updated.",
            request=self.request,
        )
        messages.success(self.request, "Company document control settings saved.")
        return response


class ProjectDocumentSettingsView(ProjectMixin, UpdateView):
    """Per-project override of the document control settings."""

    model = DocumentControlSettings
    form_class = DocumentControlSettingsForm
    template_name = "documents/settings_form.html"

    def get_object(self, queryset=None):
        project = self.get_project()
        existing = DocumentControlSettings.objects.filter(project=project).first()
        if existing:
            return existing
        # Seed the override from the current company-wide defaults.
        company = get_document_settings(None)
        return DocumentControlSettings(
            project=project,
            rfi_prefix=company.rfi_prefix,
            submittal_prefix=company.submittal_prefix,
            correspondence_prefix=company.correspondence_prefix,
            transmittal_prefix=company.transmittal_prefix,
            document_prefix=company.document_prefix,
            number_padding=company.number_padding,
            include_project_code=company.include_project_code,
            rfi_response_due_days=company.rfi_response_due_days,
            submittal_review_due_days=company.submittal_review_due_days,
            correspondence_action_due_days=company.correspondence_action_due_days,
            require_document_approval=company.require_document_approval,
            require_transmittal_acknowledgement=company.require_transmittal_acknowledgement,
            auto_supersede_on_new_revision=company.auto_supersede_on_new_revision,
            allowed_file_extensions=company.allowed_file_extensions,
            max_upload_size_mb=company.max_upload_size_mb,
            default_confidentiality=company.default_confidentiality,
            log_document_access=company.log_document_access,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["settings_scope"] = f"Project override — {self.get_project().name}"
        ctx["is_project_override"] = True
        ctx["has_override"] = DocumentControlSettings.objects.filter(
            project=self.get_project()
        ).exists()
        return ctx

    def form_valid(self, form):
        project = self.get_project()
        if not can_manage_documents(self.request.user, project):
            messages.error(
                self.request,
                "You do not have permission to manage document control settings for this project.",
            )
            return redirect("documents:projectdoc-list", project_pk=project.pk)
        form.instance.project = project
        if not form.instance.pk:
            form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        AuditLog.log(
            self.request.user,
            AuditLog.ACTION_UPDATE,
            self.object,
            changes=f"Document control settings updated for project {project.project_id}.",
            request=self.request,
        )
        messages.success(self.request, "Project document control settings saved.")
        return response

    def get_success_url(self):
        return reverse_lazy(
            "documents:project-settings", kwargs={"project_pk": self.get_project().pk}
        )


class ProjectDocumentSettingsResetView(ProjectMixin, View):
    """Remove a project override so the project follows company defaults again."""

    def post(self, request, *args, **kwargs):
        project = self.get_project()
        if not can_manage_documents(request.user, project):
            messages.error(
                request,
                "You do not have permission to manage document control settings for this project.",
            )
        else:
            deleted, _ = DocumentControlSettings.objects.filter(project=project).delete()
            if deleted:
                AuditLog.log(
                    request.user,
                    AuditLog.ACTION_DELETE,
                    project,
                    changes="Project document control override removed; company defaults now apply.",
                    request=request,
                )
                messages.success(
                    request, "Project override removed — company defaults now apply."
                )
            else:
                messages.info(request, "This project already follows company defaults.")
        return redirect("documents:project-settings", project_pk=project.pk)


class ProjectDocumentDetailView(ProjectMixin, DetailView):
    model = ProjectDocument
    template_name = "documents/projectdocument_detail.html"
    context_object_name = "document"

    def get_queryset(self):
        return ProjectDocument.objects.filter(project=self.get_project()).select_related(
            "uploaded_by", "approved_by"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["revisions"] = self.object.revisions.select_related("uploaded_by")
        ctx["revision_form"] = ProjectDocumentRevisionForm(
            document=self.object, user=self.request.user
        )
        ctx["access_logs"] = self.object.access_logs.select_related("user")[:25]
        ctx["can_manage"] = can_manage_documents(self.request.user, self.get_project())
        ctx["allowed_transitions"] = ProjectDocument.STATUS_TRANSITIONS.get(
            self.object.status, set()
        )
        return ctx


class ProjectDocumentUpdateView(ProjectMixin, UpdateView):
    model = ProjectDocument
    form_class = ProjectDocumentForm
    template_name = "documents/projectdocument_form.html"

    def get_queryset(self):
        return ProjectDocument.objects.filter(project=self.get_project())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["project"] = self.get_project()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(self.request, "You do not have permission to update this document.")
            return redirect(self.object.get_absolute_url())
        if not self.object.is_editable:
            messages.error(
                self.request,
                "Approved, superseded, or archived documents cannot be edited — upload a new revision instead.",
            )
            return redirect(self.object.get_absolute_url())
        form.instance.updated_by = self.request.user
        messages.success(self.request, "Document updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return self.object.get_absolute_url()


class ProjectDocumentRevisionCreateView(ProjectMixin, CreateView):
    model = ProjectDocumentRevision
    form_class = ProjectDocumentRevisionForm
    template_name = "documents/projectdocumentrevision_form.html"

    def get_document(self):
        if not hasattr(self, "_document"):
            self._document = get_object_or_404(
                ProjectDocument,
                pk=self.kwargs["pk"],
                project=self.get_project(),
            )
        return self._document

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["document"] = self.get_document()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["document"] = self.get_document()
        return ctx

    def form_valid(self, form):
        document = self.get_document()
        if not can_manage_documents(self.request.user, self.get_project()):
            messages.error(
                self.request, "You do not have permission to upload revisions for this document."
            )
            return redirect(document.get_absolute_url())
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        AuditLog.log(
            self.request.user,
            AuditLog.ACTION_UPDATE,
            document,
            changes=f"Revision {self.object.version} uploaded for {document.document_number}.",
            request=self.request,
        )
        messages.success(self.request, "New revision uploaded.")
        return response

    def get_success_url(self):
        return self.get_document().get_absolute_url()


class ProjectDocumentTransitionView(ProjectMixin, View):
    """POST-only controlled-document status transitions."""

    ACTIONS = {
        "submit-review": ProjectDocument.STATUS_FOR_REVIEW,
        "approve": ProjectDocument.STATUS_APPROVED,
        "return-draft": ProjectDocument.STATUS_DRAFT,
        "supersede": ProjectDocument.STATUS_SUPERSEDED,
        "archive": ProjectDocument.STATUS_ARCHIVED,
    }

    def post(self, request, *args, **kwargs):
        project = self.get_project()
        document = get_object_or_404(
            ProjectDocument, pk=kwargs["pk"], project=project
        )
        action = kwargs["action"]
        new_status = self.ACTIONS.get(action)
        if new_status is None:
            messages.error(request, "Unknown document action.")
            return redirect(document.get_absolute_url())
        if not can_manage_documents(request.user, project):
            messages.error(
                request, "You do not have permission to manage documents for this project."
            )
            return redirect(document.get_absolute_url())
        if not document.can_transition_to(new_status):
            messages.error(
                request,
                f"Cannot move this document from {document.get_status_display()} "
                f"to {dict(ProjectDocument.STATUS_CHOICES)[new_status]}.",
            )
            return redirect(document.get_absolute_url())

        old_status = document.status
        document.status = new_status
        document.updated_by = request.user
        if new_status == ProjectDocument.STATUS_APPROVED:
            document.approved_by = request.user
            document.approved_at = timezone.now()
        document.save()
        AuditLog.log(
            request.user,
            AuditLog.ACTION_APPROVE
            if new_status == ProjectDocument.STATUS_APPROVED
            else AuditLog.ACTION_UPDATE,
            document,
            changes=f"Document status changed from {old_status} to {new_status}.",
            request=request,
        )
        messages.success(
            request, f"Document marked as {document.get_status_display()}."
        )
        return redirect(document.get_absolute_url())


class ProjectDocumentDownloadView(ProjectMixin, View):
    """Serves a controlled document and records the access."""

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        document = get_object_or_404(
            ProjectDocument, pk=kwargs["pk"], project=project
        )
        if get_document_settings(project).log_document_access:
            DocumentAccessLog.objects.create(
                document=document,
                user=request.user,
                action=DocumentAccessLog.ACTION_DOWNLOAD,
            )
        return redirect(document.file.url)


class TransmittalAcknowledgeView(ProjectMixin, View):
    """POST-only acknowledgement of a sent transmittal."""

    def post(self, request, *args, **kwargs):
        project = self.get_project()
        transmittal = get_object_or_404(
            DocumentTransmittal, pk=kwargs["pk"], project=project
        )
        if transmittal.status != DocumentTransmittal.STATUS_SENT:
            messages.error(request, "Only sent transmittals can be acknowledged.")
            return redirect(transmittal.get_absolute_url())
        transmittal.status = DocumentTransmittal.STATUS_ACKNOWLEDGED
        transmittal.acknowledged_date = timezone.now().date()
        transmittal.updated_by = request.user
        transmittal.save()
        AuditLog.log(
            request.user,
            AuditLog.ACTION_UPDATE,
            transmittal,
            changes="Transmittal acknowledged.",
            request=request,
        )
        messages.success(request, "Transmittal acknowledged.")
        return redirect(transmittal.get_absolute_url())


class ProjectDocumentRegisterExportView(ProjectMixin, View):
    """CSV export of the controlled document register for a project."""

    def get(self, request, *args, **kwargs):
        project = self.get_project()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="document-register-{project.project_id}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(
            [
                "Document No.",
                "Title",
                "Type",
                "Version",
                "Status",
                "Confidentiality",
                "Uploaded By",
                "Approved By",
                "Approved At",
                "Created",
            ]
        )
        for doc in (
            ProjectDocument.objects.filter(project=project)
            .select_related("uploaded_by", "approved_by")
            .order_by("document_number")
        ):
            writer.writerow(
                [
                    doc.document_number,
                    doc.title,
                    doc.document_type,
                    doc.version,
                    doc.get_status_display(),
                    doc.get_confidentiality_display(),
                    doc.uploaded_by.get_full_name() if doc.uploaded_by else "",
                    doc.approved_by.get_full_name() if doc.approved_by else "",
                    doc.approved_at.strftime("%Y-%m-%d %H:%M") if doc.approved_at else "",
                    doc.created_at.strftime("%Y-%m-%d"),
                ]
            )
        AuditLog.log(
            request.user,
            AuditLog.ACTION_EXPORT,
            project,
            changes="Document register exported to CSV.",
            request=request,
        )
        return response
