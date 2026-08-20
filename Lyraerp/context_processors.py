"""
Context processors for Lyra ERP
Adds company and license information to all templates.

IMPORTANT: Context processors must ONLY return dictionaries.
           They must NEVER block requests or return HTTP responses.
           All access blocking must be done in middleware.
"""
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# Fragment-based exempt list — same as middleware.py
# ============================================================================
LICENSE_EXEMPT_FRAGMENTS = (
    'activate-license',
    'license/restricted',
    'license/',
    'trial-expired',
    'trail-expired',
    'trail_expired',
    'activity/new_logs/',
    'company/setup/',
)


def _is_license_exempt(path):
    """Return True if this path is a license/activation page that should never be blocked."""
    return any(fragment in path for fragment in LICENSE_EXEMPT_FRAGMENTS)


# ============================================================================
# Company Context Processor
# ============================================================================

def company_context(request):
    """
    Adds company information to all templates.

    Usage in templates:
    {{ company_code }} → TECH4-14HG
    {{ company_name }} → Tech4
    {{ company_id }}   → 1
    {{ company }}      → Full Company object with legal_name, name, etc.
    """
    context = {
        'company_code': None,
        'company_name': None,
        'company_id': None,
        'company': None,
        'active_company': None,
    }

    if not request.user.is_authenticated:
        return context

    # Get company code/id from request or session. Keep a dedicated
    # active_company value for shared layout chrome so page-specific contexts
    # can safely use "company" for document/print data.
    company_code = getattr(request, 'company_code', None) or request.session.get('company_code')
    company_id = getattr(request, 'company_id', None) or request.session.get('company_id')

    if company_code:
        context['company_code'] = company_code

    if company_id or company_code:
        try:
            from company.models import Company

            company = None
            if company_id:
                company = Company.objects.using('default').filter(id=company_id).first()
            if company is None and company_code:
                company = Company.objects.using('default').filter(
                    company_code=company_code
                ).first()

            if company:
                context['company_code'] = company.company_code or company_code
                context['company_name'] = company.name
                context['company_id'] = company.id
                context['company'] = company
                context['active_company'] = company

        except Exception as e:
            logger.debug(f"[CONTEXT] Error getting company details: {e}")

    return context


# ============================================================================
# License Context Processor
# ============================================================================

def license_context(request):
    """
    Adds license and trial status to all templates for UI use (e.g. banners).

    This context processor ONLY reads license info — it never blocks access.
    Access blocking is handled exclusively by LicenseCheckMiddleware.

    Template variables added:
    {{ license_info }}         → dict with license status fields
    {{ trial_active }}         → bool
    {{ trial_days_remaining }} → int or None
    {{ has_valid_license }}    → bool
    {{ license_type }}         → 'licensed' | 'trial' | 'none' | 'superuser'
    """
    # Default empty context — safe for all pages including login
    context = {
        'license_info': {},
        'trial_active': False,
        'trial_days_remaining': None,
        'has_valid_license': False,
        'license_type': 'none',
    }

    if not request.user.is_authenticated:
        return context

    # Pull from request.license_info if LicenseInfoMiddleware already loaded it
    license_info = getattr(request, 'license_info', None)

    if license_info:
        context['license_info'] = license_info
        context['trial_active'] = license_info.get('trial_active', False)
        context['trial_days_remaining'] = license_info.get('days_remaining')
        context['has_valid_license'] = license_info.get('is_valid', False)
        context['license_type'] = license_info.get('license_type', 'none')

    return context


# ============================================================================
# Trial Context Processor
# ============================================================================

