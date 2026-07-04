from django import forms
from django.utils import timezone
from .models import Attendance, Leave, DutyRoster


class AttendanceForm(forms.ModelForm):
    """Manual attendance form"""
    class Meta:
        model = Attendance
        fields = ['profile', 'station', 'date', 'status', 'remarks']
        widgets = {
            'profile': forms.Select(attrs={'class': 'form-control select2'}),
            'station': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class BiometricAttendanceForm(forms.Form):
    """Form for biometric check-in/out"""
    ATTENDANCE_TYPE = (
        ('CHECK_IN', 'Check In'),
        ('CHECK_OUT', 'Check Out'),
    )
    
    attendance_type = forms.ChoiceField(
        choices=ATTENDANCE_TYPE,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    biometric_method = forms.ChoiceField(
        choices=[('FACE', 'Face Recognition'), ('FINGERPRINT', 'Fingerprint')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    biometric_data = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    face_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'accept': 'image/*', 'capture': 'environment'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('biometric_method')
        
        if method == 'FACE' and not cleaned_data.get('face_image'):
            raise forms.ValidationError('Face image is required for face recognition')
        elif method == 'FINGERPRINT' and not cleaned_data.get('biometric_data'):
            raise forms.ValidationError('Fingerprint data is required')
        
        return cleaned_data


class BulkAttendanceForm(forms.Form):
    """Bulk attendance for multiple officers"""
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    station = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    officers = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    default_status = forms.ChoiceField(
        choices=Attendance.STATUS_CHOICES,
        initial='PRESENT',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from core.models import Station, Profile
        self.fields['station'].choices = [('', '---')] + [
            (s.id, s.name) for s in Station.objects.filter(is_active=True)
        ]


class LeaveForm(forms.ModelForm):
    """Leave application form"""
    class Meta:
        model = Leave
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'leave_type': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class DutyRosterForm(forms.ModelForm):
    """Duty roster form"""
    class Meta:
        model = DutyRoster
        fields = ['profile', 'station', 'shift', 'date', 'duty_description']
        widgets = {
            'profile': forms.Select(attrs={'class': 'form-control select2'}),
            'station': forms.Select(attrs={'class': 'form-control'}),
            'shift': forms.Select(attrs={'class': 'form-control'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'duty_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }