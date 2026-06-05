from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.core.permissions import accessible_projects, can_manage_documents
from apps.core.models import AuditLog
from apps.projects.models import Project

from .forms import (
    CorrespondenceForm,
    DistributionContactForm,
    DocumentTransmittalForm,
    DrawingForm,
    DrawingRevisionForm,
    ProjectDocumentForm,
    RFIForm,
    SubmittalForm,
)
from .models import (
    Correspondence,
    DistributionContact,
    DocumentTransmittal,
    Drawing,
    DrawingRevision,
    ProjectDocument,
    RFI,
    Submittal,
)


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
