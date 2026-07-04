from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import redirect
from django.utils.html import format_html
from django.urls import reverse
from .models import User, Profile, Region, District, Station

from import_export.admin import ImportExportModelAdmin, ImportExportActionModelAdmin
from import_export import resources, fields, widgets
from import_export.formats import base_formats



class ProfileResource(resources.ModelResource):
    full_name = fields.Field(column_name='FULL NAME', attribute='user', widget=widgets.ForeignKeyWidget(User, 'get_full_name'))
    username = fields.Field(column_name='USERNAME', attribute='user', widget=widgets.ForeignKeyWidget(User, 'username'))
    email = fields.Field(column_name='EMAIL', attribute='user', widget=widgets.ForeignKeyWidget(User, 'email'))
    phone = fields.Field(column_name='PHONE', attribute='user', widget=widgets.ForeignKeyWidget(User, 'phone'))
    station_name = fields.Field(column_name='STATION', attribute='current_station', widget=widgets.ForeignKeyWidget(Station, 'name'))
    rank_display = fields.Field(column_name='RANK', attribute='rank', widget=widgets.CharWidget())
    role_display = fields.Field(column_name='ROLE', attribute='role', widget=widgets.CharWidget())

    class Meta:
        model = Profile
        fields = ('username', 'full_name', 'email', 'phone', 'rank_display', 'role_display', 'force_number', 'file_number', 'badge_number', 'biometric_id', 'station_name', 'date_of_birth', 'date_joined_force', 'is_active_officer', 'is_on_duty')
        import_id_fields = ('force_number',)

    def dehydrate_full_name(self, profile): return profile.user.get_full_name()
    def dehydrate_phone(self, profile): return profile.user.phone
    def dehydrate_rank_display(self, profile): return profile.get_rank_display() if profile.rank else ''
    def dehydrate_role_display(self, profile): return profile.get_role_display() if profile.role else ''

    def before_import_row(self, row, **kwargs):
        errors = []
        if row.get('RANK') and row.get('RANK') not in dict(Profile.RANK_CHOICES): errors.append(f"Invalid rank: {row.get('RANK')}")
        if row.get('ROLE') and row.get('ROLE') not in dict(Profile.ROLE_CHOICES): errors.append(f"Invalid role: {row.get('ROLE')}")
        if not row.get('USERNAME'): errors.append("Username is required")
        return errors if errors else None


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'phone', 'is_active', 'is_staff', 'date_joined')
        import_id_fields = ('username',)


class StationResource(resources.ModelResource):
    district_name = fields.Field(column_name='DISTRICT', attribute='district', widget=widgets.ForeignKeyWidget(District, 'name'))
    region_name = fields.Field(column_name='REGION', attribute='district__region', widget=widgets.ForeignKeyWidget(Region, 'name'))
    class Meta:
        model = Station
        fields = ('name', 'station_type', 'district_name', 'region_name', 'location', 'contact_number', 'email', 'capacity', 'is_24_hours', 'has_detention', 'is_active')
       


class RegionResource(resources.ModelResource):
    class Meta:
        model = Region
        fields = ('name', 'headquarters_location', 'contact_number', 'is_active')
        


class DistrictResource(resources.ModelResource):
    region_name = fields.Field(column_name='REGION', attribute='region', widget=widgets.ForeignKeyWidget(Region, 'name'))
    class Meta:
        model = District
        fields = ('name',  'region_name', 'headquarters', 'contact_number', 'is_active')
       


