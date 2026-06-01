from user.utils import has_permission


# CRM module permission aliases
_CRM_ALIASES = ['CRM']
_DASHBOARD_ALIASES = ['CRM Dashboard']
_LEAD_ALIASES = ['CRM Lead', 'CRM Leads', 'Leads']
_OPPORTUNITY_ALIASES = ['CRM Opportunity', 'CRM Opportunities', 'Opportunities']
_UPDATE_ALIASES = ['CRM Update', 'Updates', 'CRM Updates']
_FOLLOWUP_ALIASES = ['CRM Follow Ups', 'CRM FollowUps', 'Follow Ups', 'FollowUps']
_PRESALES_ALIASES = ['CRM Presale', 'CRM Presales', 'Pre-sales', 'Pre Sales']
_LOSTREASON_ALIASES = ['CRM Lost reason', 'CRM Lost Reason', 'CRM LostReason', 'Lost reason', 'LostReason', 'LostReasons']


def _any_alias_has_perm(user, aliases, perm='View'):
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    if getattr(user, 'is_superuser', False):
        return True

    for name in aliases:
        try:
            if has_permission(user, name, perm):
                return True
        except Exception:
            continue
    return False


def check_crm_access(user, perm='View'):
    return _any_alias_has_perm(user, _CRM_ALIASES, perm=perm)


def check_dashboard_access(user, perm='View'):
    """Return True only when user has explicit CRM Dashboard permission.

    Dashboard visibility is controlled separately from the global
    `CRM` permission so granting submodule permissions (e.g. Leads)
    does not automatically show the dashboard.
    """
    return _any_alias_has_perm(user, _DASHBOARD_ALIASES, perm=perm)


def check_leads_access(user, perm='View'):
    # Require explicit 'CRM Leads' permission - don't fallback to parent 'CRM' permission
    return _any_alias_has_perm(user, _LEAD_ALIASES, perm=perm)


def check_opportunity_access(user, perm='View'):
    # Require explicit 'CRM Opportunities' permission - don't fallback to parent 'CRM' permission
    return _any_alias_has_perm(user, _OPPORTUNITY_ALIASES, perm=perm)


def check_update_access(user, perm='View'):
    # Require explicit 'CRM Update' permission - don't fallback to parent 'CRM' permission
    return _any_alias_has_perm(user, _UPDATE_ALIASES, perm=perm)


def check_followup_access(user, perm='View'):
    # Require explicit 'CRM Follow-ups' permission - don't fallback to parent 'CRM' permission
    return _any_alias_has_perm(user, _FOLLOWUP_ALIASES, perm=perm)


def check_presales_access(user, perm='View'):
    # Require explicit 'CRM Presales' permission - don't fallback to parent 'CRM' permission
    return _any_alias_has_perm(user, _PRESALES_ALIASES, perm=perm)


def check_lostreason_access(user, perm='View'):
    # Require explicit 'CRM Lost Reason' permission - don't fallback to parent 'CRM' permission
    return _any_alias_has_perm(user, _LOSTREASON_ALIASES, perm=perm)


# Convenience view helpers for templates and view checks
def can_view_opportunities(user):
    return check_opportunity_access(user, 'View')


def can_view_updates(user):
    return check_update_access(user, 'View')


def can_view_followups(user):
    return check_followup_access(user, 'View')


def can_view_presales(user):
    return check_presales_access(user, 'View')


def can_view_lostreasons(user):
    return check_lostreason_access(user, 'View')


def can_view_leads(user):
    return check_leads_access(user, 'View')


def can_create_leads(user):
    return check_leads_access(user, 'Create')


def can_edit_leads(user):
    return check_leads_access(user, 'Edit')


def can_delete_leads(user):
    return check_leads_access(user, 'Delete')


def can_create_opportunities(user):
    return check_opportunity_access(user, 'Create')


def can_edit_opportunities(user):
    return check_opportunity_access(user, 'Edit')


def can_delete_opportunities(user):
    return check_opportunity_access(user, 'Delete')


def can_create_updates(user):
    return check_update_access(user, 'Create')


def can_create_followups(user):
    return check_followup_access(user, 'Create')


def can_edit_followups(user):
    return check_followup_access(user, 'Edit')


def can_manage_lostreasons(user, perm='View'):
    return check_lostreason_access(user, perm=perm)
