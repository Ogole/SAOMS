from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone 
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.conf import settings 

# Create your models here.


class User(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='core_user_groups',  
        related_query_name='core_user',
    )
    
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='core_user_permissions',  
        related_query_name='core_user',
    )
    
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = models.CharField(
        max_length=15, 
        blank=True,
        validators=[RegexValidator(
            regex=r'^\+?256\d{9}$|^0\d{9}$',
            message='Enter a valid Uganda phone number'
        )]
    )
    is_active = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_count = models.PositiveIntegerField(default=0)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['username']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"
    
    @property
    def profile(self):
        """Get user's profile if it exists"""
        try:
            return self.user_profile
        except Profile.DoesNotExist:
            return None
    
    @property
    def full_details(self):
        """Get full name with profile details"""
        if self.profile:
            return f"{self.profile.get_rank_display()} {self.get_full_name()}"
        return self.get_full_name()

class Profile(models.Model):
    RANK_CHOICES = (
        #Junior Police Officers
        ('SPC', 'Special Police Constable'),
        ('PPC', 'Probationer Police Constable '),
        ('PC', 'Police Constable '),
        ('CPL', 'Corporal'),
        ('SGT', 'Sergent'),
        ('SSGT', 'Station Sergent'),
        ('HC', 'Head Constable'),
        ('HCM', 'Head Constable Major'),

        #Senior Police Officers
        ('LAIP', 'Learner Assitant Inspector of Police'),
        ('AIP', 'Assitant Inspector of Police'),
        ('IP', 'Inspector Police'),
        ('CASP', 'Cadet Assistant Superintendent of Police'),
        ('ASP', 'Assistant Superintendent of Police'),
        ('SP', 'Superintendent of Police'),
        ('SSP', 'Senior Superintendent of Police'),
        ('ACP', 'Assistant Commissioner of police'),
        ('CP', 'Commissioner of Police'),
        ('AIGP', 'Assistant Inspector General of Police'),
        ('IGP', 'Inspector General of Police')
    )

    SENIOR_RANKS = ['LAIP', 'AIP', 'IP', 'CASP', 'ASP','SP', 'SSP',  'ACP', 'CP','AIGP', 'IGP']
    JUNIOR_RANKS = ['SPC','PPC',  'PC', 'CPL', 'SGT', 'SSGT', 'HC', 'HCM']

    ROLE_CHOICES = (
        ('admin', 'Headquarter Admin'),
        ('regional_admin', 'Regional Commander'), 
        ('district_admin', 'District Admin'),
        ('Station_admin', 'Station Commander/OC'),
        ('officer', 'Police Officer')
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_profile'
    )
    role = models.CharField(max_length=25, choices=ROLE_CHOICES, default='officer')
    rank = models.CharField(max_length=50, choices=RANK_CHOICES, blank=True, null=True)
    force_number = models.CharField(max_length=10, unique=True, blank=True, null=True, 
    validators=[RegexValidator(
        regex=r'^\d{4,6}$',
        message='Force Number must be digits only (e.g., 91765)'
    )],
    help_text='For Junior Officers (SPC-HCM): Digits only, e.g., 91765'
    )

    file_number = models.CharField(max_length=10, unique=True, blank=True, null=True,   
        validators=[RegexValidator(
            regex=r'^[A-Z]\d{4}$',
            message='File Number format: Letter + 4 digits (e.g., A0001)'
        )],
        help_text='For Senior Officers (LAIP+): First letter of surname + 4 digits, e.g., A0001'
    )

    # Track previous numbers for promoted officers
    previous_force_number = models.CharField(max_length=10, blank=True, null=True)
    is_force_number_active = models.BooleanField(default=True)
    
    date_of_birth = models.DateField(null=True, blank=True)
    date_joined_force = models.DateField(null=True, blank=True)
    nin = models.CharField(max_length=15, blank=True, null=True)

    current_station = models.ForeignKey(
        'Station', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_officers'
    )
    is_on_duty = models.BooleanField(default=False) 

    is_active_officer = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Officer Profile'
        verbose_name_plural = 'Officer Profiles'
        ordering = ['-rank', 'force_number']
        indexes = [
            models.Index(fields=['force_number']),
            models.Index(fields=['file_number']),
            models.Index(fields=['role', 'rank']),
            models.Index(fields=['current_station'])
        ]


    def __str__(self):
        number = self.get_officer_number()
        return f"{self.get_rank_display()} {self.user.get_full_name()} ({number})"
    
    def is_senior_officer(self):
        # Check if officer is senior (uses file number)
        return self.rank in self.SENIOR_RANKS
    
    def is_junior_officer(self):
        #Check if officer is junior (uses force number)
        return self.rank in self.JUNIOR_RANKS

    def is_admin(self):
        return self.role in ['admin', 'regional_admin', 'district_admin', 'station_admin']

    def has_face_enrolled(self):
        #Check if officer has face enrolled
        import os
        from django.conf import settings
        face_path = os.path.join(settings.MEDIA_ROOT, 'face_encodings', f'{self.id}.enc')
        return os.path.exists(face_path)
    
    def get_officer_number(self):
        if self.is_senior_officer():
            return self.file_number or 'No File Number'
        else:
            return self.force_number or 'No Force Number'
    
    def get_initials(self):
        if self.user.last_name:
            return self.user.last_name[0].upper()
        return 'X'
    
    def clean(self):
        if self.rank:
            if self.is_junior_officer():
                # Junior officers MUST have force number, NOT file number
                if self.file_number:
                    raise ValidationError({
                        'file_number': 'Junior officers (PC-SGT) should NOT have file numbers. Use Force Number instead.'
                    })
                if not self.force_number:
                    # Will be auto-generated in save()
                    pass
            
            elif self.is_senior_officer():
                # Senior officers MUST have file number, NOT force number
                if self.force_number:
                    raise ValidationError({
                        'force_number': 'Senior officers (SSGT+) should NOT have force numbers. Use File Number instead.'
                    })
                if not self.file_number:
                    raise ValidationError({
                        'file_number': 'Senior officers must have a file number based on their initials.'
                    })
    
    def save(self, *args, **kwargs):
        if self.rank:
            # Junior Officer - Generate Force Number (digits only)
            if self.is_junior_officer() and not self.force_number:
                last = Profile.objects.filter(
                    rank__in=self.JUNIOR_RANKS,
                    force_number__isnull=False
                ).exclude(force_number='').order_by('-force_number').first()
                
                if last and last.force_number and last.force_number.isdigit():
                    new_num = int(last.force_number) + 1
                else:
                    new_num = 1
                self.force_number = str(new_num)
            
            # Senior Officer - Generate File Number (Letter + digits)
            elif self.is_senior_officer() and not self.file_number:
                # Get first letter of surname
                surname_initial = self.user.last_name[0].upper() if self.user.last_name else 'X'
                
                # Find last number with same letter
                last = Profile.objects.filter(
                    rank__in=self.SENIOR_RANKS,
                    file_number__startswith=surname_initial
                ).order_by('-file_number').first()
                
                if last and last.file_number:
                    last_num = int(last.file_number[1:])
                    new_num = last_num + 1
                else:
                    new_num = 1
                
                self.file_number = f"{surname_initial}{new_num:04d}"
        
        # If officer was promoted (rank changed to senior), hide force number
        if self.pk:
            old = Profile.objects.filter(pk=self.pk).first()
            if old and old.is_junior_officer() and self.is_senior_officer():
                self.previous_force_number = old.force_number
                self.force_number = None
                self.is_force_number_active = False
        
        super().save(*args, **kwargs)
    
    def get_officer_details(self):
        return {
            'name': self.user.get_full_name(),
            'rank': self.get_rank_display(),
            'number_type': 'File Number' if self.is_senior_officer() else 'Force Number',
            'number': self.get_officer_number(),
            'station': str(self.current_station) if self.current_station else 'Unassigned',
        }

