"""
Reports & Exports views.

Provides Excel downloads and PDF generation for all key system reports.
"""

from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.budget.models import BoQItem, CostCode, CostEntry
from apps.procurement.models import Material, StockLedger
from apps.projects.models import Milestone, Project
from apps.resources.models import AttendanceRecord, Worker
from apps.safety.models import Incident, ToolboxTalk

from .excel import (
    KC_AMBER,
    KC_GREEN,
    KC_LIGHT,
    KC_PRIMARY,
    KC_RED,
    add_sheet_header,
    make_workbook,
    workbook_response,
    write_row,
)


def _get_project(view):
    return get_object_or_404(Project, pk=view.kwargs["project_pk"])


# ---------------------------------------------------------------------------
# BoQ Export
# ---------------------------------------------------------------------------


class BoQExportView(LoginRequiredMixin, View):
    """Download full Bill of Quantities as Excel."""

    def get(self, request, project_pk):
        project = get_object_or_404(Project, pk=project_pk)
        items = BoQItem.objects.filter(project=project).select_related(
            "cost_code"
        ).order_by("item_number")


        wb = make_workbook(
            "Bill of Quantities",
            f"{project.project_id} — {project.name}",
        )
        ws = wb.create_sheet("BoQ")
        cols = [
            ("Item No.", 12),
            ("Trade / Section", 20),
            ("Description", 50),
            ("Unit", 8),
            ("Quantity", 12),
            ("Unit Rate (K)", 14),
            ("Amount (K)", 14),
            ("Cost Code", 20),
        ]
        next_row = add_sheet_header(ws, cols, title=f"Bill of Quantities — {project.name}")

        total_amount = Decimal("0.00")
        for item in items:
            amount = item.amount  # computed property on BoQItem
            total_amount += amount
            next_row = write_row(
                ws,
                next_row,
                [
                    item.item_number,
                    item.trade_section or "",
                    item.description,
                    item.unit,
                    float(item.quantity or 0),
                    float(item.unit_rate or 0),
                    float(amount),
                    item.cost_code.code if item.cost_code else "",
                ],
                number_format='#,##0.00',
            )

        # Total row
        write_row(
            ws, next_row,
            ["", "", "", "", "", "TOTAL", float(total_amount), ""],
            bold=True, bg_color=KC_LIGHT, number_format='#,##0.00',
        )

        return workbook_response(wb, f"BoQ_{project.project_id}.xlsx")


# ---------------------------------------------------------------------------
# Budget vs Actual Report
# ---------------------------------------------------------------------------