def trial_context(request):
    """
    Adds trial-specific information to templates.

    Used for showing trial banners, countdown timers, etc.
    NEVER blocks access — read-only context.
    """
    context = {
        'trial_status': None,
        'trial_message': '',
        'trial_expires_at': None,
        'trial_started_at': None,
    }

    if not request.user.is_authenticated:
        return context

    # Get company info
    company_id = getattr(request, 'company_id', None) or request.session.get('company_id')

    if not company_id:
        return context

    try:
        from company.models import Company

        company = Company.objects.using('default').filter(id=company_id).first()

        if not company:
            return context

        logger.debug(f"[CONTEXT] Company trial status: {company.trial_active}")

        if not company.trial_active:
            context['trial_status'] = 'inactive'
            return context

        # Get trial summary
        try:
            from company.utils.trial_utils import get_trial_summary
            summary = get_trial_summary(company)

            context['trial_status'] = summary.get('status', 'unknown')
            context['trial_message'] = summary.get('message', '')
            context['trial_expires_at'] = company.trial_expires_at
            context['trial_started_at'] = company.trial_started_at

        except ImportError:
            context['trial_status'] = 'active' if company.trial_active else 'inactive'
        except Exception as e:
            logger.error(f"[CONTEXT] Error getting trial summary: {e}")

    except Exception as e:
        logger.error(f"[CONTEXT] Error in trial_context: {e}")

    return context


# ============================================================================
# Combined License + Trial Context Processor (convenience)
# ============================================================================

def company_license_context(request):
    """
    Combined context processor that provides all company, license, and trial info.

    Use this instead of registering company_context, license_context, and
    trial_context separately if you want a single processor.

    CRITICAL: This processor ONLY returns context dictionaries.
              It NEVER raises exceptions that block page rendering.
              It NEVER returns HTTP responses.
              Access control is EXCLUSIVELY handled by middleware.
    """
    context = {
        # Company
        'company_code': None,
        'company_name': None,
        'company_id': None,

        # License
        'license_info': {},
        'has_valid_license': False,
        'license_type': 'none',
        'license_key': '',
        'license_expiry_date': None,

        # Trial
        'trial_active': False,
        'trial_days_remaining': None,
        'trial_message': '',
        'trial_expires_at': None,
        'trial_status': None,
    }

    if not request.user.is_authenticated:
        return context

    path = request.path or ''

    # ── Company info ─────────────────────────────────────────────────────────
    company_code = getattr(request, 'company_code', None) or request.session.get('company_code')

    if company_code:
        context['company_code'] = company_code

        try:
            from company.models import Company
            company = Company.objects.using('default').filter(
                company_code=company_code
            ).first()

            if company:
                context['company_name'] = company.name
                context['company_id'] = company.id

                # ── Trial info (read-only) ────────────────────────────────────
                logger.debug(f"[CONTEXT] Company trial status: {company.trial_active}")
                context['trial_active'] = company.trial_active

                if company.trial_active:
                    try:
                        from company.utils.trial_utils import get_trial_summary
                        summary = get_trial_summary(company)
                        context['trial_days_remaining'] = summary.get('days_remaining')
                        context['trial_message'] = summary.get('message', '')
                        context['trial_status'] = summary.get('status', 'active')
                        context['trial_expires_at'] = company.trial_expires_at
                    except Exception as e:
                        logger.debug(f"[CONTEXT] Trial summary error: {e}")

        except Exception as e:
            logger.debug(f"[CONTEXT] Error getting company: {e}")

    # ── License info (from middleware if available) ───────────────────────────
    license_info = getattr(request, 'license_info', None)

    if license_info:
        context['license_info'] = license_info
        context['has_valid_license'] = license_info.get('is_valid', False)
        context['license_type'] = license_info.get('license_type', 'none')
        context['license_key'] = license_info.get('license_key', '')
        context['license_expiry_date'] = license_info.get('expiry_date')

        # Override trial info from license_info if available (more accurate)
        if 'trial_active' in license_info:
            context['trial_active'] = license_info.get('trial_active', False)
        if 'days_remaining' in license_info and license_info['days_remaining'] is not None:
            context['trial_days_remaining'] = license_info.get('days_remaining')
        if 'trial_message' in license_info:
            context['trial_message'] = license_info.get('trial_message', '')

        logger.debug(
            "[CONTEXT] License type=%s valid=%s trial=%s days=%s",
            context['license_type'],
            context['has_valid_license'],
            context['trial_active'],
            context['trial_days_remaining'],
        )
    else:
        # license_info not set by middleware (e.g. exempt paths) — safe defaults already set
        logger.debug("[CONTEXT] No license_info on request (exempt path or middleware not run)")

    return context
