from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from core.models import Profile
from core.biometrics import FaceRecognition
from .models import Attendance, Leave
from .forms import LeaveForm


# Attendance  Dashboard

@login_required
def attendance_dashboard(request):
   
    try:
        profile = request.user.user_profile
    except Profile.DoesNotExist:
        messages.error(request, 'Profile not found')
        return redirect('core:dashboard')
    
    today = timezone.now().date()
    station = profile.current_station
    
    # Today's attendance for current officer
    today_attendance = Attendance.objects.filter(profile=profile, date=today).first()
    
    # Station statistics
    total_officers = Profile.objects.filter(current_station=station, is_active_officer=True).count()
    present_today = Attendance.objects.filter(
        station=station, date=today, status__in=['PRESENT', 'LATE', 'DUTY']
    ).count()
    
    # Recent attendance records
    recent_attendance = Attendance.objects.filter(station=station)\
        .select_related('profile', 'profile__user')\
        .order_by('-date', '-check_in_time')[:20]
    
    context = {
        'profile': profile,
        'today': today,
        'today_attendance': today_attendance,
        'total_officers': total_officers,
        'present_today': present_today,
        'recent_attendance': recent_attendance,
        'station': station,
    }
    
    return render(request, 'attendance_dashboard.html', context)


#Check in Face Recognition 
@login_required
def check_in(request):
    try:
        profile = request.user.user_profile
    except Profile.DoesNotExist:
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        face_data = request.POST.get('face_image_data')
        
        if face_data:
            from core.biometrics import FaceRecognition
            biometric = FaceRecognition()
            result = biometric.recognize_face(face_data)
            
            if result['success']:
                officer_id = result['match']['officer_id']
                matched_profile = Profile.objects.get(id=officer_id)
                
                today = timezone.now().date()
                existing = Attendance.objects.filter(profile=matched_profile, date=today).first()
                
                if existing and existing.check_in_time:
                    return JsonResponse({
                        'success': False,
                        'message': f'{matched_profile.user.get_full_name()} already checked in'
                    })
                
                Attendance.objects.create(
                    profile=matched_profile,
                    date=today,
                    check_in_time=timezone.now(),
                    status='PRESENT',
                    station=matched_profile.current_station,
                    check_in_method='FACE'
                )
                
                return JsonResponse({
                    'success': True,
                    'name': matched_profile.user.get_full_name(),
                    'redirect': reverse('attendance:dashboard')
                })
            
            return JsonResponse({'success': False, 'message': result.get('error', 'Face not recognized')})
    
    return render(request, 'check_in.html', {'today': timezone.now().date()})

#Check out

@login_required
def check_out(request):
    try:
        profile = request.user.user_profile
    except Profile.DoesNotExist:
        messages.error(request, 'Officer profile not found')
        return redirect('core:dashboard')
    
    today = timezone.now().date()
    
    try:
        attendance = Attendance.objects.get(profile=profile, date=today)
        
        if attendance.check_out_time:
            messages.warning(request, f'Already checked out at {attendance.check_out_time.strftime("%H:%M")}')
        else:
            attendance.check_out_time = timezone.now()
            attendance.save()
            messages.success(request, f'Goodbye {profile.user.get_full_name()}! Check-out successful.')
    
    except Attendance.DoesNotExist:
        messages.error(request, 'No check-in record found for today. Please check in first.')
    
    return redirect('attendance:dashboard')


#Leave mgt 
@login_required
def leave_management(request):
    """Manage leave applications"""
    if request.method == 'POST':
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.profile = request.user.user_profile
            leave.save()
            messages.success(request, 'Leave application submitted')
            return redirect('attendance:leave_management')
    else:
        form = LeaveForm()
    
    leaves = Leave.objects.filter(profile=request.user.user_profile).order_by('-start_date')
    
    return render(request, 'attendance/leave_management.html', {
        'form': form,
        'leaves': leaves,
    })

#Reports 

@login_required
def attendance_report(request):
    """Attendance report"""
    profile = request.user.user_profile
    station = profile.current_station
    records = Attendance.objects.filter(station=station)\
        .select_related('profile', 'profile__user')\
        .order_by('-date')[:100]
    
    return render(request, 'attendance/report.html', {
        'records': records,
        'station': station,
    })

#API End points

def offline_sync(request):
    return JsonResponse({'status': 'ok'})


def get_sync_status(request):
    return JsonResponse({'pending': 0})


def api_attendance_summary(request):
    return JsonResponse({'present': 0})