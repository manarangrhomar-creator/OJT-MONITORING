from django.contrib import admin
from .models import OJTProgram, OJTApplication, Attendance, FlagRecord, Site, SiteAssignment


@admin.register(OJTProgram)
class OJTProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'coordinator', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'start_date', 'coordinator')
    search_fields = ('name', 'coordinator__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Program Information', {'fields': ('name', 'description', 'coordinator', 'location')}),
        ('Dates & Capacity', {'fields': ('start_date', 'end_date', 'max_students')}),
        ('Status', {'fields': ('status',)}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(OJTApplication)
class OJTApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'program', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'program')
    search_fields = ('student__username', 'program__name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'program', 'date', 'time_in', 'time_out')
    list_filter = ('date', 'program', 'facial_recognition_used')
    search_fields = ('student__username', 'program__name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(FlagRecord)
class FlagRecordAdmin(admin.ModelAdmin):
    list_display = ('attendance', 'flag_type', 'reason', 'resolved', 'resolved_by', 'resolved_at')
    list_filter = ('flag_type', 'resolved', 'created_at')
    search_fields = ('attendance__student__username', 'reason')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'coordinator', 'supervisor_name', 'contact_number', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'supervisor_name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(SiteAssignment)
class SiteAssignmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'program', 'site', 'assigned_date')
    list_filter = ('assigned_date', 'program')
    search_fields = ('student__username', 'site__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
