import math
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse

def ajax_seating_plan(request):
    slot_id = request.GET.get('slot_id')
    room_id = request.GET.get('room_id')
    from .models import SeatingPlan, StudentExamMap, ExamSlot, Room
    seating = []
    if slot_id and room_id:
        plans = SeatingPlan.objects.filter(exam_slot_id=slot_id, room_id=room_id).select_related('student_exam__student', 'student_exam__exam')
        for plan in plans:
            student = plan.student_exam.student
            exam = plan.student_exam.exam
            seating.append({
                'student_id': student.student_id,
                'course_code': exam.course.course_code if exam and exam.course else '',
                'row_no': plan.row_no,
                'seat_no': plan.seat_no,
            })
    return JsonResponse({'success': True, 'seating': seating})
def seatingplan(request):
    slot_id = request.GET.get('slot_id')
    room_id = request.GET.get('room_id')
    from .models import SeatingPlan, ExamSlot, Room, Examinations, InvigilationDuty
    faculty_summary = []
    if slot_id and room_id:
        duties = InvigilationDuty.objects.filter(exam_slot_id=slot_id, room_id=room_id).select_related('faculty')
        for duty in duties:
            faculty_summary.append({
                'faculty_id': duty.faculty.faculty_id,
                'faculty_name': duty.faculty.faculty_name,
            })
    seating = SeatingPlan.objects.filter(exam_slot_id=slot_id, room_id=room_id).select_related('student_exam__student', 'student_exam__exam', 'exam_slot', 'room').order_by('row_no', 'seat_no')
    slot = ExamSlot.objects.filter(id=slot_id).first()
    room = Room.objects.filter(id=room_id).first()
    exam = slot.examination if slot else None

    # Identify user role
    is_faculty = request.user.is_authenticated and getattr(request.user, 'role', None) == "faculty"

    # Find max row and col
    max_row = 0
    max_col = 0
    seating_map = {}
    course_summary = {}
    for plan in seating:
        row = plan.row_no
        col = plan.seat_no
        if row > max_row:
            max_row = row
        if col > max_col:
            max_col = col
        if row not in seating_map:
            seating_map[row] = {}
        
        # Course info
        course_code = plan.student_exam.exam.course.course_code if plan.student_exam.exam and plan.student_exam.exam.course else ''
        
        seating_map[row][col] = {
            'student_id': plan.student_exam.student.student_id,
            'student_name': plan.student_exam.student.student_name if hasattr(plan.student_exam.student, 'student_name') else '',
            'course_code': course_code,
        }
        if course_code:
            course_summary[course_code] = course_summary.get(course_code, 0) + 1
    
    # Ensure layout boundaries
    # Use the room's actual boundaries for the grid if available
    row_range = list(range(1, (room.rows if room else max_row) + 1))
    col_range = list(range(1, (room.columns if room else max_col) + 1))

    base_template = "core/base_admin.html"
    if is_faculty:
        base_template = "core/base_faculty.html"
    
    return render(request, "operations/seatingplan.html", {
        'exam': exam,
        'room': room,
        'slot': slot,
        'seating_map': seating_map,
        'row_range': row_range,
        'col_range': col_range,
        'course_summary': course_summary,
        'faculty_summary': faculty_summary,
        'base_template': base_template,
        'is_faculty_view': is_faculty,
    })

@login_required
def mark_attendance(request):
    slot_id = request.GET.get('slot_id')
    room_id = request.GET.get('room_id')
    from .models import SeatingPlan, InvigilationDuty, Attendance, StudentExamMap, ExamSlot, Room
    from masters.models import Faculty
    
    slot = ExamSlot.objects.filter(id=slot_id).first()
    room = Room.objects.filter(id=room_id).first()
    
    # Get current faculty
    faculty = Faculty.objects.filter(user=request.user).first()
    if not faculty:
        messages.error(request, "Faculty record not found.")
        return redirect('masters:faculty_dashboard')

    # Get all students in this room
    seating = SeatingPlan.objects.filter(exam_slot_id=slot_id, room_id=room_id).select_related('student_exam__student', 'student_exam__exam').order_by('row_no', 'seat_no')
    
    # Division logic
    room_duties = InvigilationDuty.objects.filter(exam_slot_id=slot_id, room_id=room_id).order_by('faculty__faculty_id')
    faculty_count = room_duties.count()
    
    my_students = list(seating)
    if faculty_count > 1:
        my_duty_idx = -1
        for i, d in enumerate(room_duties):
            if d.faculty == faculty:
                my_duty_idx = i
                break
        
        if my_duty_idx != -1:
            total_students = len(seating)
            per_faculty = math.ceil(total_students / faculty_count)
            start = my_duty_idx * per_faculty
            end = start + per_faculty
            my_students = seating[start:end]

    # --- Time-Based Constraint Logic ---
    from datetime import datetime, timedelta
    now = datetime.now()
    exam_date = slot.exam_date
    start_time = slot.start_time
    end_time = slot.end_time
    exam_start = datetime.combine(exam_date, start_time)
    exam_end = datetime.combine(exam_date, end_time)
    exam_start_30m = exam_start + timedelta(minutes=30)

    # Check if this faculty has already posted for this slot/room
    has_posted = Attendance.objects.filter(marked_by=faculty, student_exam__exam__exam_slot=slot, room=room).exists()

    read_only = False
    if now > exam_end:
        read_only = True
        if request.method == 'POST':
            return JsonResponse({'success': False, 'error': 'Exam has ended. Transcription is no longer allowed.'})
    
    if request.method == 'POST':
        # Enforce the 30-minute rule for first-time posting
        if not has_posted and now > exam_start_30m:
             return JsonResponse({'success': False, 'error': 'Initial attendance marking window (first 30 mins) has closed.'})
        # Prevent posting before exam starts
        if now < exam_start:
             return JsonResponse({'success': False, 'error': 'Attendance marking has not started yet.'})

    if request.method == "POST":
        # Process attendance
        total_present = 0
        total_absent = 0
        
        for student_plan in my_students:
            student_exam = student_plan.student_exam
            # Check for absence
            is_absent = request.POST.get(f"absent_{student_exam.id}")
            status = 'ABSENT' if is_absent else 'PRESENT'
            
            if status == 'PRESENT':
                total_present += 1
            else:
                total_absent += 1

            Attendance.objects.update_or_create(
                student_exam=student_exam,
                defaults={'marked_by': faculty, 'status': status, 'room': room}
            )
            # Update map status
            student_exam.status = 'ATTENDED' if status == 'PRESENT' else 'ABSENT'
            student_exam.save()
        
        if request.GET.get('partial') == '1':
            return JsonResponse({
                'success': True,
                'message': f"Attendance marked for {slot.examination.exam_name} - {slot.slot_code}",
                'present': total_present,
                'absent': total_absent,
                'room_code': room.room_code,
                'exam_time': f"{slot.start_time.strftime('%I:%M %p')} - {slot.end_time.strftime('%I:%M %p')}"
            })

        messages.success(request, "Attendance marked successfully.")
        return redirect('masters:facultyview_seatingplan')

    # Get existing attendance
    attendance_data = {a.student_exam_id: a.status for a in Attendance.objects.filter(student_exam__in=[s.student_exam for s in my_students])}

    partial = request.GET.get('partial') == '1'
    template_name = "operations/partial_mark_attendance.html" if partial else "operations/mark_attendance.html"

    return render(request, template_name, {
        'slot': slot,
        'room': room,
        'students': my_students,
        'attendance_data': attendance_data,
        'base_template': "core/base_faculty.html",
        'partial': partial,
    })

