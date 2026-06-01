"""
COMPLETE AUTHENTICATION BACKEND - Simplified for Deferred Database Creation
Replace your existing Lyraerp/auth_backend.py with this
"""

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User as DjangoUser
from django.db import connections
from user.models import User as CustomUser
import logging

logger = logging.getLogger(__name__)


class CustomUserBackend(BaseBackend):
    """
    Simplified authentication backend - only checks master database
    All users are synced to master during signup, so no need to check company databases
    """

    def authenticate(self, request, username=None, password=None, company_code=None, **kwargs):
        """
        Authenticate user against master database only
        """
        if not username or not password:
            return None

        try:
            if not company_code and request is not None:
                try:
                    company_code = (request.resolver_match.kwargs or {}).get('company_code')
                except Exception:
                    company_code = None
                company_code = (
                    company_code
                    or request.POST.get('company_code')
                    or request.GET.get('code')
                    or request.session.get('company_code')
                )

            qs = (
                CustomUser.objects.using('default')
                .select_related('usr_roleid__company', 'company')
            )

            # Enforce case-sensitive username lookup on MySQL.
            if connections['default'].vendor == 'mysql':
                qs = qs.extra(
                    where=["BINARY usr_name = %s"],
                    params=[username],
                )
            else:
                qs = qs.filter(usr_name=username)

            if company_code:
                scoped = qs.filter(usr_roleid__company__company_code=company_code)
                if not scoped.exists():
                    scoped = qs.filter(company__company_code=company_code)
                qs = scoped

            count = qs.count()
            if count == 0:
                return None
            if count > 1:
                logger.warning("Multiple CustomUser rows for username '%s'", username)
                if request is not None:
                    request.session['login_ambiguous'] = True
                return None
            custom_user = qs.first()

            if not check_password(password, custom_user.usr_pwd):
                return None

            django_user, _ = DjangoUser.objects.using('default').get_or_create(
                username=custom_user.usr_name,
                defaults={
                    'first_name': custom_user.usr_fname or '',
                    'last_name': '',
                    'email': custom_user.usr_mail or '',
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False,
                }
            )

            django_user.first_name = custom_user.usr_fname or ''
            django_user.email = custom_user.usr_mail or ''
            django_user.save(using='default')

            if request is not None:
                request.session['custom_user_id'] = custom_user.id
                role = getattr(custom_user, 'usr_roleid', None)
                if role and getattr(role, 'company_id', None):
                    request.session['company_id'] = role.company_id
                    if getattr(role, 'company', None) and getattr(role.company, 'company_code', None):
                        request.session['company_code'] = role.company.company_code
                elif getattr(custom_user, 'company_id', None):
                    request.session['company_id'] = custom_user.company_id
                    if getattr(custom_user, 'company', None) and getattr(custom_user.company, 'company_code', None):
                        request.session['company_code'] = custom_user.company.company_code
            return django_user

        except Exception as e:
            logger.error(f"Authentication error for '{username}': {e}", exc_info=True)
            return None

    def get_user(self, user_id):
        try:
            return DjangoUser.objects.using('default').get(pk=user_id)
        except DjangoUser.DoesNotExist:
            return None
