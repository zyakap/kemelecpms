# CPMS Implementation TODO

This backlog tracks the path from current internal CPMS to a production-grade construction and maintenance project management platform for Papua New Guinea.

## Phase 1 - Critical Fixes

- [x] Align REST API serializers with actual model fields.
- [x] Fix GRN API/view/template references from old field names to current model fields.
- [x] Standardise role checks to use `accounts.User` constants and lowercase stored role values.
- [x] Replace incorrect `user.profile.role` template checks with `user.role` or user role helper properties.
- [x] Fix project detail template references to current `Project`, `Contract`, `Milestone`, `Variation`, and `DelayEvent` fields.
- [x] Ensure DSR API approval locks approved reports the same way as web approval.
- [x] Ensure approval/submit actions set `updated_by`, timestamps, and audit logs consistently.
- [x] Add smoke tests for critical API serializers and high-risk templates.

## Phase 2 - Functional Gaps

- [x] Implement project membership and object-level permissions.
- [x] Add central project-access helper for company-wide roles, PMs, and site supervisors.
- [x] Scope project-related REST API querysets by accessible projects.
- [x] Enforce DSR submit/approve permission checks in API and web views.
- [x] Scope procurement MR, PO, GRN, invoice, and stock views by accessible projects.
- [x] Add MR and PO submit/approve/reject permission checks with audit logging.
- [x] Add PO approval-threshold enforcement using user profile limits.
- [x] Scope IPC project views and add submit/certify/payment permission checks with audit logging.
- [x] Scope document-control project views and guard document update/revision actions.
- [x] Scope quality project views, nested inspection records, and quality management actions.
- [x] Scope safety project views, dashboards, and safety register forms by accessible projects.
- [x] Add role-specific workflow permissions for PM, supervisor, procurement, finance, document control, auditor, MD, and admin.
- [x] Add approval thresholds for purchase orders and financial actions.
- [x] Add workflow services/state transition guards for DSR, MR, PO, GRN, IPC, variations, NCRs, RFIs, submittals, and incidents.
- [x] Add evidence-based workflow guards for IPC certification/payment, RFIs, submittals, NCRs, defects, incidents, SWMS, and correspondence actions.
- [x] Add variation workflow guards, project-access scoping, audit logging, and signed omission/addition totals.
- [x] Add audit entries for RFI, submittal, NCR, defect, incident, and SWMS status changes.
- [x] Complete procurement three-way matching: MR -> PO -> GRN -> supplier invoice status/payment tracking.
- [x] Add PO/GRN/invoice match calculations and block matched/approved/paid invoice states when delivery evidence does not support them.
- [x] Auto-post GRN receipts to stock ledger for catalogue materials.
- [x] Add discrepancy handling and exception approvals for GRN/invoice mismatch.
- [x] Add IPC claim, certification, retention deduction, and payment consistency validation.
- [x] Add committed, actual, ETC, EFC, contingency, provisional sum, and margin forecasting.
- [x] Add subcontractor claims, retention, back-charges, and performance tracking.
- [x] Add schedule baseline/revision management, dependency validation, critical path, EOT workflow, and delay causation.
- [x] Link DSR evidence into schedule progress, material usage, equipment utilisation, safety, quality, and IPC support.
- [x] Add maintenance work orders, asset register, preventive maintenance, breakdown tickets, SLA response, service history, spares, and sign-off.
- [x] Expand safety with permits to work, training/certification matrix, safety observations, corrective-action workflow, and escalation.
- [x] Expand quality with inspection checklists, hold/witness-point signoffs, NCR root cause, corrective/preventive action, and closure evidence.
- [x] Add document transmittals, distribution lists, superseded drawing prevention, and latest-IFC site view.

## Phase 3 - UX/UI Improvements

- [x] Build role-based home screens/action queues.
- [x] Add global project switcher.
- [x] Add saved filters, bulk actions, export controls, and queue counts.
- [x] Rework site supervisor DSR into a mobile-first field workflow.
- [x] Add dashboard queues for approvals, overdue actions, RFIs, NCRs, late deliveries, budget overruns, and compliance.
- [x] Add guided setup steps for new projects: contract, BOQ, WBS, baseline programme, DSR.
- [x] Improve empty states, responsive tables, form grouping, and status badges.
- [x] Add accessible button labels, keyboard-friendly workflows, and consistent icon usage.

## Phase 4 - PNG-Specific Product Needs

- [x] Add government/public procurement evidence tracking and approval history.
- [x] Add national participation/local content tracking for labour, suppliers, subcontractors, and materials.
- [x] Add Building Act/authority permit, inspection, occupancy/completion certificate tracking.
- [x] Add IRC/GST tax invoice controls, voiding, invoice sequencing, and export reports.
- [x] Add funder-specific reporting packs for OTML TCS, government, donor, and private projects.
- [x] Add provincial/district reporting and GIS/project map views.
- [x] Add compliance calendar templates for PNG construction, safety, tax, funder, and maintenance obligations.

## Phase 5 - Strategic Features

- [x] Build offline-capable PWA/mobile workflows with sync conflict handling.
- [x] Add client/funder portal.
- [x] Add subcontractor/supplier portal.
- [x] Add BOQ Excel import validation and revision history.
- [x] Add executive report packs and scheduled PDF/Excel exports.
- [x] Add accounting integration export hooks.
- [x] Add SMS/email/WhatsApp-style notification integrations where supported.
- [x] Add analytics for CPI, SPI, cashflow, margin forecast, safety trends, quality trends, and supplier performance.
- [x] Add backup, monitoring, audit coverage, security hardening, and production readiness checklist.

## Phase 6 - Deployment Readiness Audit & Document Control (2026-06)

- [x] Fix profile/user-detail templates referencing fields that did not exist; implement full self-service profile (contact details, photo, password change, notification preferences).
- [x] Honour per-user notification preferences (DSR, budget, safety, milestone, IPC categories) in notification dispatch.
- [x] Fix broken URL references (`material_create`/`material_update`, `tender:rate-detail`, `documents:distribution-list`) and quality `get_absolute_url` methods missing `project_pk`.
- [x] Fix IRC tax invoice GST calculation crash (string default on `gst_rate`).
- [x] Fix stock/accounting export field errors (`Material.name`, `CostCode.description`).
- [x] Wire orphaned notification tasks into DSR/MR/PO/GRN/IPC/payment transitions with broker-outage fallback.
- [x] Add incident investigation/close and NCR review/close transition views with evidence guards, audit logs, and detail-page actions; guard defect status changes.
- [x] Add missing migrations (work package audit fields) and fix test discovery (`apps` package).
- [x] Production readiness: django-celery-beat dependency, /health/ endpoint, branded 400/403/404/500 pages, resilient production logging, .env.production.example, consistent static/media/log paths in nginx/systemd/deploy scripts, backup/restore scripts.
- [x] Document control system: company-wide + per-project `DocumentControlSettings` (numbering prefixes/padding/project-code, RFI/submittal/correspondence response windows, approval & acknowledgement policy, upload type/size limits, confidentiality default, access logging) applied throughout the documents module.
- [x] Controlled document register: auto-numbered documents with draft → review → approved → superseded/archived workflow, revision history with auto-supersede, approval records, CSV register export, download access log, and transmittal acknowledgement action.
- [x] Document control hub page with per-project register summaries and settings access.
- [x] Idempotent `seed_demo_data` command covering every module for demos/UAT.
- [x] Test suite: 33 passing tests covering document control settings/numbering/workflow, incident and NCR transitions, plus URL smoke crawl of all 367 routes with seeded data.
