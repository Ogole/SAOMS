from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Occurrence, Witness, Exhibit, CaseUpdate, CaseTrackingAccess
from core.models import Profile
import secrets
import string


@login_required
def case_dashboard(request):
    #Main case management dashboard
    try:
        profile = request.user.user_profile
    except Profile.DoesNotExist:
        messages.error(request, 'Profile not found')
        return redirect('core:dashboard')
    
    # Get cases based on user role
    if profile.role in ['admin', 'district_admin']:
        cases = Occurrence.objects.all()
    elif profile.role == 'station_admin':
        cases = Occurrence.objects.filter(station=profile.current_station)
    else:
        cases = Occurrence.objects.filter(reporting_officer=profile)
    
    # Statistics
    total_cases = cases.count()
    open_cases = cases.filter(case_status='OPEN').count()
    investigating = cases.filter(case_status='INVESTIGATING').count()
    closed_cases = cases.filter(case_status='CLOSED').count()
    
    # Recent cases
    recent_cases = cases.order_by('-date_reported')[:10]
    
    # Cases by type
    case_types = cases.values('crime_type').annotate(count=Count('id')).order_by('-count')[:5]
    
    context = {
        'total_cases': total_cases,
        'open_cases': open_cases,
        'investigating': investigating,
        'closed_cases': closed_cases,
        'recent_cases': recent_cases,
        'case_types': case_types,
        'profile': profile,
    }
    
    return render(request, 'occurrence_dashboard.html', context)

@login_required
def create_occurrence(request):
    try:
        profile = request.user.user_profile
    except Profile.DoesNotExist:
        messages.error(request, 'Profile not found')
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        # Get datetime value
        when = request.POST.get('when_happened', '')
        when_dt = timezone.now() if not when else when
        
        occurrence = Occurrence(
            reporter_full_name=request.POST.get('reporter_full_name', ''),
            reporter_sex=request.POST.get('reporter_sex', ''),
            reporter_age=request.POST.get('reporter_age', 0),
            reporter_tribe=request.POST.get('reporter_tribe', ''),
            reporter_occupation=request.POST.get('reporter_occupation', ''),
            reporter_residence=request.POST.get('reporter_residence', ''),
            reporter_contact=request.POST.get('reporter_contact', ''),
            
            what_happened=request.POST.get('what_happened', ''),
            when_it_happened=when_dt,
            where_it_happened=request.POST.get('where_happened', ''),
            who_was_involved=request.POST.get('who_involved', ''),
            why_it_happened=request.POST.get('why_happened', ''),
            how_it_happened=request.POST.get('how_happened', ''),
            
            crime_type=request.POST.get('crime_type', 'OTHER'),
            investigating_officer=request.POST.get(),
            reporting_officer=profile,
            station=profile.current_station,
            date_reported=timezone.now()
        )
        occurrence.save()
        
        tracking = CaseTrackingAccess.objects.create(
            occurrence=occurrence,
            reporter_phone=occurrence.reporter_contact
        )
        
        messages.success(request, f'Case {occurrence.reference_number} created! Citizen Access Code: {tracking.access_code}')
        return redirect('occurrence:detail', reference=occurrence.reference_number)
    
    return render(request, 'create_occurrence.html', {
        'crime_types': Occurrence.CRIME_TYPE,
        'profile': profile,
    })

@login_required
def occurrence_list(request):
    #List all cases with filters
    try:
        profile = request.user.user_profile
    except Profile.DoesNotExist:
        return redirect('core:dashboard')
    
    # Filter cases based on role
    if profile.role in ['admin', 'district_admin']:
        cases = Occurrence.objects.all()
    elif profile.role == 'station_admin':
        cases = Occurrence.objects.filter(station=profile.current_station)
    else:
        cases = Occurrence.objects.filter(reporting_officer=profile)
    
    # Search filters
    search = request.GET.get('search', '')
    status = request.GET.get('status', '')
    crime_type = request.GET.get('crime_type', '')
    
    if search:
        cases = cases.filter(
            Q(reference_number__icontains=search) |
            Q(reporter_full_name__icontains=search) |
            Q(what_happened__icontains=search)
        )
    
    if status:
        cases = cases.filter(case_status=status)
    
    if crime_type:
        cases = cases.filter(crime_type=crime_type)
    
    # Pagination
    paginator = Paginator(cases, 20)
    page = request.GET.get('page', 1)
    cases = paginator.get_page(page)
    
    context = {
        'cases': cases,
        'search': search,
        'status_filter': status,
        'crime_type_filter': crime_type,
        'status_choices': Occurrence.CASE_STATUS,
        'crime_types': Occurrence.CRIME_TYPE,
        'profile': profile,
    }
    
    return render(request, 'list.html', context)


@login_required
def occurrence_detail(request, reference):
    #View case details
    occurrence = get_object_or_404(Occurrence, reference_number=reference)
    witnesses = occurrence.witnesses.all()
    exhibits = occurrence.exhibits.all()
    updates = occurrence.updates.all()
    
    context = {
        'occurrence': occurrence,
        'witnesses': witnesses,
        'exhibits': exhibits,
        'updates': updates,
    }
    
    return render(request, 'detail.html', context)

@login_required
def delete_occurrence(request, reference):
    if request.user.user_profile.role not in ['admin', 'station_admin']:
        messages.error(request, 'Unauthorized')
        return redirect('occurrence:list')
    
    occurrence = get_object_or_404(Occurrence, reference_number=reference)
    occurrence.delete()
    messages.success(request, 'Case deleted successfully')
    return redirect('occurrence:list')


@login_required
def update_case_status(request, reference):
    #Update case status
    occurrence = get_object_or_404(Occurrence, reference_number=reference)
    
    if request.method == 'POST':
        previous_status = occurrence.case_status
        new_status = request.POST.get('new_status')
        update_text = request.POST.get('update_text')
        
        # Create case update record
        CaseUpdate.objects.create(
            occurrence=occurrence,
            updated_by=request.user.user_profile,
            previous_status=previous_status,
            new_status=new_status,
            update_text=update_text
        )
        
        # Update occurrence status
        occurrence.case_status = new_status
        occurrence.save()
        
        messages.success(request, f'Case {reference} updated to {occurrence.get_case_status_display()}')
    
    return redirect('occurrence:detail', reference=reference)


@login_required
def add_witness(request, reference):
    #Add witness to case
    occurrence = get_object_or_404(Occurrence, reference_number=reference)
    
    if request.method == 'POST':
        Witness.objects.create(
            occurrence=occurrence,
            full_name=request.POST.get('full_name'),
            sex=request.POST.get('sex'),
            age=request.POST.get('age'),
            contact=request.POST.get('contact'),
            residence=request.POST.get('residence'),
            relationship_to_case=request.POST.get('relationship_to_case'),
            statement=request.POST.get('statement'),
            recorded_by=request.user.user_profile
        )
        messages.success(request, 'Witness added successfully')
    
    return redirect('occurrence:detail', reference=reference)


@login_required
def add_exhibit(request, reference):
    #Add exhibit to case
    occurrence = get_object_or_404(Occurrence, reference_number=reference)
    
    if request.method == 'POST':
        Exhibit.objects.create(
            occurrence=occurrence,
            exhibit_type=request.POST.get('exhibit_type'),
            description=request.POST.get('description'),
            date_collected=timezone.now(),
            collected_by=request.user.user_profile,
            storage_location=request.POST.get('storage_location')
        )
        messages.success(request, 'Exhibit added successfully')
    
    return redirect('occurrence:detail', reference=reference)