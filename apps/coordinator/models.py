from django.db import models
from apps.core.models import BaseModel, User


class OJTProgram(BaseModel):
    """OJT Program information."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('completed', 'Completed'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    coordinator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ojt_programs', limit_choices_to={'role': 'coordinator'})
    max_students = models.IntegerField(default=50)
    location = models.CharField(max_length=255, blank=True)
    
    class Meta:
        verbose_name = 'OJT Program'
        verbose_name_plural = 'OJT Programs'
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def get_student_count(self):
        return self.applications.filter(status='approved').count()


class OJTApplication(BaseModel):
    """Student OJT application."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ojt_applications', limit_choices_to={'role': 'student'})
    program = models.ForeignKey(OJTProgram, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    application_letter = models.FileField(upload_to='applications/')
    resume = models.FileField(upload_to='resumes/')
    approved_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'OJT Application'
        verbose_name_plural = 'OJT Applications'
        unique_together = ('student', 'program')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.program.name} ({self.get_status_display()})"


class Attendance(BaseModel):
    """Student attendance tracking."""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances', limit_choices_to={'role': 'student'})
    program = models.ForeignKey(OJTProgram, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    time_in = models.TimeField()
    time_out = models.TimeField(blank=True, null=True)
    facial_recognition_used = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        unique_together = ('student', 'program', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student.username} - {self.date}"


class Site(BaseModel):
    """Site/company for OJT placement, managed by admin."""
    name = models.CharField(max_length=255)
    course = models.ForeignKey('core.Course', on_delete=models.CASCADE, related_name='sites')
    contact_person = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Site'
        verbose_name_plural = 'Sites'
        ordering = ['name']

    def __str__(self):
        return self.name


class SiteAssignment(BaseModel):
    """Student site/placement assignment by coordinator."""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='site_assignments', limit_choices_to={'role': 'student'})
    program = models.ForeignKey(OJTProgram, on_delete=models.CASCADE, related_name='site_assignments')
    assigned_date = models.DateField(auto_now_add=True)
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, null=True, blank=True, related_name='assignments')
    supervisor_name = models.CharField(max_length=255, blank=True)
    supervisor_contact = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Site Assignment'
        verbose_name_plural = 'Site Assignments'
        unique_together = ('student', 'program')
        ordering = ['-assigned_date']

    def __str__(self):
        return f"{self.student.username} -> {self.site.name if self.site else 'No site'}"


