from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/attendance/(?P<station_id>\d+)/$', 
            consumers.AttendanceConsumer.as_asgi()),
    re_path(r'ws/cases/$', 
            consumers.CaseUpdateConsumer.as_asgi()),
]