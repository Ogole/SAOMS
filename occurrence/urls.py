# occurrence/urls.py
from django.urls import path
from . import views

app_name = 'occurrence'

urlpatterns = [
    path('case_dashboard', views.case_dashboard, name='dashboard'),

    # Case CRUD
    path('list/', views.occurrence_list, name='list'),
    path('create/', views.create_occurrence, name='create'),
   
    

    # Case Actions
    path('<path:reference>/status/', views.update_case_status, name='update_status'),
    path('<path:reference>/witness/', views.add_witness, name='add_witness'),
    path('<path:reference>/exhibit/', views.add_exhibit, name='add_exhibit'),
    path('<path:reference>/delete/', views.delete_occurrence, name='delete'),
    path('<path:reference>/', views.occurrence_detail, name='detail'),

    
    # path('<str:reference>/update/', views.update_occurrence, name='update'),
    # path('track/', views.public_tracking, name='public_tracking'),
    # path('track/<int:tracking_id>/', views.public_case_view, name='public_case_view'),
    # path('track/<int:tracking_id>/comment/', views.public_add_comment, name='public_add_comment'),
    # path('statistics/', views.case_statistics, name='statistics'),
]


