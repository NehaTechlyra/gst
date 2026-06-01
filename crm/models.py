from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Max


class LostReason(models.Model):
    """Dynamic lost reasons that can be added by admin"""
    reason = models.CharField(max_length=200, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['reason']
    
    def __str__(self):
        return self.reason


class Lead(models.Model):
    """Lead Stage - Starting point of CRM"""
    
    PRIORITY_CHOICES = [
        ('Hot', 'Hot'),
        ('Warm', 'Warm'),
        ('Cold', 'Cold'),
    ]
    
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Interested', 'Interested'),
        ('Not Interested', 'Not Interested'),
        ('Lost', 'Lost'),
    ]
    
    SOURCE_CHOICES = [
        ('Call', 'Call'),
        ('Walk-in', 'Walk-in'),
        ('Website', 'Website'),
        ('Social Media', 'Social Media'),
        ('Referral', 'Referral'),
        ('Other', 'Other'),
    ]
    lead_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    customer_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    product_interested = models.CharField(max_length=200)
    additional_info = models.TextField(blank=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='Call')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_leads')
    # HR Employee assignment (preferred display/selection in CRM)
    assigned_employee = models.ForeignKey('HR.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads_employee')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Warm')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    lost_reason = models.ForeignKey(LostReason, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.customer_name
    
    def save(self, *args, **kwargs):
        if not self.lead_number:
            max_lead_number = Lead.objects.aggregate(
                max_num=Max('lead_number')
            )['max_num']

            if max_lead_number:
                # Extract the integer part after "LEAD"
                number = int(max_lead_number.replace('LEAD', '')) + 1
            else:
                number = 1

            self.lead_number = f"LEAD{number:05d}"  # zero-padded 5 digits: LEAD00001

        super().save(*args, **kwargs)


class Opportunity(models.Model):
    """Pre-Sales / Opportunity Stage"""
    
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Discussion', 'Discussion'),
        ('Quotation Created', 'Quotation Created'),
        ('Closed Won', 'Closed Won'),
        ('Closed Lost', 'Closed Lost'),
    ]
    opportunity_number = models.CharField(max_length=20, unique=True, blank=True, null=True)
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='opportunities')
    estimated_deal_value = models.DecimalField(max_digits=12, decimal_places=2)
    products_quantities = models.TextField(help_text="Products and quantities")
    expected_closing_date = models.DateField()
    negotiation_notes = models.TextField(blank=True)
    competitor_info = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    priority = models.CharField(max_length=10, choices=Lead.PRIORITY_CHOICES, default='Warm')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_opportunities')
    assigned_employee = models.ForeignKey('HR.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_opportunities_employee')
    lost_reason = models.ForeignKey(LostReason, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.lead.customer_name} - {self.estimated_deal_value}"
    
    def save(self, *args, **kwargs):
        if not self.opportunity_number:
            max_number = Opportunity.objects.aggregate(
                max_num=Max('opportunity_number')
            )['max_num']
            
            if max_number:
                # Extract numeric part after "OP-"
                number = int(max_number.replace('OP-', '')) + 1
            else:
                number = 1
            
            self.opportunity_number = f"OP-{number:05d}"  # e.g., OP-00001
        
        super().save(*args, **kwargs)


# Quotation models were removed here to use the Sales module's quotation implementation.
# Update and FollowUp keep a reference to the Sales quotation model via an app-model string
# to avoid tight coupling and migrations in this app.


class Update(models.Model):
    """Communication Log / Updates"""
    
    TYPE_CHOICES = [
        ('Call', 'Call'),
        ('WhatsApp', 'WhatsApp'),
        ('Email', 'Email'),
        ('Meeting', 'Meeting'),
        ('Internal Note', 'Internal Note'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='updates', null=True, blank=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='updates', null=True, blank=True)
    quotation = models.ForeignKey('sales.SalesQuotation', on_delete=models.CASCADE, related_name='updates', null=True, blank=True)
    update_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField()
    attachment = models.FileField(upload_to='updates/', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.update_type} - {self.created_at}"


class FollowUp(models.Model):
    """Follow-up System"""
    
    REMINDER_INTERVAL_CHOICES = [
        ('15min', '15 minutes'),
        ('1hour', '1 hour'),
        ('1day', '1 day'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups', null=True, blank=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='followups', null=True, blank=True)
    quotation = models.ForeignKey('sales.SalesQuotation', on_delete=models.CASCADE, related_name='followups', null=True, blank=True)
    description = models.TextField()
    followup_date = models.DateTimeField()
    reminder_interval = models.CharField(max_length=10, choices=REMINDER_INTERVAL_CHOICES, default='1day')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_followups')
    assigned_employee = models.ForeignKey('HR.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='followups_employee')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['followup_date']
    
    def __str__(self):
        return f"Follow-up: {self.description[:50]} - {self.followup_date}"




class PreSalesInteraction(models.Model):
    TYPE_CHOICES = [
        ('meeting', 'Meeting'),
        ('email', 'Email'),
        ('call', 'Call'),
        ('other', 'Other'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='presales', null=True, blank=True)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='presales', null=True, blank=True)
    customer_name = models.CharField(max_length=255)
    product = models.CharField(max_length=255)
    contact = models.CharField(max_length=255)  # phone/email/other
    description = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    assigned_employee = models.ForeignKey('HR.Employee', on_delete=models.SET_NULL, blank=True, null=True, related_name='presales_employee')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PreSales: {self.customer_name} ({self.type})"
