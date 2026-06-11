from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView, CreateView, TemplateView

from apps.budget.models import Subcontract, SubcontractorDocument
from apps.core.permissions import can_manage_project

from .forms import DocumentReviewForm, SubcontractorDocumentForm


class SubcontractorMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only subcontractor-role users pass this gate."""

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_subcontractor

    def get_subcontract(self):
        if not hasattr(self, "_subcontract"):
            self._subcontract = get_object_or_404(Subcontract, user=self.request.user)
        return self._subcontract


class StaffDocMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Staff members who can review subcontractor docs."""

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and not getattr(user, "is_subcontractor", False)


# ---------------------------------------------------------------------------
# Subcontractor-facing views
# ---------------------------------------------------------------------------

class PortalView(SubcontractorMixin, TemplateView):
    template_name = "subcontractor/portal.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        sub = self.get_subcontract()
        ctx["subcontract"] = sub
        ctx["project"] = sub.project
        ctx["recent_docs"] = sub.documents.select_related("submitted_by", "reviewed_by").order_by("-created_at")[:10]
        ctx["doc_counts"] = {
            "total": sub.documents.count(),
            "pending": sub.documents.filter(status=SubcontractorDocument.STATUS_PENDING).count(),
            "approved": sub.documents.filter(status=SubcontractorDocument.STATUS_APPROVED).count(),
            "rejected": sub.documents.filter(status=SubcontractorDocument.STATUS_REJECTED).count(),
        }
        try:
            ctx["work_package"] = sub.work_package
        except Exception:
            ctx["work_package"] = None
        return ctx


class DocumentListView(SubcontractorMixin, ListView):
    template_name = "subcontractor/document_list.html"
    context_object_name = "documents"
    paginate_by = 20

    def get_queryset(self):
        sub = self.get_subcontract()
        qs = sub.documents.select_related("submitted_by", "reviewed_by")
        status = self.request.GET.get("status", "")
        doc_type = self.request.GET.get("doc_type", "")
        if status:
            qs = qs.filter(status=status)
        if doc_type:
            qs = qs.filter(doc_type=doc_type)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["subcontract"] = self.get_subcontract()
        ctx["status_choices"] = SubcontractorDocument.STATUS_CHOICES
        ctx["doc_type_choices"] = SubcontractorDocument.DOC_TYPE_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        ctx["selected_type"] = self.request.GET.get("doc_type", "")
        return ctx


class DocumentUploadView(SubcontractorMixin, CreateView):
    template_name = "subcontractor/document_upload.html"
    form_class = SubcontractorDocumentForm

    def form_valid(self, form):
        sub = self.get_subcontract()
        form.instance.subcontract = sub
        form.instance.submitted_by = self.request.user
        form.save()
        messages.success(self.request, f'"{form.instance.title}" submitted successfully.')
        return redirect(reverse("subcontractor:document-list"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["subcontract"] = self.get_subcontract()
        return ctx


# ---------------------------------------------------------------------------
# Staff-facing views — review subcontractor documents per project
# ---------------------------------------------------------------------------

class ProjectSubcontractorDocsView(StaffDocMixin, ListView):
    template_name = "subcontractor/staff_document_list.html"
    context_object_name = "documents"
    paginate_by = 25

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.subcontract = get_object_or_404(
            Subcontract,
            pk=kwargs["subcontract_pk"],
            project__pk=kwargs["project_pk"],
        )

    def test_func(self):
        if not super().test_func():
            return False
        return can_manage_project(self.request.user, self.subcontract.project) or \
               self.request.user.role in {"document_controller", "system_admin", "managing_director"}

    def get_queryset(self):
        qs = self.subcontract.documents.select_related("submitted_by", "reviewed_by")
        status = self.request.GET.get("status", "")
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["subcontract"] = self.subcontract
        ctx["project"] = self.subcontract.project
        ctx["status_choices"] = SubcontractorDocument.STATUS_CHOICES
        ctx["selected_status"] = self.request.GET.get("status", "")
        return ctx


class DocumentReviewView(StaffDocMixin, View):
    """Staff reviews (approves/rejects) a subcontractor document."""

    def get_document(self, pk, project_pk):
        return get_object_or_404(
            SubcontractorDocument,
            pk=pk,
            subcontract__project__pk=project_pk,
        )

    def test_func(self):
        if not super().test_func():
            return False
        doc = self.get_document(self.kwargs["pk"], self.kwargs["project_pk"])
        return can_manage_project(self.request.user, doc.subcontract.project) or \
               self.request.user.role in {"document_controller", "system_admin", "managing_director"}

    def post(self, request, project_pk, subcontract_pk, pk):
        doc = self.get_document(pk, project_pk)
        form = DocumentReviewForm(request.POST, instance=doc)
        if form.is_valid():
            reviewed = form.save(commit=False)
            reviewed.reviewed_by = request.user
            reviewed.reviewed_at = timezone.now()
            reviewed.save()
            messages.success(request, f'Document "{doc.title}" marked as {doc.get_status_display()}.')
        else:
            messages.error(request, "Invalid review submission.")
        return redirect(reverse(
            "subcontractor:staff-doc-list",
            kwargs={"project_pk": project_pk, "subcontract_pk": subcontract_pk},
        ))
