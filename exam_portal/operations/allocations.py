import random
import math
from collections import defaultdict
from django.db import transaction
from django.utils import timezone
from ortools.sat.python import cp_model

from operations.models import (
    ExamSlot, Exam, StudentExamMap,
    RoomAllocation, FacultyAvailability,
    InvigilationDuty, SeatingPlan
)

# --------------------------------------------------
# SEAT HELPERS
# --------------------------------------------------

def get_all_seats(rows, cols):
    return [(r, c) for r in range(rows) for c in range(cols)]


def get_safe_seats(rows, cols):
    return [(r, c) for r in range(rows) for c in range(cols) if (r + c) % 2 == 0]


def get_zigzag_seats(rows, cols):
    seats = []
    for r in range(rows):
        if r % 2 == 0:
            seats.extend([(r, c) for c in range(cols)])
        else:
            seats.extend([(r, c) for c in reversed(range(cols))])
    return seats


# --------------------------------------------------
# SAFE CAPACITY HELPER
# --------------------------------------------------
def get_safe_capacity(room):
    return len(get_safe_seats(room.rows, room.columns))


# --------------------------------------------------
# ROOM ESTIMATION (WITH BUFFER)
# --------------------------------------------------

def estimate_rooms_optimized(students, rooms):

    required_total = int(len(students) * 1.05)  # 5% buffer
    
    subject_counts = defaultdict(int)
    for s in students:
        subject_counts[s.exam.course.course_code] += 1
        
    required_safe = int(max(subject_counts.values()) * 1.05) if subject_counts else 0

    rooms_sorted = sorted(
        rooms,
        key=lambda r: r.rows * r.columns,
        reverse=True
    )

    selected = []
    total = 0
    total_safe = 0

    for room in rooms_sorted:
        cap = room.rows * room.columns
        safe_cap = get_safe_capacity(room)
        selected.append(room)
        total += cap
        total_safe += safe_cap
        if total >= required_total and total_safe >= required_safe:
            break

    return selected


# --------------------------------------------------
# GROUP STUDENTS
# --------------------------------------------------

def group_students_by_subject(students):
    subject_map = defaultdict(list)
    for s in students:
        subject_map[s.exam.course.course_code].append(s)
    return subject_map


# --------------------------------------------------
# FIXED DISTRIBUTION (NO LOSSES)
# --------------------------------------------------

def distribute_students(subject_map, rooms):

    room_caps = {r.id: r.rows * r.columns for r in rooms}
    room_safe_caps = {r.id: get_safe_capacity(r) for r in rooms}
    room_buckets = {r.id: [] for r in rooms}
    room_course_counts = {r.id: defaultdict(int) for r in rooms}

    # flatten all students
    all_students = []
    for students in subject_map.values():
        all_students.extend(students)

    random.shuffle(all_students)

    room_ids = list(room_buckets.keys())
    room_index = 0

    for smap in all_students:

        placed = False
        course = smap.exam.course.course_code

        for _ in range(len(room_ids)):

            rid = room_ids[room_index % len(room_ids)]

            if len(room_buckets[rid]) < room_caps[rid] and room_course_counts[rid][course] < room_safe_caps[rid]:
                room_buckets[rid].append(smap)
                room_course_counts[rid][course] += 1
                placed = True
                room_index += 1
                break

            room_index += 1

        # fallback safety
        if not placed:
            for rid in room_ids:
                if len(room_buckets[rid]) < room_caps[rid]:
                    room_buckets[rid].append(smap)
                    room_course_counts[rid][course] += 1
                    placed = True
                    break

    # validation
    total = sum(len(v) for v in room_buckets.values())
    if total != len(all_students):
        raise Exception("❌ Student distribution failed!")

    return room_buckets


# --------------------------------------------------
# CP-SAT (8-WAY)
# --------------------------------------------------

def solve_8way(rows, cols, course_counts):

    seats = get_all_seats(rows, cols)
    model = cp_model.CpModel()
    seat_vars = {}

    courses = list(course_counts.keys())

    for (r, c) in seats:
        for course in courses:
            seat_vars[(r, c, course)] = model.NewBoolVar(f"s_{r}_{c}_{course}")
        model.Add(sum(seat_vars[(r, c, course)] for course in courses) <= 1)

    for course, count in course_counts.items():
        model.Add(sum(seat_vars[(r, c, course)] for (r, c) in seats) == count)

    # 8-direction constraint
    for course in courses:
        for r in range(rows):
            for c in range(cols):
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            model.Add(
                                seat_vars[(r, c, course)] +
                                seat_vars[(nr, nc, course)] <= 1
                            )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10

    status = solver.Solve(model)
    return status, solver, seat_vars, seats


# --------------------------------------------------
# CP-SAT (4-WAY)
# --------------------------------------------------

