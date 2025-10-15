from rest_framework import generics, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Attachment
from .serializers import AttachmentSerializer

# Custom permission to allow only owner of attachment or higher role
class IsOwnerOrAbove(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Owners can access all
        if request.user.role.name == 'Owner':
            return True
        # Other users can only access their own uploads
        return obj.uploaded_by == request.user

class AttachmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AttachmentSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return attachments current user can access
        user = self.request.user
        if user.role.name == 'Owner':
            return Attachment.objects.all()
        return Attachment.objects.filter(uploaded_by=user)

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

class AttachmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AttachmentSerializer
    queryset = Attachment.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAbove]
