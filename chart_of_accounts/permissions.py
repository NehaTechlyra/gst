from user.utils import has_permission

# Aliases used in RolePermission.module names
_CHART_ALIASES = ['Accounts Chart of Accounts', 'Chart of Accounts']
_JOURNAL_ALIASES = ['Accounts Journal', 'Journal']
_BALANCE_SHEET_ALIASES = ['Reports Balance Sheet']
_PROFIT_LOSS_ALIASES = ['Reports Profit and Loss']
_TRIAL_BALANCE_ALIASES = ['Reports Trial Balance']
_CASH_FLOW_ALIASES = ['Reports Cash Flow']


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


# Chart of accounts helpers
def can_view_chart(user):
    return _any_alias_has_perm(user, _CHART_ALIASES, 'View')


def can_create_chart(user):
    return _any_alias_has_perm(user, _CHART_ALIASES, 'Create')


def can_edit_chart(user):
    return _any_alias_has_perm(user, _CHART_ALIASES, 'Edit')


def can_delete_chart(user):
    return _any_alias_has_perm(user, _CHART_ALIASES, 'Delete')


# Journal helpers
def can_view_journal(user):
    return _any_alias_has_perm(user, _JOURNAL_ALIASES, 'View')


def can_create_journal(user):
    return _any_alias_has_perm(user, _JOURNAL_ALIASES, 'Create')


def can_edit_journal(user):
    return _any_alias_has_perm(user, _JOURNAL_ALIASES, 'Edit')


def can_delete_journal(user):
    return _any_alias_has_perm(user, _JOURNAL_ALIASES, 'Delete')


# Balance Sheet Report helpers
def can_view_balance_sheet(user):
    return _any_alias_has_perm(user, _BALANCE_SHEET_ALIASES, 'View')


def can_create_balance_sheet(user):
    return _any_alias_has_perm(user, _BALANCE_SHEET_ALIASES, 'Create')


def can_edit_balance_sheet(user):
    return _any_alias_has_perm(user, _BALANCE_SHEET_ALIASES, 'Edit')


def can_delete_balance_sheet(user):
    return _any_alias_has_perm(user, _BALANCE_SHEET_ALIASES, 'Delete')


# Profit & Loss Report helpers
def can_view_profit_loss(user):
    return _any_alias_has_perm(user, _PROFIT_LOSS_ALIASES, 'View')


def can_create_profit_loss(user):
    return _any_alias_has_perm(user, _PROFIT_LOSS_ALIASES, 'Create')


def can_edit_profit_loss(user):
    return _any_alias_has_perm(user, _PROFIT_LOSS_ALIASES, 'Edit')


def can_delete_profit_loss(user):
    return _any_alias_has_perm(user, _PROFIT_LOSS_ALIASES, 'Delete')


# Trial Balance Report helpers
def can_view_trial_balance(user):
    return _any_alias_has_perm(user, _TRIAL_BALANCE_ALIASES, 'View')


def can_create_trial_balance(user):
    return _any_alias_has_perm(user, _TRIAL_BALANCE_ALIASES, 'Create')


def can_edit_trial_balance(user):
    return _any_alias_has_perm(user, _TRIAL_BALANCE_ALIASES, 'Edit')


def can_delete_trial_balance(user):
    return _any_alias_has_perm(user, _TRIAL_BALANCE_ALIASES, 'Delete')


# Cash Flow Report helpers
def can_view_cash_flow(user):
    return _any_alias_has_perm(user, _CASH_FLOW_ALIASES, 'View')


def can_create_cash_flow(user):
    return _any_alias_has_perm(user, _CASH_FLOW_ALIASES, 'Create')


def can_edit_cash_flow(user):
    return _any_alias_has_perm(user, _CASH_FLOW_ALIASES, 'Edit')


def can_delete_cash_flow(user):
    return _any_alias_has_perm(user, _CASH_FLOW_ALIASES, 'Delete')
