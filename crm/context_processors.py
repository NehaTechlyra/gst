from .permissions import (
    can_view_leads, can_view_opportunities, can_view_presales,
    can_view_lostreasons, can_view_followups, check_crm_access,
    can_create_leads, can_edit_leads, can_delete_leads,
    can_create_opportunities, can_edit_opportunities, can_delete_opportunities,
    can_manage_lostreasons, check_presales_access, can_create_updates, can_create_followups, can_edit_followups
)


def crm_permissions(request):
    """Context processor to expose CRM permission flags to templates."""
    if not request.user or not request.user.is_authenticated:
        return {
            'can_view_crm': False,
            'can_view_crm_leads': False,
            'can_create_crm_leads': False,
            'can_edit_crm_leads': False,
            'can_delete_crm_leads': False,
            'can_view_crm_opportunities': False,
            'can_create_crm_opportunities': False,
            'can_edit_crm_opportunities': False,
            'can_delete_crm_opportunities': False,
            'can_view_crm_presales': False,
            'can_create_crm_presales': False,
            'can_edit_crm_presales': False,
            'can_delete_crm_presales': False,
            'can_view_crm_lostreasons': False,
            'can_manage_crm_lostreasons': False,
            'can_edit_crm_lostreasons': False,
            'can_delete_crm_lostreasons': False,
            'can_view_crm_followups': False,
            'can_create_crm_followups': False,
            'can_edit_crm_followups': False,
        }

    return {
        'can_view_crm': check_crm_access(request.user, 'View'),
        'can_view_crm_leads': can_view_leads(request.user),
        'can_create_crm_leads': can_create_leads(request.user),
        'can_edit_crm_leads': can_edit_leads(request.user),
        'can_delete_crm_leads': can_delete_leads(request.user),
        'can_view_crm_opportunities': can_view_opportunities(request.user),
        'can_create_crm_opportunities': can_create_opportunities(request.user),
        'can_edit_crm_opportunities': can_edit_opportunities(request.user),
        'can_delete_crm_opportunities': can_delete_opportunities(request.user),
        'can_view_crm_presales': can_view_presales(request.user),
        'can_create_crm_presales': check_presales_access(request.user, 'Create'),
        'can_edit_crm_presales': check_presales_access(request.user, 'Edit'),
        'can_delete_crm_presales': check_presales_access(request.user, 'Delete'),
        'can_view_crm_lostreasons': can_view_lostreasons(request.user),
        'can_manage_crm_lostreasons': can_manage_lostreasons(request.user, 'Create'),
        'can_edit_crm_lostreasons': can_manage_lostreasons(request.user, 'Edit'),
        'can_delete_crm_lostreasons': can_manage_lostreasons(request.user, 'Delete'),
        'can_view_crm_followups': can_view_followups(request.user),
        'can_create_crm_followups': can_create_followups(request.user),
        'can_edit_crm_followups': can_edit_followups(request.user),
    }
