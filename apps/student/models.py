from django.db import models
from apps.core.models import BaseModel, User


class StudentNarrativeReport(BaseModel):
    """Student-submitted daily accomplishment/narrative report."""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_narrative_reports', limit_choices_to={'role': 'student'})
    program = models.ForeignKey('coordinator.OJTProgram', on_delete=models.CASCADE, related_name='student_narratives', null=True, blank=True)
    log_date = models.DateField()
    topic = models.CharField(max_length=255)
    content = models.TextField()
    photo_1 = models.ImageField(upload_to='narratives/', blank=True, null=True)
    photo_2 = models.ImageField(upload_to='narratives/', blank=True, null=True)
    photo_3 = models.ImageField(upload_to='narratives/', blank=True, null=True)
    photo_4 = models.ImageField(upload_to='narratives/', blank=True, null=True)
    grade = models.IntegerField(blank=True, null=True, help_text='Coordinator grade (1-100)')
    feedback = models.TextField(blank=True, help_text='Coordinator feedback on the report')
    graded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='graded_narratives')
    graded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = 'Student Narrative Report'
        verbose_name_plural = 'Student Narrative Reports'
        unique_together = ('student', 'log_date')
        ordering = ['-log_date']

    def __str__(self):
        return f"{self.student.username} - {self.log_date}"


class StudentProfile(BaseModel):
    """Extended profile for student users."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', limit_choices_to={'role': 'student'})
    student_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=255)
    course = models.ForeignKey('core.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    year_level = models.IntegerField(choices=[(1, '1st Year'), (2, '2nd Year'), (3, '3rd Year'), (4, '4th Year')])
    gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student_id}"


class FacialRecognition(BaseModel):
    """Store facial recognition data for students."""
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='facial_data', limit_choices_to={'role': 'student'})
    facial_encoding = models.BinaryField()
    face_image = models.BinaryField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Facial Recognition'
        verbose_name_plural = 'Facial Recognition Records'
    
    def __str__(self):
        return f"{self.student.username} - {'Verified' if self.is_verified else 'Unverified'}"