def room_alloc_view(request):
    from .models import Examinations, ExamSlot, RoomAllocation, SeatingPlan, InvigilationDuty
    exam_id = request.GET.get('exam_id')
    exam = None
    exam_data = {}
    slot_rows = []
    if exam_id:
        exam = Examinations.objects.filter(id=exam_id).first()
        if exam:
            slots = ExamSlot.objects.filter(examination=exam)
            total_slots = slots.count()
            generated_slots = slots.filter(is_generated=True).count()
            # Calculate total students and assigned students
            from .models import StudentExamMap, SeatingPlan
            total_students = StudentExamMap.objects.filter(exam__in=ExamSlot.objects.filter(examination=exam).values_list('exams__id', flat=True)).count()
            assigned_students = SeatingPlan.objects.filter(exam_slot__in=slots).count()
            exam_data = {
                'exam_name': exam.exam_name,
                'academic_year': exam.academic_year,
                'semester': exam.semester,
                'start_date': exam.start_date.strftime('%Y-%m-%d'),
                'end_date': exam.end_date.strftime('%Y-%m-%d'),
                'total_slots': total_slots,
                'generated_slots': generated_slots,
                'total_students': total_students,
                'assigned_students': assigned_students,
            }
            for slot in slots:
                slot_total_students = StudentExamMap.objects.filter(exam__exam_slot=slot).count()
                slot_assigned_students = SeatingPlan.objects.filter(exam_slot=slot).count()
                room_allocs = RoomAllocation.objects.filter(exam_slot=slot).select_related('room')
                for room_alloc in room_allocs:
                    room = room_alloc.room
                    assigned_cap = SeatingPlan.objects.filter(exam_slot=slot, room=room).count()
                    invigilator_objs = InvigilationDuty.objects.filter(exam_slot=slot, room=room).select_related('faculty')
                    invigilator_ids = [str(inv.faculty.faculty_id) for inv in invigilator_objs]
                    slot_rows.append({
                        'exam_type': slot.exam_type,
                        'mode': slot.mode,
                        'exam_date': slot.exam_date.strftime('%Y-%m-%d'),
                        'start_time': slot.start_time.strftime('%H:%M'),
                        'end_time': slot.end_time.strftime('%H:%M'),
                        'slot_code': slot.slot_code,
                        'room_name': room.room_code,
                        'actual_cap': room.capacity,
                        'assigned_cap': assigned_cap,
                        'invigilator_ids': invigilator_ids,
                        'slot_id': slot.id,
                        'room_id': room.id,
                        'slot_total_students': slot_total_students,
                        'slot_assigned_students': slot_assigned_students,
                    })
    return render(request, "operations/room_alloc_view.html", {'exam': exam_data, 'slot_rows': slot_rows})
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .allocations import generate_seating_plan

# AJAX endpoint to generate seating plan for a slot
@require_POST
def ajax_generate_seating_plan(request):
    slot_id = request.POST.get('slot_id')
    if not slot_id:
        return JsonResponse({'status': 'error', 'error': 'Missing slot_id'})
    from operations.models import ExamSlot, Exam, StudentExamMap, RoomAllocation, FacultyAvailability, SeatingPlan, InvigilationDuty
    try:
        slot = ExamSlot.objects.get(pk=slot_id)
    except ExamSlot.DoesNotExist:
        return JsonResponse({'status': 'error', 'error': 'Slot not found'})
    exams = Exam.objects.filter(exam_slot=slot)
    student_maps = StudentExamMap.objects.filter(exam__in=exams)
    students_count = student_maps.count()
    rooms = RoomAllocation.objects.filter(exam_slot=slot)
    faculty_avail = FacultyAvailability.objects.filter(exam_slot=slot, is_active=True)
    seating_count = SeatingPlan.objects.filter(exam_slot=slot).count()
    invigilation_count = InvigilationDuty.objects.filter(exam_slot=slot).count()
    # If already generated, check if all assigned
    if slot.is_generated:
        all_seated = seating_count >= students_count and students_count > 0
        all_invigilated = invigilation_count >= rooms.count() and rooms.count() > 0
        if not (all_seated and all_invigilated):
            # If seating/invigilation data is missing, reset is_generated and proceed to generate
            slot.is_generated = False
            slot.save()
        if all_seated and all_invigilated:
            return JsonResponse({'status': 'assigned', 'message': 'Seating and invigilation already completed.'})
        # If not all assigned, proceed to generate seating plan
    # If not generated, proceed
    result = generate_seating_plan(slot_id)
    return JsonResponse(result)
from django.shortcuts import render
from .models import ExamSlot, Exam, StudentCourse
from masters.models import Course, Room
from django.contrib import messages

