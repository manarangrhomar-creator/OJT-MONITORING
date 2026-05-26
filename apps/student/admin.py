from django.contrib import admin
from .models import StudentProfile, FacialRecognition


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'user', 'department', 'course', 'year_level')
    list_filter = ('department', 'course', 'year_level', 'created_at')
    search_fields = ('student_id', 'user__username', 'user__email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('User Information', {'fields': ('user',)}),
        ('Student Information', {'fields': ('student_id', 'department', 'course', 'year_level', 'gpa')}),
        ('Timestamps', {'fields': ('id', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(FacialRecognition)
class FacialRecognitionAdmin(admin.ModelAdmin):
    list_display = ('student', 'is_verified', 'verification_date')
    list_filter = ('is_verified', 'verification_date', 'created_at')
    search_fields = ('student__username', 'student__email')
    readonly_fields = ('id', 'created_at', 'updated_at', 'facial_encoding')
