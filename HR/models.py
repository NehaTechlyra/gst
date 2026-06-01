from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from department.models import Department
from designation.models import Designations
from bank.models import Bank
from personaldocuments.models import PersonalDocumentType
from django.utils import timezone
from datetime import timedelta

class Employee(models.Model):
    # === Auto Employee Code ===
    emp_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    # === Personal Details ===
    salutation = models.CharField(max_length=20, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    dob = models.DateField(blank=True, null=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    marital_status = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    # photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True)
    photo_base64 = models.TextField(blank=True, null=True)

    # === Bank & Document Details ===
    bank_name = models.ForeignKey(Bank,on_delete=models.SET_NULL,null=True,related_name='employees')
    account_number = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    # bank_upload = models.FileField(upload_to='bank_docs/', blank=True, null=True)
    bank_upload_base64 = models.TextField(blank=True, null=True)


    # === Department Details ===
    department = models.ForeignKey(Department,on_delete=models.SET_NULL,null=True)
    designation = models.ForeignKey(Designations, on_delete=models.SET_NULL, null=True, blank=True, related_name='employees') 
    
    job_category = models.CharField(max_length=50, blank=True, null=True)
    joining_date = models.DateField(blank=True, null=True)
    confirm_date = models.DateField(blank=True, null=True)
    notice_period = models.PositiveIntegerField(blank=True, null=True)
    current_salary = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], blank=True, null=True)
    salary_mode = models.CharField(max_length=50, blank=True, null=True)

    allowances = models.ManyToManyField('allowances.Allowances', blank=True, related_name='employees')
    leaves = models.ManyToManyField('leaves.Leaves', blank=True, related_name='employees')

    # === Education Details ===
    

    # === Work Experience ===
    
    upload_resume_base64 = models.TextField(blank=True, null=True)
    upload_resume_name = models.CharField(max_length=255, blank=True, null=True)

    
    # === Meta ===
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='employee_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='employee_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    


    # === Auto-generate EMP Code ===
    def save(self, *args, **kwargs):
        if not self.emp_code:
            last_emp = Employee.objects.all().order_by('-id').first()
            if last_emp and last_emp.emp_code:
                try:
                    last_num = int(last_emp.emp_code.replace('EMP', ''))
                except ValueError:
                    last_num = 0
            else:
                last_num = 0
            new_num = last_num + 1
            self.emp_code = f"EMP{new_num:03d}"  # EMP001, EMP002, etc.
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    


class EmployeeEducation(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='educations')
    qualification = models.CharField(max_length=100)
    board_university = models.CharField(max_length=150)
    stream = models.CharField(max_length=100, blank=True, null=True)
    year_of_joining = models.DateField(blank=True, null=True)
    year_of_passing = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.employee.first_name} - {self.qualification}"
    
class EmployeeExperience(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='experiences')
    role = models.CharField(max_length=100)
    company_name = models.CharField(max_length=150)
    ctc = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    duration_months = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.employee.first_name} - {self.role}"
    
class EmployeePersonalDocument(models.Model):
    """Link employee to a document type, number, uploaded file, and optional expiry date"""
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='personaldocuments')
    document_type = models.ForeignKey(PersonalDocumentType, on_delete=models.PROTECT)
    document_number = models.CharField(max_length=100, default='NA')
    document_file_base64 = models.TextField(blank=True, null=True)
    document_file_name = models.CharField(max_length=255, blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)  # <-- Add this

    def __str__(self):
        return f"{self.employee.first_name} - {self.document_type.name}"




