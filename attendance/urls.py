from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('', views.attendance_dashboard, name='dashboard'),
    path('check-in/', views.check_in, name='check_in'),
    
    path('check-out/', views.check_out, name='check_out'),
    path('leaves/', views.leave_management, name='leave_management'),
    path('report/', views.attendance_report, name='report'),
    path('sync/', views.offline_sync, name='offline_sync'),
    path('sync/status/', views.get_sync_status, name='sync_status'),
    path('api/summary/', views.api_attendance_summary, name='api_summary'),
]