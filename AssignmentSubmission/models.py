from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from datetime import timedelta
import uuid


class CustomUserManager(BaseUserManager):
    def create_user(self, student_id, password=None, email=None, **extra_fields):
        if not student_id:
            raise ValueError("Student ID is required")

        user = self.model(student_id=student_id, email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, password, email=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(student_id, password, email, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    student_id = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)

     # Required fields for admin and permissions to work
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # <-- This is missing
    is_superuser = models.BooleanField(default=False)  # Optional but often needed
    
    USERNAME_FIELD = 'student_id'
    REQUIRED_FIELDS = ['email']

    objects = CustomUserManager()
    
    def __repr__(self):
        return f"{self.student_id} - {self.email}"
        
class RegistrationStage(models.TextChoices):
    id_entered = "id_entered"
    otp_sent = "otp_sent"
    otp_verified = "otp_verified"
    password_set = "password_set"
    completed = "completed"

class PreApprovedStudents(models.Model):
    name = models.CharField(max_length=50)
    student_id = models.CharField(max_length=15, unique=True)
    email = models.EmailField(null=True, blank=True)
    registration_stage = models.CharField(max_length= 15, choices=RegistrationStage.choices, blank=True, default=None, null=True)
    is_registered = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)


class Courses(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10, unique=True)
    lecturer = models.CharField(max_length=50)

    def __str__(self):

        return f"{self.code} - {self.name}"

def validate_file_size(value):
    limit = 5 * 1024 * 1024  # 5MB
    if value.size > limit:
        raise ValidationError('File too large. Size should not exceed 5MB.')

class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    @property
    def is_expired(self):
        return self.created_at + timedelta(minutes=30) < timezone.now()
    
import os
from datetime import date

def student_submission_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    today = date.today().strftime("%d.%m.%Y")
    student_id = instance.student.student_id
    new_name = f"{student_id}_BCE_GROUP_B_{today}{ext}"
    return f"submissions/{instance.submission.id}/{new_name}"
    
class Submission(models.Model):
    class FORMAT_CHOICES(models.TextChoices):
        PDF = ".pdf", "PDF"
        TXT = ".txt", "Text"
        PPT= ".pptx", "Power Point"
        DOCX = ".docx" "Word Document"

    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    title = models.CharField(max_length=20)
    note = models.TextField(default=None, null=True, blank=True)
    lecturer = models.CharField(max_length=50, default=None, null=True, blank=True)
    course = models.ForeignKey(Courses, on_delete=models.CASCADE, default=None, null=True, blank=True)
    format = models.CharField(max_length=20, choices=FORMAT_CHOICES.choices)
    deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_open = models.BooleanField(default=True)

    def __str__(self):
        return f"Submission: {self.title} for {self.course}"

class StudentSubmission(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file = models.FileField(upload_to=student_submission_path)
    submitted_at = models.DateTimeField(auto_now_add=True)

    @property
    def filename(self):
        return os.path.basename(self.file.name)

    class Meta:
        unique_together = ('submission', 'student')
    
    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'name'):
            ext = os.path.splitext(self.file.name)[1]
            today = date.today().strftime("%d.%m.%Y")
            student_id = self.student.student_id
            self.file.name = f"submissions/{self.submission.id}/{student_id}_BCE_GROUP_B_{today}{ext}"
        super().save(*args, **kwargs)
