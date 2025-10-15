from django.db import models

from django.db import models
from django.conf import settings

class Attachment(models.Model):
    file_url = models.FileField(upload_to='attachments/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    related_table = models.CharField(max_length=100, blank=True, null=True)
    related_id = models.PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.file_url} uploaded by {self.uploaded_by}"

