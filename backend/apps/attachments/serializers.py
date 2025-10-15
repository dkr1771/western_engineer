from rest_framework import serializers
from .models import Attachment

class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ['id', 'file_url', 'uploaded_by', 'related_table', 'related_id', 'description', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_by', 'uploaded_at']
