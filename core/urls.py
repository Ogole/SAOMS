from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('dashboard', views.index, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('enroll-face/<int:profile_id>/', views.enroll_face_view, name='enroll_face'),
    path('profile/', views.profile_view, name='profile'),
    path('officers/', views.officer_list, name='officer_list'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),

    
    # Management URLs
    path('manage/officers/', views.manage_officers, name='manage_officers'),
    path('manage/officers/add/', views.add_officer, name='add_officer'),
    path('manage/stations/', views.manage_stations, name='manage_stations'),
    path('manage/stations/add/', views.add_station, name='add_station'),
    path('officer-photo/<int:profile_id>/', views.officer_photo, name='officer_photo'),
    path('manage/regions/', views.manage_regions, name='manage_regions'),
    path('manage/regions/add/', views.add_region, name='add_region'),
    path('manage/districts/', views.manage_districts, name='manage_districts'),
    path('manage/districts/add/', views.add_district, name='add_district'),
   
]

