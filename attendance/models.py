from django.db import models
from django.utils import timezone 
from django.conf import settings
from core.models import *
# Create your models here.



class Attendance(models.Model):
    STATUS_CHOICES = (
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('DUTY', 'On Duty Outpost'),
        ('LEAVE', 'On Leave'),
        ('SICK', 'Sick Leave'),
        ('SUSPENDED', 'Suspended'),
    )
    
    profile = models.ForeignKey('core.Profile', on_delete=models.CASCADE, related_name='attendances')
    station = models.ForeignKey('core.Station', on_delete=models.SET_NULL, null=True, related_name='attendances' )
    date = models.DateField(default=timezone.now)
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PRESENT')
    check_in_method = models.CharField(max_length=20, choices=[('BIOMETRIC', 'Biometric'), ('MANUAL', 'Manual'), ('MOBILE', 'Mobile App')], default='MANUAL')
    check_in_location = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    verified_by = models.ForeignKey('core.Profile', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_attendances')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-date', '-check_in_time']
        unique_together = ['profile', 'date']  
        indexes = [
            models.Index(fields=['profile', 'date']),
            models.Index(fields=['station', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['check_in_time']),
        ]
    
    def __str__(self):
        return f"{self.profile.user.get_full_name()} - {self.date} - {self.status}"
    
    def save(self, *args, **kwargs):
        # Auto-set station from profile if not set
        if not self.station_id:
            self.station = self.profile.current_station
        
        # Auto-detect late status
        if self.check_in_time and self.status == 'PRESENT':
            expected_time = timezone.datetime.combine(
                self.date,
                timezone.datetime.strptime('08:00', '%H:%M').time()
            )
            expected_time = timezone.make_aware(expected_time)
            if self.check_in_time > expected_time:
                self.status = 'LATE'
        
        super().save(*args, **kwargs)
    
    @property
    def hours_worked(self):
        #Calculate hours worked
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            return round(delta.total_seconds() / 3600, 2)
        return None
    
    @property
    def is_early(self):
        #Check if arrived before 8 AM
        if self.check_in_time:
            return self.check_in_time.hour < 8
        return False
    
    @property
    def is_overtime(self):
        #Check if worked more than 8 hours
        if self.hours_worked:
            return self.hours_worked > 8
        return False

class Leave(models.Model):
    LEAVE_TYPES = (
        ('ANNUAL', 'Annual Leave'),
        ('SICK', 'Sick Leave'),
        ('MATERNITY', 'Maternity Leave'),
        ('PATERNITY', 'Paternity Leave'),
        ('Passleave', 'Pass Leave'),
        ('STUDY', 'Study Leave'),
        ('AWOL', 'AWOL'),
        ('OTHER', 'Other'),
    )
    
    STATUS = (
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    )
    
    profile = models.ForeignKey('core.Profile', on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS, default='PENDING')
    approved_by = models.ForeignKey('core.Profile', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Leave Record'
        verbose_name_plural = 'Leave Records'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['profile', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.profile.user.get_full_name()} - {self.leave_type} ({self.start_date} to {self.end_date})"
    
    @property
    def duration(self):
        delta = self.end_date - self.start_date
        return delta.days + 1
    
    def save(self, *args, **kwargs):
        # Auto_create attendance records for leave days
        if self.status == 'APPROVED':
            from datetime import timedelta
            current_date = self.start_date
            while current_date <= self.end_date:
                Attendance.objects.update_or_create(
                    profile=self.profile,
                    date=current_date,
                    defaults={'status': 'LEAVE', 'remarks': f'{self.get_leave_type_display()}'}
                )
                current_date += timedelta(days=1)
        super().save(*args, **kwargs)


class DutyRoster(models.Model):
    SHIFT_CHOICES = (
        ('NIGHT', 'Night Shift (18:00-06:00)'),
        ('DAY', 'Day Duty (06:00-18:00)'),
        ('SPECIAL', 'Special Duty'),
    )
    
    profile = models.ForeignKey('core.Profile', on_delete=models.CASCADE, related_name='duty_rosters')
    station = models.ForeignKey('core.Station', on_delete=models.CASCADE, related_name='duty_rosters')
    shift = models.CharField(max_length=20, choices=SHIFT_CHOICES)
    date = models.DateField()
    duty_description = models.TextField(blank=True)
    created_by = models.ForeignKey('core.Profile', on_delete=models.SET_NULL, null=True, related_name='created_rosters')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Duty Roster'
        verbose_name_plural = 'Duty Rosters'
        ordering = ['-date', 'shift']
        unique_together = ['profile', 'date', 'shift']
        indexes = [
            models.Index(fields=['station', 'date']),
            models.Index(fields=['profile', 'date']),
        ]
    
    def __str__(self):
        return f"{self.profile.user.get_full_name()} - {self.get_shift_display()} on {self.date}"