REMINDER_INTERVAL_DAYS = 10
class HRNotification(models.Model):
    document = models.ForeignKey('EmployeePersonalDocument', on_delete=models.CASCADE)
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.CASCADE,
        related_name='hr_notifications',
        null=True,
        blank=True
    )

    method_email = models.BooleanField(default=False)
    method_sms = models.BooleanField(default=False)

    last_sent_email = models.DateTimeField(null=True, blank=True)
    last_sent_sms = models.DateTimeField(null=True, blank=True)

    email_content = models.TextField(null=True, blank=True)
    sms_content = models.TextField(null=True, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        doc_name = getattr(self.document.document_type, "name", "Document")
        return f"Reminder for {self.document.employee.first_name} - {doc_name}"

    # ----------- Reset Logic ------------ #

    def should_reset_method(self, method):
        now = timezone.now().date()

        if method == "email":
            base_date = (self.last_sent_email or self.created_at).date()
        elif method == "sms":
            base_date = (self.last_sent_sms or self.created_at).date()
        else:
            return False

        return (now - base_date).days >= REMINDER_INTERVAL_DAYS

    def reset_method_if_due(self, method):
        """
        Reset email or SMS method if reminder interval passed.
        """
        updated = False
        now = timezone.now()

        if method == "email" and self.should_reset_method("email"):
            self.method_email = False
            self.last_sent_email = None
            self.email_content = None
            updated = True

        if method == "sms" and self.should_reset_method("sms"):
            self.method_sms = False
            self.last_sent_sms = None
            self.sms_content = None
            updated = True

        if updated:
            self.is_read = False
            self.created_at = now
            self.save(update_fields=[
                "method_email",
                "method_sms",
                "last_sent_email",
                "last_sent_sms",
                "email_content",
                "sms_content",
                "is_read",
                "created_at",
            ])


class JobOpening(models.Model):
    EMPLOYMENT_TYPE_CHOICES = [
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('on_hold', 'On Hold'),
        ('closed', 'Closed'),
    ]

    title = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='job_openings')
    designation = models.ForeignKey(Designations, on_delete=models.SET_NULL, null=True, blank=True, related_name='job_openings')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='permanent')
    vacancies = models.PositiveIntegerField(default=1)
    work_location = models.CharField(max_length=150, blank=True, null=True)
    hiring_manager = models.CharField(max_length=150, blank=True, null=True)
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    required_experience_years = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, validators=[MinValueValidator(0)])
    required_skills = models.TextField(blank=True, null=True)
    description = models.TextField()
    opening_date = models.DateField(default=timezone.now)
    closing_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='job_openings_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='job_openings_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Candidate(models.Model):
    SOURCE_CHOICES = [
        ('referral', 'Referral'),
        ('website', 'Website'),
        ('linkedin', 'LinkedIn'),
        ('indeed', 'Indeed'),
        ('consultant', 'Consultant'),
        ('walk_in', 'Walk-in'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('screening', 'Screening'),
        ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('interviewed', 'Interviewed'),
        ('selected', 'Selected'),
        ('offer_sent', 'Offer Sent'),
        ('offer_accepted', 'Offer Accepted'),
        ('offer_declined', 'Offer Declined'),
        ('offer_cancelled', 'Offer Cancelled'),
        ('joined', 'Joined'),
        ('rejected', 'Rejected'),
        ('hold', 'Hold'),
    ]

    job_opening = models.ForeignKey(JobOpening, on_delete=models.CASCADE, related_name='candidates')
    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='website')
    current_company = models.CharField(max_length=150, blank=True, null=True)
    current_ctc = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    expected_ctc = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    notice_period_days = models.PositiveIntegerField(blank=True, null=True)
    total_experience_years = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True, validators=[MinValueValidator(0)])
    key_skills = models.TextField(blank=True, null=True)
    resume_base64 = models.TextField(blank=True, null=True)
    resume_name = models.CharField(max_length=255, blank=True, null=True)
    recruiter_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='recruitment_candidates',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    employee = models.ForeignKey(
        'Employee',
        related_name='source_candidates',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    remarks = models.TextField(blank=True, null=True)
    current_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='applied')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='candidates_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='candidates_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.job_opening.title}"


class CandidateStatusHistory(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=30, blank=True, null=True)
    new_status = models.CharField(max_length=30, choices=Candidate.STATUS_CHOICES)
    remarks = models.TextField(blank=True, null=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='candidate_status_changes',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.candidate.full_name}: {self.old_status or 'new'} -> {self.new_status}"


class RecruitmentOffer(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
    ]

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='offers')
    job_opening = models.ForeignKey(JobOpening, on_delete=models.CASCADE, related_name='offers')
    offered_ctc = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])
    joining_date = models.DateField(blank=True, null=True)
    reporting_manager = models.CharField(max_length=150, blank=True, null=True)
    offer_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(blank=True, null=True)
    email_to = models.EmailField(blank=True, null=True)
    response_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    sent_at = models.DateTimeField(blank=True, null=True)
    responded_at = models.DateTimeField(blank=True, null=True)
    converted_to_employee_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='recruitment_offers_created',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='recruitment_offers_updated',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Offer for {self.candidate.full_name}"

    def save(self, *args, **kwargs):
        if self.candidate_id:
            self.job_opening = self.candidate.job_opening
            if not self.email_to:
                self.email_to = self.candidate.email
            if not self.reporting_manager:
                self.reporting_manager = self.job_opening.hiring_manager
        super().save(*args, **kwargs)



