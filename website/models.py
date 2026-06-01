from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class DashboardLayout(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard_layout')
    layout_json = models.TextField(default='{}')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Layout for {self.user}"
