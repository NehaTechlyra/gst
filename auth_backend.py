from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User as DjangoUser  # Django's default User model
from django.db import connection
from user.models import User as CustomUser  # Your custom User model

class CustomUserBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            # Get user from your custom User model by username
            user_qs = CustomUser.objects.filter(usr_name=username)
            if connection.vendor == 'mysql':
                user_qs = user_qs.extra(
                    where=["BINARY usr_name = %s"],
                    params=[username],
                )
            custom_user = user_qs.get()
            
            # Verify the hashed password using Django's check_password
            if check_password(password, custom_user.usr_pwd):
                # Get or create a corresponding Django user object (for session management)
                django_user, created = DjangoUser.objects.get_or_create(username=username)
                
                # Optionally update DjangoUser fields
                django_user.first_name = custom_user.usr_fname
                django_user.email = custom_user.usr_mail
                # Mark staff if this custom user is company admin and persist hashed password
                try:
                    django_user.first_name = custom_user.usr_fname
                    django_user.email = custom_user.usr_mail
                    django_user.is_staff = getattr(custom_user, 'is_admin', False)
                    # If custom_user.usr_pwd stores a Django-compatible hashed password,
                    # copy it into the auth_user.password field so the auth_user row has the hash.
                    if getattr(custom_user, 'usr_pwd', None):
                        django_user.password = custom_user.usr_pwd
                    django_user.save()
                except Exception:
                    # Fallback: attempt save even if assignment failed
                    try:
                        django_user.save()
                    except Exception:
                        pass

                # Attach simple custom data and set session company information
                django_user.custom_user_data = {
                    'usr_roleid': custom_user.usr_roleid,
                    'custom_user_id': custom_user.pk,
                }
                if request is not None:
                    try:
                        if getattr(custom_user, 'company', None):
                            request.session['company_id'] = custom_user.company_id
                            request.session['company_db'] = custom_user.company.db_name
                        # Save custom_user_id for reliable lookups in views
                        request.session['custom_user_id'] = custom_user.pk
                    except Exception:
                        pass

                return django_user
        except CustomUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return DjangoUser.objects.get(pk=user_id)
        except DjangoUser.DoesNotExist:
            return None