def exam_rooms_alloc(request):
    slot_id = request.GET.get('slot_id') or request.POST.get('slot_id')
    slot = None
    student_count = 0
    overlapping_room_ids = []
    rooms = Room.objects.filter(is_active=True).exclude(id__in=overlapping_room_ids)
    allocated_room_ids = []
    allocated_room_count = 0
    allocated_room_capacity = 0
    if slot_id:
        try:
            slot = ExamSlot.objects.get(id=slot_id)

            # --- Use the same estimator context as the popup (ajax.py) ---
            from operations.models import StudentExamMap
            from masters.models import Student
            from .allocations import estimate_rooms_optimized
            # Get all students for this slot (across all exams) as StudentExamMap objects
            student_exam_maps = list(StudentExamMap.objects.filter(exam__exam_slot=slot).select_related('exam__course'))
            student_count = len(student_exam_maps)
            # Use all active rooms
            available_rooms_list = list(Room.objects.filter(is_active=True))
            # Run estimator (using full room capacity, as in popup)
            estimated_rooms = estimate_rooms_optimized(student_exam_maps, available_rooms_list)
            required_room_count = len(estimated_rooms)
            required_capacity = sum([room.capacity for room in estimated_rooms])
            allocated_room_ids = [room.id for room in estimated_rooms]
            allocated_room_count = len(estimated_rooms)
            allocated_room_capacity = required_capacity

            # --- Optimized Estimator Integration ---
            from .allocations import estimate_rooms_optimized
            available_rooms_list = list(Room.objects.filter(is_active=True))
            optimized_rooms = estimate_rooms_optimized(student_exam_maps, available_rooms_list)
            optimized_room_count = len(optimized_rooms)
            optimized_capacity = sum([room.capacity for room in optimized_rooms])
            if request.method == "POST":
                from .models import RoomAllocation
                selected_room_ids = set(map(int, request.POST.getlist('selected_rooms')))
                prev_allocs = RoomAllocation.objects.filter(exam_slot=slot)
                prev_room_ids = set(prev_allocs.values_list('room_id', flat=True))
                deleted_ids = prev_room_ids - selected_room_ids
                added_ids = selected_room_ids - prev_room_ids
                prev_allocs.delete()
                for room_id in selected_room_ids:
                    try:
                        room_obj = Room.objects.get(id=room_id)
                        RoomAllocation.objects.create(exam_slot=slot, room=room_obj)
                    except Room.DoesNotExist:
                        continue
                from masters.models import Room as MasterRoom
                added_rooms = MasterRoom.objects.filter(id__in=added_ids).values_list('room_code', flat=True)
                deleted_rooms = MasterRoom.objects.filter(id__in=deleted_ids).values_list('room_code', flat=True)
                msg = "Room allocations saved."
                if added_rooms:
                    msg += f"<br>Added rooms: {', '.join(added_rooms)}"
                from django.shortcuts import redirect
                from django.urls import reverse
                request.session['room_alloc_success'] = msg
                if deleted_rooms:
                    request.session['room_alloc_warning'] = f"Deleted rooms: {', '.join(deleted_rooms)}"
                exam_obj = None
                exam_slot_obj = None
                params = {}
                from urllib.parse import urlencode
                url = reverse('operations:exams')
                if params:
                    url += '?' + urlencode(params)
                return redirect(url)
            if request.method == "GET":
                from .models import RoomAllocation
                allocated_room_ids = list(RoomAllocation.objects.filter(exam_slot=slot).values_list('room_id', flat=True))
                # Auto-select rooms if none are allocated, using safe seating estimator
                if not allocated_room_ids:
                    from .allocations import estimate_rooms_optimized, get_safe_capacity
                    from operations.models import StudentExamMap
                    # Use the student exam maps for the estimator
                    student_exam_maps_fallback = list(StudentExamMap.objects.filter(exam__exam_slot=slot).select_related('exam__course'))
                    
                    available_rooms_list = list(Room.objects.filter(is_active=True))
                    optimized_rooms = estimate_rooms_optimized(student_exam_maps_fallback, available_rooms_list)
                    # Ensure allocated rooms meet or exceed required_capacity
                    allocated_room_ids = [room.id for room in optimized_rooms]
                    allocated_rooms = [room for room in available_rooms_list if room.id in allocated_room_ids]
                    allocated_capacity = sum([get_safe_capacity(r) for r in allocated_rooms])
                    required_capacity = math.ceil(len(student_exam_maps_fallback) * 1.1)
                    if allocated_capacity < required_capacity:
                        # Add only one extra best-fit room if capacity is not met
                        extra_rooms = [room for room in available_rooms_list if room.id not in allocated_room_ids]
                        if extra_rooms:
                            best_room = max(extra_rooms, key=lambda r: get_safe_capacity(r))
                            allocated_room_ids.append(best_room.id)
            # Calculate allocated room count and capacity
            if allocated_room_ids:
                from .allocations import get_safe_capacity
                allocated_rooms = Room.objects.filter(id__in=allocated_room_ids)
                allocated_room_count = allocated_rooms.count()
                allocated_room_capacity = sum([get_safe_capacity(r) for r in allocated_rooms])
        except ExamSlot.DoesNotExist:
            slot = None
    return render(request, "operations/exam_rooms_alloc.html", {
        'slot': slot,
        'rooms': rooms,
        'allocated_room_ids': allocated_room_ids,
        'student_count': student_count,
        'required_room_count': required_room_count,
        'required_capacity': required_capacity,
        'allocated_room_count': allocated_room_count,
        'allocated_room_capacity': allocated_room_capacity,
    })

