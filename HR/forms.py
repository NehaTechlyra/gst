from django import forms
from django.db.models import Q

from department.models import Department
from designation.models import Designations

from .models import Candidate, JobOpening, RecruitmentOffer


class JobOpeningForm(forms.ModelForm):
    class Meta:
        model = JobOpening
        fields = [
            'title',
            'department',
            'designation',
            'employment_type',
            'vacancies',
            'work_location',
            'hiring_manager',
            'salary_min',
            'salary_max',
            'required_experience_years',
            'required_skills',
            'description',
            'opening_date',
            'closing_date',
            'status',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'required_skills': forms.Textarea(attrs={'rows': 3}),
            'opening_date': forms.DateInput(attrs={'type': 'date'}),
            'closing_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(status=True).order_by('department_name')
        self.fields['designation'].queryset = Designations.objects.filter(status=True).order_by('designation_name')


class CandidateForm(forms.ModelForm):
    resume = forms.FileField(required=False)

    class Meta:
        model = Candidate
        fields = [
            'job_opening',
            'full_name',
            'email',
            'phone',
            'source',
            'current_company',
            'current_ctc',
            'expected_ctc',
            'notice_period_days',
            'total_experience_years',
            'key_skills',
        ]
        widgets = {
            'key_skills': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['job_opening'].queryset = JobOpening.objects.filter(is_active=True).exclude(status='closed').order_by('title')
        self.fields['job_opening'].empty_label = 'Select job opening'


class CandidateStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['current_status', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }


class RecruitmentOfferForm(forms.ModelForm):
    class Meta:
        model = RecruitmentOffer
        fields = [
            'candidate',
            'offered_ctc',
            'joining_date',
            'reporting_manager',
            'offer_date',
            'expiry_date',
            'email_to',
            'response_notes',
            'status',
        ]
        widgets = {
            'joining_date': forms.DateInput(attrs={'type': 'date'}),
            'offer_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'response_notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        status_filter = Q(
            is_active=True,
            current_status='selected',
        )
        candidate_filter = status_filter
        if self.instance.pk and self.instance.candidate_id:
            candidate_filter |= Q(pk=self.instance.candidate_id)
        self.fields['candidate'].queryset = Candidate.objects.filter(
            candidate_filter
        ).select_related('job_opening').order_by('full_name')
        self.fields['candidate'].empty_label = 'Select selected candidate'
