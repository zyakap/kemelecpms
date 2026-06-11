"""
Idempotent demo-data seeder for Kemele CPMS.

Creates one record (or a small set) for every list/detail view in the
system: users for each role, a project with its full commercial,
schedule, resource, procurement, site-reporting, safety, quality,
maintenance, payment, document, compliance and tender data chain.

Run:    python manage.py seed_demo_data
Re-running is safe: every object is looked up via get_or_create keyed
on natural identifiers.
"""

import datetime
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User, UserProfile
from apps.budget.models import (
    BoQItem,
    CostCode,
    CostEntry,
    Subcontract,
    SubcontractBackCharge,
    SubcontractClaim,
    SubcontractPerformanceReview,
    SubcontractorDocument,
)
from apps.compliance.models import (
    AuthorityPermit,
    ComplianceCalendarEntry,
    ComplianceCalendarTemplate,
    FunderReportPack,
    IRCTaxInvoice,
    LocalContentRecord,
    OTMLTCSReport,
    PublicProcurementRecord,
)
from apps.documents.models import (
    Correspondence,
    DistributionContact,
    DocumentTransmittal,
    Drawing,
    DrawingRevision,
    ProjectDocument,
    RFI,
    Submittal,
)
from apps.dsr.models import (
    DailySiteReport,
    DSRActivity,
    DSREquipment,
    DSRIssue,
    DSRLabour,
    DSRMaterialDelivery,
    DSRMaterialUsage,
    DSRPhoto,
    DSRVisitor,
)
from apps.ipc.models import IPC, Certification, IPCLineItem, Payment, RetentionRelease
from apps.maintenance.models import (
    Asset,
    BreakdownTicket,
    PreventiveMaintenanceSchedule,
    ServiceRecord,
    SparePart,
    SparePartUsage,
    WorkOrder,
)
from apps.notifications.models import Notification, Task
from apps.procurement.models import (
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
from apps.projects.models import (
    Client,
    Contract,
    DelayEvent,
    Funder,
    Milestone,
    Project,
    ProjectMembership,
    Variation,
    WorkPackage,
    WorkPackageProgress,
)
from apps.quality.models import (
    Defect,
    InspectionChecklist,
    InspectionChecklistItem,
    InspectionRecord,
    ITP,
    ITPItem,
    MaterialTestResult,
    NCR,
)
from apps.resources.models import (
    AttendanceRecord,
    Crew,
    CrewMember,
    Equipment,
    EquipmentAllocation,
    EquipmentUtilisation,
    SubcontractorCompany,
    Worker,
)
from apps.safety.models import (
    HazardRisk,
    Incident,
    PermitToWork,
    PPEIssue,
    SafetyCorrectiveAction,
    SafetyInduction,
    SafetyObservation,
    SafetyTrainingRecord,
    SWMS,
    ToolboxAttendee,
    ToolboxTalk,
)
from apps.schedule.models import (
    Activity,
    LookAhead,
    LookAheadTask,
    Programme,
    ProgrammeRevision,
    ProgressEntry,
    WBSActivity,
)
from apps.tender.models import (
    BidEstimate,
    BidEstimateItem,
    CostRate,
    LessonsLearned,
    TenderArchive,
    TenderDocument,
)

# 1x1 transparent PNG (valid image bytes for ImageFields)
PNG_1PX = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfa\xcf"
    b"\xf0\xbf\x1e\x00\x06\x83\x02\x7f\x94\xad\xd0\xeb\x00\x00\x00\x00IEND"
    b"\xaeB`\x82"
)
PDF_BYTES = b"%PDF-1.4 placeholder demo document for Kemele CPMS seed data\n%%EOF"

DEMO_PASSWORD = "demo1234"


def png_file(name="placeholder.png"):
    return ContentFile(PNG_1PX, name=name)


def pdf_file(name="placeholder.pdf"):
    return ContentFile(PDF_BYTES, name=name)


