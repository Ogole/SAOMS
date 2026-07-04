from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import secrets
import string
# Create your models here.

class Occurrence(models.Model):
    #Case/Occurrence 
    CASE_STATUS = (
        ('Under_Inquiry', 'Under Inquiry'),
        ('COURT', 'Submitted to Court/RSA'),
        ('OPEN', 'Open'),
        ('INVESTIGATING', 'Under Investigation'),
        ('CLOSED', 'Closed/Put away'),
    )
    
    CRIME_TYPE = (
        ('THEFT', 'Theft'),
        ('ROBBERY', 'Aggravated Robbery'),
        ('BURGLARY', 'Burglary/Breaking'),
        ('ASSAULT', 'Assault'),
        ('ASSAULT_AGG', 'Aggravated Assault'),
        ('DOMESTIC', 'Domestic Violence'),
        ('RAPE', 'Rape'),
        ('DEFILEMENT', 'Defilement'),
        ('HOMICIDE', 'Homicide/Murder'),
        ('MANSLAUGHTER', 'Manslaughter'),
        ('KIDNAP', 'Kidnapping'),
        ('FRAUD', 'Fraud'),
        ('FORGERY', 'Forgery'),
        ('DRUGS', 'Narcotics/Drugs'),
        ('TRAFFIC', 'Traffic Offense'),
        ('CYBER', 'Cyber Crime'),
        ('CORRUPTION', 'Corruption'),
        ('TERRORISM', 'Terrorism'),
        ('OTHER', 'Other Criminal Offense'),
    )
    
    # REPORTER DETAILS 
    reference_number = models.CharField(max_length=30, unique=True, editable=False, help_text='Auto-generated: UPF/OCC/STATION/YYYY/MM/XXXXX')
    reporter_full_name = models.CharField(max_length=250)
    reporter_sex = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    reporter_age = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(120)])
    reporter_tribe = models.CharField(max_length=50)
    reporter_occupation = models.CharField(max_length=150, blank=True, null=True )
    reporter_residence = models.TextField()
    reporter_contact = models.CharField(max_length=13, null=True, blank=True )
    reporter_email = models.EmailField(blank=True, null=True)
    reporter_national_id = models.CharField(max_length=20, blank=True, null=True )
    
    # CASE DETAILS 
    what_happened = models.TextField()
    when_it_happened = models.DateTimeField()
    where_it_happened = models.TextField()
    who_was_involved = models.TextField(help_text='Describe victims, suspects, and witnesses')
    why_it_happened = models.TextField(blank=True, help_text='Motive or cause if known')
    how_it_happened = models.TextField(help_text='Method, means, or weapons used')
    
    #  CASE MANAGEMENT 
    crime_type = models.CharField(max_length=50, choices=CRIME_TYPE)
    case_status = models.CharField(max_length=50, choices=CASE_STATUS, default='OPEN', verbose_name='Case Status' )
    reporting_officer = models.ForeignKey('core.Profile', on_delete=models.SET_NULL, null=True, related_name='reported_cases', verbose_name='Reporting Officer')
    investigating_officer = models.ForeignKey('core.Profile', on_delete=models.SET_NULL, null=True, blank=True, related_name='investigating_cases', verbose_name='Investigating Officer')
    station = models.ForeignKey('core.Station', on_delete=models.SET_NULL, null=True, related_name='occurrences', verbose_name='Police Station')
    crime_scene_location = models.CharField(max_length=255, blank=True, verbose_name='Crime Scene Location')
    is_sensitive = models.BooleanField(default=False, verbose_name='Sensitive Case', help_text='Involves minors, sexual offenses, or security matters' )
    date_reported = models.DateTimeField(default=timezone.now, verbose_name='Date Reported')
    date_updated = models.DateTimeField(auto_now=True)
    date_closed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Occurrence/Case'
        verbose_name_plural = 'Occurrences/Cases'
        ordering = ['-date_reported']
        indexes = [
            models.Index(fields=['reference_number']),
            models.Index(fields=['case_status']),
            models.Index(fields=['crime_type']),
            models.Index(fields=['date_reported']),
            models.Index(fields=['station', 'case_status']),
        ]
        permissions = [
            ('view_sensitive_case', 'Can view sensitive cases'),
            ('update_case_status', 'Can update case status'),
            ('assign_investigator', 'Can assign investigating officer'),
        ]
    
    def __str__(self):
        return f"{self.reference_number} - {self.get_crime_type_display()}"
    
    def save(self, *args, **kwargs):
        # Generate reference number on first save
        if not self.reference_number:
            station_code = self.station.station_code if self.station else 'GEN'
            year = timezone.now().year
            month = timezone.now().month
            count = Occurrence.objects.filter(
                station=self.station,
                date_reported__year=year,
                date_reported__month=month
            ).count() + 1
            self.reference_number = f"UPF/OCC/{station_code}/{year}/{month:02d}/{count:05d}"
        
        # Auto set date closed
        if self.case_status in ['CLOSED', 'CONVICTED', 'ACQUITTED'] and not self.date_closed:
            self.date_closed = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def case_age(self):
        #Calculate case age in days
        delta = timezone.now() - self.date_reported
        return delta.days
    
    def generate_tracking_access(self):
        #Create public tracking access
        if not hasattr(self, 'tracking_access'):
            return CaseTrackingAccess.objects.create(
                occurrence=self,
                reporter_phone=self.reporter_contact,
                reporter_email=self.reporter_email
            )
        return self.tracking_access
    
    def total_witnesses(self):
        return self.witnesses.count()
    
    def total_exhibits(self):
        return self.exhibits.count()