def exam_faculty_alloc(request):
    slot_id = request.GET.get('slot_id') if request.method == 'GET' else request.POST.get('slot_id')
    slot = None
    faculties = []
    total_students = 0
    allocated_faculty = 0
    from operations.models import FacultyAvailability, ExamSlot
    if not slot_id:
        debug_message = "Slot ID is missing. Please select a slot before assigning faculty."
        from .models import ExamSlot
        slots = ExamSlot.objects.filter(status="ACTIVE").order_by("exam_date", "start_time")
        return render(request, "operations/exam_faculty_alloc.html", {
            'slot': None,
            'faculties': [],
            'required_faculty': 0,
            'allocated_faculty': 0,
            'debug_message': debug_message,
            'slots': slots
        })
    from django.contrib import messages
    success_message = None
    selected_faculty_objs = []
    required_faculty = 0
    try:
        slot = ExamSlot.objects.get(id=slot_id)
        # Find overlapping slots
        overlapping_slots = ExamSlot.objects.filter(
            exam_date=slot.exam_date,
            start_time__lt=slot.end_time,
            end_time__gt=slot.start_time
        ).exclude(id=slot.id)
        # Get faculty assigned to overlapping slots
        overlapping_faculty_ids = list(FacultyAvailability.objects.filter(
            exam_slot__in=overlapping_slots
        ).values_list('faculty__faculty_id', flat=True))
        from masters.models import Faculty
        if request.method == 'POST' and 'assign_faculty' in request.POST:
            selected_faculty_ids = request.POST.getlist('selected_faculty')
            selected_faculty_ids_set = set(selected_faculty_ids)
            prev_allocated_set = set([f.faculty_id for f in Faculty.objects.filter(facultyavailability__exam_slot=slot)])
            # Find removed and added
            removed_ids = prev_allocated_set - selected_faculty_ids_set
            added_ids = selected_faculty_ids_set - prev_allocated_set
            removed_faculty_objs = []
            added_faculty_objs = []
            # Remove only deselected
            for faculty_id in removed_ids:
                FacultyAvailability.objects.filter(exam_slot=slot, faculty__faculty_id=faculty_id).delete()
                try:
                    removed_faculty_objs.append(Faculty.objects.get(faculty_id=faculty_id))
                except Faculty.DoesNotExist:
                    continue
            # Add only newly selected
            for faculty_id in added_ids:
                if faculty_id in overlapping_faculty_ids:
                    continue  # Skip assigning faculty already assigned to overlapping slot
                try:
                    faculty_obj = Faculty.objects.get(faculty_id=faculty_id)
                    FacultyAvailability.objects.create(exam_slot=slot, faculty=faculty_obj, is_active=True)
                    added_faculty_objs.append(faculty_obj)
                except Faculty.DoesNotExist:
                    continue
            msg_parts = []
            if added_faculty_objs:
                msg_parts.append("Added: " + ', '.join([f.faculty_name for f in added_faculty_objs]))
            if removed_faculty_objs:
                msg_parts.append("Removed: " + ', '.join([f.faculty_name for f in removed_faculty_objs]))
            if msg_parts:
                messages.success(request, "Faculty allocation updated. " + ' | '.join(msg_parts))
            else:
                messages.info(request, "No changes made to faculty allocation.")
            # Redirect to avoid repeated processing/messages
            from django.shortcuts import redirect
            return redirect(f'/ops/exam_faculty_alloc/?slot_id={slot.id}')
        # Always show currently allocated faculty for this slot
        allocated_faculty_objs = Faculty.objects.filter(facultyavailability__exam_slot=slot)
        from operations.models import Exam
        exams = Exam.objects.filter(exam_slot=slot)
        from operations.models import FacultyCourse
        found_assignment = False
        total_students = 0
        for exam in exams:
            academic_year = slot.examination.academic_year if slot.examination else ''
            semester = slot.examination.semester if slot.examination else ''
            from operations.models import StudentCourse
            students = StudentCourse.objects.filter(course=exam.course, academic_year=academic_year, semester=semester)
            total_students += students.count()
            faculty_courses = FacultyCourse.objects.filter(course=exam.course, academic_year=academic_year, semester=semester, is_active=True)
            for fc in faculty_courses:
                faculty_obj = fc.faculty
                if faculty_obj.faculty_id in overlapping_faculty_ids:
                    continue  # Skip faculty assigned to overlapping slot
                faculties.append({
                    'id': faculty_obj.faculty_id,
                    'name': faculty_obj.faculty_name,
                    'department': faculty_obj.dept.dept_name if faculty_obj.dept else '',
                    'course': exam.course.course_name if exam.course else '',
                    'role': faculty_obj.designation if hasattr(faculty_obj, 'designation') else ''
                })
                found_assignment = True
        allocated_faculty = len(faculties)
        # Use estimate_rooms_required to get faculty_required based on selected rooms
        # Assign required_faculty based on room capacity
        from operations.models import Room, RoomAllocation
        allocated_room_ids = list(RoomAllocation.objects.filter(exam_slot=slot).values_list('room_id', flat=True))
        allocated_rooms = Room.objects.filter(id__in=allocated_room_ids)
        # Use full room capacity for faculty estimation
        import sys
        required_faculty = 0
        for room in allocated_rooms:
            cap = room.capacity
            if cap <= 60:
                fac = 1
            elif cap <= 120:
                fac = 2
            elif cap <= 180:
                fac = 3
            else:
                fac = 4
            print(f"[DEBUG] Room {room.room_code} cap={cap} => faculty={fac}", file=sys.stdout, flush=True)
            required_faculty += fac
        # Show a warning if not enough faculty are available
        available_faculty_count = Faculty.objects.filter(status='ACTIVE').exclude(faculty_id__in=overlapping_faculty_ids).count()
        faculty_shortage_warning = None
        if available_faculty_count < required_faculty:
            faculty_shortage_warning = f"Warning: Only {available_faculty_count} faculty available for {required_faculty} rooms. Some rooms may not be assigned faculty."
        if not found_assignment:
            active_faculty = Faculty.objects.filter(status='ACTIVE').exclude(faculty_id__in=overlapping_faculty_ids)
            for faculty_obj in active_faculty:
                faculties.append({
                    'id': faculty_obj.faculty_id,
                    'name': faculty_obj.faculty_name,
                    'department': faculty_obj.dept.dept_name if faculty_obj.dept else '',
                    'course': '',
                    'role': faculty_obj.designation if hasattr(faculty_obj, 'designation') else ''
                })
            allocated_faculty = len(active_faculty)
    except ExamSlot.DoesNotExist:
        slot = None
        allocated_faculty_objs = []
    allocated_faculty_ids = [f.faculty_id for f in allocated_faculty_objs]
    return render(request, "operations/exam_faculty_alloc.html", {
        'slot': slot,
        'faculties': faculties,
        'required_faculty': required_faculty,
        'allocated_faculty': allocated_faculty,
        'success_message': success_message,
        'allocated_faculty_objs': allocated_faculty_objs,
        'allocated_faculty_ids': allocated_faculty_ids,
        'faculty_shortage_warning': faculty_shortage_warning
    })
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

from django.db import transaction

