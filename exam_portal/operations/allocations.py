# operations/allocation.py

import numpy as np
import random
from django.db import transaction
from django.utils import timezone
from ortools.sat.python import cp_model

from operations.models import (
    ExamSlot,
    Exam,
    StudentExamMap,
    RoomAllocation,
    FacultyAvailability,
    InvigilationDuty,
    SeatingPlan
)

# --------------------------------------------------
# GLOBAL FACULTY REGISTRY (prevent double duty)
# --------------------------------------------------

faculty_registry = {}


# --------------------------------------------------
# BUFFER SEATS (5–10 seats)
# --------------------------------------------------

def calculate_buffer(capacity):

    if capacity <= 40:
        return 5
    elif capacity <= 80:
        return 7
    else:
        return 10


# --------------------------------------------------
# FACULTY CALCULATION
# --------------------------------------------------

def calculate_faculty_needed(student_count):

    base = student_count // 50
    remainder = student_count % 50

    if remainder > 25:
        base += 1

    return max(1, base)


# --------------------------------------------------
# ROOM ESTIMATION
# --------------------------------------------------

def estimate_rooms_required(slot_id):

    slot = ExamSlot.objects.get(id=slot_id)

    exams = Exam.objects.filter(exam_slot=slot)

    students = StudentExamMap.objects.filter(exam__in=exams)

    total_students = students.count()

    rooms_alloc = list(RoomAllocation.objects.filter(exam_slot=slot).select_related("room"))

    # If no rooms allocated, use all active rooms
    if not rooms_alloc:
        from masters.models import Room
        rooms_alloc = [type('FakeAlloc', (), {'room': r}) for r in Room.objects.filter(is_active=True)]

    room_data = []

    for r in rooms_alloc:

        room = r.room

        capacity = room.rows * room.columns

        buffer = calculate_buffer(capacity)

        usable = capacity - buffer

        room_data.append({
            "room": room.room_code,
            "usable": usable,
            "capacity": capacity
        })

    room_data.sort(key=lambda x: x["usable"], reverse=True)

    remaining = total_students

    used = []

    for r in room_data:

        if remaining <= 0:
            break

        allocate = min(remaining, r["usable"])

        used.append({
            "room": r["room"],
            "students": allocate
        })

        remaining -= allocate

    faculty_needed = calculate_faculty_needed(total_students)

    return {
        "total_students": total_students,
        "rooms_required": len(used),
        "faculty_required": faculty_needed,
        "room_distribution": used
    }


# --------------------------------------------------
# STUDENT COURSE DISTRIBUTION
# --------------------------------------------------

def distribute_students_by_course(students):

    course_groups = {}

    for s in students:

        c = s.exam.course.course_code

        course_groups.setdefault(c, []).append(s)

    for c in course_groups:
        random.shuffle(course_groups[c])

    distributed = []

    while any(course_groups.values()):

        for c in list(course_groups.keys()):

            if course_groups[c]:
                distributed.append(course_groups[c].pop())

    return distributed


# --------------------------------------------------
# CP-SAT 8-WAY SOLVER
# --------------------------------------------------

def solve_seating(rows, cols, course_counts):

    courses = list(course_counts.keys())

    model = cp_model.CpModel()

    seat_vars = {}

    for r in range(rows):
        for c in range(cols):

            for course in courses:

                seat_vars[(r, c, course)] = model.NewBoolVar(
                    f"s_{r}_{c}_{course}"
                )

            model.Add(
                sum(seat_vars[(r, c, course)] for course in courses) <= 1
            )

    # exact course counts
    for course, count in course_counts.items():

        model.Add(
            sum(
                seat_vars[(r, c, course)]
                for r in range(rows)
                for c in range(cols)
            ) == count
        )

    # 8-direction adjacency
    for course in courses:

        for r in range(rows):
            for c in range(cols):

                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:

                        if dr == 0 and dc == 0:
                            continue

                        nr = r + dr
                        nc = c + dc

                        if 0 <= nr < rows and 0 <= nc < cols:

                            model.Add(
                                seat_vars[(r, c, course)]
                                + seat_vars[(nr, nc, course)]
                                <= 1
                            )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0

    status = solver.Solve(model)

    return status, solver, seat_vars


# --------------------------------------------------
# FACULTY ASSIGNMENT
# --------------------------------------------------

def assign_faculty(slot, faculty_pool, count):

    key = (slot.exam_date, slot.slot_code)

    if key not in faculty_registry:
        faculty_registry[key] = set()

    assigned = []

    shuffled = faculty_pool.copy()
    random.shuffle(shuffled)

    for f in shuffled:

        if len(assigned) >= count:
            break

        if f.id not in faculty_registry[key]:

            assigned.append(f)
            faculty_registry[key].add(f.id)

    while len(assigned) < count:
        assigned.append(None)

    return assigned


