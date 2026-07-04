from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages 
from django.utils import timezone
from .models import *
from occurrence.models import Occurrence
from attendance.models import Attendance
from django.http import HttpResponse
import pickle
import os
import base64
from django.conf import settings
from cryptography.fernet import Fernet


# Create your views here.

def index(request):
    try:
        profile = request.user.user_profile
    except Profile.DoesNotExist:
        return render(request, 'dashboard.html')
    
    station = profile.current_station
    
    if station:
        total_officers = Profile.objects.filter(
            current_station=station, 
            is_active_officer=True
        ).count()
        
        today_attendance = Attendance.objects.filter(
            station=station,
            date=timezone.now().date(),
            status__in=['PRESENT', 'LATE']
        ).count()
        
        total_cases = Occurrence.objects.filter(station=station).count()
        open_cases = Occurrence.objects.filter(station=station, case_status='OPEN').count()
        investigating = Occurrence.objects.filter(station=station, case_status='INVESTIGATING').count()
        
        recent_cases = Occurrence.objects.filter(station=station).order_by('-date_reported')[:5]
    else:
        total_officers = 0
        today_attendance = 0
        total_cases = 0
        open_cases = 0
        investigating = 0
        recent_cases = []
    
    context = {
        'profile': profile,
        'total_officers': total_officers,
        'today_attendance': today_attendance,
        'total_cases': total_cases,
        'open_cases': open_cases,
        'investigating': investigating,
        'recent_cases': recent_cases,
        'station': station,
    }
    
    return render(request, 'dashboard.html', context)

def login_view(request):
    if request.user.is_authenticated:
        try:
            profile = request.user.user_profile
            if profile.role != 'officer':
                return redirect('core:admin_dashboard')
            return redirect('core:dashboard')
        except Profile.DoesNotExist:
            return redirect('core:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome, {user.get_full_name()}!')
            
            try:
                profile = user.user_profile
                if profile.role != 'officer':
                    return redirect('core:admin_dashboard')
                return redirect('core:dashboard')
            except Profile.DoesNotExist:
                return redirect('core:dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Logged out successfully')
    return redirect('core:login')


@login_required
def admin_dashboard(request):
    #Custom admin dashboard based on user role
    try:
        profile = request.user.user_profile
    except Profile.DoesNotExist:
        messages.error(request, 'Profile not found')
        return redirect('core:dashboard')
    
    role = profile.role
    station = profile.current_station
    today = timezone.now().date()
    
    context = {
        'profile': profile,
        'role': role,
        'today': today,
    }
    
    if role == 'admin':
        # Headquarters Admin
        context.update({
            'total_regions': Region.objects.filter(is_active=True).count(),
            'total_districts': District.objects.filter(is_active=True).count(),
            'total_stations': Station.objects.filter(is_active=True).count(),
            'total_officers': Profile.objects.filter(is_active_officer=True).count(),
            'total_cases': Occurrence.objects.count(),
            'open_cases': Occurrence.objects.filter(case_status='OPEN').count(),
            'today_attendance': Attendance.objects.filter(date=today, status='PRESENT').count(),
            'recent_cases': Occurrence.objects.order_by('-date_reported')[:10],
            'regions': Region.objects.filter(is_active=True),
        })
        template = 'hq_dashboard.html'
    
    elif role == 'regional_admin':
        # Regional Commander
        region = station.district.region if station else None
        context.update({
            'region': region,
            'total_districts': District.objects.filter(region=region, is_active=True).count() if region else 0,
            'total_stations': Station.objects.filter(district__region=region, is_active=True).count() if region else 0,
            'total_officers': Profile.objects.filter(current_station__district__region=region, is_active_officer=True).count() if region else 0,
            'total_cases': Occurrence.objects.filter(station__district__region=region).count() if region else 0,
            'open_cases': Occurrence.objects.filter(station__district__region=region, case_status='OPEN').count() if region else 0,
            'today_attendance': Attendance.objects.filter(station__district__region=region, date=today, status='PRESENT').count() if region else 0,
            'recent_cases': Occurrence.objects.filter(station__district__region=region).order_by('-date_reported')[:10] if region else [],
            'districts': District.objects.filter(region=region, is_active=True) if region else [],
        })
        template = 'regional_dashboard.html'
    
    elif role == 'district_admin':
        # District Commander
        district = station.district if station else None
        context.update({
            'district': district,
            'total_stations': Station.objects.filter(district=district, is_active=True).count() if district else 0,
            'total_officers': Profile.objects.filter(current_station__district=district, is_active_officer=True).count() if district else 0,
            'total_cases': Occurrence.objects.filter(station__district=district).count() if district else 0,
            'open_cases': Occurrence.objects.filter(station__district=district, case_status='OPEN').count() if district else 0,
            'today_attendance': Attendance.objects.filter(station__district=district, date=today, status='PRESENT').count() if district else 0,
            'recent_cases': Occurrence.objects.filter(station__district=district).order_by('-date_reported')[:10] if district else [],
            'stations': Station.objects.filter(district=district, is_active=True) if district else [],
        })
        template = 'district_dashboard.html'
    
    elif role == 'station_admin':
        # Station Commander
        context.update({
            'station': station,
            'total_officers': Profile.objects.filter(current_station=station, is_active_officer=True).count() if station else 0,
            'total_cases': Occurrence.objects.filter(station=station).count() if station else 0,
            'open_cases': Occurrence.objects.filter(station=station, case_status='OPEN').count() if station else 0,
            'closed_cases': Occurrence.objects.filter(station=station, case_status='CLOSED').count() if station else 0,
            'today_present': Attendance.objects.filter(station=station, date=today, status__in=['PRESENT', 'LATE']).count() if station else 0,
            'recent_cases': Occurrence.objects.filter(station=station).order_by('-date_reported')[:10] if station else [],
            'today_attendance_list': Attendance.objects.filter(station=station, date=today).select_related('profile__user') if station else [],
        })
        template = 'station_dashboard.html'
    
    else:
        return redirect('core:dashboard')
    
    return render(request, template, context)

