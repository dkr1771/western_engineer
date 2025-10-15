from django.urls import path
from .views import AttachmentListCreateView, AttachmentDetailView

urlpatterns = [
    path('attachments/', AttachmentListCreateView.as_view(), name='attachments_list_create'),
    path('attachments/<int:pk>/', AttachmentDetailView.as_view(), name='attachment_detail'),
]
