from django import forms
from django.utils import timezone
from .models import (
    Occurrence, Witness, Exhibit, CaseUpdate,
    CaseTrackingAccess, PublicCaseComment, PoliceResponse
)


class OccurrenceForm(forms.ModelForm):
    """Form for creating/updating occurrences - 5W+H format"""
    
    class Meta:
        model = Occurrence
        fields = [
            # Reporter Details
            'reporter_full_name', 'reporter_sex', 'reporter_age',
            'reporter_tribe', 'reporter_occupation', 'reporter_residence',
            'reporter_contact', 'reporter_email', 'reporter_national_id',
            # Case Details (5W+H)
            'what_happened', 'when_happened', 'where_happened',
            'who_involved', 'why_happened', 'how_happened',
            # Additional Info
            'crime_type', 'station', 'is_sensitive'
        ]
        widgets = {
            # Reporter Details
            'reporter_full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full names of the reporter'
            }),
            'reporter_sex': forms.Select(attrs={'class': 'form-control'}),
            'reporter_age': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '120'
            }),
            'reporter_tribe': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Muganda, Acholi, etc.'
            }),
            'reporter_occupation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Teacher, Business, etc.'
            }),
            'reporter_residence': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Full residential address'
            }),
            'reporter_contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'reporter_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email (optional)'
            }),
            'reporter_national_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'National ID number'
            }),
            
            # 5W+H
            'what_happened': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe what happened in detail...'
            }),
            'when_happened': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'where_happened': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Specific location where incident occurred'
            }),
            'who_involved': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'List all persons involved: victims, suspects, witnesses...'
            }),
            'why_happened': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Motive or reason for the incident (if known)'
            }),
            'how_happened': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'How the incident occurred, methods used, weapons involved...'
            }),
            
            # Additional
            'crime_type': forms.Select(attrs={'class': 'form-control'}),
            'station': forms.Select(attrs={'class': 'form-control'}),
            'is_sensitive': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'reporter_full_name': '1. Full Names of Reporter',
            'reporter_sex': '2. Sex',
            'reporter_age': '3. Age',
            'reporter_tribe': '4. Tribe',
            'reporter_occupation': '5. Occupation',
            'reporter_residence': '6. Residence/Address',
            'reporter_contact': '7. Contact Number',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make certain fields required but not too strict
        self.fields['reporter_email'].required = False
        self.fields['reporter_national_id'].required = False
        self.fields['why_happened'].required = False


class WitnessForm(forms.ModelForm):
    """Form for adding witnesses"""
    class Meta:
        model = Witness
        fields = [
            'full_name', 'sex', 'age', 'contact',
            'residence', 'relationship_to_case', 'statement', 'is_protected'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'residence': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'relationship_to_case': forms.TextInput(attrs={'class': 'form-control'}),
            'statement': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'is_protected': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExhibitForm(forms.ModelForm):
    """Form for adding exhibits"""
    class Meta:
        model = Exhibit
        fields = [
            'exhibit_type', 'description', 'serial_number',
            'date_collected', 'storage_location', 'chain_of_custody'
        ]
        widgets = {
            'exhibit_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'date_collected': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'storage_location': forms.TextInput(attrs={'class': 'form-control'}),
            'chain_of_custody': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CaseUpdateForm(forms.ModelForm):
    """Form for updating case status"""
    class Meta:
        model = CaseUpdate
        fields = ['new_status', 'update_text', 'action_taken', 'next_steps']
        widgets = {
            'new_status': forms.Select(attrs={'class': 'form-control'}),
            'update_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the update...'
            }),
            'action_taken': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'What action was taken?'
            }),
            'next_steps': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'What are the next steps?'
            }),
        }


class PublicCaseSearchForm(forms.Form):
    """Form for public to search their case"""
    reference_number = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g., UPF/OCC/KLA/2024/01/00001'
        })
    )
    access_code = forms.CharField(
        max_length=12,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': '8-character access code'
        })
    )