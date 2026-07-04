from django import forms
from django.core.validators import RegexValidator
import json


class BiometricRegistrationForm(forms.Form):
  
    # Complete biometric registration form
    # Supports both face recognition and fingerprint capture
    
    
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
        required=False,
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
        """Validate fingerprint template format"""
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