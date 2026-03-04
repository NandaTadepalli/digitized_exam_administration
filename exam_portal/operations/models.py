from django.db import models, transaction
from masters.models import Student, Faculty, Course, Room
class Examinations(models.Model):
    exam_name = models.CharField(max_length=100, null=False, blank=False)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    academic_year = models.CharField(max_length=9, null=True, blank=False)
    semester = models.CharField(max_length=20, null=True, blank=False)

    class Meta:
        db_table = "examinations"
        constraints = [
            models.CheckConstraint(check=models.Q(start_date__lt=models.F('end_date')), name="start_date_before_end_date")
        ]

    def __str__(self):
        return self.exam_name


class StudentAcademicData(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="academic_records")
    academic_year = models.CharField(max_length=9)  # e.g. "2025-2026"
    year = models.PositiveSmallIntegerField()
    semester = models.CharField(max_length=20)
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = "student_academic_data"
        constraints = [
            models.CheckConstraint(check=models.Q(year__gte=1, year__lte=4), name="chk_sad_year_1_4"),
            models.UniqueConstraint(fields=["student", "academic_year", "year", "semester"], name="uq_sad_student_term"),
        ]

    def save(self, *args, **kwargs):
        """
        MySQL can't enforce 'only one current row per student' with partial unique index.
        So we enforce it here: if this record is_current=True, set others False.
        """
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_current:
                StudentAcademicData.objects.filter(student=self.student).exclude(id=self.id).update(is_current=False)


class StudentCourse(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="course_map")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="student_map")
    academic_year = models.CharField(max_length=9)
    semester = models.CharField(max_length=20)
    registration_type = models.CharField(max_length=20, default="regular", help_text="Type of registration (e.g., regular, supply, improvement)")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "student_course"
        constraints = [
            models.UniqueConstraint(fields=["student", "course", "academic_year", "semester"], name="uq_student_course"),
        ]
        indexes = [
            models.Index(fields=["academic_year"]),
            models.Index(fields=["semester"]),
            models.Index(fields=["course"]),
            models.Index(fields=["student"]),
            models.Index(fields=["student", "academic_year", "semester"]),
        ]


class FacultyCourse(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="course_map")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="faculty_map")
    academic_year = models.CharField(max_length=9)
    semester = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "faculty_course"
        constraints = [
            models.UniqueConstraint(fields=["faculty", "course", "academic_year", "semester"], name="uq_faculty_course"),
        ]


class ExamSlot(models.Model):
    examination = models.ForeignKey('Examinations', blank=True, null=True, on_delete=models.CASCADE, db_column='examination_id')
    exam_type = models.CharField(max_length=25, blank=True, null=True)
    mode = models.CharField(max_length=25, blank=True, null=True)

    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_code = models.CharField(max_length=10, blank=True, null=True)
    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
        ("CANCELLED", "Cancelled"),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")

    class Meta:
        db_table = "exam_slot"
        indexes = [
            models.Index(fields=["exam_date", "slot_code"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["exam_date", "start_time", "end_time", "slot_code", "exam_type", "mode"], name="uq_exam_slot_time"),
        ]


class Exam(models.Model):
    exam_slot = models.ForeignKey(ExamSlot, on_delete=models.CASCADE, related_name="exams")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="exams", null=True, blank=True)
    regulation = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = "exam"


class StudentExamMap(models.Model):
    ATTEMPT_TYPE = (("REGULAR", "REGULAR"), ("BACKLOG", "BACKLOG"), ("IMPROVEMENT", "IMPROVEMENT"))
    STATUS = (("REGISTERED", "REGISTERED"), ("ATTENDED", "ATTENDED"), ("ABSENT", "ABSENT"))

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="student_map")
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="exam_map")
    attempt_type = models.CharField(max_length=12, choices=ATTEMPT_TYPE)
    status = models.CharField(max_length=10, choices=STATUS, default="REGISTERED")

    class Meta:
        db_table = "student_exam_map"
        constraints = [
            models.UniqueConstraint(fields=["exam", "student"], name="uq_exam_student"),
        ]
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["exam"]),
        ]


class RoomAllocation(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="room_allocations", null=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="exam_allocations")

    class Meta:
        db_table = "room_allocation"
        constraints = [
            models.UniqueConstraint(fields=["exam", "room"], name="uq_exam_room"),
        ]


class SeatingPlan(models.Model):
    student_exam = models.ForeignKey(StudentExamMap, on_delete=models.CASCADE, related_name="seating")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="seating")
    row_no = models.PositiveIntegerField()
    seat_no = models.PositiveIntegerField()

    class Meta:
        db_table = "seating_plan"
        constraints = [
            models.UniqueConstraint(fields=["room", "row_no", "seat_no"], name="uq_room_seat"),
        ]


class InvigilationDuty(models.Model):
    exam_slot = models.ForeignKey(ExamSlot, on_delete=models.CASCADE, related_name="invigilation")
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="invigilation")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="invigilation")

    class Meta:
        db_table = "invigilation_duty"


class Attendance(models.Model):
    STATUS = (("PRESENT", "PRESENT"), ("ABSENT", "ABSENT"))

    student_exam = models.OneToOneField(StudentExamMap, on_delete=models.CASCADE, related_name="attendance")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="attendance")
    marked_by = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name="attendance_marked")
    status = models.CharField(max_length=7, choices=STATUS)
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "attendance"