class Command(BaseCommand):
    help = "Idempotently seed a realistic demo dataset across every module."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = {}  # model verbose name -> count created this run

    def track(self, obj, was_created):
        if was_created:
            label = obj.__class__.__name__
            self.created[label] = self.created.get(label, 0) + 1
        return obj

    @transaction.atomic
    def handle(self, *args, **options):
        today = timezone.now().date()
        users = self.seed_users()
        client, funder = self.seed_client_funder()
        project = self.seed_project(users, client, funder, today)
        self.seed_memberships(project, users)
        self.seed_contract_and_milestones(project, users, today)
        cost_codes, boq_items = self.seed_budget(project, users, today)
        subcontract = self.seed_subcontract(project, users, today)
        work_packages = self.seed_work_packages(project, users, subcontract, today)
        programme, activities = self.seed_schedule(project, users, cost_codes, today)
        workers, crew, equipment = self.seed_resources(project, users, today)
        supplier, materials, grn = self.seed_procurement(project, users, today)
        dsr = self.seed_dsr(
            project, users, work_packages, activities, crew, equipment,
            materials, grn, today,
        )
        incident = self.seed_safety(project, users, workers, today)
        ncr, defect = self.seed_quality(project, users, today)
        self.seed_maintenance(project, users, materials, today)
        ipc = self.seed_ipc(project, users, boq_items, today)
        self.seed_documents(project, users, today)
        self.seed_compliance(project, users, ipc, client, today)
        self.seed_tender(project, users, today)
        self.seed_notifications(project, users, today)

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Seed summary (objects created this run):"))
        if not self.created:
            self.stdout.write("  Nothing new created — dataset already seeded (idempotent re-run).")
        else:
            for label in sorted(self.created):
                self.stdout.write(f"  {label}: {self.created[label]}")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            "Demo data seeded. All demo users have password "
            f"'{DEMO_PASSWORD}' (e.g. pm@demo.kemele.com.pg)."
        ))

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def seed_users(self):
        spec = {
            User.ROLE_MD: ("md", "Mathew", "Dorum"),
            User.ROLE_PM: ("pm", "Peter", "Maip"),
            User.ROLE_SUPERVISOR: ("supervisor", "Simon", "Kawage"),
            User.ROLE_PROCUREMENT: ("procurement", "Pauline", "Oala"),
            User.ROLE_FINANCE: ("finance", "Freda", "Natera"),
            User.ROLE_DOC_CTRL: ("doccontrol", "Daniel", "Kops"),
            User.ROLE_AUDITOR: ("auditor", "Agnes", "Tamate"),
            User.ROLE_ADMIN: ("admin", "Sysadmin", "Kemele"),
            User.ROLE_SUBCONTRACTOR: ("subcontractor", "Steven", "Wamp"),
        }
        users = {}
        for role, (alias, first, last) in spec.items():
            email = f"{alias}@demo.kemele.com.pg"
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "first_name": first,
                    "last_name": last,
                    "role": role,
                    "phone": "+675 7000 0000",
                    "department": "Demo",
                    "is_staff": role == User.ROLE_ADMIN,
                    "is_superuser": role == User.ROLE_ADMIN,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save(update_fields=["password"])
            self.track(user, created)
            profile, p_created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "position": dict(User.ROLE_CHOICES)[role],
                    "po_approval_threshold": Decimal("100000.00"),
                    "financial_approval_threshold": Decimal("500000.00"),
                },
            )
            self.track(profile, p_created)
            users[role] = user
        return users

    # ------------------------------------------------------------------
    # Client / Funder / Project
    # ------------------------------------------------------------------

    def seed_client_funder(self):
        client, created = Client.objects.get_or_create(
            name="Western Province Provincial Health Authority",
            defaults={
                "client_type": Client.TYPE_GOVERNMENT,
                "contact_person": "Dr. Ila Geno",
                "email": "projects@wpphealth.gov.pg",
                "phone": "+675 645 9000",
                "address": "Kiunga, Western Province, Papua New Guinea",
            },
        )
        self.track(client, created)
        funder, created = Funder.objects.get_or_create(
            name="OTML Tax Credit Scheme",
            defaults={
                "funder_type": Funder.TYPE_OTML_TCS,
                "contact_person": "Grace Sailas",
                "email": "tcs@otml.com.pg",
                "phone": "+675 649 9111",
            },
        )
        self.track(funder, created)
        return client, funder

    def seed_project(self, users, client, funder, today):
        start = today - datetime.timedelta(days=120)
        project, created = Project.objects.get_or_create(
            name="Kiunga Rural Health Centre Upgrade",
            defaults={
                "description": (
                    "Construction of a new 30-bed rural health centre including "
                    "staff duplexes, water supply, and standalone solar power."
                ),
                "project_type": Project.TYPE_MIXED,
                "status": Project.STATUS_ACTIVE,
                "province": "Western Province",
                "district": "North Fly",
                "site_address": "Lot 12, Kiunga Station Road, Kiunga",
                "gps_lat": Decimal("-6.121944"),
                "gps_lng": Decimal("141.291944"),
                "project_manager": users[User.ROLE_PM],
                "site_supervisor": users[User.ROLE_SUPERVISOR],
                "client": client,
                "funder": funder,
                "start_date": start,
                "target_completion_date": start + datetime.timedelta(days=365),
            },
        )
        self.track(project, created)
        if created and not project.thumbnail:
            project.thumbnail.save("demo_thumbnail.png", png_file(), save=True)
        return project

    def seed_memberships(self, project, users):
        role_map = {
            User.ROLE_PM: (ProjectMembership.ROLE_PM, True, True),
            User.ROLE_SUPERVISOR: (ProjectMembership.ROLE_SUPERVISOR, True, False),
            User.ROLE_PROCUREMENT: (ProjectMembership.ROLE_PROCUREMENT, True, False),
            User.ROLE_FINANCE: (ProjectMembership.ROLE_FINANCE, True, True),
            User.ROLE_DOC_CTRL: (ProjectMembership.ROLE_DOC_CTRL, True, False),
            User.ROLE_AUDITOR: (ProjectMembership.ROLE_AUDITOR, False, False),
            User.ROLE_MD: (ProjectMembership.ROLE_VIEWER, True, True),
        }
        for user_role, (pm_role, can_edit, can_approve) in role_map.items():
            membership, created = ProjectMembership.objects.get_or_create(
                project=project,
                user=users[user_role],
                defaults={
                    "role": pm_role,
                    "can_edit": can_edit,
                    "can_approve": can_approve,
                },
            )
            self.track(membership, created)

    def seed_contract_and_milestones(self, project, users, today):
        contract, created = Contract.objects.get_or_create(
            project=project,
            defaults={
                "contract_number": "WPPHA-2026-014",
                "contract_type": Contract.TYPE_LUMP_SUM,
                "original_value": Decimal("18500000.00"),
                "start_date": project.start_date,
                "original_completion_date": project.target_completion_date,
                "liquidated_damages_rate": Decimal("5000.00"),
                "dlp_months": 12,
                "retention_percentage": Decimal("5.00"),
                "retention_cap_percentage": Decimal("10.00"),
                "payment_terms_days": 30,
            },
        )
        self.track(contract, created)
        if created and not contract.letter_of_award:
            contract.letter_of_award.save("letter_of_award.pdf", pdf_file(), save=True)

        variation, created = Variation.objects.get_or_create(
            project=project,
            description="Additional retaining wall to eastern boundary following geotech survey.",
            defaults={
                "date_instructed": today - datetime.timedelta(days=40),
                "status": Variation.STATUS_APPROVED,
                "variation_type": Variation.TYPE_ADD,
                "amount": Decimal("245000.00"),
            },
        )
        self.track(variation, created)

        milestones = [
            ("Site Mobilisation Complete", Milestone.TYPE_CONTRACTUAL, -90, True),
            ("Substructure Complete", Milestone.TYPE_CONTRACTUAL, -10, True),
            ("Roof Structure Complete", Milestone.TYPE_INTERNAL, 60, False),
            ("Practical Completion", Milestone.TYPE_FUNDER, 245, False),
        ]
        for name, mtype, offset, achieved in milestones:
            target = today + datetime.timedelta(days=offset)
            milestone, created = Milestone.objects.get_or_create(
                project=project,
                name=name,
                defaults={
                    "milestone_type": mtype,
                    "target_date": target,
                    "actual_date": target if achieved else None,
                    "is_achieved": achieved,
                    "description": f"Demo milestone: {name}.",
                },
            )
            self.track(milestone, created)

        delay, created = DelayEvent.objects.get_or_create(
            project=project,
            date=today - datetime.timedelta(days=30),
            delay_type=DelayEvent.DELAY_WEATHER,
            defaults={
                "description": "Five days of continuous heavy rainfall flooded the excavations.",
                "responsible_party": DelayEvent.PARTY_FORCE_MAJEURE,
                "impact_days": 5,
                "linked_milestone": Milestone.objects.filter(
                    project=project, name="Roof Structure Complete"
                ).first(),
            },
        )
        self.track(delay, created)

    # ------------------------------------------------------------------
    # Budget / BoQ
    # ------------------------------------------------------------------

    def seed_budget(self, project, users, today):
        cost_code_spec = [
            ("01.PRELIMS", "Preliminaries & General", CostCode.CATEGORY_PRELIMINARIES, "1850000.00"),
            ("02.CIVIL.EARTHWORKS", "Bulk Earthworks & Drainage", CostCode.CATEGORY_CIVIL, "2400000.00"),
            ("03.STRUCT.CONCRETE", "Structural Concrete Works", CostCode.CATEGORY_STRUCTURAL, "5200000.00"),
            ("04.ELEC.SOLAR", "Electrical & Solar Installation", CostCode.CATEGORY_ELECTRICAL, "3100000.00"),
            ("09.CONTINGENCY", "Project Contingency", CostCode.CATEGORY_CONTINGENCY, "925000.00"),
        ]
        cost_codes = {}
        for code, name, category, amount in cost_code_spec:
            cost_code, created = CostCode.objects.get_or_create(
                project=project,
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                    "budget_amount": Decimal(amount),
                    "forecast_etc": Decimal(amount) * Decimal("0.6"),
                    "is_contingency": category == CostCode.CATEGORY_CONTINGENCY,
                },
            )
            self.track(cost_code, created)
            cost_codes[code] = cost_code

        boq_spec = [
            ("1.1.1", "Excavate foundations to formation level", "m3", "1850.0000", "85.5000",
             "02.CIVIL.EARTHWORKS", CostCode.CATEGORY_CIVIL),
            ("2.1.1", "Supply and place 25 MPa concrete to footings", "m3", "420.0000", "1450.0000",
             "03.STRUCT.CONCRETE", CostCode.CATEGORY_STRUCTURAL),
            ("3.1.1", "Install 40kW rooftop solar array complete", "lump", "1.0000", "780000.0000",
             "04.ELEC.SOLAR", CostCode.CATEGORY_ELECTRICAL),
        ]
        boq_items = {}
        for number, desc, unit, qty, rate, cc_code, trade in boq_spec:
            boq_item, created = BoQItem.objects.get_or_create(
                project=project,
                item_number=number,
                defaults={
                    "cost_code": cost_codes[cc_code],
                    "description": desc,
                    "unit": unit,
                    "quantity": Decimal(qty),
                    "unit_rate": Decimal(rate),
                    "trade_section": trade,
                },
            )
            self.track(boq_item, created)
            boq_items[number] = boq_item

        entry, created = CostEntry.objects.get_or_create(
            project=project,
            cost_code=cost_codes["02.CIVIL.EARTHWORKS"],
            reference="PO-DEMO-EARTH-01",
            defaults={
                "boq_item": boq_items["1.1.1"],
                "entry_type": CostEntry.TYPE_ACTUAL,
                "description": "Plant hire and fuel for bulk earthworks (month 2)",
                "supplier": "Fly River Plant Hire Ltd",
                "amount": Decimal("385000.00"),
                "date": today - datetime.timedelta(days=45),
                "approved_by": users[User.ROLE_FINANCE],
            },
        )
        self.track(entry, created)
        entry2, created = CostEntry.objects.get_or_create(
            project=project,
            cost_code=cost_codes["03.STRUCT.CONCRETE"],
            reference="PO-DEMO-CONC-01",
            defaults={
                "entry_type": CostEntry.TYPE_COMMITTED,
                "description": "Committed PO for ready-mix concrete supply",
                "supplier": "Kiunga Concrete Supplies",
                "amount": Decimal("610000.00"),
                "date": today - datetime.timedelta(days=20),
                "approved_by": users[User.ROLE_FINANCE],
            },
        )
        self.track(entry2, created)
        return cost_codes, boq_items

    # ------------------------------------------------------------------
    # Subcontract
    # ------------------------------------------------------------------

    def seed_subcontract(self, project, users, today):
        subcontract, created = Subcontract.objects.get_or_create(
            project=project,
            company_name="Wamp Electrical Contractors Ltd",
            defaults={
                "user": users[User.ROLE_SUBCONTRACTOR],
                "trade": "Electrical & Solar",
                "scope": "Complete electrical reticulation, solar array and standby generator installation.",
                "contract_value": Decimal("2950000.00"),
                "start_date": today - datetime.timedelta(days=60),
                "end_date": today + datetime.timedelta(days=200),
                "retention_held": Decimal("29500.00"),
                "status": Subcontract.STATUS_ACTIVE,
            },
        )
        self.track(subcontract, created)

        claim, created = SubcontractClaim.objects.get_or_create(
            subcontract=subcontract,
            period_from=today - datetime.timedelta(days=60),
            period_to=today - datetime.timedelta(days=30),
            defaults={
                "submitted_date": today - datetime.timedelta(days=28),
                "claimed_amount": Decimal("310000.00"),
                "assessed_amount": Decimal("295000.00"),
                "approved_amount": Decimal("295000.00"),
                "retention_deducted": Decimal("14750.00"),
                "status": SubcontractClaim.STATUS_APPROVED,
                "notes": "First progress claim — conduit rough-in and switchboards.",
            },
        )
        self.track(claim, created)

        backcharge, created = SubcontractBackCharge.objects.get_or_create(
            subcontract=subcontract,
            date=today - datetime.timedelta(days=25),
            defaults={
                "description": "Make good damaged blockwork during conduit chasing.",
                "amount": Decimal("4800.00"),
                "status": SubcontractBackCharge.STATUS_APPROVED,
            },
        )
        self.track(backcharge, created)

        review, created = SubcontractPerformanceReview.objects.get_or_create(
            subcontract=subcontract,
            review_date=today - datetime.timedelta(days=15),
            defaults={
                "reviewer": users[User.ROLE_PM],
                "quality_score": 4,
                "schedule_score": 3,
                "safety_score": 4,
                "commercial_score": 4,
                "notes": "Good quality work; programme slipping slightly on switchboard delivery.",
            },
        )
        self.track(review, created)

        doc, created = SubcontractorDocument.objects.get_or_create(
            subcontract=subcontract,
            title="Electrical Installation Method Statement",
            defaults={
                "doc_type": SubcontractorDocument.TYPE_METHOD_STATEMENT,
                "revision": "B",
                "description": "Method statement for electrical rough-in and solar installation.",
                "file": pdf_file("method_statement.pdf"),
                "status": SubcontractorDocument.STATUS_APPROVED,
                "submitted_by": users[User.ROLE_SUBCONTRACTOR],
                "reviewed_by": users[User.ROLE_PM],
                "review_notes": "Approved for construction.",
                "reviewed_at": timezone.now(),
            },
        )
        self.track(doc, created)
        return subcontract

    # ------------------------------------------------------------------
    # Work Packages
    # ------------------------------------------------------------------

    def seed_work_packages(self, project, users, subcontract, today):
        packages = {}
        wp_main, created = WorkPackage.objects.get_or_create(
            project=project,
            name="Main Building & Civil Works (Kemele)",
            defaults={
                "contractor_type": WorkPackage.CONTRACTOR_PRINCIPAL,
                "description": "Health centre main building, earthworks and external works.",
                "scope_quantity": Decimal("1.00"),
                "scope_unit": "building",
                "contract_value": Decimal("15550000.00"),
                "start_date": project.start_date,
                "end_date": project.target_completion_date,
            },
        )
        self.track(wp_main, created)
        packages["principal"] = wp_main

        wp_sub, created = WorkPackage.objects.get_or_create(
            project=project,
            name="Electrical & Solar Package (Wamp Electrical)",
            defaults={
                "contractor_type": WorkPackage.CONTRACTOR_SUBCONTRACTOR,
                "subcontract": subcontract,
                "description": "Electrical reticulation and 40kW solar installation.",
                "scope_quantity": Decimal("1.00"),
                "scope_unit": "package",
                "contract_value": Decimal("2950000.00"),
                "start_date": today - datetime.timedelta(days=60),
                "end_date": today + datetime.timedelta(days=200),
            },
        )
        self.track(wp_sub, created)
        packages["subcontract"] = wp_sub

        progress, created = WorkPackageProgress.objects.get_or_create(
            work_package=wp_main,
            date=today - datetime.timedelta(days=7),
            defaults={
                "percent_complete": Decimal("32.50"),
                "narrative": "Substructure complete; blockwork to window head level.",
                "recorded_by": users[User.ROLE_SUPERVISOR],
            },
        )
        self.track(progress, created)
        return packages

    # ------------------------------------------------------------------
    # Schedule (WBS, Programme, Activities)
    # ------------------------------------------------------------------

    def seed_schedule(self, project, users, cost_codes, today):
        phase, created = WBSActivity.objects.get_or_create(
            project=project,
            wbs_code="1",
            defaults={
                "name": "Construction Phase",
                "level": WBSActivity.LEVEL_PHASE,
                "responsible": users[User.ROLE_PM],
            },
        )
        self.track(phase, created)
        wp_node, created = WBSActivity.objects.get_or_create(
            project=project,
            wbs_code="1.1",
            defaults={
                "name": "Substructure",
                "parent": phase,
                "level": WBSActivity.LEVEL_WORK_PACKAGE,
                "cost_code": cost_codes["03.STRUCT.CONCRETE"],
            },
        )
        self.track(wp_node, created)
        activity_node, created = WBSActivity.objects.get_or_create(
            project=project,
            wbs_code="1.1.1",
            defaults={
                "name": "Footings & Ground Beams",
                "parent": wp_node,
                "level": WBSActivity.LEVEL_ACTIVITY,
                "cost_code": cost_codes["03.STRUCT.CONCRETE"],
                "responsible": users[User.ROLE_SUPERVISOR],
            },
        )
        self.track(activity_node, created)

        programme, created = Programme.objects.get_or_create(
            project=project,
            defaults={
                "baseline_start": project.start_date,
                "baseline_end": project.target_completion_date,
                "current_start": project.start_date,
                "current_end": project.target_completion_date,
                "version": 1,
                "is_baseline": True,
                "notes": "Approved baseline programme rev 0.",
            },
        )
        self.track(programme, created)

        act1, created = Activity.objects.get_or_create(
            programme=programme,
            name="Bulk Earthworks",
            defaults={
                "wbs_activity": activity_node,
                "description": "Cut to fill, detailed excavation and drainage.",
                "start_date": project.start_date,
                "end_date": project.start_date + datetime.timedelta(days=45),
                "planned_percent": Decimal("100.00"),
                "actual_percent": Decimal("100.00"),
                "responsible": users[User.ROLE_SUPERVISOR],
            },
        )
        self.track(act1, created)
        act2, created = Activity.objects.get_or_create(
            programme=programme,
            name="Substructure Concrete",
            defaults={
                "wbs_activity": activity_node,
                "description": "Footings, ground beams and slab on grade.",
                "start_date": project.start_date + datetime.timedelta(days=45),
                "end_date": project.start_date + datetime.timedelta(days=110),
                "planned_percent": Decimal("80.00"),
                "actual_percent": Decimal("70.00"),
                "predecessor": act1,
                "dependency_type": Activity.DEP_FS,
                "is_critical": True,
                "responsible": users[User.ROLE_SUPERVISOR],
            },
        )
        self.track(act2, created)

        prog_entry, created = ProgressEntry.objects.get_or_create(
            activity=act2,
            date=today - datetime.timedelta(days=7),
            defaults={
                "percent_complete": Decimal("70.00"),
                "recorded_by": users[User.ROLE_SUPERVISOR],
                "notes": "Ground beams poured; slab prep underway.",
            },
        )
        self.track(prog_entry, created)

        revision, created = ProgrammeRevision.objects.get_or_create(
            programme=programme,
            submitted_date=today - datetime.timedelta(days=20),
            defaults={
                "reason": "EOT claim for 5 days of exceptional rainfall in month 3.",
                "revised_start": programme.current_start,
                "revised_end": programme.current_end + datetime.timedelta(days=5),
                "eot_days": 5,
                "causation_summary": "Rainfall exceeded 1:10 year event; critical earthworks suspended.",
                "status": ProgrammeRevision.STATUS_SUBMITTED,
            },
        )
        self.track(revision, created)
        if created:
            delay = DelayEvent.objects.filter(project=project).first()
            if delay:
                revision.delay_events.add(delay)

        look_ahead, created = LookAhead.objects.get_or_create(
            project=project,
            period_start=today,
            defaults={
                "period_end": today + datetime.timedelta(days=14),
                "created_by": users[User.ROLE_PM],
                "notes": "Two-week look-ahead covering slab pours and blockwork.",
            },
        )
        self.track(look_ahead, created)
        la_task, created = LookAheadTask.objects.get_or_create(
            look_ahead=look_ahead,
            description="Pour ward block slab panels 3 and 4",
            defaults={
                "activity": act2,
                "assigned_to": users[User.ROLE_SUPERVISOR],
                "planned_start": today + datetime.timedelta(days=2),
                "planned_end": today + datetime.timedelta(days=5),
            },
        )
        self.track(la_task, created)
        return programme, {"earthworks": act1, "substructure": act2}

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------

    def seed_resources(self, project, users, today):
        worker_spec = [
            ("Joseph", "Kuman", "Carpenter", Worker.CLASSIFICATION_SKILLED),
            ("Maria", "Tone", "Labourer", Worker.CLASSIFICATION_UNSKILLED),
            ("Robert", "Aihi", "Plant Operator", Worker.CLASSIFICATION_SKILLED),
        ]
        workers = []
        for first, last, occupation, classification in worker_spec:
            worker, created = Worker.objects.get_or_create(
                first_name=first,
                last_name=last,
                defaults={
                    "occupation": occupation,
                    "trade": occupation,
                    "classification": classification,
                    "employment_type": Worker.EMPLOYMENT_DIRECT,
                    "phone": "+675 7100 0000",
                    "project": project,
                    "date_joined": today - datetime.timedelta(days=100),
                },
            )
            self.track(worker, created)
            workers.append(worker)

        crew, created = Crew.objects.get_or_create(
            project=project,
            name="Structures Crew A",
            defaults={"foreman": workers[0], "notes": "Primary concrete and blockwork crew."},
        )
        self.track(crew, created)
        for worker in workers:
            member, created = CrewMember.objects.get_or_create(
                crew=crew,
                worker=worker,
                defaults={"date_joined": today - datetime.timedelta(days=90)},
            )
            self.track(member, created)

        attendance, created = AttendanceRecord.objects.get_or_create(
            project=project,
            worker=workers[0],
            date=today - datetime.timedelta(days=1),
            defaults={
                "crew": crew,
                "time_in": datetime.time(7, 0),
                "time_out": datetime.time(17, 0),
                "overtime_hours": Decimal("1.50"),
                "is_present": True,
                "recorded_by": users[User.ROLE_SUPERVISOR],
            },
        )
        self.track(attendance, created)

        equipment, created = Equipment.objects.get_or_create(
            description="CAT 320 Hydraulic Excavator",
            defaults={
                "equipment_type": "Excavator",
                "ownership_type": Equipment.OWNERSHIP_HIRED,
                "supplier": "Fly River Plant Hire Ltd",
                "model": "CAT 320 GC",
                "year": 2022,
                "registration_number": "PNG-EX-3201",
            },
        )
        self.track(equipment, created)

        allocation, created = EquipmentAllocation.objects.get_or_create(
            equipment=equipment,
            project=project,
            allocated_date=today - datetime.timedelta(days=100),
            defaults={
                "hire_rate_daily": Decimal("2800.00"),
                "notes": "Wet hire including operator and fuel.",
            },
        )
        self.track(allocation, created)

        utilisation, created = EquipmentUtilisation.objects.get_or_create(
            allocation=allocation,
            date=today - datetime.timedelta(days=1),
            defaults={
                "hours_worked": Decimal("7.50"),
                "hours_idle": Decimal("1.00"),
                "hours_breakdown": Decimal("0.50"),
                "fuel_litres": Decimal("145.00"),
                "operator": workers[2],
            },
        )
        self.track(utilisation, created)

        sub_company, created = SubcontractorCompany.objects.get_or_create(
            company_name="Wamp Electrical Contractors Ltd",
            defaults={
                "trade": "Electrical & Solar",
                "contact_person": "Steven Wamp",
                "email": "subcontractor@demo.kemele.com.pg",
                "phone": "+675 7200 0000",
                "address": "Section 4, Lot 9, Mt Hagen, WHP",
                "irc_tin": "500123456",
                "is_prequalified": True,
                "performance_rating": Decimal("4.0"),
            },
        )
        self.track(sub_company, created)
        return workers, crew, equipment

    # ------------------------------------------------------------------
    # Procurement chain
    # ------------------------------------------------------------------

    def seed_procurement(self, project, users, today):
        supplier, created = Supplier.objects.get_or_create(
            name="Kiunga Hardware & Building Supplies",
            defaults={
                "address": "Main Wharf Road, Kiunga, Western Province",
                "irc_tin": "500654321",
                "bank_name": "BSP",
                "bank_account_name": "Kiunga Hardware Ltd",
                "bank_account_number": "1001234567",
                "contact_person": "Lina Karava",
                "email": "sales@kiungahardware.com.pg",
                "phone": "+675 649 1234",
                "categories": "HARDWARE,ELECTRICAL",
                "is_preferred": True,
                "performance_rating": Decimal("4.5"),
            },
        )
        self.track(supplier, created)

        category, created = MaterialCategory.objects.get_or_create(
            name="Cement & Concrete",
            defaults={"description": "Cementitious materials and admixtures."},
        )
        self.track(category, created)

        material_spec = [
            ("CEM-001", "Portland Cement 40kg bag", "bag", "200.000"),
            ("REO-Y12", "Deformed Rebar Y12 x 6m", "len", "150.000"),
        ]
        materials = []
        for code, desc, unit, min_stock in material_spec:
            material, created = Material.objects.get_or_create(
                item_code=code,
                defaults={
                    "description": desc,
                    "unit": unit,
                    "category": category,
                    "min_stock_level": Decimal(min_stock),
                },
            )
            self.track(material, created)
            materials.append(material)

        mr, created = MaterialRequisition.objects.get_or_create(
            project=project,
            date=today - datetime.timedelta(days=21),
            requested_by=users[User.ROLE_SUPERVISOR],
            defaults={
                "required_by_date": today - datetime.timedelta(days=7),
                "justification": "Cement and rebar for ward block slab pours.",
                "status": MaterialRequisition.STATUS_ORDERED,
                "approved_by": users[User.ROLE_PM],
                "approved_at": timezone.now(),
            },
        )
        self.track(mr, created)

        mr_item1, created = MRItem.objects.get_or_create(
            mr=mr,
            material=materials[0],
            defaults={
                "unit": "bag",
                "quantity_requested": Decimal("600.000"),
                "quantity_ordered": Decimal("600.000"),
            },
        )
        self.track(mr_item1, created)
        mr_item2, created = MRItem.objects.get_or_create(
            mr=mr,
            material=materials[1],
            defaults={
                "unit": "len",
                "quantity_requested": Decimal("400.000"),
                "quantity_ordered": Decimal("400.000"),
            },
        )
        self.track(mr_item2, created)

        po, created = PurchaseOrder.objects.get_or_create(
            project=project,
            supplier=supplier,
            date=today - datetime.timedelta(days=18),
            defaults={
                "mr": mr,
                "delivery_address": "Kiunga Health Centre site, Kiunga Station Road",
                "expected_delivery_date": today - datetime.timedelta(days=10),
                "status": PurchaseOrder.STATUS_DELIVERED,
                "approved_by": users[User.ROLE_PM],
                "approved_at": timezone.now(),
                "notes": "Urgent delivery required before slab pour.",
            },
        )
        self.track(po, created)

        po_item1, created = POItem.objects.get_or_create(
            po=po,
            description="Portland Cement 40kg bag",
            defaults={
                "mr_item": mr_item1,
                "material": materials[0],
                "unit": "bag",
                "quantity": Decimal("600.000"),
                "unit_price": Decimal("62.5000"),
            },
        )
        self.track(po_item1, created)
        po_item2, created = POItem.objects.get_or_create(
            po=po,
            description="Deformed Rebar Y12 x 6m",
            defaults={
                "mr_item": mr_item2,
                "material": materials[1],
                "unit": "len",
                "quantity": Decimal("400.000"),
                "unit_price": Decimal("48.0000"),
            },
        )
        self.track(po_item2, created)
        po.recalculate_total()

        grn, created = GoodsReceivedNote.objects.get_or_create(
            po=po,
            delivery_date=today - datetime.timedelta(days=10),
            defaults={
                "delivered_by": "Kiunga Hardware truck — driver J. Sine",
                "received_by": users[User.ROLE_SUPERVISOR],
                "condition_notes": "All goods received in good condition.",
                "is_partial": False,
            },
        )
        self.track(grn, created)
        if created and not grn.delivery_photo:
            grn.delivery_photo.save("delivery_photo.png", png_file(), save=True)

        for po_item, qty in ((po_item1, "600.000"), (po_item2, "400.000")):
            grn_item, created = GRNItem.objects.get_or_create(
                grn=grn,
                po_item=po_item,
                defaults={"quantity_delivered": Decimal(qty)},
            )
            self.track(grn_item, created)

        invoice, created = SupplierInvoice.objects.get_or_create(
            supplier=supplier,
            invoice_number="KH-INV-20260520",
            defaults={
                "po": po,
                "invoice_date": today - datetime.timedelta(days=8),
                "amount": Decimal("56700.00"),
                "document": pdf_file("supplier_invoice.pdf"),
                "status": SupplierInvoice.STATUS_APPROVED,
                "is_matched": True,
            },
        )
        self.track(invoice, created)

        ledger, created = StockLedger.objects.get_or_create(
            project=project,
            material=materials[0],
            date=today - datetime.timedelta(days=10),
            transaction_type=StockLedger.TYPE_RECEIPT,
            defaults={
                "quantity": Decimal("600.000"),
                "reference": grn.grn_number,
                "recorded_by": users[User.ROLE_SUPERVISOR],
            },
        )
        self.track(ledger, created)
        issue, created = StockLedger.objects.get_or_create(
            project=project,
            material=materials[0],
            date=today - datetime.timedelta(days=5),
            transaction_type=StockLedger.TYPE_ISSUE,
            defaults={
                "quantity": Decimal("180.000"),
                "reference": "Slab pour panels 1-2",
                "recorded_by": users[User.ROLE_SUPERVISOR],
            },
        )
        self.track(issue, created)
        return supplier, materials, grn

    # ------------------------------------------------------------------
    # DSR
    # ------------------------------------------------------------------

    def seed_dsr(self, project, users, work_packages, activities, crew,
                 equipment, materials, grn, today):
        dsr, created = DailySiteReport.objects.get_or_create(
            project=project,
            date=today - datetime.timedelta(days=1),
            defaults={
                "work_package": work_packages["principal"],
                "weather_am": "SUNNY",
                "weather_pm": "LIGHT_RAIN",
                "prepared_by": users[User.ROLE_SUPERVISOR],
                "status": DailySiteReport.STATUS_APPROVED,
                "approved_by": users[User.ROLE_PM],
                "approved_at": timezone.now(),
                "is_locked": True,
                "notes": "Productive day; light rain after 3pm did not stop works.",
            },
        )
        self.track(dsr, created)

        dsr_activity, created = DSRActivity.objects.get_or_create(
            dsr=dsr,
            description="Ground beam reinforcement fixing — ward block grid A-D",
            defaults={
                "schedule_activity": activities["substructure"],
                "location_on_site": "Ward Block",
                "status": DSRActivity.STATUS_IN_PROGRESS,
                "quantity_achieved": Decimal("42.000"),
                "unit": "m",
                "percent_complete": Decimal("70.00"),
                "crew": crew,
            },
        )
        self.track(dsr_activity, created)

        labour, created = DSRLabour.objects.get_or_create(
            dsr=dsr,
            classification="Carpenter",
            nationality=DSRLabour.NATIONALITY_PNG,
            defaults={"count": 6},
        )
        self.track(labour, created)
        labour2, created = DSRLabour.objects.get_or_create(
            dsr=dsr,
            classification="Labourer",
            nationality=DSRLabour.NATIONALITY_PNG,
            defaults={"count": 12},
        )
        self.track(labour2, created)

        visitor, created = DSRVisitor.objects.get_or_create(
            dsr=dsr,
            name="Dr. Ila Geno",
            defaults={
                "organization": "WPPHA",
                "purpose": "Client monthly site walk",
                "time_in": datetime.time(10, 0),
                "time_out": datetime.time(11, 30),
            },
        )
        self.track(visitor, created)

        dsr_equipment, created = DSREquipment.objects.get_or_create(
            dsr=dsr,
            equipment=equipment,
            defaults={
                "hours_worked": Decimal("7.50"),
                "hours_idle": Decimal("1.00"),
                "hours_breakdown": Decimal("0.50"),
                "notes": "Hydraulic hose replaced at smoko.",
            },
        )
        self.track(dsr_equipment, created)

        delivery, created = DSRMaterialDelivery.objects.get_or_create(
            dsr=dsr,
            description="Portland cement 40kg bags",
            defaults={"grn": grn, "quantity": Decimal("600.000"), "unit": "bag"},
        )
        self.track(delivery, created)

        usage, created = DSRMaterialUsage.objects.get_or_create(
            dsr=dsr,
            material=materials[0],
            defaults={
                "quantity_used": Decimal("85.000"),
                "notes": "Blinding and ground beam pours.",
            },
        )
        self.track(usage, created)

        if not DSRPhoto.objects.filter(dsr=dsr, caption="Ground beam reinforcement progress").exists():
            photo = DSRPhoto(
                dsr=dsr,
                caption="Ground beam reinforcement progress",
                tag=DSRPhoto.TAG_PROGRESS,
                schedule_activity=activities["substructure"],
            )
            photo.photo.save("dsr_progress.png", png_file(), save=True)
            self.track(photo, True)

        issue, created = DSRIssue.objects.get_or_create(
            dsr=dsr,
            issue_type=DSRIssue.ISSUE_MATERIAL_DELAY,
            description="Switchboard delivery delayed at Port Moresby wharf — awaiting customs clearance.",
            defaults={
                "raised_by": users[User.ROLE_SUPERVISOR],
                "date": today - datetime.timedelta(days=1),
                "action_required": "Procurement to expedite customs broker.",
            },
        )
        self.track(issue, created)
        return dsr

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------

    def seed_safety(self, project, users, workers, today):
        induction, created = SafetyInduction.objects.get_or_create(
            project=project,
            worker=workers[0],
            date=today - datetime.timedelta(days=95),
            defaults={
                "topics_covered": "Site rules, emergency procedures, PPE requirements, manual handling.",
                "inducted_by": users[User.ROLE_SUPERVISOR],
                "expiry_date": today + datetime.timedelta(days=270),
                "acknowledged": True,
            },
        )
        self.track(induction, created)

        toolbox, created = ToolboxTalk.objects.get_or_create(
            project=project,
            date=today - datetime.timedelta(days=2),
            topic="Working safely around mobile plant",
            defaults={
                "presenter": users[User.ROLE_SUPERVISOR],
                "notes": "Discussed exclusion zones and spotter duties for the excavator.",
            },
        )
        self.track(toolbox, created)
        for worker in workers:
            attendee, created = ToolboxAttendee.objects.get_or_create(
                toolbox=toolbox, worker=worker
            )
            self.track(attendee, created)

        incident, created = Incident.objects.get_or_create(
            project=project,
            date=today - datetime.timedelta(days=14),
            time=datetime.time(10, 45),
            defaults={
                "location": "Ward block — scaffold bay 3",
                "incident_type": Incident.TYPE_FIRST_AID,
                "description": "Worker sustained a minor laceration to the left hand while stripping formwork.",
                "persons_involved": "Joseph Kuman (Carpenter)",
                "body_part": "Left hand",
                "injury_nature": "Minor laceration",
                "treatment_given": "Wound cleaned and dressed on site by first aider.",
                "reported_by": users[User.ROLE_SUPERVISOR],
                "status": Incident.STATUS_CLOSED,
                "corrective_action": "Toolbox talk on formwork stripping; gloves mandatory for stripping work.",
                "corrective_action_due": today - datetime.timedelta(days=7),
                "corrective_action_closed": today - datetime.timedelta(days=7),
                "corrective_action_person": users[User.ROLE_SUPERVISOR],
            },
        )
        self.track(incident, created)

        hazard, created = HazardRisk.objects.get_or_create(
            project=project,
            activity="Deep excavation adjacent to existing clinic",
            defaults={
                "hazard_description": "Trench collapse and underground services strike.",
                "likelihood": 3,
                "consequence": 5,
                "control_measure": "Battered sides, daily inspection, service location scan before digging.",
                "control_type": HazardRisk.CONTROL_ENGINEERING,
                "reviewed_by": users[User.ROLE_PM],
                "reviewed_date": today - datetime.timedelta(days=30),
            },
        )
        self.track(hazard, created)

        swms, created = SWMS.objects.get_or_create(
            project=project,
            title="SWMS — Concrete Pumping Operations",
            defaults={
                "activity": "Concrete pumping and placement",
                "version": 2,
                "status": SWMS.STATUS_APPROVED,
                "document": pdf_file("swms_concrete_pumping.pdf"),
                "approved_by": users[User.ROLE_PM],
                "approved_date": today - datetime.timedelta(days=50),
            },
        )
        self.track(swms, created)

        ppe, created = PPEIssue.objects.get_or_create(
            project=project,
            worker=workers[1],
            ppe_type=PPEIssue.PPE_BOOTS,
            date_issued=today - datetime.timedelta(days=90),
            defaults={
                "size": "9",
                "quantity": 1,
                "issued_by": users[User.ROLE_SUPERVISOR],
            },
        )
        self.track(ppe, created)

        permit, created = PermitToWork.objects.get_or_create(
            project=project,
            permit_type=PermitToWork.TYPE_HOT_WORK,
            work_area="Workshop container — rebar cutting bench",
            defaults={
                "description": "Oxy-cutting and welding of reinforcement starter bars.",
                "valid_from": timezone.now() - datetime.timedelta(days=1),
                "valid_to": timezone.now() + datetime.timedelta(days=6),
                "requested_by": users[User.ROLE_SUPERVISOR],
                "approved_by": users[User.ROLE_PM],
                "approved_at": timezone.now() - datetime.timedelta(days=1),
                "status": PermitToWork.STATUS_APPROVED,
                "controls": "Fire extinguisher at hand, fire watch for 30 min after works, hot work screen.",
            },
        )
        self.track(permit, created)

        training, created = SafetyTrainingRecord.objects.get_or_create(
            project=project,
            worker=workers[2],
            course_name="Mobile Plant Operator Competency (Excavator)",
            defaults={
                "provider": "PNG National Training Council",
                "certificate_number": "NTC-EXC-04417",
                "completed_date": today - datetime.timedelta(days=200),
                "expiry_date": today + datetime.timedelta(days=530),
            },
        )
        self.track(training, created)

        observation, created = SafetyObservation.objects.get_or_create(
            project=project,
            date=today - datetime.timedelta(days=3),
            location="Site access road",
            defaults={
                "observation_type": SafetyObservation.TYPE_UNSAFE,
                "description": "Delivery truck reversing without a spotter near pedestrian walkway.",
                "observed_by": users[User.ROLE_PM],
                "immediate_action": "Truck stopped; spotter assigned; driver re-briefed on traffic plan.",
                "status": SafetyObservation.STATUS_OPEN,
            },
        )
        self.track(observation, created)

        corrective, created = SafetyCorrectiveAction.objects.get_or_create(
            project=project,
            description="Install fixed pedestrian barriers along the site access road walkway.",
            defaults={
                "observation": observation,
                "assigned_to": users[User.ROLE_SUPERVISOR],
                "due_date": today + datetime.timedelta(days=7),
                "status": SafetyCorrectiveAction.STATUS_IN_PROGRESS,
            },
        )
        self.track(corrective, created)
        return incident

    # ------------------------------------------------------------------
    # Quality
    # ------------------------------------------------------------------

    def seed_quality(self, project, users, today):
        itp, created = ITP.objects.get_or_create(
            project=project,
            title="Structural Concrete — Ward Block",
            defaults={
                "description": "Inspection and test plan for all structural concrete elements.",
                "trade_section": "Structural",
                "status": ITP.STATUS_IN_PROGRESS,
            },
        )
        self.track(itp, created)

        itp_item1, created = ITPItem.objects.get_or_create(
            itp=itp,
            sequence=1,
            defaults={
                "description": "Pre-pour inspection of reinforcement and formwork.",
                "inspection_type": ITPItem.INSPECTION_HOLD,
                "responsible_party": ITPItem.RESPONSIBLE_CONSULTANT,
                "acceptance_criteria": "Reinforcement per drawings S-201 Rev B; cover 40mm ±5mm.",
                "status": ITPItem.STATUS_PASSED,
                "hold_point_released_by": users[User.ROLE_PM],
                "hold_point_released_date": today - datetime.timedelta(days=12),
            },
        )
        self.track(itp_item1, created)
        itp_item2, created = ITPItem.objects.get_or_create(
            itp=itp,
            sequence=2,
            defaults={
                "description": "Concrete slump and cylinder sampling at point of placement.",
                "inspection_type": ITPItem.INSPECTION_WITNESS,
                "responsible_party": ITPItem.RESPONSIBLE_CONTRACTOR,
                "acceptance_criteria": "Slump 100mm ±25mm; one set of cylinders per 50m3.",
                "status": ITPItem.STATUS_PENDING,
            },
        )
        self.track(itp_item2, created)

        inspection, created = InspectionRecord.objects.get_or_create(
            itp_item=itp_item1,
            date=today - datetime.timedelta(days=12),
            defaults={
                "inspector_name": "G. Lawes",
                "inspector_org": "Pacific Consult Engineers",
                "location": "Ward block — grid A-D ground beams",
                "result": InspectionRecord.RESULT_PASS,
                "notes": "Reinforcement compliant. Released for pour.",
                "signed_off_by": users[User.ROLE_PM],
            },
        )
        self.track(inspection, created)

        checklist, created = InspectionChecklist.objects.get_or_create(
            itp=itp,
            title="Pre-pour checklist — ground beams GB1-GB6",
            defaults={
                "location": "Ward block",
                "inspection_date": today - datetime.timedelta(days=12),
                "inspected_by": users[User.ROLE_SUPERVISOR],
                "signed_off_by": users[User.ROLE_PM],
                "signed_off_date": today - datetime.timedelta(days=12),
            },
        )
        self.track(checklist, created)
        check_item, created = InspectionChecklistItem.objects.get_or_create(
            checklist=checklist,
            description="Formwork dimensions and alignment checked",
            defaults={
                "acceptance_criteria": "Within ±10mm of design dimensions",
                "passed": True,
                "comments": "Verified against drawing S-201 Rev B.",
            },
        )
        self.track(check_item, created)

        ncr, created = NCR.objects.get_or_create(
            project=project,
            description="Honeycombing identified on ground beam GB4 south face after formwork strip.",
            defaults={
                "location": "Ward block — ground beam GB4",
                "trade_responsible": "Concrete",
                "severity": NCR.SEVERITY_MAJOR,
                "raised_by": users[User.ROLE_PM],
                "raised_date": today - datetime.timedelta(days=9),
                "corrective_action_required": "Break out defective concrete and repair with approved structural mortar.",
                "responsible_person": users[User.ROLE_SUPERVISOR],
                "due_date": today + datetime.timedelta(days=5),
                "root_cause": "Insufficient vibration around congested reinforcement.",
                "status": NCR.STATUS_UNDER_REVIEW,
                "itp_item": itp_item1,
            },
        )
        self.track(ncr, created)

        test, created = MaterialTestResult.objects.get_or_create(
            project=project,
            sample_reference="CYL-026-A",
            defaults={
                "test_type": MaterialTestResult.TEST_CONCRETE,
                "test_date": today - datetime.timedelta(days=5),
                "location": "Ward block — ground beam pour 2",
                "specified_value": "25 MPa",
                "actual_value": "28.6 MPa",
                "passed": True,
            },
        )
        self.track(test, created)

        defect, created = Defect.objects.get_or_create(
            project=project,
            description="Hairline crack in blinding slab near grid C2.",
            defaults={
                "location": "Ward block — grid C2",
                "trade": "Concrete",
                "identified_date": today - datetime.timedelta(days=6),
                "severity": Defect.SEVERITY_MINOR,
                "phase": Defect.PHASE_CONSTRUCTION,
                "responsible_party": "Kemele Construction",
                "target_rectification_date": today + datetime.timedelta(days=10),
                "status": Defect.STATUS_IN_PROGRESS,
            },
        )
        self.track(defect, created)
        return ncr, defect

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def seed_maintenance(self, project, users, materials, today):
        asset, created = Asset.objects.get_or_create(
            project=project,
            asset_code="GEN-001",
            defaults={
                "name": "Standby Diesel Generator 150kVA",
                "category": Asset.CATEGORY_ELECTRICAL,
                "location": "Site compound — generator shed",
                "make_model": "Cummins C150D5",
                "serial_number": "CMN-150-88412",
                "installed_date": today - datetime.timedelta(days=100),
                "status": Asset.STATUS_ACTIVE,
                "criticality": Asset.CRITICALITY_HIGH,
                "service_interval_days": 30,
                "last_service_date": today - datetime.timedelta(days=20),
                "next_service_due": today + datetime.timedelta(days=10),
            },
        )
        self.track(asset, created)

        work_order, created = WorkOrder.objects.get_or_create(
            project=project,
            title="250-hour service — standby generator",
            defaults={
                "asset": asset,
                "work_type": WorkOrder.TYPE_PREVENTIVE,
                "priority": WorkOrder.PRIORITY_MEDIUM,
                "description": "Oil and filter change, coolant check, load bank test.",
                "requested_by": users[User.ROLE_SUPERVISOR],
                "assigned_to": users[User.ROLE_SUPERVISOR],
                "requested_date": today - datetime.timedelta(days=21),
                "due_date": today - datetime.timedelta(days=14),
                "status": WorkOrder.STATUS_COMPLETED,
                "completed_at": timezone.now() - datetime.timedelta(days=20),
                "completion_notes": "Service completed; generator load tested OK.",
                "labour_hours": Decimal("6.00"),
                "cost": Decimal("3850.00"),
                "parts_used": "Oil filter, fuel filter, 20L 15W-40 oil",
            },
        )
        self.track(work_order, created)

        pm_schedule, created = PreventiveMaintenanceSchedule.objects.get_or_create(
            asset=asset,
            title="Monthly generator service",
            defaults={
                "frequency": PreventiveMaintenanceSchedule.FREQUENCY_MONTHLY,
                "next_due_date": today + datetime.timedelta(days=10),
                "checklist": "Check oil, coolant, belts, batteries; run under load 30 min.",
            },
        )
        self.track(pm_schedule, created)

        service, created = ServiceRecord.objects.get_or_create(
            work_order=work_order,
            service_date=today - datetime.timedelta(days=20),
            defaults={
                "technician": "B. Kaupa (Ela Motors field tech)",
                "work_performed": "Completed 250-hour service per Cummins schedule.",
                "downtime_hours": Decimal("4.00"),
                "cost": Decimal("3850.00"),
            },
        )
        self.track(service, created)

        spare_usage, created = SparePartUsage.objects.get_or_create(
            service_record=service,
            description="Cummins oil filter LF9009",
            defaults={
                "quantity": Decimal("1.000"),
                "unit_cost": Decimal("220.00"),
            },
        )
        self.track(spare_usage, created)

        breakdown_wo, created = WorkOrder.objects.get_or_create(
            project=project,
            title="Generator failed to start — battery fault",
            defaults={
                "asset": asset,
                "work_type": WorkOrder.TYPE_BREAKDOWN,
                "priority": WorkOrder.PRIORITY_HIGH,
                "description": "Generator failed morning start check; suspected flat starting batteries.",
                "requested_by": users[User.ROLE_SUPERVISOR],
                "requested_date": today - datetime.timedelta(days=4),
                "due_date": today - datetime.timedelta(days=3),
                "sla_response_hours": 4,
                "status": WorkOrder.STATUS_IN_PROGRESS,
            },
        )
        self.track(breakdown_wo, created)

        ticket, created = BreakdownTicket.objects.get_or_create(
            asset=asset,
            work_order=breakdown_wo,
            defaults={
                "reported_at": timezone.now() - datetime.timedelta(days=4),
                "cause": "Starting batteries beyond service life.",
                "operational_impact": "No standby power for site offices during outage.",
                "status": BreakdownTicket.STATUS_OPEN,
            },
        )
        self.track(ticket, created)

        spare, created = SparePart.objects.get_or_create(
            project=project,
            part_number="LF9009",
            defaults={
                "asset": asset,
                "description": "Cummins spin-on oil filter",
                "quantity_on_hand": Decimal("3.00"),
                "minimum_quantity": Decimal("2.00"),
                "unit_cost": Decimal("220.00"),
            },
        )
        self.track(spare, created)

    # ------------------------------------------------------------------
    # IPC
    # ------------------------------------------------------------------

    def seed_ipc(self, project, users, boq_items, today):
        ipc, created = IPC.objects.get_or_create(
            project=project,
            claim_period_from=today - datetime.timedelta(days=60),
            claim_period_to=today - datetime.timedelta(days=30),
            defaults={
                "submitted_date": today - datetime.timedelta(days=28),
                "status": IPC.STATUS_SUBMITTED,
                "notes": "Interim payment claim no. 2 — substructure works.",
            },
        )
        self.track(ipc, created)

        line_spec = [
            ("1.1.1", "40.00", "35.00"),
            ("2.1.1", "10.00", "25.00"),
        ]
        for item_number, prev_pct, curr_pct in line_spec:
            boq_item = boq_items[item_number]
            line, created = IPCLineItem.objects.get_or_create(
                ipc=ipc,
                boq_item=boq_item,
                defaults={
                    "boq_description": boq_item.description,
                    "boq_quantity": boq_item.quantity,
                    "unit_rate": boq_item.unit_rate,
                    "previous_percent": Decimal(prev_pct),
                    "current_percent": Decimal(curr_pct),
                },
            )
            self.track(line, created)

        certification, created = Certification.objects.get_or_create(
            ipc=ipc,
            defaults={
                "certified_by": "G. Lawes",
                "certifier_org": "Pacific Consult Engineers",
                "certified_date": today - datetime.timedelta(days=14),
                "amount_certified": Decimal("207500.00"),
                "retention_deducted": Decimal("10375.00"),
                "net_certified": Decimal("197125.00"),
                "notes": "Certified less minor deduction for incomplete drainage.",
            },
        )
        self.track(certification, created)

        payment, created = Payment.objects.get_or_create(
            ipc=ipc,
            payment_reference="EFT-2026-0457",
            defaults={
                "payment_date": today - datetime.timedelta(days=5),
                "amount": Decimal("197125.00"),
                "received_by": users[User.ROLE_FINANCE],
                "notes": "Paid by WPPHA via BSP EFT.",
            },
        )
        self.track(payment, created)

        release, created = RetentionRelease.objects.get_or_create(
            project=project,
            release_type=RetentionRelease.RELEASE_PRACTICAL_COMPLETION,
            defaults={
                "amount": Decimal("0.00"),
                "release_date": today + datetime.timedelta(days=245),
                "approved_by": users[User.ROLE_MD],
            },
        )
        self.track(release, created)
        return ipc

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------

    def seed_documents(self, project, users, today):
        drawing, created = Drawing.objects.get_or_create(
            project=project,
            drawing_number="S-201",
            defaults={
                "title": "Ward Block — Footing & Ground Beam Layout",
                "discipline": Drawing.DISCIPLINE_STRUCTURAL,
                "scale": "1:100",
                "current_revision": "A",
                "current_revision_date": today - datetime.timedelta(days=80),
                "status": Drawing.STATUS_IFC,
                "file": pdf_file("S-201_revA.pdf"),
            },
        )
        self.track(drawing, created)

        revision, created = DrawingRevision.objects.get_or_create(
            drawing=drawing,
            revision="B",
            defaults={
                "date": today - datetime.timedelta(days=40),
                "uploaded_by": users[User.ROLE_DOC_CTRL],
                "file": pdf_file("S-201_revB.pdf"),
                "notes": "Revised ground beam GB4 reinforcement following RFI-0001 response.",
            },
        )
        self.track(revision, created)

        rfi, created = RFI.objects.get_or_create(
            project=project,
            subject="Clarification of ground beam GB4 reinforcement lap lengths",
            defaults={
                "date_raised": today - datetime.timedelta(days=50),
                "question": "Drawing S-201 Rev A shows conflicting lap lengths for GB4 (40d vs 50d). Please confirm.",
                "raised_by": users[User.ROLE_SUPERVISOR],
                "directed_to": "Pacific Consult Engineers",
                "drawing": drawing,
                "response": "Use 50d laps throughout. Drawing revised — see S-201 Rev B.",
                "response_date": today - datetime.timedelta(days=42),
                "status": RFI.STATUS_CLOSED,
                "schedule_impact_days": 0,
                "cost_impact": Decimal("0.00"),
            },
        )
        self.track(rfi, created)

        submittal, created = Submittal.objects.get_or_create(
            project=project,
            title="Ready-mix concrete mix design — 25 MPa",
            defaults={
                "submittal_type": Submittal.TYPE_MATERIAL,
                "submitted_by": users[User.ROLE_DOC_CTRL],
                "submitted_date": today - datetime.timedelta(days=70),
                "document": pdf_file("mix_design_25mpa.pdf"),
                "status": Submittal.STATUS_APPROVED,
                "review_notes": "Approved for structural works.",
                "reviewed_by": users[User.ROLE_PM],
                "reviewed_date": today - datetime.timedelta(days=63),
            },
        )
        self.track(submittal, created)

        correspondence, created = Correspondence.objects.get_or_create(
            project=project,
            subject="Notice of intention to claim EOT — exceptional rainfall",
            date=today - datetime.timedelta(days=25),
            defaults={
                "direction": Correspondence.DIRECTION_OUTGOING,
                "sender": "Kemele Construction Ltd",
                "recipient": "WPPHA — The Project Director",
                "summary": "Formal notice under clause 35.5 of intention to claim a 5-day extension of time.",
                "document": pdf_file("eot_notice.pdf"),
                "action_required": True,
                "action_due_date": today + datetime.timedelta(days=5),
            },
        )
        self.track(correspondence, created)

        project_doc, created = ProjectDocument.objects.get_or_create(
            project=project,
            title="Project Quality Management Plan",
            defaults={
                "document_type": "Management Plan",
                "file": pdf_file("quality_management_plan.pdf"),
                "description": "Project-specific QMP aligned to ISO 9001.",
                "uploaded_by": users[User.ROLE_DOC_CTRL],
                "version": "2.0",
            },
        )
        self.track(project_doc, created)

        contact, created = DistributionContact.objects.get_or_create(
            project=project,
            email="g.lawes@pacificconsult.com.pg",
            defaults={
                "name": "Gordon Lawes",
                "organization": "Pacific Consult Engineers",
                "role": "Superintendent's Representative",
            },
        )
        self.track(contact, created)

        transmittal, created = DocumentTransmittal.objects.get_or_create(
            project=project,
            subject="Issue of S-201 Rev B for construction",
            defaults={
                "sent_date": today - datetime.timedelta(days=40),
                "sent_by": users[User.ROLE_DOC_CTRL],
                "status": DocumentTransmittal.STATUS_ACKNOWLEDGED,
                "acknowledged_date": today - datetime.timedelta(days=38),
                "notes": "Hard copy also issued to site office.",
            },
        )
        self.track(transmittal, created)
        transmittal.recipients.add(contact)
        transmittal.drawings.add(drawing)
        transmittal.submittals.add(submittal)
        transmittal.documents.add(project_doc)

    # ------------------------------------------------------------------
    # Compliance
    # ------------------------------------------------------------------

    def seed_compliance(self, project, users, ipc, client, today):
        tcs, created = OTMLTCSReport.objects.get_or_create(
            project=project,
            period_from=today - datetime.timedelta(days=60),
            period_to=today - datetime.timedelta(days=30),
            defaults={
                "period_type": OTMLTCSReport.PERIOD_MONTHLY,
                "submission_date": today - datetime.timedelta(days=25),
                "status": OTMLTCSReport.STATUS_SUBMITTED,
                "total_tcs_budget": Decimal("18500000.00"),
                "expenditure_to_date": Decimal("4250000.00"),
                "expenditure_this_period": Decimal("995000.00"),
                "overall_progress_pct": Decimal("28.50"),
                "narrative": "Substructure works substantially complete; blockwork commenced.",
                "issues_risks": "Switchboard import delays; wet season impact on earthworks.",
                "local_labour_pct": Decimal("92.00"),
                "expat_labour_pct": Decimal("8.00"),
                "local_materials_pct": Decimal("61.00"),
                "submitted_by": users[User.ROLE_PM],
            },
        )
        self.track(tcs, created)

        invoice, created = IRCTaxInvoice.objects.get_or_create(
            project=project,
            ipc=ipc,
            defaults={
                "invoice_date": today - datetime.timedelta(days=14),
                "status": IRCTaxInvoice.STATUS_ISSUED,
                "kemele_tinpng": "500111222",
                "kemele_gst_number": "GST-500111222",
                "client_name": client.name,
                "client_address": client.address,
                "client_tinpng": "500999888",
                "subtotal": Decimal("197125.00"),
                "description": "Interim payment claim no. 2 — substructure works, Kiunga Rural Health Centre.",
            },
        )
        self.track(invoice, created)

        procurement_record, created = PublicProcurementRecord.objects.get_or_create(
            project=project,
            tender_number="NPC-WP-2025-117",
            defaults={
                "procurement_method": PublicProcurementRecord.METHOD_OPEN_TENDER,
                "procuring_entity": "National Procurement Commission",
                "approval_reference": "NPC Board Minute 2025/41",
                "evaluation_summary": "Kemele ranked first of six conforming bids on weighted criteria.",
                "status": PublicProcurementRecord.STATUS_AWARDED,
            },
        )
        self.track(procurement_record, created)

        local_content, created = LocalContentRecord.objects.get_or_create(
            project=project,
            period_from=today - datetime.timedelta(days=60),
            period_to=today - datetime.timedelta(days=30),
            defaults={
                "png_labour_count": 46,
                "expat_labour_count": 4,
                "local_supplier_spend": Decimal("610000.00"),
                "total_supplier_spend": Decimal("995000.00"),
                "local_subcontractor_spend": Decimal("295000.00"),
                "total_subcontractor_spend": Decimal("295000.00"),
                "png_material_spend": Decimal("420000.00"),
                "total_material_spend": Decimal("690000.00"),
            },
        )
        self.track(local_content, created)

        authority_permit, created = AuthorityPermit.objects.get_or_create(
            project=project,
            permit_type="Building Permit — Health Centre Main Building",
            defaults={
                "authority": AuthorityPermit.AUTHORITY_BUILDING_BOARD,
                "reference_number": "WP-BB-2026-031",
                "status": AuthorityPermit.STATUS_APPROVED,
                "submission_date": today - datetime.timedelta(days=150),
                "approval_date": today - datetime.timedelta(days=120),
                "responsible": users[User.ROLE_DOC_CTRL],
                "conditions": "Fire authority inspection required prior to occupancy.",
            },
        )
        self.track(authority_permit, created)

        pack, created = FunderReportPack.objects.get_or_create(
            project=project,
            period_from=today - datetime.timedelta(days=60),
            period_to=today - datetime.timedelta(days=30),
            defaults={
                "funder_type": Funder.TYPE_OTML_TCS,
                "pack_type": FunderReportPack.PACK_MONTHLY,
                "status": FunderReportPack.STATUS_SUBMITTED,
                "narrative": "Monthly funder pack: progress photos, TCS report and expenditure summary.",
                "submitted_date": today - datetime.timedelta(days=25),
            },
        )
        self.track(pack, created)

        template, created = ComplianceCalendarTemplate.objects.get_or_create(
            name="Monthly OTML TCS progress report",
            defaults={
                "category": ComplianceCalendarTemplate.CATEGORY_TCS,
                "frequency": ComplianceCalendarTemplate.FREQUENCY_MONTHLY,
                "default_reminder_days": 7,
                "description": "Submit monthly TCS progress and expenditure report to OTML.",
            },
        )
        self.track(template, created)

        entry, created = ComplianceCalendarEntry.objects.get_or_create(
            project=project,
            title="Submit monthly OTML TCS report (current month)",
            due_date=today + datetime.timedelta(days=10),
            defaults={
                "category": ComplianceCalendarEntry.CATEGORY_TCS,
                "description": "Compile and submit the TCS progress report for the current period.",
                "reminder_days": 7,
                "responsible": users[User.ROLE_PM],
                "status": ComplianceCalendarEntry.STATUS_PENDING,
            },
        )
        self.track(entry, created)

        gst_entry, created = ComplianceCalendarEntry.objects.get_or_create(
            project=None,
            title="Lodge monthly GST return with IRC",
            due_date=today + datetime.timedelta(days=20),
            defaults={
                "category": ComplianceCalendarEntry.CATEGORY_IRC,
                "description": "Company-wide GST return lodgement.",
                "reminder_days": 7,
                "responsible": users[User.ROLE_FINANCE],
                "status": ComplianceCalendarEntry.STATUS_PENDING,
            },
        )
        self.track(gst_entry, created)

    # ------------------------------------------------------------------
    # Tender / Bid Library
    # ------------------------------------------------------------------

    def seed_tender(self, project, users, today):
        archive, created = TenderArchive.objects.get_or_create(
            project=project,
            defaults={
                "archived_by": users[User.ROLE_MD],
                "original_contract_value": Decimal("18500000.00"),
                "final_contract_value": Decimal("18745000.00"),
                "total_cost": Decimal("16100000.00"),
                "margin_pct": Decimal("14.10"),
                "planned_duration_days": 365,
                "actual_duration_days": 370,
                "executive_summary": "Rural health centre delivered in a remote riverine location.",
                "key_scope": "30-bed health centre, staff housing, solar power, water supply.",
                "unique_challenges": "Barge logistics on the Fly River; wet season earthworks.",
                "searchable_tags": "HEALTH,REMOTE,SOLAR,WESTERN_PROVINCE",
            },
        )
        self.track(archive, created)

        rate, created = CostRate.objects.get_or_create(
            trade=CostRate.TRADE_STRUCTURAL,
            region=CostRate.REGION_SOUTHERN,
            year=2026,
            description="Supply and place 25 MPa structural concrete (remote site)",
            defaults={
                "source_project": project,
                "archive": archive,
                "unit": "m³",
                "unit_rate": Decimal("1450.00"),
                "notes": "Includes barge freight to Kiunga.",
                "is_verified": True,
            },
        )
        self.track(rate, created)
        rate2, created = CostRate.objects.get_or_create(
            trade=CostRate.TRADE_LABOUR,
            region=CostRate.REGION_SOUTHERN,
            year=2026,
            description="Skilled carpenter day rate (Western Province)",
            defaults={
                "source_project": project,
                "unit": "day",
                "unit_rate": Decimal("185.00"),
                "is_verified": True,
            },
        )
        self.track(rate2, created)

        estimate, created = BidEstimate.objects.get_or_create(
            tender_reference="RFT-WPG-2026-022",
            defaults={
                "title": "Tabubil Primary School Double Classroom Blocks",
                "client_name": "Western Province Division of Education",
                "funder": "OTML TCS",
                "location": "Tabubil, Western Province",
                "tender_due_date": today + datetime.timedelta(days=30),
                "status": BidEstimate.STATUS_DRAFT,
                "estimate_total": Decimal("5200000.00"),
                "bid_amount": Decimal("5980000.00"),
                "margin_pct": Decimal("15.00"),
                "notes": "Re-use Kiunga rates uplifted 4% for Tabubil logistics.",
            },
        )
        self.track(estimate, created)

        estimate_item, created = BidEstimateItem.objects.get_or_create(
            estimate=estimate,
            description="Supply and place 25 MPa structural concrete",
            defaults={
                "trade": CostRate.TRADE_STRUCTURAL,
                "unit": "m³",
                "quantity": Decimal("310.000"),
                "unit_rate": Decimal("1508.00"),
                "rate_source": rate,
            },
        )
        self.track(estimate_item, created)

        tender_doc, created = TenderDocument.objects.get_or_create(
            title="Kemele Construction Company Profile 2026",
            defaults={
                "doc_type": TenderDocument.DOC_TYPE_PROFILE,
                "description": "Capability statement covering building, civil and EPC works.",
                "document": pdf_file("company_profile_2026.pdf"),
                "version": "3.1",
                "tags": "PROFILE,CAPABILITY,ISO9001",
            },
        )
        self.track(tender_doc, created)

        lesson, created = LessonsLearned.objects.get_or_create(
            project=project,
            title="Order long-lead electrical equipment at contract award",
            defaults={
                "archive": archive,
                "category": LessonsLearned.CATEGORY_PROCUREMENT,
                "what_went_well": "Early cement procurement avoided wet-season barge delays.",
                "what_went_wrong": "Switchboards ordered 6 weeks after award caused programme pressure.",
                "recommendation": "Place POs for all imported long-lead items within 2 weeks of award.",
                "recorded_by": users[User.ROLE_PM],
            },
        )
        self.track(lesson, created)

    # ------------------------------------------------------------------
    # Notifications & Tasks
    # ------------------------------------------------------------------

    def seed_notifications(self, project, users, today):
        notif_spec = [
            (users[User.ROLE_PM], Notification.APPROVAL_REQUIRED,
             "DSR awaiting approval",
             "Daily Site Report for yesterday has been submitted and requires your approval."),
            (users[User.ROLE_FINANCE], Notification.PAYMENT,
             "IPC-0001 certified",
             "IPC for the substructure period has been certified — payment now due from client."),
            (users[User.ROLE_SUPERVISOR], Notification.OVERDUE,
             "NCR corrective action due soon",
             "NCR for ground beam GB4 honeycombing is due for close-out within 5 days."),
        ]
        for recipient, ntype, title, message in notif_spec:
            notification, created = Notification.objects.get_or_create(
                recipient=recipient,
                title=title,
                defaults={
                    "notification_type": ntype,
                    "message": message,
                    "link": "/projects/",
                },
            )
            self.track(notification, created)

        task_spec = [
            (users[User.ROLE_SUPERVISOR], users[User.ROLE_PM],
             "Close out NCR-0001 — GB4 honeycombing repair",
             Task.PRIORITY_HIGH, 5),
            (users[User.ROLE_PROCUREMENT], users[User.ROLE_PM],
             "Expedite switchboard customs clearance",
             Task.PRIORITY_URGENT, 3),
            (users[User.ROLE_DOC_CTRL], users[User.ROLE_PM],
             "Distribute S-201 Rev B to all site copies",
             Task.PRIORITY_MEDIUM, 7),
        ]
        for assigned_to, assigned_by, title, priority, due_in in task_spec:
            task, created = Task.objects.get_or_create(
                assigned_to=assigned_to,
                title=title,
                defaults={
                    "description": f"Demo task: {title}.",
                    "assigned_by": assigned_by,
                    "project": project,
                    "due_date": today + datetime.timedelta(days=due_in),
                    "priority": priority,
                    "status": Task.STATUS_PENDING,
                },
            )
            self.track(task, created)
