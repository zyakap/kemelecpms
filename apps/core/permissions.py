from django.db.models import Q

from apps.accounts.models import User
from apps.projects.models import Project, ProjectMembership


COMPANY_WIDE_READ_ROLES = {
    User.ROLE_MD,
    User.ROLE_ADMIN,
    User.ROLE_FINANCE,
    User.ROLE_PROCUREMENT,
    User.ROLE_DOC_CTRL,
    User.ROLE_AUDITOR,
}

WORKFLOW_ROLE_MATRIX = {
    "dsr.submit": {User.ROLE_PM, User.ROLE_SUPERVISOR, User.ROLE_ADMIN},
    "dsr.approve": {User.ROLE_PM, User.ROLE_MD, User.ROLE_ADMIN},
    "mr.submit": {User.ROLE_PM, User.ROLE_SUPERVISOR, User.ROLE_PROCUREMENT, User.ROLE_ADMIN},
    "mr.approve": {User.ROLE_PM, User.ROLE_PROCUREMENT, User.ROLE_MD, User.ROLE_ADMIN},
    "po.submit": {User.ROLE_PROCUREMENT, User.ROLE_PM, User.ROLE_ADMIN},
    "po.approve": {User.ROLE_PROCUREMENT, User.ROLE_MD, User.ROLE_ADMIN},
    "grn.create": {User.ROLE_PROCUREMENT, User.ROLE_SUPERVISOR, User.ROLE_PM, User.ROLE_ADMIN},
    "ipc.submit": {User.ROLE_PM, User.ROLE_FINANCE, User.ROLE_ADMIN},
    "ipc.certify": {User.ROLE_FINANCE, User.ROLE_MD, User.ROLE_ADMIN},
    "ipc.pay": {User.ROLE_FINANCE, User.ROLE_MD, User.ROLE_ADMIN},
    "documents.manage": {User.ROLE_DOC_CTRL, User.ROLE_PM, User.ROLE_MD, User.ROLE_ADMIN},
    "quality.manage": {User.ROLE_PM, User.ROLE_MD, User.ROLE_ADMIN},
    "safety.manage": {User.ROLE_PM, User.ROLE_SUPERVISOR, User.ROLE_MD, User.ROLE_ADMIN},
    "audit.read": {User.ROLE_AUDITOR, User.ROLE_MD, User.ROLE_ADMIN},
}


def has_company_wide_access(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_superuser or user.role in COMPANY_WIDE_READ_ROLES)
    )


def accessible_projects(user):
    """Projects a user can read in the application/API."""
    qs = Project.objects.all()
    if has_company_wide_access(user):
        return qs
    if not user or not user.is_authenticated:
        return qs.none()
    return qs.filter(
        Q(project_manager=user)
        | Q(site_supervisor=user)
        | Q(memberships__user=user, memberships__is_active=True)
    ).distinct()


def can_access_project(user, project):
    if not user or not user.is_authenticated or not project:
        return False
    if has_company_wide_access(user):
        return True
    return (
        project.project_manager_id == user.id
        or project.site_supervisor_id == user.id
        or project.memberships.filter(user=user, is_active=True).exists()
    )


def project_membership(user, project):
    if not user or not user.is_authenticated or not project:
        return None
    try:
        return project.memberships.get(user=user, is_active=True)
    except ProjectMembership.DoesNotExist:
        return None


def can_manage_project(user, project):
    if not user or not user.is_authenticated or not project:
        return False
    if user.is_superuser or user.role in {User.ROLE_MD, User.ROLE_ADMIN}:
        return True
    membership = project_membership(user, project)
    return (
        project.project_manager_id == user.id
        or bool(membership and (membership.can_edit or membership.role == ProjectMembership.ROLE_PM))
    )


def can_submit_dsr(user, dsr):
    if not dsr:
        return False
    membership = project_membership(user, dsr.project)
    return (
        can_manage_project(user, dsr.project)
        or dsr.project.site_supervisor_id == user.id
        or bool(membership and membership.role == ProjectMembership.ROLE_SUPERVISOR)
    )


def can_approve_dsr(user, dsr):
    if not dsr:
        return False
    membership = project_membership(user, dsr.project)
    return can_manage_project(user, dsr.project) or bool(membership and membership.can_approve)


def has_role(user, *roles):
    return bool(user and user.is_authenticated and (user.is_superuser or user.role in roles))


