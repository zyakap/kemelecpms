# CONSTRUCTION PROJECT MANAGEMENT SOFTWARE (CPMS)
## Full System Blueprint — Kemele Construction
**Prepared by:** Tribes IT  
**Version:** 1.0  
**Date:** June 2026  
**Classification:** Internal Development Reference

---

## TABLE OF CONTENTS

1. [System Overview](#1-system-overview)
2. [Module 01 — Project Setup & Contract Management](#2-module-01--project-setup--contract-management)
3. [Module 02 — Budget & Cost Control](#3-module-02--budget--cost-control)
4. [Module 03 — Schedule & Progress Tracking](#4-module-03--schedule--progress-tracking)
5. [Module 04 — Resource Management](#5-module-04--resource-management)
6. [Module 05 — Materials & Procurement](#6-module-05--materials--procurement)
7. [Module 06 — Daily Site Reports (DSR)](#7-module-06--daily-site-reports-dsr)
8. [Module 07 — Safety, Health & Environment (SHE)](#8-module-07--safety-health--environment-she)
9. [Module 08 — Quality Management](#9-module-08--quality-management)
10. [Module 09 — Interim Payment Claims (IPC)](#10-module-09--interim-payment-claims-ipc)
11. [Module 10 — Document Management](#11-module-10--document-management)
12. [Module 11 — Compliance & Funder Reporting](#12-module-11--compliance--funder-reporting)
13. [Module 12 — Tender & Bid Library](#13-module-12--tender--bid-library)
14. [Module 13 — Analytics & Executive Dashboard](#14-module-13--analytics--executive-dashboard)
15. [Module 14 — User Management & Permissions](#15-module-14--user-management--permissions)
16. [Module 15 — Notifications & Communications](#16-module-15--notifications--communications)
17. [Module 16 — Mobile Application](#17-module-16--mobile-application)
18. [System Architecture & Technical Specifications](#18-system-architecture--technical-specifications)
19. [Data Models Overview](#19-data-models-overview)
20. [Integration Points](#20-integration-points)
21. [Development Phasing & Roadmap](#21-development-phasing--roadmap)

---

## 1. SYSTEM OVERVIEW

### 1.1 Purpose
The Construction Project Management Software (CPMS) is a purpose-built, web and mobile platform for Kemele Construction to plan, execute, monitor, and close construction projects — including EPC (Engineering, Procurement, Construction) and government-funded contracts such as the OTML Tax Credit Scheme (TCS).

### 1.2 Core Objectives
- Manage multiple concurrent construction projects from a single platform
- Deliver real-time cost control to prevent overruns on fixed-price contracts
- Generate compliant documentation for OTML TCS, RPNGC, and IRC requirements
- Build an institutional knowledge base from completed projects to win future tenders
- Replace manual spreadsheets and paper-based reporting with digital workflows

### 1.3 Target Users
| Role | Primary Use |
|------|-------------|
| Managing Director | Portfolio oversight, financial approvals, strategic reports |
| Project Manager | Full project lifecycle management |
| Site Supervisor | Daily reports, labour attendance, site activities |
| Procurement Officer | Purchase orders, supplier management, materials |
| Finance / Accounts | Cost tracking, IPC generation, payment status |
| Document Controller | Drawing register, submittals, version control |
| Auditor / Funder Rep | Read-only access, compliance reports |
| System Administrator | User management, system configuration |

### 1.4 Design Principles
- **Offline-first mobile** — PNG sites have unreliable connectivity; data syncs when online
- **Audit trail everywhere** — every record is timestamped, user-stamped, and immutable
- **PNG compliance built-in** — IRC, OTML TCS, and RPNGC formats native, not bolted on
- **Multi-project from day one** — no single-project workarounds
- **Evidence chain** — DSR → Photos → Progress % → IPC → Payment, all linked

---

## 2. MODULE 01 — PROJECT SETUP & CONTRACT MANAGEMENT

### 2.1 Purpose
Establish the foundational record for every project. All other modules draw from this master data.

### 2.2 Submodules

#### 2.2.1 Project Register
- Create new project with unique Project ID (auto-generated)
- Project name, description, type (Building / Civil / Electrical / EPC / Mixed)
- Project location: province, district, site address, GPS coordinates
- Project status lifecycle: `Tendering → Awarded → Mobilisation → Active → Practical Completion → Defects Liability → Closed`
- Assign Project Manager, Site Supervisor, and supporting team
- Project thumbnail / site image upload
- Link to client record and funder record

#### 2.2.2 Client & Stakeholder Management
- Client register: name, type (Government / Private / NGO), contact persons, address
- Funder register: OTML TCS, ADB, World Bank, DFAT, private, etc.
- Stakeholder register: consultants, certifiers, government agencies
- Contact directory per project with role assignments

#### 2.2.3 Contract Details
- Contract number and reference
- Letter of Award (LoA) upload and metadata
- Contract type: Lump Sum / Schedule of Rates / Cost Plus / EPC / Design & Build
- Original contract value (in PGK)
- Contract start date and original completion date
- Contractual milestones with dates
- Liquidated damages (LD) rate per day (if applicable)
- Defects Liability Period (DLP) duration
- Retention percentage and cap (e.g., 5% capped at 10% of contract sum)
- Payment terms (e.g., Net 30 days after certification)

#### 2.2.4 Variation & Amendment Management
- Log contract variations: description, instruction reference, date instructed
- Variation status: `Instructed → Submitted → Assessed → Approved → Rejected`
- Variation amount (add or omit)
- Running revised contract value (Original + Approved Variations)
- Amendment register for formal contract amendments
- Attach supporting documents to each variation
- Audit log of all variation status changes

#### 2.2.5 Project Milestones
- Define milestones with target dates
- Milestone types: Contractual / Internal / Funder-Required
- Mark milestone as achieved with actual date and evidence attachment
- Delay logging against milestone: reason, duration, responsibility (Client / Contractor / Force Majeure)
- Auto-flag overdue milestones

#### 2.2.6 Project Closeout
- Practical Completion checklist
- Defects register during DLP
- Final Account summary
- Project closure report generation
- Archive project to Tender Library

---

## 3. MODULE 02 — BUDGET & COST CONTROL

### 3.1 Purpose
Maintain real-time financial visibility across all projects to prevent cost overruns on fixed-price government contracts.

### 3.2 Submodules

#### 3.2.1 Bill of Quantities (BoQ)
- Import BoQ from Excel or CSV
- Manual BoQ entry: item number, description, unit, quantity, unit rate, amount
- BoQ organised by trade / work section (Civil, Structural, Electrical, Mechanical, Plumbing, Carpentry, Finishes, Preliminaries, Contingency)
- Link BoQ items to WBS (Work Breakdown Structure) activities
- BoQ revision history when variations are approved
- Lock original BoQ; variations tracked separately

#### 3.2.2 Budget Setup & Cost Codes
- Define cost code structure (e.g., 01.CIVIL.EARTHWORKS, 02.STRUCT.CONCRETE)
- Budget allocation per cost code
- Allocate contingency budget with approval required to access
- Provisional sums management
- Budget approval workflow: PM → Finance → MD

#### 3.2.3 Cost Tracking — Commitments & Actuals
- **Committed costs**: approved POs, subcontracts, hire agreements
- **Actual costs**: invoices received and approved, petty cash, direct payments
- Post costs against cost codes
- Three-way match: PO → Delivery Receipt → Invoice
- Petty cash register: site expenditure log with receipt photos, amount, description, approved by
- Cost entry requires supporting document attachment

#### 3.2.4 Budget vs. Actual Dashboard
- Real-time budget vs. committed vs. actual per cost code
- Variance amount and variance % per line
- Traffic light (RAG) status per cost code
- Forecast cost to complete (ETC) and estimated final cost (EFC)
- Cost Performance Index (CPI) calculation
- Auto-alert when cost code exceeds 80% of budget

#### 3.2.5 Cost Reports
- Monthly cost report by trade
- Cost-to-date summary for IPC support
- Overhead and profit margin tracker
- Cash flow forecast (planned vs. actual receipts and payments)
- Exportable to PDF and Excel

#### 3.2.6 Subcontract Cost Management
- Subcontract register: trade, contractor name, scope, contract value
- Progress claims from subcontractors
- Subcontract payment status
- Back-charges against subcontractors
- Retention held on subcontractors

---

## 4. MODULE 03 — SCHEDULE & PROGRESS TRACKING

### 4.1 Purpose
Plan, monitor, and report construction progress against the agreed programme.

### 4.2 Submodules

#### 4.2.1 Work Breakdown Structure (WBS)
- Define WBS hierarchy: Project → Phase → Work Package → Activity
- Assign cost codes and BoQ items to activities
- Assign responsible person per activity
- WBS import from Excel

#### 4.2.2 Programme / Gantt Chart
- Interactive Gantt chart builder
- Activity list with start date, end date, duration, predecessor links
- Dependency types: Finish-to-Start (FS), Start-to-Start (SS), Finish-to-Finish (FF)
- Critical path identification and highlighting
- Baseline programme save (locked at contract award)
- Revised programme versions with change reason
- View by day / week / month / quarter
- Zoom and scroll within Gantt
- Print and export Gantt as PDF

#### 4.2.3 Progress Entry
- Update % complete per activity (manual or calculated from sub-tasks)
- Progress entry linked to DSR for evidence
- Planned % vs. actual % per activity
- Schedule Performance Index (SPI) per activity
- Bulk progress update for multiple activities

#### 4.2.4 S-Curve Reporting
- Auto-generated S-curve: Planned Cumulative % vs. Actual Cumulative %
- Monthly snapshot saved automatically
- S-curve exportable as PNG and PDF
- Ahead/behind schedule indicator with days variance

#### 4.2.5 Delay Management
- Delay event register: date, description, responsible party, impact in days
- Delay categories: Weather / Material Supply / Design Issue / Client Instruction / Labour / Force Majeure
- Extension of Time (EOT) claim tracker: submitted → assessed → approved
- Revised completion date after approved EOT
- Delay impact on critical path auto-calculated

#### 4.2.6 Look-Ahead Scheduling
- 2-week and 4-week look-ahead plan builder
- Assign tasks to supervisors and crews
- Look-ahead published to site team via mobile
- Comparison: look-ahead planned vs. what was actually completed

---

## 5. MODULE 04 — RESOURCE MANAGEMENT

### 5.1 Purpose
Track labour, equipment, and subcontractors deployed on each project.

### 5.2 Submodules

#### 5.2.1 Labour Management
- Worker register: full name, gender, nationality, occupation/trade, NID number, TFN, contact
- Worker classification: Unskilled / Semi-Skilled / Skilled Tradesman / Supervisor / Professional
- Employment type: Direct / Day Labour / Subcontractor
- Daily attendance register per project, per crew
- Attendance methods: manual entry (site supervisor) / QR code scan
- Time in / time out logging
- Overtime recording
- Daily labour count summary (by trade, by nationality, total headcount)
- Payroll export (hours per worker per week)

#### 5.2.2 Crew & Gang Management
- Define crews/gangs per project
- Assign gang foreman
- Assign workers to gangs
- Gang daily output logging (linked to progress entry)

#### 5.2.3 Equipment & Plant Management
- Equipment register: ID, description, type, owned/hired, supplier
- Equipment allocation: assign to project, start date, end date
- Daily utilisation log: hours worked, idle hours, breakdown hours
- Fuel log: date, litres filled, equipment ID, logged by
- Maintenance schedule and service log
- Hire cost tracking (linked to cost module)
- Plant return and release from project

#### 5.2.4 Subcontractor Management
- Subcontractor register: company name, trade, contacts, IRC TIN, license details
- Subcontract scope of works
- Subcontractor daily presence on site (in/out log)
- Performance rating per project
- Payment status linked to IPC module
- Pre-qualification checklist (insurance, WC, tax compliance)

---

## 6. MODULE 05 — MATERIALS & PROCUREMENT

### 6.1 Purpose
Control the full procurement cycle from site requisition through to stock on site and consumption tracking.

### 6.2 Submodules

#### 6.2.1 Materials Register
- Master materials catalogue: item code, description, unit, category
- Project-specific materials list linked to BoQ
- Stock register: quantity on-site, quantity consumed, wastage
- Minimum stock level alerts

#### 6.2.2 Materials Requisition
- Site supervisor raises Material Requisition (MR)
- MR fields: project, date, items required, quantity, required-by date, justification
- Approval workflow: Site Supervisor → Project Manager → Procurement Officer
- MR status tracking: `Draft → Submitted → Approved → Ordered → Delivered → Closed`
- Rejected MR with reason returned to requester

#### 6.2.3 Supplier / Vendor Database
- Supplier register: name, address, IRC TIN, bank details, contact persons
- Supplier categories (Hardware, Electrical, Mechanical, Fuel, Plant Hire, etc.)
- Price history per item per supplier
- Supplier performance rating
- Preferred supplier flag per item category
- Blacklist flag with reason

#### 6.2.4 Purchase Orders (PO)
- Generate PO from approved MR (auto-populated)
- PO fields: PO number (auto), project, supplier, date, delivery address, items, quantities, unit prices, total
- PO approval workflow: Procurement → Finance → PM → MD (threshold-based)
- Approval thresholds: e.g., <K5,000 PM only; K5,000–K50,000 PM + Finance; >K50,000 MD required
- Send PO to supplier (PDF email or printed)
- PO amendment / revision tracking
- PO cancellation with reason

#### 6.2.5 Goods Received & Delivery Tracking
- Goods Received Note (GRN) creation against PO
- GRN fields: delivery date, delivered by, received by, items received, condition notes
- Partial delivery handling (multiple GRNs against one PO)
- Photo of delivery docket / goods
- Discrepancy report if delivery doesn't match PO
- GRN updates stock register automatically

#### 6.2.6 Invoice Processing & Three-Way Match
- Supplier invoice received against PO
- Three-way match check: PO qty vs. GRN qty vs. Invoice qty
- Flag discrepancies for resolution before payment
- Invoice approved → payment instruction to finance
- Invoice payment status: `Received → Matched → Approved → Paid`

#### 6.2.7 Stock Management
- Stock on-site ledger: receipts, issues, transfers, returns
- Issue materials to work activity (deducted from stock)
- Inter-project material transfers
- Stocktake feature: count vs. system balance reconciliation
- Wastage recording with reason code
- End-of-project stock return or write-off

---

## 7. MODULE 06 — DAILY SITE REPORTS (DSR)

### 7.1 Purpose
The DSR is the single most important evidence document in construction — every IPC, delay claim, and dispute resolution depends on it. This module makes DSR creation fast, consistent, and tamper-evident.

### 7.2 Submodules

#### 7.2.1 DSR Creation
- One DSR per project per day
- Locked to date (cannot back-date beyond 24 hours without PM override)
- Header: project name, date, day number, weather (AM/PM), prepared by
- Weather conditions: Sunny / Partly Cloudy / Overcast / Light Rain / Heavy Rain / Storm
- Temperature and visibility (optional)

#### 7.2.2 Activities Section
- Work activities completed today: description, location on site, crew, quantity achieved, unit
- Work activities in progress: description, % complete, constraints
- Work not started (planned but not started) with reason
- Link activities to WBS items for progress update

#### 7.2.3 Labour Section
- Pull from attendance register (auto-populated if attendance entered)
- Display: total workers on site by trade/classification
- Visitor log (client reps, consultants, government inspectors)

#### 7.2.4 Equipment Section
- Pull from equipment utilisation log
- Equipment on site: list with hours worked / idle / breakdown

#### 7.2.5 Materials Section
- Materials delivered today (linked to GRN)
- Materials used today (linked to stock issues)
- Materials shortages impacting work

#### 7.2.6 Photo Log
- Upload site photos directly from phone camera
- Auto-capture GPS coordinates and timestamp on photo
- Tag photo to: Activity / Area / Equipment / Defect / Safety / Progress
- Minimum and maximum photos per DSR (configurable)
- Photos compressed but full resolution stored

#### 7.2.7 Issues & Instructions
- Record verbal and written instructions received from client/consultant
- Record RFIs raised or responded to
- Issues affecting progress: material delays, design queries, access issues
- Correspondence reference linking

#### 7.2.8 DSR Approval & Lock
- Supervisor submits DSR for PM review
- PM reviews and approves (or returns with comments)
- Approved DSR is locked and digitally signed
- DSR PDF auto-generated on approval
- Late DSR flagging (>48 hours after site date)

---

## 8. MODULE 07 — SAFETY, HEALTH & ENVIRONMENT (SHE)

### 8.1 Purpose
Maintain OHS compliance, protect workers, and meet PNG regulatory and OTML TCS requirements.

### 8.2 Submodules

#### 8.2.1 Safety Induction Register
- Record worker safety inductions: date, topics covered, inducted by
- Worker signs off on induction (digital signature or checkbox)
- Induction expiry tracking (e.g., annual re-induction)
- Visitor induction log

#### 8.2.2 Toolbox Talk Register
- Log daily/weekly toolbox talks: date, topic, presenter, attendees
- Attach toolbox talk notes or template
- Workers acknowledge attendance (digital)

#### 8.2.3 Incident Register
- Incident types: Near Miss / First Aid / Medical Treatment / Lost Time Injury / Fatality / Property Damage / Environmental
- Incident fields: date, time, location, persons involved, description, immediate cause, contributing factors
- Injury details: body part, nature of injury, treatment given
- Lost Time Injury (LTI) counter per project
- Incident photos
- Corrective actions: what, responsible person, due date, closed out date

#### 8.2.4 Hazard & Risk Register
- Identify hazards per activity type
- Risk rating: Likelihood × Consequence = Risk Level
- Control measures: Eliminate / Substitute / Isolate / Engineering / Administrative / PPE
- Risk register reviewed and approved by PM
- Link hazards to work activities in DSR

#### 8.2.5 Safe Work Method Statements (SWMS)
- Create SWMS per high-risk activity
- SWMS approval workflow
- Workers acknowledge SWMS before commencing activity
- Archive SWMS with project records

#### 8.2.6 PPE Register
- Record PPE issued to each worker: type, size, date issued, quantity
- PPE replacement log
- PPE compliance check (daily inspection, logged in DSR)

#### 8.2.7 Safety Statistics Dashboard
- Total Man-Hours Worked
- Lost Time Injury Frequency Rate (LTIFR)
- Total Recordable Injury Frequency Rate (TRIFR)
- Days since last LTI
- Incident trend chart by month

---

## 9. MODULE 08 — QUALITY MANAGEMENT

### 9.1 Purpose
Ensure construction works comply with specifications, drawings, and contract quality requirements.

### 9.2 Submodules

#### 9.2.1 Inspection & Test Plan (ITP)
- Define ITP per work activity/trade
- ITP items: Hold Points (H) / Witness Points (W) / Review Points (R)
- Assign responsible party per inspection point (Contractor / Consultant / Client)
- ITP status: Not Started / In Progress / Complete / Closed

#### 9.2.2 Inspection Records
- Create inspection record against ITP item
- Fields: inspection date, inspector name, location, description, result (Pass / Fail / Conditional Pass)
- Attach supporting documents (test certificates, photos)
- Digital sign-off by inspector and supervisor
- Failed inspection triggers NCR

#### 9.2.3 Non-Conformance Reports (NCR)
- Raise NCR: description of non-conformance, location, trade responsible
- NCR severity: Minor / Major / Critical
- Corrective action required: description, responsible person, due date
- NCR response by contractor
- Close-out inspection confirming rectification
- NCR register per project with status tracking

#### 9.2.4 Material Test Results
- Record test results: concrete compressive strength, soil compaction, weld inspection, etc.
- Compare against specified values (pass/fail)
- Attach lab test certificates
- Failed test triggers NCR automatically

#### 9.2.5 Defects Management
- Defects register: description, location, trade, date identified, severity
- Defects raised during construction and during DLP
- Assign defect to responsible party (contractor/subcontractor)
- Target rectification date
- Photo before and after rectification
- Close-out sign-off by PM or consultant

---

## 10. MODULE 09 — INTERIM PAYMENT CLAIMS (IPC)

### 10.1 Purpose
Generate, submit, and track payment claims efficiently — reducing payment delays and disputes on government contracts.

### 10.2 Submodules

#### 10.2.1 IPC Generation
- IPC number (auto-generated, sequential per project)
- Claim period: from date / to date
- Pull progress % from Schedule module per BoQ item
- Auto-calculate value of work done this period and cumulative to date
- Previous payments deducted automatically
- Retention deducted (calculated against contract retention terms)
- Net claim amount calculated

#### 10.2.2 IPC Supporting Evidence Pack
- Auto-attach approved DSRs for claim period
- Auto-attach site progress photos from claim period
- BoQ progress schedule as attachment
- S-curve as attachment
- Any variation works included with variation approval reference

#### 10.2.3 IPC Submission Workflow
- Internal review: PM → Finance → MD approval before submission
- Mark as submitted with date, method (email / hand delivered), and recipient
- Attach acknowledgement receipt from client

#### 10.2.4 Payment Certification Tracking
- Log certification received: amount certified, date certified, certifier name
- Differences between claimed and certified with reason
- Disputed items register
- Retention released (at Practical Completion and at end of DLP)

#### 10.2.5 Payment Status & Ledger
- Payment received: date, amount, payment reference
- Running ledger: claimed → certified → paid → outstanding
- Late payment flag (beyond contract payment terms)
- Retention ledger (held / released)
- Final Account preparation

#### 10.2.6 Tax Invoice Generation
- Generate tax invoice aligned to certified amount
- IRC-compliant format (GST applicable where required)
- Invoice number, date, TINPNG number, GST number
- Link to IPC reference

---

## 11. MODULE 10 — DOCUMENT MANAGEMENT

### 11.1 Purpose
Centralise all project documents with version control, access management, and auto-generation of standard reports.

### 11.2 Submodules

#### 11.2.1 Drawing Register
- Upload drawings: drawing number, revision, title, discipline, scale, date
- Version control: each revision saved; previous revisions accessible but flagged as superseded
- Transmittal log when drawings sent to site or subcontractors
- Drawing status: Issued for Construction (IFC) / Issued for Review / Superseded / For Information
- Set active revision per drawing (distributed to site)

#### 11.2.2 Specification Register
- Upload technical specifications per section
- Version control and revision tracking
- Link specs to work activities

#### 11.2.3 RFI (Request for Information) Register
- Raise RFI: number (auto), date raised, subject, question, raised by, directed to
- Attach relevant drawings, photos
- Response recorded with date received
- RFI response time tracking (days open)
- Overdue RFI alerts
- Impact assessment: schedule impact, cost impact

#### 11.2.4 Submittal Register
- Submittal types: Material / Shop Drawing / Method Statement / Sample / Certificate
- Submittal workflow: Contractor Submits → Consultant Reviews → Approved / Approved as Noted / Revise & Resubmit / Rejected
- Resubmission tracking
- Approved submittals linked to work activities

#### 11.2.5 Correspondence Register
- Log all formal correspondence: letters, emails, notices
- Incoming and outgoing
- Reference number, date, subject, from, to, summary
- Attach original document
- Action required flag and due date
- Response tracking

#### 11.2.6 Report Generation
- Auto-generate Monthly Progress Report (PDF): cover, S-curve, progress photos, cost summary, schedule summary, issues
- Weekly report (lighter version)
- OTML TCS milestone report template
- All reports branded with Kemele Construction logo and project details
- Report archive: every generated report saved with date stamp

#### 11.2.7 Document Library
- Reusable document templates: method statements, SWMS, quality checklists, inspection forms
- Organised by document type and project phase
- Accessible across all projects (company-wide templates)
- Project-specific documents visible only within that project

---

## 12. MODULE 11 — COMPLIANCE & FUNDER REPORTING

### 12.1 Purpose
Meet the specific reporting and documentation requirements of OTML TCS, RPNGC, and IRC without manual reformatting.

### 12.2 Submodules

#### 12.2.1 OTML TCS Reporting
- OTML TCS milestone progress report template (pre-formatted)
- Tax Credit Scheme expenditure schedule (monthly)
- Funding utilisation report: budget vs. actual vs. remaining TCS credit
- Compliance checklist: PNG content, local labour %, materials sourcing
- PNG Local Content tracking: % local vs. expatriate labour, local vs. imported materials

#### 12.2.2 Government / RPNGC Reporting
- Works progress report for Department of Works and Highways (DWH) format
- Infrastructure Development Authority (IDA) report templates
- Photos report for government milestone sign-off
- Certified completion evidence package

#### 12.2.3 IRC Tax Compliance
- GST return data extract (output tax on progress claims)
- Withholding tax tracking on subcontractor payments
- Annual income tax support data
- TINPNG verification fields on supplier and subcontractor records

#### 12.2.4 Audit Trail
- Every record: created by, created at, last modified by, last modified at
- Deleted records: soft delete only (never hard delete), retained for audit
- Approval history: full log of who approved what and when
- System event log: logins, exports, report generations, user changes
- Immutable once approved (DSRs, IPCs, approved POs cannot be edited)

#### 12.2.5 Compliance Calendar
- Scheduled compliance reporting dates per project
- Reminders to responsible persons before due dates
- Overdue compliance items dashboard

---

## 13. MODULE 12 — TENDER & BID LIBRARY

### 13.1 Purpose
Convert completed project data into competitive intelligence for future tenders — Kemele's primary long-term advantage.

### 13.2 Submodules

#### 13.2.1 Project Archive
- On project closure, archive full project to Tender Library
- Archive includes: BoQ actuals, resource data, schedule, cost data, documents, lessons learned
- Searchable by project type, location, contract value, scope of work, funder

#### 13.2.2 Cost Intelligence Database
- Actual unit rates from completed projects (per m², per m³, per linear metre, per item)
- Rates by trade, by region, by year
- Labour productivity rates (e.g., m² of formwork per gang per day)
- Material consumption rates (e.g., concrete yield per bag of cement)
- Equipment utilisation costs (fuel, hire, maintenance per hour)

#### 13.2.3 Bid Estimate Builder
- Start new estimate from blank or clone from similar past project
- Auto-suggest unit rates from cost intelligence database based on item description
- Adjust for location factor, current pricing, and project-specific conditions
- Build preliminary and general (P&G) / preliminaries from past actuals
- Generate estimate summary for tender submission

#### 13.2.4 Reusable Document Library (Tender)
- Store approved method statements by work type
- Company CVs for key personnel (auto-updated from HR records)
- Organisational charts per project type
- Company profile, certifications, registration documents
- Past project experience sheets (auto-generated from archive)

#### 13.2.5 Lessons Learned Register
- Lessons learned entry at project close-out
- Category: Cost / Schedule / Quality / Safety / Procurement / Client Relations / Design
- What went well, what went wrong, recommendation for next project
- Searchable and visible to all PMs on new project setup

---

## 14. MODULE 13 — ANALYTICS & EXECUTIVE DASHBOARD

### 14.1 Purpose
Give the MD and senior leadership a real-time portfolio view across all active projects.

### 14.2 Submodules

#### 14.2.1 Portfolio Dashboard
- Active project count, total contract value, total billed, total collected
- Per-project health indicators: Budget RAG / Schedule RAG / Safety RAG
- Map view: project locations plotted on PNG map
- Project portfolio summary table (sortable and filterable)

#### 14.2.2 Financial Analytics
- Revenue recognised vs. total contract value (portfolio)
- Outstanding claims (submitted but not paid) by project and total
- Cash flow: monthly in/out across all projects
- Margin analysis: contract value vs. total cost (%) per project
- Cost overrun alert: projects where EFC exceeds contract value

#### 14.2.3 Schedule Analytics
- % of projects on schedule / behind schedule / ahead of schedule
- Average schedule performance index across portfolio
- Projects with critical path delays
- Milestones due in next 30/60/90 days

#### 14.2.4 Resource Analytics
- Total workforce headcount across all projects (by date)
- Labour cost trend per project
- Equipment utilisation rate across fleet
- Subcontractor spend by trade (portfolio-wide)

#### 14.2.5 Safety Analytics
- Total man-hours worked (portfolio)
- LTIFR and TRIFR (portfolio)
- Incident count by type and project
- Projects with open incidents or overdue corrective actions

#### 14.2.6 Custom Reports
- Report builder: select metrics, filter by project/date/trade, choose chart type
- Scheduled reports: auto-email to MD weekly/monthly
- Export all reports to PDF and Excel

---

## 15. MODULE 14 — USER MANAGEMENT & PERMISSIONS

### 15.1 Purpose
Control who can see and do what across the system.

### 15.2 Submodules

#### 15.2.1 User Accounts
- User creation: name, email, mobile, role, assigned projects
- Password policy (minimum complexity, expiry)
- Multi-factor authentication (MFA) option
- Single Sign-On (SSO) capability (future phase)
- User deactivation (access removed on staff departure, records retained)

#### 15.2.2 Roles & Permissions
- Pre-defined system roles (see Section 1.3)
- Custom role creation
- Permission matrix: per module, per action (View / Create / Edit / Delete / Approve / Export)
- Project-level access: user can only see projects they are assigned to
- Company-level admin: Tribes IT / System Admin sees all

#### 15.2.3 Approval Hierarchies
- Define approval chains per module (PO approvals, IPC approvals, DSR approvals)
- Delegation of authority: define financial approval thresholds per role
- Escalation rules: auto-escalate if approver inactive >48 hours

#### 15.2.4 Activity Log
- Full user activity log: login times, records accessed, records created/modified/approved
- Failed login attempts flagged
- Exportable for HR or security audit

---

## 16. MODULE 15 — NOTIFICATIONS & COMMUNICATIONS

### 16.1 Purpose
Keep all team members informed of tasks, approvals, and alerts without leaving the platform.

### 16.2 Submodules

#### 16.2.1 In-App Notifications
- Notification bell in app header
- Notification types: Approval Required / Overdue Item / Milestone Due / Submission Received / Payment Received
- Mark as read / dismiss
- Notification history (last 90 days)

#### 16.2.2 Email Notifications
- Email alerts for critical events: IPC submission, PO approval, overdue DSR
- Daily digest email option (summary of outstanding actions)
- Configurable per user (opt-in/out per notification type)

#### 16.2.3 SMS Notifications (Optional)
- SMS for urgent alerts: incident reported, critical overdue action
- Digicel / Bmobile PNG gateway integration
- Per-user mobile number on profile

#### 16.2.4 Task Assignment & Reminders
- Assign tasks to users from within any module
- Task: description, assigned to, due date, priority
- Reminder before due date
- Overdue task escalation to supervisor

---

## 17. MODULE 16 — MOBILE APPLICATION

### 17.1 Purpose
Give site supervisors a fast, simple mobile interface optimised for on-site use with intermittent connectivity.

### 17.2 Submodules

#### 17.2.1 Mobile DSR
- Simplified DSR entry form for phone screen
- Voice-to-text for activity descriptions
- Camera integration for site photos with automatic geo-tag and timestamp
- Works fully offline; syncs when connectivity restored
- Sync status indicator (pending sync items shown)

#### 17.2.2 Mobile Attendance
- QR code scan attendance per worker
- Manual attendance as fallback
- Labour count per crew visible instantly

#### 17.2.3 Mobile Materials
- Raise materials requisition from site
- Confirm delivery (GRN) with photo of delivery docket
- View current stock levels

#### 17.2.4 Mobile Safety
- Report incident from site (with photo)
- Complete toolbox talk attendee sign-off
- Acknowledge SWMS before starting high-risk work

#### 17.2.5 Mobile Notifications
- Push notifications for approvals and tasks
- View look-ahead schedule
- View own outstanding actions

#### 17.2.6 Mobile Technical Specs
- Platform: iOS and Android (React Native or Flutter)
- Offline storage: SQLite local database
- Sync engine: conflict resolution (last write wins for non-financial records; flag for financial)
- Data compression for photo sync over limited data
- Minimum device requirements: Android 9+ / iOS 14+

---

## 18. SYSTEM ARCHITECTURE & TECHNICAL SPECIFICATIONS

### 18.1 Architecture Overview
```
┌─────────────────────────────────────┐
│          Mobile App (PWA / Native)  │
│     iOS · Android · Offline Sync    │
└──────────────┬──────────────────────┘
               │ HTTPS / REST API
┌──────────────▼──────────────────────┐
│          Web Application            │
│     React / Next.js Frontend        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│          API Layer (Backend)        │
│     Node.js / Django REST API       │
│     Authentication · Business Logic │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│          Database Layer             │
│     PostgreSQL (Primary)            │
│     Redis (Cache / Sessions)        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│          File Storage               │
│     AWS S3 / Local NAS              │
│     Photos · Documents · Reports    │
└─────────────────────────────────────┘
```

### 18.2 Technology Stack (Recommended)
| Layer | Technology | Reason |
|-------|-----------|--------|
| Frontend | React + Next.js | Fast, SEO-ready, good ecosystem |
| Mobile | React Native | Code share with web frontend |
| Backend | Node.js (Express) or Python (Django) | Team capability |
| Database | PostgreSQL | Relational, ACID compliant, robust |
| Cache | Redis | Sessions, real-time counters |
| File Storage | AWS S3 or local MinIO | Scalable document/photo storage |
| PDF Generation | Puppeteer / WeasyPrint | Auto-report PDF generation |
| Email | SendGrid or SMTP | Notification emails |
| Hosting | AWS / DigitalOcean / Local Server | Depends on connectivity |
| Auth | JWT + Refresh Tokens | Secure, stateless |

### 18.3 Security Requirements
- HTTPS enforced on all endpoints
- Passwords hashed (bcrypt, min 12 rounds)
- JWT tokens with short expiry (15 min) + refresh token rotation
- Role-based access control (RBAC) at API level, not just frontend
- SQL injection prevention (parameterised queries / ORM)
- File upload validation (type, size, virus scan)
- Rate limiting on authentication endpoints
- Regular automated database backups (daily, 30-day retention)
- Backup tested quarterly

### 18.4 Performance Requirements
- Page load: < 3 seconds on 4G connection
- API response: < 500ms for standard queries
- Report generation: < 30 seconds for full monthly PDF
- Concurrent users: minimum 50 simultaneous without degradation
- File upload: support up to 50MB per file
- Photo compression: auto-compress to < 2MB for sync

### 18.5 Offline & Sync Specifications
- Offline modules: DSR, Attendance, Material issues, Incident reporting
- Local storage: SQLite on device
- Sync trigger: automatic on network detect, manual sync button available
- Sync conflict handling: timestamp-based; financial records flagged for manual review
- Sync queue: items queued and retried if sync fails

---

## 19. DATA MODELS OVERVIEW

### 19.1 Core Entities
```
Project
├── Contract
│   └── Variation
├── WBS Activity
│   └── Progress Entry
├── BoQ Item
│   └── Cost Entry
├── Milestone
│   └── Delay Event
├── Daily Site Report (DSR)
│   ├── Labour Entry
│   ├── Equipment Entry
│   ├── Activity Entry
│   └── Photo
├── Resource
│   ├── Worker
│   ├── Equipment
│   └── Subcontractor
├── Procurement
│   ├── Requisition
│   ├── Purchase Order
│   │   └── GRN
│   └── Invoice
├── IPC
│   ├── IPC Line (BoQ)
│   ├── Certification
│   └── Payment
├── Document
│   ├── Drawing
│   ├── Submittal
│   ├── RFI
│   └── Correspondence
├── Safety
│   ├── Incident
│   ├── Toolbox Talk
│   └── SWMS
├── Quality
│   ├── Inspection Record
│   ├── NCR
│   └── Test Result
└── User
    ├── Role
    └── Permission
```

---

## 20. INTEGRATION POINTS

### 20.1 Internal Integrations (Module to Module)
| From | To | Data Passed |
|------|----|-------------|
| DSR Labour | Resource Module | Daily attendance count |
| DSR Activities | Schedule Module | Progress % update |
| GRN | Stock Register | Received quantities |
| Stock Issue | BoQ Cost | Material cost consumed |
| Progress % | IPC Module | Value of work done |
| IPC | Finance | Tax invoice trigger |
| Incident | Safety Dashboard | LTIFR calculation |
| Project Close | Tender Library | Archived cost and resource data |

### 20.2 External Integrations (Future Phase)
| System | Purpose |
|--------|---------|
| MYOB / Xero | Accounting sync (invoices, payments) |
| Digicel Business | SMS notifications |
| Google Maps API | GPS plotting of projects and photos |
| DocuSign | Digital signature on IPCs and contracts |
| NASFUND / BSP | Payroll file export |
| IRC TIN Lookup | Supplier / worker TIN verification |

---

## 21. DEVELOPMENT PHASING & ROADMAP

### Phase 1 — Foundation (Months 1–3)
**Goal:** Core project and financial management working end-to-end

- [ ] User Management & Authentication
- [ ] Project Setup & Contract Management
- [ ] Budget & Cost Control (BoQ, cost codes, actuals)
- [ ] Basic Schedule & Gantt Chart
- [ ] Daily Site Reports (DSR) — web version
- [ ] Document Management (upload, register, version control)
- [ ] Basic Dashboard

**Deliverable:** System operational for one live project (Gordons)

---

### Phase 2 — Field Operations (Months 4–5)
**Goal:** Site team fully on system; procurement loop closed

- [ ] Labour & Attendance Module
- [ ] Equipment & Plant Module
- [ ] Materials & Procurement (MR → PO → GRN → Invoice)
- [ ] Stock Register
- [ ] Safety Module (Incident, Toolbox, SWMS)
- [ ] Mobile App — DSR, Attendance, Incident Reporting

**Deliverable:** Site operations paperless; mobile app deployed to site

---

### Phase 3 — Financial & Compliance (Month 6)
**Goal:** Revenue cycle complete; audit-ready for OTML TCS

- [ ] IPC Generation & Submission Workflow
- [ ] Payment Tracking & Ledger
- [ ] Retention Management
- [ ] Tax Invoice Generation (IRC compliant)
- [ ] OTML TCS Report Templates
- [ ] Compliance Calendar & Audit Trail
- [ ] Quality Module (ITP, Inspections, NCR)

**Deliverable:** First IPC generated and submitted through system

---

### Phase 4 — Intelligence & Tender Library (Month 7–8)
**Goal:** Build the competitive intelligence layer

- [ ] Project Archive & Closeout Workflow
- [ ] Cost Intelligence Database
- [ ] Bid Estimate Builder
- [ ] Lessons Learned Register
- [ ] Reusable Document Library
- [ ] Executive Analytics Dashboard
- [ ] Custom Report Builder

**Deliverable:** First tender estimate built from system data

---

### Phase 5 — Optimisation & Integrations (Month 9+)
**Goal:** External integrations and advanced features

- [ ] Accounting System Integration (MYOB / Xero)
- [ ] SMS Notification Gateway (Digicel)
- [ ] Advanced offline sync (conflict resolution)
- [ ] API for third-party access (future consultants / clients)
- [ ] Performance optimisation and load testing
- [ ] User training and onboarding materials

---

## APPENDIX A — KEY REPORTS GENERATED BY SYSTEM

| Report | Module | Format | Audience |
|--------|--------|--------|----------|
| Monthly Progress Report | Document Mgmt | PDF | Client / Funder |
| S-Curve Report | Schedule | PDF / PNG | PM / Client |
| IPC Summary | IPC Module | PDF | Client |
| Cost Report (Budget vs Actual) | Cost Control | PDF / Excel | PM / MD |
| Daily Site Report | DSR | PDF | PM / Client |
| Safety Statistics Report | Safety | PDF | PM / MD / Regulator |
| OTML TCS Milestone Report | Compliance | PDF | OTML / RPNGC |
| Labour Attendance Report | Resource | Excel | HR / Payroll |
| Plant Utilisation Report | Resource | PDF / Excel | PM |
| Stock Ledger Report | Procurement | Excel | Procurement |
| Outstanding Claims Report | IPC / Finance | PDF | MD / Finance |
| Project Portfolio Summary | Dashboard | PDF | MD |
| Bid Estimate | Tender Library | Excel / PDF | Tender Team |
| Lessons Learned Report | Tender Library | PDF | All PMs |

---

## APPENDIX B — GLOSSARY

| Term | Definition |
|------|-----------|
| BoQ | Bill of Quantities — itemised list of works with quantities and rates |
| DSR | Daily Site Report — daily record of all site activities |
| DLP | Defects Liability Period — period after completion during which contractor fixes defects |
| EFC | Estimated Final Cost — total projected cost at project completion |
| EPC | Engineering, Procurement, Construction — full turnkey delivery model |
| EOT | Extension of Time — approved extension to contract completion date |
| GRN | Goods Received Note — confirms delivery of goods against a Purchase Order |
| IPC | Interim Payment Claim — periodic claim for work completed to date |
| IRC | Internal Revenue Commission — PNG tax authority |
| ITP | Inspection and Test Plan — schedule of quality inspections |
| LD | Liquidated Damages — daily penalty for late completion |
| LoA | Letter of Award — formal notification of contract award |
| LTIFR | Lost Time Injury Frequency Rate — safety KPI |
| MR | Material Requisition — site request for materials |
| NCR | Non-Conformance Report — record of work not meeting specification |
| OHS | Occupational Health and Safety |
| OTML TCS | Ok Tedi Mining Limited Tax Credit Scheme |
| PO | Purchase Order — formal order to supplier |
| PNG | Papua New Guinea |
| RAG | Red / Amber / Green — traffic light status indicator |
| RFI | Request for Information — formal query to designer or client |
| RPNGC | Royal Papua New Guinea Constabulary (or relevant government body) |
| SPI | Schedule Performance Index — measure of schedule efficiency |
| SWMS | Safe Work Method Statement |
| TIN | Tax Identification Number |
| WBS | Work Breakdown Structure — hierarchical breakdown of project scope |

---

*End of CPMS Blueprint v1.0*  
*Tribes IT — Internal Development Reference*  
*Document Owner: Zechariah Yakap, I.T. Team Leader*
