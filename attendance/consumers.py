import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Attendance
from core.models import Profile, Station


class AttendanceConsumer(AsyncWebsocketConsumer):
    """Real-time attendance updates"""
    
    async def connect(self):
        """Connect to WebSocket"""
        self.station_id = self.scope['url_route']['kwargs']['station_id']
        self.room_group_name = f'attendance_{self.station_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send current attendance stats
        stats = await self.get_attendance_stats()
        await self.send(text_data=json.dumps(stats))
    
    async def disconnect(self, close_code):
        """Disconnect from WebSocket"""
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        data = json.loads(text_data)
        action = data.get('action')
        
        if action == 'check_in':
            result = await self.process_check_in(data)
            await self.send(text_data=json.dumps(result))
    
    async def attendance_update(self, event):
        """Receive attendance update from group"""
        # Send update to WebSocket
        await self.send(text_data=json.dumps(event['data']))
    
    @database_sync_to_async
    def get_attendance_stats(self):
        """Get current attendance statistics"""
        from django.utils import timezone
        today = timezone.now().date()
        
        stats = Attendance.objects.filter(
            station_id=self.station_id,
            date=today
        ).values('status').count()
        
        return {
            'type': 'attendance_stats',
            'data': stats,
            'timestamp': str(timezone.now())
        }
    
    @database_sync_to_async
    def process_check_in(self, data):
        """Process check-in and broadcast update"""
        from django.utils import timezone
        
        officer_id = data.get('officer_id')
        try:
            profile = Profile.objects.get(id=officer_id)
            attendance, created = Attendance.objects.get_or_create(
                profile=profile,
                date=timezone.now().date(),
                defaults={
                    'check_in_time': timezone.now(),
                    'status': 'PRESENT',
                    'station_id': self.station_id
                }
            )
            
            return {
                'type': 'check_in_result',
                'success': True,
                'officer': profile.user.get_full_name(),
                'time': str(timezone.now()),
                'created': created
            }
        except Exception as e:
            return {'type': 'check_in_result', 'success': False, 'error': str(e)}


class CaseUpdateConsumer(AsyncWebsocketConsumer):
    """Real-time case updates"""
    
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_authenticated:
            self.room_group_name = f'case_updates_{self.user.id}'
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def case_notification(self, event):
        """Send case update notification"""
        await self.send(text_data=json.dumps({
            'type': 'case_update',
            'message': event['message'],
            'case_ref': event['case_ref'],
            'timestamp': event['timestamp']
        }))