def solve_4way(rows, cols, course_counts):

    seats = get_all_seats(rows, cols)
    model = cp_model.CpModel()
    seat_vars = {}

    courses = list(course_counts.keys())

    for (r, c) in seats:
        for course in courses:
            seat_vars[(r, c, course)] = model.NewBoolVar(f"s_{r}_{c}_{course}")
        model.Add(sum(seat_vars[(r, c, course)] for course in courses) <= 1)

    for course, count in course_counts.items():
        model.Add(sum(seat_vars[(r, c, course)] for (r, c) in seats) == count)

    directions = [(-1,0),(1,0),(0,-1),(0,1)]

    for course in courses:
        for r in range(rows):
            for c in range(cols):
                for dr, dc in directions:
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        model.Add(
                            seat_vars[(r,c,course)] +
                            seat_vars[(nr,nc,course)] <= 1
                        )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 8

    status = solver.Solve(model)
    return status, solver, seat_vars, seats


# --------------------------------------------------
# ZIG-ZAG FALLBACK
# --------------------------------------------------

def fallback_zigzag(students_by_course, rows, cols):

    seats = get_zigzag_seats(rows, cols)
    grid = {}
    result = []

    ordered = []
    courses = list(students_by_course.keys())

    while any(students_by_course.values()):
        for c in courses:
            if students_by_course[c]:
                ordered.append(students_by_course[c].pop())

    unplaced = []

    for smap in ordered:

        course = smap.exam.course.course_code
        placed = False

        for (r, c) in seats:

            if (r, c) in grid:
                continue

            left = (r, c - 1)
            right = (r, c + 1)

            if left in grid and grid[left] == course:
                continue
            if right in grid and grid[right] == course:
                continue

            grid[(r, c)] = course
            result.append((smap, r, c))
            placed = True
            break
            
        if not placed:
            unplaced.append(smap)

    # Force placement of unplaced students into any available seat
    for smap in unplaced:
        course = smap.exam.course.course_code
        for (r, c) in seats:
            if (r, c) not in grid:
                grid[(r, c)] = course
                result.append((smap, r, c))
                break

    return result


# --------------------------------------------------
# FACULTY RULE (BEST VERSION)
# --------------------------------------------------

def faculty_required(student_count):

    if student_count == 0:
        return 0

    return min(4, math.ceil(student_count / 60))


# --------------------------------------------------
# MAIN FUNCTION
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

            rooms = [
                r.room for r in RoomAllocation.objects.filter(exam_slot=slot)
            ]

            faculty_pool = [
                f.faculty for f in FacultyAvailability.objects.filter(
                    exam_slot=slot, is_active=True
                )
            ]

            # ---------------- ROOM SELECTION ----------------
            selected_rooms = estimate_rooms_optimized(students, rooms)

            # ---------------- DISTRIBUTION ----------------
            subject_map = group_students_by_subject(students)
            room_distribution = distribute_students(subject_map, selected_rooms)

            # remove empty rooms
            selected_rooms = [
                r for r in selected_rooms if len(room_distribution[r.id]) > 0
            ]

            seating_objects = []

            # ---------------- SEATING ----------------
            for room in selected_rooms:

                chunk = room_distribution[room.id]
                rows, cols = room.rows, room.columns

                course_counts = defaultdict(int)
                students_by_course = defaultdict(list)

                for s in chunk:
                    c = s.exam.course.course_code
                    course_counts[c] += 1
                    students_by_course[c].append(s)

                # SINGLE SUBJECT
                if len(course_counts) == 1:

                    seats = get_safe_seats(rows, cols)

                    for i, smap in enumerate(list(students_by_course.values())[0]):
                        if i >= len(seats):
                            break
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

                else:

                    max_sub = max(course_counts.values())
                    cap = rows * cols

                    # 8-WAY
                    if max_sub <= cap // 2:

                        status, solver, seat_vars, seats = solve_8way(rows, cols, course_counts)

                        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:

                            for (r, c) in seats:
                                for course in course_counts:
                                    if solver.BooleanValue(seat_vars[(r, c, course)]):
                                        smap = students_by_course[course].pop()
                                        seating_objects.append(
                                            SeatingPlan(
                                                student_exam=smap,
                                                exam_slot=slot,
                                                room=room,
                                                row_no=r,
                                                seat_no=c
                                            )
                                        )
                            continue

                    # 4-WAY
                    status, solver, seat_vars, seats = solve_4way(rows, cols, course_counts)

                    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:

                        for (r, c) in seats:
                            for course in course_counts:
                                if solver.BooleanValue(seat_vars[(r, c, course)]):
                                    smap = students_by_course[course].pop()
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

                        fallback = fallback_zigzag(students_by_course, rows, cols)

                        for smap, r, c in fallback:
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

            # ---------------- FACULTY ----------------
            invigilation = []
            random.shuffle(faculty_pool)
            idx = 0

            for room in selected_rooms:

                student_count = len(room_distribution[room.id])
                needed = faculty_required(student_count)

                for _ in range(needed):

                    if idx >= len(faculty_pool):
                        break

                    invigilation.append(
                        InvigilationDuty(
                            exam_slot=slot,
                            faculty=faculty_pool[idx],
                            room=room
                        )
                    )
                    idx += 1

            InvigilationDuty.objects.bulk_create(invigilation)

            slot.is_generated = True
            slot.generated_at = timezone.now()
            slot.save()

            return {
                "status": "success",
                "rooms_used": len(selected_rooms),
                "students_assigned": len(seating_objects)
            }

    except Exception as e:
        return {"status": "error", "error": str(e)}