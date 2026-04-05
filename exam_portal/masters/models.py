from django.conf import settings
from django.db import models

class Batch(models.Model):
    batch_code = models.CharField(max_length=20, unique=True, help_text="Batch/Regulation code")
    admission_year = models.PositiveIntegerField(help_text="Year of admission")
    grad_year = models.PositiveIntegerField(help_text="Year of graduation")
    status = models.CharField(max_length=10, choices=(('ACTIVE', 'ACTIVE'), ('INACTIVE', 'INACTIVE')), default='ACTIVE')

    class Meta:
        db_table = "batches"

    def __str__(self):
        return f"{self.batch_code} ({self.admission_year}-{self.grad_year})"

class Department(models.Model):
    dept_code = models.CharField(max_length=50, unique=True)
    dept_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "departments"

    def __str__(self):
        return f"{self.dept_code} - {self.dept_name}"


class Program(models.Model):
    program_code = models.CharField(max_length=20, unique=True)
    program_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "programs"

    def __str__(self):
        return f"{self.program_code} - {self.program_name}"


class Student(models.Model):
    STATUS_CHOICES = (
        ("ACTIVE", "ACTIVE"),
        ("GRADUATED", "GRADUATED"),
        ("DROPPED", "DROPPED"),
    )

    student_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")

    std_name = models.CharField(max_length=100)
    program = models.ForeignKey(Program, on_delete=models.PROTECT, related_name="students")
    dept = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="students")

    email = models.EmailField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    parent_phone_number = models.CharField(max_length=15, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")

    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="students", null=True, blank=True, help_text="Batch/Regulation")

    class Meta:
        db_table = "students"
        indexes = [
            models.Index(fields=["student_id"]),
            models.Index(fields=["dept"]),
            models.Index(fields=["program"]),
        ]

    def __str__(self):
        return f"{self.student_id} - {self.std_name}"


class Faculty(models.Model):
    DESIGNATION_CHOICES = (
        ("Assistant Professor", "Assistant Professor"),
        ("Associate Professor", "Associate Professor"),
        ("Professor", "Professor"),
    )
    STATUS_CHOICES = (
        ("ACTIVE", "ACTIVE"),
        ("RESIGNED", "RESIGNED"),
        ("ON_LEAVE", "ON_LEAVE"),
    )

    faculty_id = models.CharField(max_length=20, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="faculty_profile")

    faculty_name = models.CharField(max_length=100)
    dept = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="faculty")

    email = models.EmailField(max_length=100, blank=True, null=True)

    phone_number = models.CharField(max_length=15, blank=True, null=True)

    designation = models.CharField(max_length=30, choices=DESIGNATION_CHOICES, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")

    class Meta:
        db_table = "faculty"
        indexes = [
            models.Index(fields=["faculty_id"]),
            models.Index(fields=["dept"]),
        ]

    def __str__(self):
        return f"{self.faculty_id} - {self.faculty_name}"


class Course(models.Model):
    course_code = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "courses"

    def __str__(self):
        return f"{self.course_code} - {self.course_name}"


class Room(models.Model):
    room_code = models.CharField(max_length=20, unique=True)
    rows = models.PositiveIntegerField()
    columns = models.PositiveIntegerField()
    # capacity computed in Django (instead of generated column)
    capacity = models.PositiveIntegerField(editable=False)
    room_type = models.CharField(max_length=30, blank=True, null=True, help_text="Type of room (e.g., Lecture Hall, Lab, etc.)")
    floor = models.CharField(max_length=10, blank=True, null=True)
    block = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "room"

    def save(self, *args, **kwargs):
        self.capacity = (self.rows or 0) * (self.columns or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.room_code