@login_required
def profile_view(request):
    try:
        profile = request.user.user_profile
    except Profile.DoesNotExist:
        messages.error(request, 'Profile not found')
        return redirect('core:dashboard')
    
    return render(request, 'profile.html', {
        'profile': profile,
    })


@login_required
def manage_officers(request):
    profile = request.user.user_profile
    if profile.role == 'officer':
        messages.error(request, 'Access denied')
        return redirect('core:dashboard')
    
    # Filter officers based on admin level
    if profile.role == 'admin':
        officers = Profile.objects.all()
    elif profile.role == 'regional_admin':
        officers = Profile.objects.filter(current_station__district__region=profile.current_station.district.region)
    elif profile.role == 'district_admin':
        officers = Profile.objects.filter(current_station__district=profile.current_station.district)
    else:
        officers = Profile.objects.filter(current_station=profile.current_station)
    
    officers = officers.select_related('user', 'current_station').order_by('rank')
    
    return render(request, 'officers.html', {
        'officers': officers,
        'profile': profile,
        'stations': Station.objects.filter(is_active=True),
        'ranks': Profile.RANK_CHOICES,
        'roles': Profile.ROLE_CHOICES,
    })

@login_required
def add_officer(request):
    if request.user.user_profile.role == 'officer':
        messages.error(request, 'Access denied')
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username').strip()
        first_name = request.POST.get('first_name').strip()
        last_name = request.POST.get('last_name').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password')
        rank = request.POST.get('rank')
        role = request.POST.get('role')
        station_id = request.POST.get('station')
        face_data = request.POST.get('face_image_data', '')
        
        if not email:
            email = f"{username}@upf.go.ug"
        
        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists')
            return redirect('core:manage_officers')
        
        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )
        user.set_password(password)
        user.save()
        
        station = Station.objects.get(id=station_id) if station_id else None
        profile = Profile.objects.create(
            user=user,
            rank=rank,
            role=role,
            current_station=station
        )
        
        # Optional face enrollment
        if face_data:
            from core.biometrics import FaceRecognition
            biometric = FaceRecognition()
            result = biometric.register_face(profile.id, face_data)
            if result['success']:
                messages.success(request, f'Officer {user.get_full_name()} added with face enrolled!')
            else:
                messages.warning(request, f'Officer added but face enrollment failed: {result["error"]}')
        else:
            messages.success(request, f'Officer {user.get_full_name()} added successfully!')
        
        return redirect('core:manage_officers')
    
    return redirect('core:manage_officers')

@login_required
def manage_regions(request):
    profile = request.user.user_profile
    if profile.role not in ['admin']:
        messages.error(request, 'Only HQ Admin can manage regions')
        return redirect('core:admin_dashboard')
    
    regions = Region.objects.filter(is_active=True)
    return render(request, 'regions.html', {
        'regions': regions,
        'profile': profile,
    })