def delete_exam_and_related(exam_id):
    from .models import Examinations, ExamSlot, Exam, StudentExamMap, RoomAllocation, FacultyAvailability, InvigilationDuty, SeatingPlan, Attendance
    with transaction.atomic():
        exam = Examinations.objects.filter(id=exam_id).first()
        if not exam:
            return False
        slots = ExamSlot.objects.filter(examination=exam)
        for slot in slots:
            exams = Exam.objects.filter(exam_slot=slot)
            for e in exams:
                # Delete student exam maps and attendance
                student_maps = StudentExamMap.objects.filter(exam=e)
                for sm in student_maps:
                    Attendance.objects.filter(student_exam=sm).delete()
                SeatingPlan.objects.filter(student_exam__in=student_maps).delete()
                student_maps.delete()
                e.delete()
            RoomAllocation.objects.filter(exam_slot=slot).delete()
            FacultyAvailability.objects.filter(exam_slot=slot).delete()
            InvigilationDuty.objects.filter(exam_slot=slot).delete()
            SeatingPlan.objects.filter(exam_slot=slot).delete()
            slot.delete()
        exam.delete()
    return True

def ajax_examinations(request):
    from .models import Examinations
    page = int(request.GET.get('page', 1))
    per_page = 10
    exams = Examinations.objects.order_by('-start_date', '-end_date', 'exam_name')
    paginator = Paginator(exams, per_page)
    page_obj = paginator.get_page(page)
    results = []
    from operations.models import ExamSlot
    for idx, exam in enumerate(page_obj.object_list, start=1 + (page_obj.number-1)*per_page):
        slots = ExamSlot.objects.filter(examination=exam)
        all_generated = slots.exists() and all([slot.is_generated for slot in slots])
        # Revoke published status if any slot is not generated
        if not all_generated and exam.published:
            exam.published = False
            exam.save()
        results.append({
            'number': idx,
            'exam_id': exam.id,
            'exam_name': exam.exam_name,
            'academic_year': getattr(exam, 'academic_year', ''),
            'semester': getattr(exam, 'semester', ''),
            'start_date': exam.start_date.strftime('%Y-%m-%d'),
            'end_date': exam.end_date.strftime('%Y-%m-%d'),
            'published': exam.published,
        })
    return JsonResponse({
        'results': results,
        'page': page_obj.number,
        'num_pages': paginator.num_pages,
        'total': paginator.count
    })
@login_required
def examination(request):
    from .models import Examinations
    import datetime
    today = datetime.date.today()
    from .models import StudentCourse
    acd_years = StudentCourse.objects.values_list('academic_year', flat=True).distinct().order_by('academic_year')
    semesters = StudentCourse.objects.values_list('semester', flat=True).distinct().order_by('semester')
    if request.method == "POST":
        # Handle exam deletion
        if request.POST.get("delete_exam_id"):
            delete_exam_id = request.POST.get("delete_exam_id")
            success = delete_exam_and_related(delete_exam_id)
            if success:
                messages.success(request, "Exam and all related data deleted successfully.")
            else:
                messages.error(request, "Failed to delete exam. Exam not found.")
            # After deletion, skip further processing
            return render(request, "operations/examination.html", {"form_data": {}, "today": today, "acd_years": acd_years, "semesters": semesters})
        exam_name = request.POST.get("examname", "").strip()
        academic_year = request.POST.get("academic_year", "").strip()
        semester = request.POST.get("semester", "").strip()
        start_date = request.POST.get("start_date", "").strip()
        end_date = request.POST.get("end_date", "").strip()
        form_data = {
            'examname': exam_name,
            'academic_year': academic_year,
            'semester': semester,
            'start_date': start_date,
            'end_date': end_date
        }
        # Validate all fields present
        if not exam_name or not academic_year or not semester or not start_date or not end_date:
            messages.error(request, "Provide all fields.")
            return render(request, "operations/examination.html", {"form_data": form_data, "today": today, "acd_years": acd_years, "semesters": semesters})
        # Validate date order
        try:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        except Exception:
            messages.error(request, "Invalid date format.")
            return render(request, "operations/examination.html", {"form_data": form_data, "today": today, "acd_years": acd_years, "semesters": semesters})
        if start_dt < today:
            messages.error(request, "Start date must be today or a future date.")
            return render(request, "operations/examination.html", {"form_data": form_data, "today": today, "acd_years": acd_years, "semesters": semesters})
        if start_dt >= end_dt:
            messages.error(request, "Start date must be before end date.")
            return render(request, "operations/examination.html", {"form_data": form_data, "today": today, "acd_years": acd_years, "semesters": semesters})
        # Check for duplicate exam name (case-insensitive) with same dates and academic year/semester
        existing_exam = Examinations.objects.filter(
            exam_name__iexact=exam_name,
            academic_year=academic_year,
            semester=semester,
            start_date=start_date,
            end_date=end_date
        ).first()
        if existing_exam:
            messages.error(request, "An exam with the same name, academic year, semester, and dates already exists.")
            return render(request, "operations/examination.html", {"form_data": form_data, "today": today, "acd_years": acd_years, "semesters": semesters})
        # Save to DB
        try:
            Examinations.objects.create(
                exam_name=exam_name,
                academic_year=academic_year,
                semester=semester,
                start_date=start_date,
                end_date=end_date
            )
            messages.success(request, "Exam dates declared successfully.")
            from django.shortcuts import redirect
            return redirect('operations:examination')
        except Exception as e:
            messages.error(request, f"Error saving examination: {e}")
            return render(request, "operations/examination.html", {"form_data": form_data, "today": today})
    return render(request, "operations/examination.html", {"form_data": {}, "today": today, "acd_years": acd_years, "semesters": semesters})


def attendence(request):
    return render(request, "operations/attendence.html")

