from django.contrib import admin
from django.utils.html import format_html
from .models import Attachment

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'file_link',  # clickable link
        'uploaded_by', 
        'related_table', 
        'related_id', 
        'description', 
        'uploaded_at'
    )

    search_fields = (
        'related_table', 
        'description', 
        'uploaded_by__email', 
        'uploaded_by__username'
    )

    list_filter = (
        'related_table', 
        'uploaded_by', 
        'uploaded_at'
    )

    readonly_fields = ('uploaded_at',)
    ordering = ('-uploaded_at',)

    def file_link(self, obj):
        if obj.file_url:
            return format_html('<a href="{}" target="_blank">Open</a>', obj.file_url)
        return "-"
    file_link.short_description = "File"

