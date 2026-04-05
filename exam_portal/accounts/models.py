from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("hod", "HOD"),
        ("faculty", "Faculty"),
        ("student", "Student"),
        ("dept_exam_controller", "Dept Exam Controller"),
    )

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default="student",
    )

    def save(self, *args, **kwargs):
        if self.is_superuser and not self.role == 'admin':
            self.role = 'admin'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"
