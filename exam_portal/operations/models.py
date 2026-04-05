from django.db import models, transaction
from masters.models import Student, Faculty, Course, Room

class Examinations(models.Model):
    exam_name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    academic_year = models.CharField(max_length=20, null=True)
    semester = models.CharField(max_length=20,null=True)
    published = models.BooleanField(default=False)

    class Meta:
        db_table = "examinations"
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_date__lt=models.F('end_date')),
                name="start_date_before_end_date"
            )
        ]

    def __str__(self):
        return self.exam_name

class StudentAcademicData(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="academic_records")
    academic_year = models.CharField(max_length=9)
    year = models.PositiveSmallIntegerField()
    semester = models.CharField(max_length=20)
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = "student_academic_data"
        constraints = [
            models.CheckConstraint(
                check=models.Q(year__gte=1, year__lte=4),
                name="chk_sad_year_1_4"
            ),
            models.UniqueConstraint(
                fields=["student", "academic_year", "year", "semester"],
                name="uq_sad_student_term"
            ),
        ]

    def save(self, *args, **kwargs):
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.is_current:
                StudentAcademicData.objects.filter(
                    student=self.student
                ).exclude(id=self.id).update(is_current=False)

class StudentCourse(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)
    registration_type = models.CharField(max_length=20, default="REGULAR")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "student_course"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course", "academic_year", "semester"],
                name="uq_student_course"
            ),
        ]
        indexes = [
            models.Index(fields=["student"]),
            models.Index(fields=["course"]),
            models.Index(fields=["academic_year", "semester"]),
            models.Index(fields=["academic_year"]),
            models.Index(fields=["semester"]),
        ]

class FacultyCourse(models.Model):
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    academic_year = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "faculty_course"
        constraints = [
            models.UniqueConstraint(
                fields=["faculty", "course", "academic_year", "semester"],
                name="uq_faculty_course"
            ),
        ]

class ExamSlot(models.Model):
    examination = models.ForeignKey(Examinations, on_delete=models.CASCADE, null=True)
    exam_type = models.CharField(max_length=25, null=True)
    mode = models.CharField(max_length=25, null=True)

    exam_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_code = models.CharField(max_length=10, null=True)
    registration_type = models.CharField(max_length=20, default="REGULAR")

    status = models.CharField(
        max_length=10,
        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive"), ("CANCELLED", "Cancelled")],
        default="ACTIVE"
    )

    # generation tracking
    is_generated = models.BooleanField(default=False)
    generated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "exam_slot"
        constraints = [
            models.UniqueConstraint(
                fields=["exam_date", "start_time", "end_time", "slot_code"],
                name="uq_exam_slot_time"
            )
        ]
        indexes = [
            models.Index(fields=["exam_date"]),
        ]

class Exam(models.Model):
    exam_slot = models.ForeignKey(ExamSlot, on_delete=models.CASCADE, related_name="exams")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, null=True)
    regulation = models.CharField(max_length=20, null=True)

    class Meta:
        db_table = "exam"
        indexes = [
            models.Index(fields=["exam_slot"]),
        ]

class StudentExamMap(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="student_map")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

    attempt_type = models.CharField(
        max_length=12,
        choices=[("REGULAR", "REGULAR"), ("BACKLOG", "BACKLOG"), ("IMPROVEMENT", "IMPROVEMENT")]
    )

    status = models.CharField(
        max_length=10,
        choices=[("REGISTERED", "REGISTERED"), ("ATTENDED", "ATTENDED"), ("ABSENT", "ABSENT")],
        default="REGISTERED"
    )

    class Meta:
        db_table = "student_exam_map"
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "student"],
                name="uq_exam_student"
            )
        ]
        indexes = [
            models.Index(fields=["exam"]),
            models.Index(fields=["student"]),
        ]

class RoomAllocation(models.Model):
    exam_slot = models.ForeignKey(ExamSlot, on_delete=models.CASCADE, related_name="rooms", null=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    class Meta:
        db_table = "room_allocation"
        constraints = [
            models.UniqueConstraint(
                fields=["exam_slot", "room"],
                name="uq_slot_room"
            )
        ]

class FacultyAvailability(models.Model):
    exam_slot = models.ForeignKey(ExamSlot, on_delete=models.CASCADE, related_name="available_faculty")
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "faculty_availability"
        constraints = [
            models.UniqueConstraint(
                fields=["exam_slot", "faculty"],
                name="uq_faculty_slot"
            )
        ]

class InvigilationDuty(models.Model):
    exam_slot = models.ForeignKey(ExamSlot, on_delete=models.CASCADE, related_name="invigilation")
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    class Meta:
        db_table = "invigilation_duty"
        constraints = [
            models.UniqueConstraint(
                fields=["exam_slot", "faculty"],
                name="uq_faculty_once_per_slot"
            )
        ]

class SeatingPlan(models.Model):
    student_exam = models.ForeignKey(StudentExamMap, on_delete=models.CASCADE, related_name="seating")
    exam_slot = models.ForeignKey(ExamSlot, on_delete=models.CASCADE, related_name="seating", null=True)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)

    row_no = models.PositiveIntegerField()
    seat_no = models.PositiveIntegerField()

    class Meta:
        db_table = "seating_plan"
        constraints = [
            models.UniqueConstraint(
                fields=["exam_slot", "room", "row_no", "seat_no"],
                name="uq_slot_room_seat"
            ),
            models.UniqueConstraint(
                fields=["student_exam"],
                name="uq_student_single_seat"
            )
        ]

class Attendance(models.Model):
    student_exam = models.OneToOneField(StudentExamMap, on_delete=models.CASCADE)
    marked_by = models.ForeignKey(Faculty, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, null=True)
    status = models.CharField(
        max_length=7,
        choices=[("PRESENT", "PRESENT"), ("ABSENT", "ABSENT")]
    )
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "attendance"

    def __str__(self):
        return f"Attendance Record {self.id}"