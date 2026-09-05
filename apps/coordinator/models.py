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
    start_date = models.DateField(null=True, blank=True, db_index=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', db_index=True)
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
    preferred_site = models.ForeignKey('Site', on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    application_letter = models.FileField(upload_to='applications/')
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
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
    time_in_am = models.TimeField(blank=True, null=True)
    time_out_am = models.TimeField(blank=True, null=True)
    time_in_pm = models.TimeField(blank=True, null=True)
    time_out_pm = models.TimeField(blank=True, null=True)
    facial_recognition_used = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    auto_clocked_out = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'
        unique_together = ('student', 'program', 'date')
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student.username} - {self.date}"

    def get_am_status(self):
        """Return AM attendance status: 'Not Yet', 'Present', 'Late', 'Absent'."""
        if not self.time_in_am:
            return 'Not Yet'
        # Late threshold: 8:00 AM
        from datetime import time
        late_threshold = time(8, 0)
        if self.time_in_am <= late_threshold:
            return 'Present' if self.time_out_am else 'Active'
        return 'Late' if self.time_out_am else 'Active'

    def get_pm_status(self):
        """Return PM attendance status: 'Not Yet', 'Present', 'Late', 'Absent'."""
        if not self.time_in_pm:
            return 'Not Yet'
        from datetime import time
        late_threshold = time(13, 0)
        if self.time_in_pm <= late_threshold:
            return 'Present' if self.time_out_pm else 'Active'
        return 'Late' if self.time_out_pm else 'Active'

    def get_overall_status(self):
        """Return overall status based on AM/PM presence."""
        am = self.get_am_status()
        pm = self.get_pm_status()
        if am == 'Not Yet' and pm == 'Not Yet':
            return 'Absent'
        if am == 'Late' or pm == 'Late':
            return 'Late'
        if am in ('Present', 'Active') or pm in ('Present', 'Active'):
            return 'Present'
        return self.status if hasattr(self, 'status') else 'Absent'


class FlagRecord(BaseModel):
    """Flag records for attendance anomalies (geofence violations, auto-timeout, etc)."""
    FLAG_TYPES = [
        ('geofence', 'Geofence Violation'),
        ('auto_timeout', 'Auto Timeout'),
        ('suspicious', 'Suspicious Activity'),
    ]
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='flags')
    flag_type = models.CharField(max_length=20, choices=FLAG_TYPES)
    reason = models.TextField()
    resolved = models.BooleanField(default=False, db_index=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_flags')
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Flag Record'
        verbose_name_plural = 'Flag Records'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_flag_type_display()} - {self.attendance}"


class Site(BaseModel):
    """Site/company for OJT placement, managed by admin."""
    SITE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    name = models.CharField(max_length=255)
    course = models.ForeignKey('core.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='sites')
    coordinator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_sites', limit_choices_to={'role': 'coordinator'})
    supervisor_name = models.CharField(max_length=255, blank=True)
    contact_number = models.CharField(max_length=50, blank=True)
    gmail = models.EmailField(max_length=255, blank=True)
    contact_persons = models.JSONField(default=list, blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=SITE_STATUS_CHOICES, default='pending', db_index=True)
    rejection_reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

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