@login_required
def exams(request):
    # from .models import Exam (already imported at top)
    slot_list = ExamSlot.objects.all().order_by('-exam_date', '-start_time')
    # Build a dict of slot_id to status
    exam_status = {}
    for slot in slot_list:
        from operations.models import Exam
        if Exam.objects.filter(exam_slot=slot).exists():
            exam_status[slot.id] = 'Created'
        else:
            exam_status[slot.id] = 'Pending'

    # Show room allocation messages from session
    from django.contrib import messages
    if request.session.get('room_alloc_success'):
        messages.success(request, request.session['room_alloc_success'])
        del request.session['room_alloc_success']
    if request.session.get('room_alloc_warning'):
        messages.warning(request, request.session['room_alloc_warning'])
        del request.session['room_alloc_warning']

    # Get examname from Examinations table using exam_id from GET parameters
    from .models import StudentCourse
    reg_types = list(StudentCourse.objects.values_list('registration_type', flat=True).distinct().order_by('registration_type'))
    
    exam_id = request.GET.get('exam_id')
    q_reg_type = request.GET.get('registration_type') or ''
    examname = ''
    if exam_id:
        try:
            from .models import Examinations
            exam_obj = Examinations.objects.filter(id=exam_id).first()
            if exam_obj:
                examname = exam_obj.exam_name
        except Exception:
            examname = ''

    q_start_date = request.GET.get('start_date') or request.POST.get('start_date') or ''
    q_end_date = request.GET.get('end_date') or request.POST.get('end_date') or ''
    if request.method == "POST":
        exam_id = request.POST.get("exam_id", "").strip()
        exam_name = request.POST.get("examname", "").strip()
        exam_type = request.POST.get("examtype", "")
        mode = request.POST.get("mode", "")
        reg_type = request.POST.get("registration_type", "REGULAR")
        if mode and len(mode) > 25:
            mode = mode[:25]
        exam_date = request.POST.get("exam_date", "")
        start_time = request.POST.get("starttime", "")
        end_time = request.POST.get("endtime", "")
        slot_code = request.POST.get("slot_code", "")
        form_data = dict(request.POST)
        form_data['examname'] = exam_name or examname
        # Basic validation
        required_fields = {
            'Exam Name': exam_name,
            'Exam Type': exam_type,
            'Mode': mode,
            'Exam Date': exam_date,
            'Start Time': start_time,
            'End Time': end_time,
            'Slot Code': slot_code,
            'Registration Type': reg_type
        }
        missing = [name for name, value in required_fields.items() if not value]
        if missing:
            formatted = '\n'.join([f"- {field}" for field in missing])
            messages.error(request, f"Please fill the following required fields:\n{formatted}")
            return render(request, "operations/exams.html", {
                'form_data': form_data,
                'slot_list': slot_list,
                'exam_status': exam_status,
                'examname': examname,
                'q_start_date': q_start_date,
                'q_end_date': q_end_date,
                'reg_types': reg_types,
                'q_reg_type': q_reg_type
            })

        import datetime
        today = datetime.date.today()
        try:
            exam_date_obj = datetime.datetime.strptime(exam_date, "%Y-%m-%d").date()
        except ValueError:
            messages.error(request, "Invalid exam date format.")
            return render(request, "operations/exams.html", {
                'form_data': form_data,
                'slot_list': slot_list,
                'exam_status': exam_status,
                'examname': examname,
                'q_start_date': q_start_date,
                'q_end_date': q_end_date,
                'reg_types': reg_types,
                'q_reg_type': q_reg_type
            })
        if exam_date_obj < today:
            messages.error(request, "Exam date must be today or later.")
            return render(request, "operations/exams.html", {
                'form_data': form_data,
                'slot_list': slot_list,
                'exam_status': exam_status,
                'examname': examname,
                'q_start_date': q_start_date,
                'q_end_date': q_end_date,
                'reg_types': reg_types,
                'q_reg_type': q_reg_type
            })

        try:
            start_time_obj = datetime.datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = datetime.datetime.strptime(end_time, "%H:%M").time()
        except ValueError:
            messages.error(request, "Invalid time format.")
            return render(request, "operations/exams.html", {
                'form_data': request.POST,
                'reg_types': reg_types,
                'q_reg_type': q_reg_type
            })
        if start_time_obj >= end_time_obj:
            messages.error(request, "Start time should be before end time.")
            return render(request, "operations/exams.html", {
                'form_data': request.POST,
                'reg_types': reg_types,
                'q_reg_type': q_reg_type
            })
        # Direct assignment for exam_type, mode, and slot_code
        # Map exam type to short code to fit DB column
        exam_type_map = {
            "Regular": "REGULAR",
            "Supplementary": "SUPPLY",
            "Improvement": "IMPROVE",
            "Backlog": "BACKLOG"
        }
        exam_type_db = exam_type_map.get(exam_type, "REGULAR")
        mode_db = mode
        slot_code_db = slot_code
        try:
            exam_obj = None
            if exam_id:
                exam_obj = Examinations.objects.filter(id=exam_id).first()
            elif exam_name:
                exam_obj = Examinations.objects.filter(exam_name=exam_name).first()

            # Check for slot clash with all required fields
            clash_exists = ExamSlot.objects.filter(
                exam_date=exam_date,
                start_time=start_time,
                end_time=end_time,
                slot_code=slot_code_db,
                exam_type=exam_type_db,
                mode=mode_db,
                registration_type=reg_type
            ).exists()
            if clash_exists:
                messages.error(request, "An exam slot with the same date, start time, end time, slot code, exam type, mode and registration type already exists.")
            else:
                slot = ExamSlot(
                    examination=exam_obj,
                    exam_type=exam_type_db,
                    mode=mode_db,
                    exam_date=exam_date,
                    start_time=start_time,
                    end_time=end_time,
                    slot_code=slot_code_db,
                    registration_type=reg_type
                )
                slot.save()
                messages.success(request, "Exam slot created successfully.")
                from django.shortcuts import redirect
                from django.urls import reverse
                import urllib.parse
                # Build query params for redirect
                query_params = {}
                if exam_id:
                    query_params['exam_id'] = exam_id
                if exam_name:
                    query_params['exam_name'] = exam_name
                if q_start_date:
                    query_params['start_date'] = q_start_date
                if q_end_date:
                    query_params['end_date'] = q_end_date
                if q_reg_type:
                    query_params['registration_type'] = q_reg_type
                url = reverse('operations:exams')
                if query_params:
                    url += '?' + urllib.parse.urlencode(query_params)
                return redirect(url)
        except Exception as e:
            messages.error(request, f"Error creating exam slot: {str(e)}")
    slot_list = ExamSlot.objects.all().order_by('-exam_date', '-start_time')
    form_data = {'examname': examname}
    return render(request, "operations/exams.html", {
        'form_data': form_data,
        'slot_list': slot_list,
        'exam_status': exam_status,
        'examname': examname,
        'q_start_date': q_start_date,
        'q_end_date': q_end_date,
        'reg_types': reg_types,
        'q_reg_type': q_reg_type
    })

