from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification
from .utils import send_unread_count_update


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        notifications = Notification.objects.filter(recipient=request.user)
        data = [{
            'id': str(n.id),
            'title': n.title,
            'message': n.message,
            'type': n.type,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat(),
            'related_object_id': str(n.related_object_id) if n.related_object_id else None,
            'related_object_type': n.related_object_type,
        } for n in notifications]
        return Response(data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'count': count})

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        try:
            notification = Notification.objects.get(id=pk, recipient=request.user)
            notification.is_read = True
            notification.save()
            send_unread_count_update(request.user)
            return Response({'message': 'Notification marked as read'})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        send_unread_count_update(request.user)
        return Response({'message': 'All notifications marked as read'})