class Witness(models.Model):
    occurrence = models.ForeignKey( Occurrence, on_delete=models.CASCADE, related_name='witnesses')
    full_name = models.CharField(max_length=250)
    sex = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]
    )
    age = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(120)])
    contact = models.CharField(max_length=13)
    residence = models.TextField()
    relationship_to_case = models.CharField(
        max_length=50,
        blank=True,
        help_text='e.g., Eyewitness, Neighbor, Relative'
    )
    statement = models.TextField()
    statement_date = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(
        'core.Profile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_statements'
    )
    is_protected = models.BooleanField(default=False, help_text='Mark if witness requires protection' )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Witness'
        verbose_name_plural = 'Witnesses'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Witness: {self.full_name} - {self.occurrence.reference_number}"


class Exhibit(models.Model):
    #Physical/Digital exhibits
    EXHIBIT_TYPE = (
        ('WEAPON', 'Weapon'),
        ('DOCUMENT', 'Document'),
        ('DIGITAL', 'Digital Evidence'),
        ('BIOLOGICAL', 'Biological Sample'),
        ('PHOTO', 'Photograph'),
        ('VIDEO', 'Video Recording'),
        ('OTHER', 'Other'),
    )
    
    occurrence = models.ForeignKey(Occurrence, on_delete=models.CASCADE,  related_name='exhibits' )
    exhibit_type = models.CharField(max_length=50, choices=EXHIBIT_TYPE)
    description = models.TextField()
    exhibit_number = models.CharField(max_length=50, unique=True)
    serial_number = models.CharField(max_length=100, blank=True, null=True)
    date_collected = models.DateTimeField(default=timezone.now)
    collected_by = models.ForeignKey(
        'core.Profile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='collected_exhibits'
    )
    storage_location = models.CharField(max_length=200)
    chain_of_custody = models.TextField(
        blank=True,
        help_text='Record of everyone who handled this exhibit'
    )
    is_returned = models.BooleanField(default=False)
    date_returned = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Exhibit'
        verbose_name_plural = 'Exhibits'
        ordering = ['-date_collected']
    
    def __str__(self):
        return f"Exhibit {self.exhibit_number} - {self.occurrence.reference_number}"
    
    def save(self, *args, **kwargs):
        if not self.exhibit_number:
            count = Exhibit.objects.filter(
                occurrence=self.occurrence
            ).count() + 1
            self.exhibit_number = f"EXH-{self.occurrence.reference_number}-{count:03d}"
        super().save(*args, **kwargs)


class CaseUpdate(models.Model):
    #Track case progress
    occurrence = models.ForeignKey(
        Occurrence,
        on_delete=models.CASCADE,
        related_name='updates'
    )
    updated_by = models.ForeignKey(
        'core.Profile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='case_updates'
    )
    previous_status = models.CharField(
        max_length=20,
        choices=Occurrence.CASE_STATUS,
        null=True,
        blank=True
    )
    new_status = models.CharField(
        max_length=20,
        choices=Occurrence.CASE_STATUS
    )
    update_text = models.TextField()
    action_taken = models.TextField(blank=True)
    next_steps = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Case Update'
        verbose_name_plural = 'Case Updates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['occurrence', '-created_at']),
            models.Index(fields=['new_status']),
        ]
    
    def __str__(self):
        return f"Update for {self.occurrence.reference_number} - {self.created_at}"


class CaseTrackingAccess(models.Model):
    #Public access to track cases
    #Citizens can view case status without login
   
    occurrence = models.OneToOneField(
        Occurrence,
        on_delete=models.CASCADE,
        related_name='tracking_access'
    )
    access_code = models.CharField(
        max_length=12,
        unique=True,
        editable=False,
        help_text='8-character code for citizen access'
    )
    reporter_phone = models.CharField(max_length=15)
    reporter_email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(null=True, blank=True)
    access_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Case Tracking Access'
        verbose_name_plural = 'Case Tracking Access Records'
        indexes = [
            models.Index(fields=['access_code']),
            models.Index(fields=['occurrence']),
        ]
    
    def __str__(self):
        return f"Tracking for {self.occurrence.reference_number}"
    
    def save(self, *args, **kwargs):
        if not self.access_code:
            alphabet = string.ascii_uppercase + string.digits
            while True:
                code = ''.join(secrets.choice(alphabet) for _ in range(8))
                if not CaseTrackingAccess.objects.filter(access_code=code).exists():
                    self.access_code = code
                    break
        super().save(*args, **kwargs)
    
    def record_access(self):
        #Record when citizen accesses their case
        self.last_accessed = timezone.now()
        self.access_count += 1
        self.save(update_fields=['last_accessed', 'access_count'])


class PublicCaseComment(models.Model):
    #Public comments/questions on their cases
    tracking_access = models.ForeignKey(
        CaseTrackingAccess,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    comment_text = models.TextField()
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Public Comment'
        verbose_name_plural = 'Public Comments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment on {self.tracking_access.occurrence.reference_number}"


class PoliceResponse(models.Model):
    #Police responses to public comments
    comment = models.OneToOneField(
        PublicCaseComment,
        on_delete=models.CASCADE,
        related_name='police_response'
    )
    responded_by = models.ForeignKey(
        'core.Profile',
        on_delete=models.SET_NULL,
        null=True
    )
    response_text = models.TextField()
    is_visible_to_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Police Response'
        verbose_name_plural = 'Police Responses'
    
    def __str__(self):
        return f"Response to {self.comment}"