def roomalloc(request):
    from .models import Examinations, ExamSlot
    exams = Examinations.objects.all().order_by('-start_date', '-end_date', 'exam_name')
    exam_list = []
    for exam in exams:
        slots = ExamSlot.objects.filter(examination=exam)
        total_slots = slots.count()
        generated_slots = slots.filter(is_generated=True).count()
        exam_list.append({
            'id': exam.id,
            'exam_name': exam.exam_name,
            'academic_year': exam.academic_year,
            'semester': exam.semester,
            'start_date': exam.start_date.strftime('%Y-%m-%d'),
            'end_date': exam.end_date.strftime('%Y-%m-%d'),
            'total_slots': total_slots,
            'generated_slots': generated_slots,
        })
    return render(request, "operations/roomalloc.html", {'exams': exam_list})

@login_required
def roomalloc_content(request):
    return render(request, "operations/roomalloc_content.html")

def report(request):
    from .models import Examinations, StudentCourse
    acd_years = StudentCourse.objects.values_list('academic_year', flat=True).distinct().order_by('-academic_year')
    exams = Examinations.objects.all().order_by('-start_date')
    return render(request, "operations/report.html", {
        'acd_years': acd_years,
        'exams': exams
    })

@login_required
def exam_scheduling(request, slot_id):
    from operations.models import StudentCourse, Exam
    from masters.models import Course
    slot = ExamSlot.objects.get(id=slot_id)
    # Handle POST for scheduling selected groups
    if request.method == "POST":
        selected = request.POST.getlist('selected_groups')
        # Get filter values from POST
        # Always use slot/examination context for filters
        filter_academic_year = slot.examination.academic_year if slot.examination else ''
        filter_semester = slot.examination.semester if slot.examination else ''
        filter_regulation = slot.regulation if hasattr(slot, 'regulation') else ''
        created = 0
        from operations.models import StudentExamMap, StudentCourse
        import logging
        logging.info(f"Scheduling POST: filter_academic_year={filter_academic_year}, filter_semester={filter_semester}, filter_regulation={filter_regulation}")
        import collections
        error_groups = collections.defaultdict(list)
        for group in selected:
            # group format: course_code|regulation|academic_year|semester
            try:
                logging.info(f"Raw group value: {group}")
                course_code, regulation, academic_year, semester = group.split('|')
                logging.info(f"Parsed group: course_code={course_code}, regulation={regulation}, academic_year={academic_year}, semester={semester}")
                # Only schedule if matches slot/examination context
                if (filter_academic_year and academic_year != filter_academic_year) or \
                    (filter_semester and semester != filter_semester) or \
                    (filter_regulation and regulation != filter_regulation):
                    logging.info("Group skipped due to filter mismatch.")
                    continue
                course = Course.objects.get(course_code=course_code)
                # Check if Exam for this group and slot already exists
                from operations.models import Exam
                existing_exam = Exam.objects.filter(
                    exam_slot=slot,
                    course=course,
                    regulation=regulation
                ).first()
                if existing_exam:
                    logging.info(f"Exam already exists for group {group} in slot {slot_id}, skipping.")
                    continue
                # Create new Exam
                exam = Exam.objects.create(
                    exam_slot=slot,
                    course=course,
                    regulation=regulation
                )
                students = StudentCourse.objects.filter(
                    course=course,
                    academic_year=filter_academic_year,
                    semester=filter_semester,
                    student__batch__batch_code=regulation,
                    registration_type=slot.registration_type
                ).select_related('student')
                logging.info(f"StudentCourse Query: course={course_code}, academic_year={filter_academic_year}, semester={filter_semester}, batch_code={regulation}, registration_type={slot.registration_type}")
                logging.info(f"Scheduling group {group}: Found {students.count()} students.")
                logging.info(f"Student IDs: {[reg.student.id for reg in students]}")
                for reg in students:
                    StudentExamMap.objects.create(
                        exam=exam,
                        student=reg.student,
                        attempt_type=slot.registration_type,
                        status="REGISTERED"
                    )
                created += 1
            except Exception as e:
                import logging
                logging.exception(f"Error scheduling exam for group {group}: {e}")
                error_groups[str(e)].append(group)

        if error_groups:
            for msg, groups in error_groups.items():
                groups_str = ", ".join(groups)
                messages.error(request, f"Error for groups [{groups_str}]: {msg}")

        from django.shortcuts import redirect
        if created:
            messages.success(request, f"Scheduled {created} exam(s) successfully.")
            from django.urls import reverse
            return redirect(reverse('operations:schedule_exam', kwargs={'slot_id': slot_id}))
        elif not error_groups:
            messages.error(request, "No exams were scheduled. Please try again.")
    # Only fetch filter values for dropdowns
    courseregs = StudentCourse.objects.all()
    academic_years = sorted(set(courseregs.values_list('academic_year', flat=True)))
    semesters = sorted(set(courseregs.values_list('semester', flat=True)), key=str)
    regulations = sorted(set(courseregs.values_list('student__batch__batch_code', flat=True)))
    exam_name = slot.examination.exam_name if slot.examination else ''
    return render(request, "operations/exam_scheduling.html", {
        'slot': slot,
        'exam_name': exam_name,
        'academic_years': academic_years,
        'semesters': semesters,
        'regulations': regulations,
    })

def report_timetable(request):
    from .models import Examinations, ExamSlot
    from django.shortcuts import render
    exam_id = request.GET.get('exam_id')
    exams = Examinations.objects.all().order_by('-start_date')
    
    exam = None
    slots = []
    if exam_id:
        try:
            exam = Examinations.objects.get(id=exam_id)
            slots = ExamSlot.objects.filter(examination=exam).order_by('exam_date', 'start_time')
        except Examinations.DoesNotExist:
            pass
    
    return render(request, "operations/reports/timetable.html", {
        'exams': exams,
        'exam': exam,
        'slots': slots,
        'selected_exam_id': exam_id
    })

