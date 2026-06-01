from django.contrib import admin

from HR.models import Candidate, CandidateStatusHistory, Employee, JobOpening, RecruitmentOffer


@admin.register(JobOpening)
class JobOpeningAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'employment_type', 'vacancies', 'status', 'created_at')
    list_filter = ('status', 'employment_type', 'department')
    search_fields = ('title', 'work_location', 'hiring_manager')


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'job_opening', 'source', 'current_status', 'employee', 'created_at')
    list_filter = ('current_status', 'source', 'job_opening')
    search_fields = ('full_name', 'email', 'phone')


@admin.register(CandidateStatusHistory)
class CandidateStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'old_status', 'new_status', 'changed_by', 'changed_at')
    list_filter = ('new_status', 'changed_at')
    search_fields = ('candidate__full_name', 'remarks')


@admin.register(RecruitmentOffer)
class RecruitmentOfferAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'job_opening', 'offered_ctc', 'joining_date', 'status', 'sent_at', 'converted_to_employee_at')
    list_filter = ('status', 'job_opening')
    search_fields = ('candidate__full_name', 'candidate__email', 'job_opening__title')


admin.site.register(Employee)
