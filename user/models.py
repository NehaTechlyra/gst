from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User as DjangoUser  # Assuming you want to reference Django's auth User model
from django.utils import timezone
from django.conf import settings
from company.models import Company

#remove the below if roles is seted
class RightsDtl(models.Model):
    rightdtl_id = models.AutoField(primary_key=True)
    rightdtl_name = models.CharField(max_length=45)
    rightdtl_acc = models.BooleanField()
    rightdtl_inv = models.BooleanField()
    rightdtl_pos = models.BooleanField()
    rightdtl_pur = models.BooleanField()
    rightdtl_hrm = models.BooleanField()
    rightdtl_sys = models.BooleanField()

    def __str__(self):
        return self.rightdtl_name

class User(models.Model):
    usr_name = models.CharField(max_length=45)
    usr_pwd = models.CharField(max_length=128)
    usr_fname = models.CharField(max_length=45,blank=True, null=True)
    usr_mail = models.CharField(max_length=45)
    usr_phn = models.CharField(max_length=15)
    usr_rmrks = models.CharField(max_length=45, blank=True, null=True)
    usr_roleid = models.ForeignKey(
        'user.Role',  # string reference to avoid circular import
        on_delete=models.SET_NULL,
        null=True,
        db_column='usr_roleid',
        verbose_name='User Role'
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='master_users',
        db_column='company_id',
        verbose_name='Company'
    )
    is_admin = models.BooleanField(default=False)
    # Tracking fields
    crtd_by = models.ForeignKey(
        DjangoUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        verbose_name='Created By'
    )
    crtd_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    updt_by = models.ForeignKey(
        DjangoUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_users',
        verbose_name='Updated By'
    )
    updt_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )

    def __str__(self):
        return f"{self.usr_name} ({self.company.name if self.company else 'NoCompany'})"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['usr_name', 'company'],
                name='unique_username_per_company',
            ),
            models.UniqueConstraint(
                fields=['usr_mail', 'company'],
                name='unique_email_per_company',
            ),
        ]

    def clean(self):
        # Enforce only one admin per company at model-validation time
        if self.is_admin and self.company:
            using = getattr(self, '_state', None) and getattr(self._state, 'db', None) or 'default'
            qs = User.objects.using(using).filter(company=self.company, is_admin=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError('An admin already exists for this company.')

    def save(self, *args, **kwargs):
        # Run clean to check admin uniqueness before saving
        self.clean()
        super().save(*args, **kwargs)
    

class Module(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
class PermissionType(models.Model):
    name = models.CharField(max_length=50, unique=True)  # e.g. 'Full Access', 'View', etc.

    def __str__(self):
        return self.name
class Role(models.Model):
    role_name = models.CharField(max_length=150)
    description = models.TextField(blank=True, max_length=500)
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        db_column='company_id',
        verbose_name='Company'
    )
    
    # Tracking fields
    crtd_at = models.DateTimeField(
        default=timezone.now,  # Use default instead of auto_now_add
        verbose_name='Created At',
        db_column='crtd_at'
    )
    crtd_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='userRole_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who created this user role",
        db_column='crtd_by'
    )
    updt_at = models.DateTimeField(
        default=timezone.now,  # Use default for existing rows
        verbose_name='Updated At',
        db_column='updt_at'
    )
    updt_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='userRole_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text="User who last updated this role",
        db_column='updt_by'
    )
    # These fields are already in the database
    # We'll handle them properly in the migration

    class Meta:
        # Ensure role_name is unique per company
        constraints = [
            models.UniqueConstraint(
                fields=['role_name', 'company'],
                name='unique_role_per_company'
            ),
        ]

    def __str__(self):
        return self.role_name
        
class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    permission_type = models.ForeignKey(PermissionType, on_delete=models.CASCADE)
    allowed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('role', 'module', 'permission_type')

    def __str__(self):
        return f"{self.role} - {self.module} - {self.permission_type}: {'Yes' if self.allowed else 'No'}"