@login_required
def add_region(request):
    if request.user.user_profile.role not in ['admin']:
        messages.error(request, 'Access denied')
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        Region.objects.create(
            name=request.POST.get('name'),
            headquarters_location=request.POST.get('headquarters', ''),
            contact_number=request.POST.get('contact', ''),
        )
        messages.success(request, 'Region added successfully')
    return redirect('core:manage_regions')


@login_required
def manage_districts(request):
    profile = request.user.user_profile
    if profile.role == 'admin':
        districts = District.objects.filter(is_active=True)
    elif profile.role == 'regional_admin':
        region = profile.current_station.district.region if profile.current_station else None
        districts = District.objects.filter(region=region, is_active=True) if region else []
    else:
        messages.error(request, 'Access denied')
        return redirect('core:admin_dashboard')
    
    return render(request, 'districts.html', {
        'districts': districts,
        'regions': Region.objects.filter(is_active=True),
        'profile': profile,
    })


@login_required
def add_district(request):
    if request.user.user_profile.role not in ['admin', 'regional_admin']:
        messages.error(request, 'Access denied')
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        region = Region.objects.get(id=request.POST.get('region'))
        District.objects.create(
            name=request.POST.get('name'),
            region=region,
            headquarters=request.POST.get('headquarters', ''),
            contact_number=request.POST.get('contact', ''),
        )
        messages.success(request, 'District added successfully')
    return redirect('core:manage_districts')

@login_required
def manage_stations(request):
    profile = request.user.user_profile
    if profile.role == 'officer':
        messages.error(request, 'Access denied')
        return redirect('core:dashboard')
    
    if profile.role == 'admin':
        stations = Station.objects.all()
    elif profile.role == 'regional_admin':
        stations = Station.objects.filter(district__region=profile.current_station.district.region)
    elif profile.role == 'district_admin':
        stations = Station.objects.filter(district=profile.current_station.district)
    else:
        stations = Station.objects.filter(id=profile.current_station.id)
    
    stations = stations.select_related('district', 'district__region', 'station_commander__user')
    
    return render(request, 'stations.html', {
        'stations': stations,
        'profile': profile,
        'districts': District.objects.filter(is_active=True),
        'station_types': Station.STATION_TYPE,
    })


@login_required
def add_station(request):
    if request.user.user_profile.role not in ['admin', 'regional_admin', 'district_admin']:
        messages.error(request, 'Access denied')
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        Station.objects.create(
            name=request.POST.get('name'),
            district_id=request.POST.get('district'),
            station_type=request.POST.get('station_type', 'station'),
            location=request.POST.get('location', ''),
            contact_number=request.POST.get('contact_number', ''),
            capacity=request.POST.get('capacity', 50),
            is_24_hours=request.POST.get('is_24_hours') == 'on',
        )
        messages.success(request, 'Station added successfully')
    
    return redirect('core:manage_stations')


@login_required
def enroll_face_view(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    
    if request.method == 'POST':
        face_data = request.POST.get('face_image_data')
        if face_data:
            from core.biometrics import FaceRecognition
            biometric = FaceRecognition()
            result = biometric.register_face(profile.id, face_data)
            
            if result['success']:
                messages.success(request, f'Face enrolled for {profile.user.get_full_name()}')
            else:
                messages.error(request, f'Failed: {result["error"]}')
            return redirect('core:manage_officers')
    
    return render(request, 'enroll_face.html', {'profile': profile})

@login_required
def officer_photo(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    
    key_file = os.path.join(settings.MEDIA_ROOT, 'face_encodings', '.key')
    face_path = os.path.join(settings.MEDIA_ROOT, 'face_encodings', f'{profile_id}.enc')
    
    if not os.path.exists(key_file) or not os.path.exists(face_path):
        return HttpResponse(status=404)
    
    try:
        with open(key_file, 'rb') as f:
            key = f.read()
        cipher = Fernet(key)
        
        with open(face_path, 'rb') as f:
            encrypted = f.read()
        
        decrypted = cipher.decrypt(encrypted)
        data = pickle.loads(decrypted)
        
        if 'face_image' in data:
            img_bytes = base64.b64decode(data['face_image'])
            return HttpResponse(img_bytes, content_type='image/jpeg')
        
        return HttpResponse(status=404)
    except Exception:
        return HttpResponse(status=404)

def officer_list(request):
    return render(request, 'officer_list.html')