class Region(models.Model):
    name = models.CharField(max_length=150)
    regional_commander = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='commanded_region', limit_choices_to={'role':'admin'})
    headquarters_location = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=13, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Region'
        verbose_name_plural = 'Regions'
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"

    def totoal_officers(self):
        return Profile.objects.filter(
            current_station__district__region=self, is_active_officer=True
        ).count()

    def total_stations(self):
        return Station.objects.filter(district__region=self, is_active=True).count()

    def total_cases(self):
        from occurrence.models import Occurrence 
        return Occurrence.objects.filter(station__district__region=self).count()

class District(models.Model):
    name = models.CharField(max_length=150)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='districts')
    district_commander = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='commanded_district', limit_choices_to={'role': 'district_admin'})
    headquarters = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=13, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'District'
        verbose_name_plural = 'Districts'
        ordering = ['region__name', 'name']
        unique_together = ['region', 'name']
        indexes = [
            models.Index(fields=['region', 'name']),

        ]
    
    def __str__(self):
        return f"{self.name} - {self.region.name}"
    
    def total_stations(self):
        return self.stations.filter(is_active=True).count()

    def total_officers(self):
        return Profile.objects.filter(
            current_station__district=self,
            is_active_officer=True
        ).count()

class Station(models.Model):
    STATION_TYPE = (
        ('headquarters', 'Police Headquarters'),
        ('division', 'Division Police Station'),
        ('station', 'Police Station'),
        ('post', 'Police Post'),
        ('detach', 'Detach'),
    )
    name = models.CharField(max_length=250)
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='stations')
    station_type = models.CharField(max_length=20, choices=STATION_TYPE, default='station')
    station_commander = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name='commanded_station', limit_choices_to={'role__in': ['station_admin', 'admin']})
    location = models.CharField(max_length=255, blank=True)
    physical_address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    capacity = models.PositiveIntegerField(default=12)
    is_active = models.BooleanField(default=True)
    is_24_hours = models.BooleanField(default=True)
    has_detention = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Police Station'
        verbose_name_plural = 'Police Stations'
        ordering = ['district__name', 'name']
        indexes = [
            models.Index(fields=['district', 'is_active']),
        ]
    
 
    
    def current_officer_count(self):
        return self.assigned_officers.filter(is_active_officer=True).count()
    
    def is_over_capacity(self):
        return self.current_officer_count() > self.capacity
    
    def today_attendance_count(self):
        from attendance.models import Attendance
        return Attendance.objects.filter(station=self, date=timezone.now().date(), status='PRESENT').count()