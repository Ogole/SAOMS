from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import RegexValidator
from .models import User, Profile, Region, District, Station
from django.core.validators import RegexValidator
import json


class UserLoginForm(AuthenticationForm):
    #Custom login form
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Force/File Number or Username',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Password'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'password']


class UserRegistrationForm(UserCreationForm):
    #User registration form
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        validators=[RegexValidator(
            regex=r'^\+?256\d{9}$|^0\d{9}$',
            message='Enter valid Uganda phone number'
        )],
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ProfileForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    date_joined_force = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    class Meta:
        model = Profile
        fields = [
            'role', 'rank', 'force_number', 'badge_number',
            'biometric_id', 'date_of_birth', 'date_joined_force',
            'national_id', 'current_station'
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'rank': forms.Select(attrs={'class': 'form-control'}),
            'force_number': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'badge_number': forms.TextInput(attrs={'class': 'form-control'}),
            'biometric_id': forms.TextInput(attrs={'class': 'form-control'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control'}),
            'current_station': forms.Select(attrs={'class': 'form-control'}),
        }


class StationForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = [
            'name', 'station_code', 'district', 'station_type',
            'location', 'physical_address', 'contact_number', 'email',
            'capacity', 'is_24_hours', 'has_detention'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'station_code': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.Select(attrs={'class': 'form-control'}),
            'station_type': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'physical_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
        }




class BiometricRegistrationForm(forms.Form):    
    BIOMETRIC_METHODS = (
        ('FACE', 'Face Recognition'),
        ('FINGERPRINT', 'Fingerprint'),
        ('BOTH', 'Both Face & Fingerprint'),
    )
    
    FINGERPRINT_DEVICES = (
        ('USB', 'USB Fingerprint Scanner'),
        ('BLUETOOTH', 'Bluetooth Scanner'),
        ('BUILTIN', 'Built-in Device Scanner'),
        ('MOBILE', 'Mobile Fingerprint Sensor'),
    )
    
    # Officer identification
    officer_id = forms.IntegerField(widget=forms.HiddenInput())
    
    # Biometric method selection
    biometric_method = forms.ChoiceField(
        choices=BIOMETRIC_METHODS,
        initial='BOTH',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    # Face recognition fields
    face_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': 'image/*',
            'capture': 'environment',
            'class': 'form-control',
            'id': 'faceImageInput'
        }),
        help_text='Capture using webcam or upload a clear face photo'
    )
    
    # OR use base64 encoded image from webcam
    face_image_data = forms.CharField(
        required=True,
        widget=forms.HiddenInput(attrs={'id': 'faceImageData'}),
        help_text='Base64 encoded image from webcam'
    )
    
    # Fingerprint fields
    fingerprint_device = forms.ChoiceField(
        choices=FINGERPRINT_DEVICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'fingerprintDevice'
        })
    )
    
    fingerprint_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'fingerprintData'}),
        help_text='Fingerprint template from scanner (populated by JavaScript)'
    )
    
    # Multiple fingerprints (some systems require multiple fingers)
    fingerprint_thumb = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'fingerprintThumb'})
    )
    fingerprint_index = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'fingerprintIndex'})
    )
    
    # Fingerprint quality metrics
    fingerprint_quality = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'fingerprintQuality'}),
        help_text='Quality score from scanner (0-100)'
    )
    
    # Scanner information for audit
    scanner_serial = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.HiddenInput(attrs={'id': 'scannerSerial'})
    )
    
    # Registration metadata
    registration_location = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.HiddenInput(attrs={'id': 'registrationLocation'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('biometric_method')
        
        # Validate based on selected method
        if method in ['FACE', 'BOTH']:
            if not cleaned_data.get('face_image') and not cleaned_data.get('face_image_data'):
                raise forms.ValidationError(
                    'Face image is required for face recognition registration'
                )
        
        if method in ['FINGERPRINT', 'BOTH']:
            if not cleaned_data.get('fingerprint_data') and not cleaned_data.get('fingerprint_thumb'):
                raise forms.ValidationError(
                    'At least one fingerprint is required for fingerprint registration'
                )
            
            # Validate fingerprint quality
            quality = cleaned_data.get('fingerprint_quality')
            if quality and quality < 50:
                raise forms.ValidationError(
                    f'Fingerprint quality too low ({quality}%). Please scan again.'
                )
        
        return cleaned_data
    
    def clean_fingerprint_data(self):
        #Validate fingerprint template format
        data = self.cleaned_data.get('fingerprint_data')
        if data:
            try:
                # Check if it's valid base64
                import base64
                base64.b64decode(data)
                
                # Check template size (typical fingerprint templates are 256-2048 bytes)
                decoded = base64.b64decode(data)
                if len(decoded) < 100:
                    raise forms.ValidationError(
                        'Fingerprint template too small. Please scan again.'
                    )
                if len(decoded) > 10000:
                    raise forms.ValidationError(
                        'Fingerprint template too large. Invalid data.'
                    )
            except Exception:
                raise forms.ValidationError('Invalid fingerprint data format')
        return data