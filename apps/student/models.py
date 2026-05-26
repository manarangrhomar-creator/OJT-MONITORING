from django.db import models
from apps.core.models import BaseModel, User


class StudentProfile(BaseModel):
    """Extended profile for student users."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile', limit_choices_to={'role': 'student'})
    student_id = models.CharField(max_length=50, unique=True)
    department = models.CharField(max_length=255)
    course = models.CharField(max_length=255)
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
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Facial Recognition'
        verbose_name_plural = 'Facial Recognition Records'
    
    def __str__(self):
        return f"{self.student.username} - {'Verified' if self.is_verified else 'Unverified'}"