def can_perform_workflow(user, project, workflow_key):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    allowed_roles = WORKFLOW_ROLE_MATRIX.get(workflow_key, set())
    if user.role in allowed_roles:
        if has_company_wide_access(user) or not project:
            return True
        return can_access_project(user, project)
    membership = project_membership(user, project)
    if not membership:
        return False
    workflow_area = workflow_key.split(".", 1)[0]
    membership_area_roles = {
        "dsr": {ProjectMembership.ROLE_PM, ProjectMembership.ROLE_SUPERVISOR},
        "mr": {ProjectMembership.ROLE_PM, ProjectMembership.ROLE_PROCUREMENT},
        "po": {ProjectMembership.ROLE_PM, ProjectMembership.ROLE_PROCUREMENT},
        "grn": {ProjectMembership.ROLE_PM, ProjectMembership.ROLE_PROCUREMENT, ProjectMembership.ROLE_SUPERVISOR},
        "ipc": {ProjectMembership.ROLE_PM, ProjectMembership.ROLE_FINANCE},
        "documents": {ProjectMembership.ROLE_PM, ProjectMembership.ROLE_DOC_CTRL},
        "quality": {ProjectMembership.ROLE_PM, ProjectMembership.ROLE_QAQC},
        "safety": {ProjectMembership.ROLE_PM, ProjectMembership.ROLE_HSE, ProjectMembership.ROLE_SUPERVISOR},
    }
    if membership.role not in membership_area_roles.get(workflow_area, set()):
        return False
    if workflow_key.endswith((".approve", ".certify", ".pay")):
        return membership.can_approve
    return membership.can_edit


def can_manage_procurement(user):
    return has_role(user, User.ROLE_ADMIN, User.ROLE_MD, User.ROLE_PROCUREMENT)


def can_manage_project_procurement(user, project):
    membership = project_membership(user, project)
    return can_manage_procurement(user) or can_manage_project(user, project) or bool(
        membership and membership.role == ProjectMembership.ROLE_PROCUREMENT and membership.can_edit
    )


def can_submit_mr(user, mr):
    if not mr:
        return False
    return (
        can_manage_project_procurement(user, mr.project)
        or can_manage_project(user, mr.project)
        or mr.created_by_id == getattr(user, "id", None)
        or mr.requested_by_id == getattr(user, "id", None)
    )


def can_approve_mr(user, mr):
    if not mr:
        return False
    membership = project_membership(user, mr.project)
    return (
        can_manage_project_procurement(user, mr.project)
        or bool(membership and membership.can_approve)
    )


def can_submit_po(user, po):
    if not po:
        return False
    return (
        can_manage_project_procurement(user, po.project)
        or can_manage_project(user, po.project)
        or po.created_by_id == getattr(user, "id", None)
    )


def po_approval_threshold(user):
    if not user or not user.is_authenticated:
        return 0
    try:
        return user.profile.po_approval_threshold or 0
    except Exception:
        return 0


def financial_approval_threshold(user):
    if not user or not user.is_authenticated:
        return 0
    try:
        return user.profile.financial_approval_threshold or 0
    except Exception:
        return 0


def can_approve_financial_action(user, project, amount):
    if not project:
        return False
    if has_role(user, User.ROLE_ADMIN, User.ROLE_MD):
        return True
    if not can_manage_ipc(user, project):
        return False
    return financial_approval_threshold(user) >= (amount or 0)


def can_approve_po(user, po):
    if not po:
        return False
    if has_role(user, User.ROLE_ADMIN, User.ROLE_MD):
        return True
    membership = project_membership(user, po.project)
    if can_manage_project(user, po.project) or bool(membership and membership.can_approve):
        return True
    if can_manage_procurement(user):
        return po_approval_threshold(user) >= po.total_amount
    return po_approval_threshold(user) >= po.total_amount and can_access_project(user, po.project)


def can_create_grn(user, po):
    if not po:
        return False
    return (
        can_manage_project_procurement(user, po.project)
        or can_manage_project(user, po.project)
        or po.project.site_supervisor_id == getattr(user, "id", None)
    )


def can_manage_ipc(user, project):
    if not project:
        return False
    membership = project_membership(user, project)
    return (
        has_role(user, User.ROLE_ADMIN, User.ROLE_MD, User.ROLE_FINANCE)
        or can_manage_project(user, project)
        or bool(membership and membership.role == ProjectMembership.ROLE_FINANCE and membership.can_edit)
    )


def can_submit_ipc(user, ipc):
    return bool(ipc and can_manage_ipc(user, ipc.project))


def can_certify_ipc(user, ipc):
    return bool(ipc and has_role(user, User.ROLE_ADMIN, User.ROLE_MD, User.ROLE_FINANCE))


def can_record_payment(user, ipc):
    return bool(ipc and has_role(user, User.ROLE_ADMIN, User.ROLE_MD, User.ROLE_FINANCE))


def can_manage_documents(user, project):
    if not project:
        return False
    membership = project_membership(user, project)
    return (
        has_role(user, User.ROLE_ADMIN, User.ROLE_MD, User.ROLE_DOC_CTRL)
        or can_manage_project(user, project)
        or bool(membership and membership.role == ProjectMembership.ROLE_DOC_CTRL and membership.can_edit)
    )


def can_manage_safety(user, project):
    if not project:
        return False
    membership = project_membership(user, project)
    return (
        has_role(user, User.ROLE_ADMIN, User.ROLE_MD)
        or can_manage_project(user, project)
        or bool(membership and membership.role == ProjectMembership.ROLE_HSE and membership.can_edit)
    )


def can_manage_quality(user, project):
    if not project:
        return False
    membership = project_membership(user, project)
    return (
        has_role(user, User.ROLE_ADMIN, User.ROLE_MD)
        or can_manage_project(user, project)
        or bool(membership and membership.role == ProjectMembership.ROLE_QAQC and membership.can_edit)
    )