# --------------------------------------------------
# MAIN SEATING GENERATOR
# --------------------------------------------------

def generate_seating_plan(slot_id):

    try:

        with transaction.atomic():

            slot = ExamSlot.objects.get(id=slot_id)

            SeatingPlan.objects.filter(exam_slot=slot).delete()
            InvigilationDuty.objects.filter(exam_slot=slot).delete()

            exams = Exam.objects.filter(exam_slot=slot)

            students = list(
                StudentExamMap.objects.filter(
                    exam__in=exams
                ).select_related("student", "exam__course")
            )

            # distribute courses first
            students = distribute_students_by_course(students)

            rooms_alloc = list(
                RoomAllocation.objects.filter(
                    exam_slot=slot
                ).select_related("room")
            )

            faculty_avail = list(
                FacultyAvailability.objects.filter(
                    exam_slot=slot,
                    is_active=True
                ).select_related("faculty")
            )

            faculty_pool = [f.faculty for f in faculty_avail]

            rooms = sorted(
                [r.room for r in rooms_alloc],
                key=lambda x: x.rows * x.columns,
                reverse=True
            )

            seating_objects = []

            index = 0

            for room in rooms:

                rows = room.rows
                cols = room.columns

                capacity = rows * cols

                buffer = calculate_buffer(capacity)

                usable = capacity - buffer

                chunk = students[index:index + usable]

                if not chunk:
                    continue

                index += len(chunk)

                course_counts = {}

                for s in chunk:

                    c = s.exam.course.course_code

                    course_counts[c] = (
                        course_counts.get(c, 0) + 1
                    )

                # SINGLE COURSE CASE
                if len(course_counts) == 1:
                    seats = [
                        (r, c)
                        for r in range(rows)
                        for c in range(cols)
                        if c % 2 == 0
                    ]
                    seat_count = len(seats)
                    student_count = len(chunk)
                    assign_count = min(seat_count, student_count)
                    # Assign only up to available seats
                    for i in range(assign_count):
                        smap = chunk[i]
                        r, c = seats[i]
                        seating_objects.append(
                            SeatingPlan(
                                student_exam=smap,
                                exam_slot=slot,
                                room=room,
                                row_no=r,
                                seat_no=c
                            )
                        )
                    # If more students than seats, skip or handle overflow (could log or assign to next room)
                    continue

                status, solver, seat_vars = solve_seating(
                    rows,
                    cols,
                    course_counts
                )

                students_by_course = {}

                for s in chunk:

                    c = s.exam.course.course_code

                    students_by_course.setdefault(
                        c, []
                    ).append(s)

                if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:

                    for r in range(rows):
                        for c in range(cols):

                            for course in course_counts:

                                if solver.BooleanValue(
                                    seat_vars[(r, c, course)]
                                ):

                                    smap = students_by_course[
                                        course
                                    ].pop()

                                    seating_objects.append(
                                        SeatingPlan(
                                            student_exam=smap,
                                            exam_slot=slot,
                                            room=room,
                                            row_no=r,
                                            seat_no=c
                                        )
                                    )

                else:

                    # fallback
                    courses = list(course_counts.keys())

                    interleaved = []

                    while any(students_by_course.values()):

                        for c in courses:

                            if students_by_course[c]:
                                interleaved.append(
                                    students_by_course[c].pop()
                                )

                    for i, smap in enumerate(interleaved):

                        r = i // cols
                        c = i % cols

                        seating_objects.append(
                            SeatingPlan(
                                student_exam=smap,
                                exam_slot=slot,
                                room=room,
                                row_no=r,
                                seat_no=c
                            )
                        )

            SeatingPlan.objects.bulk_create(seating_objects)

            # --------------------------------------------------
            # FACULTY ALLOCATION
            # --------------------------------------------------

            invigilation_objects = []

            for room in rooms:

                count = SeatingPlan.objects.filter(
                    exam_slot=slot,
                    room=room
                ).count()

                needed = calculate_faculty_needed(count)

                assigned = assign_faculty(
                    slot,
                    faculty_pool,
                    needed
                )

                for f in assigned:

                    invigilation_objects.append(
                        InvigilationDuty(
                            exam_slot=slot,
                            faculty=f,
                            room=room
                        )
                    )

            InvigilationDuty.objects.bulk_create(invigilation_objects)

            slot.is_generated = True
            slot.generated_at = timezone.now()
            slot.save()

            return {
                "status": "success",
                "seats_created": len(seating_objects)
            }

    except Exception as e:

        return {
            "status": "error",
            "error": str(e)
        }