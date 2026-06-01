from django.db import models
from .constants import SMS_TEMPLATE_NAME_CHOICES  # use same choices for both

class SMSTemplateOption(models.Model):

    # Hard-coded template name list
    template_name = models.CharField(
        max_length=150,
        choices=SMS_TEMPLATE_NAME_CHOICES,
        default="-"
    )

    style = models.CharField(max_length=100, default="Default")
    content = models.TextField()

    is_default = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    is_hardcoded = models.BooleanField(default=False) 

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['template_name', 'style']
        unique_together = ('template_name', 'style')

    def __str__(self):
        return f"{self.template_name} — {self.style}"

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)

        # Keep only ONE default per template_name
        options = SMSTemplateOption.objects.filter(template_name=self.template_name)

        if self.is_default:
            options.exclude(id=self.id).update(is_default=False)

        elif creating and options.count() == 1:
            self.is_default = True
            super().save(update_fields=['is_default'])

        elif not options.filter(is_default=True).exists():
            first_option = options.first()
            first_option.is_default = True
            first_option.save(update_fields=['is_default'])

    def delete(self, *args, **kwargs):
        template_name = self.template_name
        was_default = self.is_default

        super().delete(*args, **kwargs)

        if was_default:
            next_opt = SMSTemplateOption.objects.filter(template_name=template_name).first()
            if next_opt:
                next_opt.is_default = True
                next_opt.save(update_fields=['is_default'])