class BudgetReportExportView(LoginRequiredMixin, View):
    """Download Budget vs Actual report as Excel."""

    def get(self, request, project_pk):
        project = get_object_or_404(Project, pk=project_pk)
        cost_codes = CostCode.objects.filter(project=project).order_by("code")

        wb = make_workbook(
            "Budget vs Actual Report",
            f"{project.project_id} — {project.name}",
        )
        ws = wb.create_sheet("Budget vs Actual")
        cols = [
            ("Cost Code", 22),
            ("Description", 40),
            ("Budget (K)", 14),
            ("Committed (K)", 14),
            ("Actual (K)", 14),
            ("Total Spent (K)", 14),
            ("Remaining (K)", 14),
            ("% Used", 10),
            ("Status", 10),
        ]
        next_row = add_sheet_header(ws, cols, title=f"Budget vs Actual — {project.name}")

        total_budget = Decimal("0")
        total_committed = Decimal("0")
        total_actual = Decimal("0")

        for cc in cost_codes:
            committed = CostEntry.objects.filter(
                project=project, cost_code=cc, entry_type="COMMITTED"
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            actual = CostEntry.objects.filter(
                project=project, cost_code=cc, entry_type="ACTUAL"
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            spent = committed + actual
            remaining = cc.budget_amount - spent
            pct = float(spent / cc.budget_amount * 100) if cc.budget_amount else 0
            if pct > 100:
                status = "OVER BUDGET"
                bg = KC_RED
            elif pct >= 80:
                status = "NEAR LIMIT"
                bg = KC_AMBER
            else:
                status = "OK"
                bg = None

            total_budget += cc.budget_amount
            total_committed += committed
            total_actual += actual

            next_row = write_row(
                ws, next_row,
                [
                    cc.code,
                    cc.description,
                    float(cc.budget_amount),
                    float(committed),
                    float(actual),
                    float(spent),
                    float(remaining),
                    round(pct, 1),
                    status,
                ],
                bg_color=bg, number_format='#,##0.00',
            )

        total_spent = total_committed + total_actual
        write_row(
            ws, next_row,
            ["", "TOTAL", float(total_budget), float(total_committed),
             float(total_actual), float(total_spent),
             float(total_budget - total_spent), "", ""],
            bold=True, bg_color=KC_LIGHT, number_format='#,##0.00',
        )

        return workbook_response(wb, f"Budget_{project.project_id}.xlsx")


# ---------------------------------------------------------------------------
# Labour Attendance Report
# ---------------------------------------------------------------------------


class AttendanceReportExportView(LoginRequiredMixin, View):
    """Download attendance records as Excel."""

    def get(self, request, project_pk):
        project = get_object_or_404(Project, pk=project_pk)

        date_from_str = request.GET.get("from")
        date_to_str = request.GET.get("to")
        today = timezone.now().date()

        qs = AttendanceRecord.objects.filter(
            project=project
        ).select_related("worker", "crew").order_by("date", "worker__last_name")

        if date_from_str:
            from datetime import date as dt
            try:
                parts = date_from_str.split("-")
                date_from = dt(int(parts[0]), int(parts[1]), int(parts[2]))
                qs = qs.filter(date__gte=date_from)
            except (ValueError, IndexError):
                pass
        if date_to_str:
            from datetime import date as dt
            try:
                parts = date_to_str.split("-")
                date_to = dt(int(parts[0]), int(parts[1]), int(parts[2]))
                qs = qs.filter(date__lte=date_to)
            except (ValueError, IndexError):
                pass

        wb = make_workbook(
            "Labour Attendance Report",
            f"{project.project_id} — {project.name}",
        )
        ws = wb.create_sheet("Attendance")
        cols = [
            ("Date", 12),
            ("Worker Name", 25),
            ("Trade", 18),
            ("Crew", 18),
            ("Present", 10),
            ("Time In", 10),
            ("Time Out", 10),
            ("Overtime Hrs", 14),
        ]
        next_row = add_sheet_header(ws, cols, title=f"Labour Attendance — {project.name}")

        total_ot = Decimal("0")
        for rec in qs:
            worker = rec.worker
            total_ot += rec.overtime_hours or Decimal("0")
            next_row = write_row(
                ws, next_row,
                [
                    rec.date.strftime("%d/%m/%Y"),
                    f"{worker.first_name} {worker.last_name}".strip() or worker.employee_id,
                    getattr(worker, "trade", "") or "",
                    rec.crew.name if rec.crew else "",
                    "Yes" if rec.is_present else "No",
                    rec.time_in.strftime("%H:%M") if rec.time_in else "",
                    rec.time_out.strftime("%H:%M") if rec.time_out else "",
                    float(rec.overtime_hours or 0),
                ],
                number_format='0.00',
            )

        write_row(
            ws, next_row,
            ["", f"Total Records: {qs.count()}", "", "", "", "", "Total OT:", float(total_ot)],
            bold=True, bg_color=KC_LIGHT,
        )

        return workbook_response(wb, f"Attendance_{project.project_id}.xlsx")


# ---------------------------------------------------------------------------
# Stock Ledger Export
# ---------------------------------------------------------------------------


class StockLedgerExportView(LoginRequiredMixin, View):
    """Download stock ledger as Excel."""

    def get(self, request, project_pk):
        project = get_object_or_404(Project, pk=project_pk)
        entries = StockLedger.objects.filter(
            project=project
        ).select_related("material").order_by("material__name", "date")

        wb = make_workbook(
            "Stock Ledger Report",
            f"{project.project_id} — {project.name}",
        )
        ws = wb.create_sheet("Stock Ledger")
        cols = [
            ("Date", 12),
            ("Material", 35),
            ("Unit", 8),
            ("Transaction Type", 22),
            ("Qty In", 10),
            ("Qty Out", 10),
            ("Reference", 20),
            ("Notes", 35),
        ]
        next_row = add_sheet_header(ws, cols, title=f"Stock Ledger — {project.name}")

        for entry in entries:
            mat = entry.material
            is_in = entry.transaction_type in ("RECEIPT", "RETURN")
            qty_in = float(entry.quantity) if is_in else ""
            qty_out = float(entry.quantity) if not is_in else ""

            next_row = write_row(
                ws, next_row,
                [
                    entry.date.strftime("%d/%m/%Y"),
                    mat.name,
                    mat.unit,
                    entry.get_transaction_type_display(),
                    qty_in,
                    qty_out,
                    entry.reference or "",
                    entry.notes or "",
                ],
                number_format='#,##0.00',
            )

        return workbook_response(wb, f"StockLedger_{project.project_id}.xlsx")


# ---------------------------------------------------------------------------
# Safety Report Export
# ---------------------------------------------------------------------------


class SafetyReportExportView(LoginRequiredMixin, View):
    """Download safety statistics as Excel."""

    def get(self, request, project_pk):
        project = get_object_or_404(Project, pk=project_pk)
        incidents = Incident.objects.filter(project=project).order_by("date")
        toolbox_talks = ToolboxTalk.objects.filter(project=project).order_by("-date")

        wb = make_workbook(
            "Safety Report",
            f"{project.project_id} — {project.name}",
        )

        # Incidents sheet
        ws_inc = wb.create_sheet("Incidents")
        cols = [
            ("Incident No.", 16),
            ("Date", 12),
            ("Type", 20),
            ("Location", 25),
            ("Description", 50),
            ("Persons Involved", 30),
            ("LTI?", 8),
            ("Days Lost", 10),
            ("Status", 18),
        ]
        next_row = add_sheet_header(ws_inc, cols, title=f"Incident Register — {project.name}")
        for inc in incidents:
            next_row = write_row(
                ws_inc, next_row,
                [
                    inc.incident_number,
                    inc.date.strftime("%d/%m/%Y"),
                    inc.get_incident_type_display(),
                    inc.location,
                    inc.description,
                    inc.persons_involved or "",
                    "Yes" if inc.is_lti else "No",
                    inc.days_lost or 0,
                    inc.get_status_display(),
                ],
            )

        # Toolbox Talks sheet
        ws_tb = wb.create_sheet("Toolbox Talks")
        cols2 = [
            ("Date", 12),
            ("Topic", 50),
            ("Presenter", 25),
            ("Attendees", 10),
            ("Notes", 40),
        ]
        next_row2 = add_sheet_header(ws_tb, cols2, title=f"Toolbox Talks — {project.name}")
        for tb in toolbox_talks:
            presenter = tb.presenter
            next_row2 = write_row(
                ws_tb, next_row2,
                [
                    tb.date.strftime("%d/%m/%Y"),
                    tb.topic,
                    presenter.get_full_name() if presenter else "",
                    tb.attendee_count or 0,
                    tb.notes or "",
                ],
            )

        return workbook_response(wb, f"Safety_{project.project_id}.xlsx")


# ---------------------------------------------------------------------------
# Monthly Progress Report (PDF)
# ---------------------------------------------------------------------------


class MonthlyProgressReportView(LoginRequiredMixin, TemplateView):
    """Generate a Monthly Progress Report PDF."""

    template_name = "reports/monthly_progress_report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs["project_pk"])
        today = timezone.now().date()

        # Report period: default to current month, overridable via query params
        try:
            year = int(self.request.GET.get("year", today.year))
            month = int(self.request.GET.get("month", today.month))
        except ValueError:
            year, month = today.year, today.month

        import calendar
        period_from = today.replace(year=year, month=month, day=1)
        period_to = today.replace(
            year=year, month=month,
            day=calendar.monthrange(year, month)[1]
        )
        period_label = period_from.strftime("%B %Y")

        # Budget
        total_budget = (
            CostCode.objects.filter(project=project)
            .aggregate(total=Sum("budget_amount"))["total"] or Decimal("0")
        )
        total_committed = (
            CostEntry.objects.filter(project=project, entry_type="COMMITTED")
            .aggregate(total=Sum("amount"))["total"] or Decimal("0")
        )
        total_actual = (
            CostEntry.objects.filter(project=project, entry_type="ACTUAL")
            .aggregate(total=Sum("amount"))["total"] or Decimal("0")
        )
        total_spent = total_committed + total_actual

        # Schedule
        from apps.schedule.models import Programme, WBSActivity
        milestones = Milestone.objects.filter(project=project).order_by("target_date")
        achieved = milestones.filter(is_achieved=True).count()
        total_ms = milestones.count()
        overall_pct = round(achieved / total_ms * 100, 1) if total_ms else 0

        # DSRs for this month
        from apps.dsr.models import DailySiteReport, DSRActivity
        dsrs = DailySiteReport.objects.filter(
            project=project,
            date__gte=period_from,
            date__lte=period_to,
            status=DailySiteReport.STATUS_APPROVED,
        ).order_by("date")

        # Recent site photos
        from apps.dsr.models import DSRPhoto
        recent_photos = DSRPhoto.objects.filter(
            dsr__project=project,
            dsr__date__gte=period_from,
            dsr__date__lte=period_to,
        ).select_related("dsr").order_by("-dsr__date")[:12]

        # Safety this month
        incidents_this_month = Incident.objects.filter(
            project=project,
            date__gte=period_from,
            date__lte=period_to,
        )
        lti_count = incidents_this_month.filter(incident_type="LTI").count()
        near_miss_count = incidents_this_month.filter(incident_type="NEAR_MISS").count()

        tb_count = ToolboxTalk.objects.filter(
            project=project,
            date__gte=period_from,
            date__lte=period_to,
        ).count()

        # Upcoming milestones (next 60 days)
        upcoming_milestones = milestones.filter(
            is_achieved=False,
            target_date__gte=today,
            target_date__lte=today + timezone.timedelta(days=60),
        )

        # Open RFIs / NCRs
        from apps.documents.models import RFI
        from apps.quality.models import NCR
        open_rfis = RFI.objects.filter(project=project, status__in=["OPEN", "RESPONDED"])
        open_ncrs = NCR.objects.filter(project=project, status__in=["OPEN", "UNDER_REVIEW"])

        ctx.update({
            "project": project,
            "period_label": period_label,
            "period_from": period_from,
            "period_to": period_to,
            "report_date": today,
            # Budget
            "total_budget": total_budget,
            "total_spent": total_spent,
            "total_actual": total_actual,
            "total_committed": total_committed,
            "budget_remaining": total_budget - total_spent,
            "budget_pct": round(float(total_spent / total_budget * 100), 1) if total_budget else 0,
            # Schedule
            "overall_pct": overall_pct,
            "milestones": milestones,
            "achieved_milestones": achieved,
            "total_milestones": total_ms,
            "upcoming_milestones": upcoming_milestones,
            # DSR
            "dsrs": dsrs,
            "dsr_count": dsrs.count(),
            # Photos
            "photos": recent_photos,
            # Safety
            "incident_count": incidents_this_month.count(),
            "lti_count": lti_count,
            "near_miss_count": near_miss_count,
            "tb_count": tb_count,
            # Open items
            "open_rfis": open_rfis,
            "open_ncrs": open_ncrs,
        })
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get("format") == "pdf":
            from django.http import HttpResponse
            try:
                from weasyprint import HTML
                from django.template.loader import render_to_string
                html_string = render_to_string(
                    self.template_name, context, request=self.request
                )
                html = HTML(string=html_string, base_url=self.request.build_absolute_uri("/"))
                pdf_bytes = html.write_pdf()
                project = context["project"]
                period = context["period_label"].replace(" ", "_")
                response = HttpResponse(pdf_bytes, content_type="application/pdf")
                response["Content-Disposition"] = (
                    f'inline; filename="MPR_{project.project_id}_{period}.pdf"'
                )
                return response
            except ImportError:
                from django.contrib import messages
                messages.error(self.request, "PDF generation requires WeasyPrint.")
        return super().render_to_response(context, **response_kwargs)


# ---------------------------------------------------------------------------
# Portfolio Report (MD-level PDF)
# ---------------------------------------------------------------------------


class PortfolioReportView(LoginRequiredMixin, TemplateView):
    """Generate a portfolio summary PDF for the MD."""

    template_name = "reports/portfolio_report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()
        projects = Project.objects.filter(
            status__in=["ACTIVE", "MOBILISATION", "PRACTICAL_COMPLETION"]
        ).select_related("client", "project_manager")

        rows = []
        for project in projects:
            try:
                cv = project.contract_value
            except Exception:
                cv = 0

            budget = (
                CostCode.objects.filter(project=project)
                .aggregate(total=Sum("budget_amount"))["total"] or 0
            )
            spent = (
                CostEntry.objects.filter(project=project)
                .aggregate(total=Sum("amount"))["total"] or 0
            )
            pct = round(float(spent / budget * 100), 1) if budget else 0
            if pct > 100:
                rag = "RED"
            elif pct >= 80:
                rag = "AMBER"
            else:
                rag = "GREEN"

            rows.append({
                "project": project,
                "contract_value": cv,
                "budget": budget,
                "spent": spent,
                "remaining": budget - spent,
                "pct": pct,
                "rag": rag,
                "open_incidents": Incident.objects.filter(
                    project=project, status__in=["OPEN", "UNDER_INVESTIGATION"]
                ).count(),
            })

        ctx.update({
            "projects": rows,
            "total_projects": len(rows),
            "report_date": today,
        })
        return ctx

    def render_to_response(self, context, **response_kwargs):
        if self.request.GET.get("format") == "pdf":
            from django.http import HttpResponse
            try:
                from weasyprint import HTML
                from django.template.loader import render_to_string
                html_string = render_to_string(
                    self.template_name, context, request=self.request
                )
                html = HTML(string=html_string, base_url=self.request.build_absolute_uri("/"))
                pdf_bytes = html.write_pdf()
                response = HttpResponse(pdf_bytes, content_type="application/pdf")
                today = context["report_date"].strftime("%Y%m%d")
                response["Content-Disposition"] = f'inline; filename="Portfolio_{today}.pdf"'
                return response
            except ImportError:
                from django.contrib import messages
                messages.error(self.request, "PDF generation requires WeasyPrint.")
        return super().render_to_response(context, **response_kwargs)


# ---------------------------------------------------------------------------
# Reports Index
# ---------------------------------------------------------------------------


class ReportsIndexView(LoginRequiredMixin, TemplateView):
    """Landing page listing all available reports and exports."""
    template_name = "reports/index.html"


# ---------------------------------------------------------------------------
# Accounting Export (MYOB-compatible CSV)
# ---------------------------------------------------------------------------


class AccountingExportView(LoginRequiredMixin, View):
    """
    Export cost entries in a MYOB General Journal CSV format.

    Columns: Date, Account, Description, Debit, Credit, Reference, Tax Code
    """

    def get(self, request, project_pk):
        import csv
        from django.http import HttpResponse

        project = get_object_or_404(Project, pk=project_pk)
        entries = CostEntry.objects.filter(project=project).select_related(
            "cost_code"
        ).order_by("date")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="Accounting_{project.project_id}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow([
            "Date",
            "Account Code",
            "Account Description",
            "Description / Memo",
            "Debit",
            "Credit",
            "Reference",
            "Tax Code",
            "Entry Type",
            "Project",
        ])

        for entry in entries:
            amount = float(entry.amount or 0)
            debit = amount if entry.entry_type == "ACTUAL" else 0
            credit = amount if entry.entry_type == "COMMITTED" else 0
            writer.writerow([
                entry.date.strftime("%d/%m/%Y"),
                entry.cost_code.code if entry.cost_code else "",
                entry.cost_code.description if entry.cost_code else "",
                entry.description or "",
                f"{debit:.2f}" if debit else "",
                f"{credit:.2f}" if credit else "",
                entry.reference or "",
                "G10",  # GST standard-rated (PNG IRC)
                entry.get_entry_type_display(),
                project.project_id,
            ])

        from apps.core.models import AuditLog
        AuditLog.log(
            user=request.user,
            action=AuditLog.ACTION_EXPORT,
            model_name="CostEntry",
            object_repr=f"{project.project_id} accounting export",
            request=request,
        )
        return response