@admin.register(User)
class CustomUserAdmin(ImportExportActionModelAdmin, UserAdmin):
    resource_class = UserResource
    formats = [base_formats.CSV, base_formats.XLSX, base_formats.JSON]
    list_display = ['username', 'get_full_name', 'email', 'get_rank', 'get_role', 'get_station', 'phone', 'is_active', 'last_login']
    list_filter = ['is_active', 'is_staff']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'phone']
    fieldsets = (
        ('Account Information', {'fields': ('username', 'password')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'), 'classes': ('collapse',)}),
        ('Security Information', {'fields': ('last_login', 'last_login_ip', 'login_count', 'failed_login_attempts', 'date_joined'), 'classes': ('collapse',)}),
    )
    add_fieldsets = (
        ('Account Information', {'fields': ('username', 'password1', 'password2')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
    )
    readonly_fields = ['last_login', 'date_joined', 'login_count', 'failed_login_attempts']

    def get_rank(self, obj):
        try: return obj.user_profile.get_rank_display()
        except (Profile.DoesNotExist, AttributeError): return '-'
    get_rank.short_description = 'Rank'

    def get_role(self, obj):
        try: return obj.user_profile.get_role_display()
        except (Profile.DoesNotExist, AttributeError): return '-'
    get_role.short_description = 'Role'

    def get_station(self, obj):
        try:
            p = obj.user_profile
            if p and p.current_station:
                url = reverse('admin:core_station_change', args=[p.current_station.id])
                return format_html('<a href="{}">{}</a>', url, p.current_station.name)
        except (Profile.DoesNotExist, AttributeError): pass
        return '-'
    get_station.short_description = 'Station'



@admin.register(Profile)
class ProfileAdmin(ImportExportModelAdmin):
    resource_class = ProfileResource
    formats = [base_formats.CSV, base_formats.XLSX, base_formats.JSON, base_formats.HTML]
    list_display = ['get_officer_number', 'get_full_name', 'rank', 'role', 'current_station', 'is_active_officer', 'get_years_of_service']
    list_filter = ['role', 'rank', 'is_active_officer', 'is_on_duty', 'current_station__district__region', 'current_station__district', 'current_station']
    search_fields = ['force_number', 'file_number', 'badge_number', 'biometric_id', 'user__first_name', 'user__last_name', 'user__email']
    fieldsets = (
        ('Officer Information', {'fields': ('user', 'rank', 'role')}),
        ('Identification', {'fields': ('force_number', 'file_number'),  'description': 'Force Number (PC-SGT) | File Number (SSGT+)'}),
        ('Personal Details', {'fields': ('date_of_birth', 'date_joined_force')}),
        ('Assignment & Status', {'fields': ('current_station', 'is_on_duty', 'is_active_officer')}),
    )
    actions = ['enroll_face']

    def enroll_face(self, request, queryset):
        profile = queryset.first()
        if profile:
            return redirect('core:enroll_face', profile_id=profile.id)
        self.message_user(request, 'No profile selected', messages.ERROR)
    enroll_face.short_description = "Enroll Face Recognition"

    def get_readonly_fields(self, request, obj=None):
        return ['force_number', 'file_number'] if obj else []

    def get_officer_number(self, obj):
        number = obj.get_officer_number()
        color = '#0d47a1' if obj.is_senior_officer() else '#1b5e20'
        return format_html('<strong style="color: {};">{}</strong>', color, number)
    get_officer_number.short_description = 'ID Number'

    def get_full_name(self, obj):
        url = reverse('admin:core_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
    get_full_name.short_description = 'Name'

    def get_years_of_service(self, obj):
        if obj.date_joined_force:
            from datetime import date
            return f"{date.today().year - obj.date_joined_force.year} years"
        return '-'
    get_years_of_service.short_description = 'Service'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'current_station', 'current_station__district', 'current_station__district__region')



class StationInline(admin.TabularInline):
    model = Station
    extra = 0
    show_change_link = True
    fields = ['name', 'station_type', 'is_active']


class DistrictInline(admin.TabularInline):
    model = District
    extra = 0
    show_change_link = True
    fields = ['name']


@admin.register(Region)
class RegionAdmin(ImportExportModelAdmin):
    resource_class = RegionResource
    formats = [base_formats.CSV, base_formats.XLSX, base_formats.JSON]
    list_display = ['name', 'get_districts_count', 'get_stations_count', 'get_officers_count', 'regional_commander', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    inlines = [DistrictInline]
    fieldsets = (
        ('Region Information', {'fields': ('name', 'headquarters_location', 'contact_number')}),
        ('Command', {'fields': ('regional_commander',)}),
        ('Status', {'fields': ('is_active',)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'regional_commander' in form.base_fields:
            form.base_fields['regional_commander'].queryset = Profile.objects.filter(role='admin', is_active_officer=True)
        return form

    def get_districts_count(self, obj): return obj.districts.count()
    get_districts_count.short_description = 'Districts'
    def get_stations_count(self, obj): return Station.objects.filter(district__region=obj).count()
    get_stations_count.short_description = 'Stations'
    def get_officers_count(self, obj): return Profile.objects.filter(current_station__district__region=obj, is_active_officer=True).count()
    get_officers_count.short_description = 'Officers'


@admin.register(District)
class DistrictAdmin(ImportExportModelAdmin):
    resource_class = DistrictResource
    formats = [base_formats.CSV, base_formats.XLSX, base_formats.JSON]
    list_display = ['name', 'region', 'get_stations_count', 'get_officers_count', 'district_commander', 'is_active']
    list_filter = ['region', 'is_active']
    search_fields = ['name',  'region__name']
    list_select_related = ['region', 'district_commander']
    inlines = [StationInline]
    fieldsets = (
        ('District Information', {'fields': ('name', 'region', 'headquarters', 'contact_number')}),
        ('Command', {'fields': ('district_commander',)}),
        ('Status', {'fields': ('is_active',)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'district_commander' in form.base_fields:
            form.base_fields['district_commander'].queryset = Profile.objects.filter(role='district_admin', is_active_officer=True)
        return form

    def get_stations_count(self, obj): return obj.stations.count()
    get_stations_count.short_description = 'Stations'
    def get_officers_count(self, obj): return Profile.objects.filter(current_station__district=obj, is_active_officer=True).count()
    get_officers_count.short_description = 'Officers'


@admin.register(Station)
class StationAdmin(ImportExportModelAdmin):
    resource_class = StationResource
    formats = [base_formats.CSV, base_formats.XLSX, base_formats.JSON]
    list_display = ['name', 'get_district', 'get_region', 'station_type', 'get_officers_count', 'get_capacity_status', 'station_commander', 'is_active', 'is_24_hours']
    list_filter = ['district__region', 'district', 'station_type', 'is_active', 'is_24_hours', 'has_detention']
    search_fields = ['name', 'district__name', 'district__region__name', 'location']
    list_select_related = ['district', 'district__region', 'station_commander']
    fieldsets = (
        ('Station Information', {'fields': ('name', 'station_type', 'district')}),
        ('Location', {'fields': ('location', 'physical_address', ('latitude', 'longitude'))}),
        ('Contact Information', {'fields': ('contact_number', 'email')}),
        ('Command', {'fields': ('station_commander',)}),
        ('Capacity & Facilities', {'fields': ('capacity', 'is_24_hours', 'has_detention')}),
        ('Status', {'fields': ('is_active',)}),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'station_commander' in form.base_fields:
            form.base_fields['station_commander'].queryset = Profile.objects.filter(role__in=['station_admin', 'admin'], is_active_officer=True)
        return form

    def get_district(self, obj): return obj.district.name
    get_district.short_description = 'District'
    def get_region(self, obj): return obj.district.region.name
    get_region.short_description = 'Region'
    def get_officers_count(self, obj): return obj.assigned_officers.filter(is_active_officer=True).count()
    get_officers_count.short_description = 'Officers'

    def get_capacity_status(self, obj):
        count = obj.assigned_officers.filter(is_active_officer=True).count()
        pct = (count / obj.capacity * 100) if obj.capacity else 0
        if pct >= 90: color, icon = 'red', '⚠️'
        elif pct >= 70: color, icon = 'orange', '⚡'
        else: color, icon = 'green', '✅'
        return format_html('<span style="color: {};">{} {}/{} ({}%)</span>', color, icon, count, obj.capacity, int(pct))
    get_capacity_status.short_description = 'Capacity'