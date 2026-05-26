from django.contrib import admin
from .models import OJTProgram, OJTApplication, Attendance


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