def report_room_occupancy(request):
    from .models import Examinations, ExamSlot, RoomAllocation, SeatingPlan
    from django.shortcuts import render
    exam_id = request.GET.get('exam_id')
    exams = Examinations.objects.all().order_by('-start_date')
    
    exam = None
    report_data = []
    if exam_id:
        try:
            exam = Examinations.objects.get(id=exam_id)
            slots = ExamSlot.objects.filter(examination=exam).order_by('exam_date')
            for slot in slots:
                allocations = RoomAllocation.objects.filter(exam_slot=slot).select_related('room')
                for alloc in allocations:
                    seated_count = SeatingPlan.objects.filter(exam_slot=slot, room=alloc.room).count()
                    utilization = round((seated_count / alloc.room.capacity) * 100, 1) if alloc.room.capacity > 0 else 0
                    
                    # Determine color class or hex
                    if utilization > 90:
                        util_color = "#ef4444"
                        util_status = "high"
                    elif utilization > 70:
                        util_color = "#f59e0b"
                        util_status = "med"
                    else:
                        util_color = "#10b981"
                        util_status = "low"

                    report_data.append({
                        'slot': slot,
                        'room': alloc.room,
                        'capacity': alloc.room.capacity,
                        'seated': seated_count,
                        'utilization': utilization,
                        'util_color': util_color,
                        'util_status': util_status
                    })
        except Examinations.DoesNotExist:
            pass
            
    return render(request, "operations/reports/room_occupancy.html", {
        'exams': exams,
        'exam': exam,
        'report_data': report_data,
        'selected_exam_id': exam_id
    })

def report_student_coursereg(request):
    from .models import StudentCourse
    from django.db.models import Count
    from django.shortcuts import render
    acd_year = request.GET.get('acd_year')
    acd_years = StudentCourse.objects.values_list('academic_year', flat=True).distinct().order_by('-academic_year')
    
    regs = StudentCourse.objects.all()
    if acd_year:
        regs = regs.filter(academic_year=acd_year)
    
    summary = regs.values('course__course_code', 'course__course_name', 'registration_type') \
                  .annotate(count=Count('id')) \
                  .order_by('course__course_code')
    
    return render(request, "operations/reports/student_coursereg.html", {
        'summary': summary,
        'acd_year': acd_year,
        'acd_years': acd_years
    })

def report_invigilation(request):
    from .models import Examinations, ExamSlot, InvigilationDuty
    from django.shortcuts import render
    exam_id = request.GET.get('exam_id')
    exams = Examinations.objects.all().order_by('-start_date')
    
    exam = None
    report_data = []
    if exam_id:
        try:
            exam = Examinations.objects.get(id=exam_id)
            duties = InvigilationDuty.objects.filter(exam_slot__examination=exam).select_related('exam_slot', 'faculty', 'room').order_by('exam_slot__exam_date', 'exam_slot__slot_code', 'room__room_code')
            report_data = duties
        except Examinations.DoesNotExist:
            pass
            
    return render(request, "operations/reports/invigilation.html", {
        'exams': exams,
        'exam': exam,
        'report_data': report_data,
        'selected_exam_id': exam_id
    })

def report_master_seating(request):
    from .models import Examinations, SeatingPlan
    from django.shortcuts import render
    exam_id = request.GET.get('exam_id')
    exams = Examinations.objects.all().order_by('-start_date')
    
    exam = None
    report_data = []
    if exam_id:
        try:
            exam = Examinations.objects.get(id=exam_id)
            plans = SeatingPlan.objects.filter(exam_slot__examination=exam).select_related('student_exam__student', 'student_exam__exam__course', 'room', 'exam_slot').order_by('exam_slot__exam_date', 'room__room_code', 'row_no', 'seat_no')
            report_data = plans
        except Examinations.DoesNotExist:
            pass
            
    return render(request, "operations/reports/master_seating.html", {
        'exams': exams,
        'exam': exam,
        'report_data': report_data,
        'selected_exam_id': exam_id
    })

def report_attendance(request):
    from .models import Examinations, ExamSlot, RoomAllocation, SeatingPlan, InvigilationDuty, Attendance, StudentExamMap
    from django.shortcuts import render
    import math
    
    exam_id = request.GET.get('exam_id')
    exams = Examinations.objects.all().order_by('-start_date')
    
    exam = None
    report_data = []
    stats = {'total': 0, 'present': 0, 'absent': 0, 'unmarked': 0}
    
    if exam_id:
        try:
            exam = Examinations.objects.get(id=exam_id)
            slots = ExamSlot.objects.filter(examination=exam).order_by('exam_date', 'slot_code')
            
            for slot in slots:
                rooms = RoomAllocation.objects.filter(exam_slot=slot).select_related('room')
                for r_alloc in rooms:
                    room = r_alloc.room
                    seating = SeatingPlan.objects.filter(exam_slot=slot, room=room).select_related('student_exam__student', 'student_exam__exam__course').order_by('row_no', 'seat_no')
                    duties = list(InvigilationDuty.objects.filter(exam_slot=slot, room=room).select_related('faculty').order_by('faculty__faculty_id'))
                    
                    student_list = list(seating)
                    total_stud = len(student_list)
                    faculty_count = len(duties)
                    
                    # Replicate division logic used in marking
                    for idx, stud_plan in enumerate(student_list):
                        stats['total'] += 1
                        assigned_faculty = None
                        if faculty_count > 0:
                            per_faculty = math.ceil(total_stud / faculty_count)
                            faculty_idx = idx // per_faculty
                            if faculty_idx < faculty_count:
                                assigned_faculty = duties[faculty_idx].faculty
                        
                        # Get actual attendance record
                        att_record = Attendance.objects.filter(student_exam=stud_plan.student_exam).first()
                        
                        status = "NOT MARKED"
                        marked_by = None
                        if att_record:
                            status = att_record.status
                            marked_by = att_record.marked_by
                            if status == "PRESENT": stats['present'] += 1
                            else: stats['absent'] += 1
                        else:
                            stats['unmarked'] += 1
                            
                        report_data.append({
                            'slot': slot,
                            'room': room,
                            'student': stud_plan.student_exam.student,
                            'course': stud_plan.student_exam.exam.course,
                            'assigned_to': assigned_faculty,
                            'marked_by': marked_by,
                            'status': status,
                            'time': att_record.marked_at if att_record else None
                        })
        except Examinations.DoesNotExist:
            pass
            
    return render(request, "operations/reports/attendance.html", {
        'exams': exams,
        'exam': exam,
        'report_data': report_data,
        'stats': stats,
        'selected_exam_id': exam_id
    })
