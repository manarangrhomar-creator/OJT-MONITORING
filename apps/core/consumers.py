import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache

from apps.core.models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_message(self, event):
        await self.send(text_data=json.dumps({
            'type': event['type'],
            'count': event['count'],
            'notification': event.get('notification'),
        }))

    async def get_unread_count(self):
        cache_key = f'unread_count_{self.user.id}'
        count = await sync_to_async(cache.get)(cache_key)
        if count is None:
            count = await Notification.objects.filter(recipient=self.user, is_read=False).acount()
            await sync_to_async(cache.set)(cache_key, count, 30)
        return count


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            return

        self.group_name = 'dashboard_updates'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def dashboard_refresh(self, event):
        message = {
            'type': 'dashboard_refresh',
            'section': event.get('section', ''),
        }
        if 'data' in event:
            message['data'] = event['data']
        await self.send(text_data=json.dumps(message))
