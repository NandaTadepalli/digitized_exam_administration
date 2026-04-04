from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Examinations
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Examinations, ExamSlot, SeatingPlan, InvigilationDuty

# AJAX endpoint to check slot completion for publish
@require_POST
@csrf_exempt
def ajax_check_exam_publishable(request):
    import json
    try:
        data = json.loads(request.body.decode('utf-8'))
        exam_id = data.get('exam_id')
        if not exam_id:
            return JsonResponse({'all_completed': False, 'published': False, 'error': 'Missing exam_id'})
        exam = Examinations.objects.filter(id=exam_id).first()
        if not exam:
            return JsonResponse({'all_completed': False, 'published': False, 'error': 'Exam not found'})
        slots = ExamSlot.objects.filter(examination=exam)
        all_completed = True
        for slot in slots:
            seating_count = SeatingPlan.objects.filter(exam_slot=slot).count()
            invigilation_count = InvigilationDuty.objects.filter(exam_slot=slot).count()
            if not slot.is_generated or seating_count == 0 or invigilation_count == 0:
                all_completed = False
                break
        return JsonResponse({'all_completed': all_completed, 'published': exam.published})
    except Exception as e:
        return JsonResponse({'all_completed': False, 'published': False, 'error': str(e)})

# AJAX endpoint to publish an examination
@csrf_exempt
def ajax_publish_exam(request):
    import json
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        exam_id = data.get('exam_id')
        if not exam_id:
            return JsonResponse({'success': False, 'error': 'Missing exam_id.'})
        exam = Examinations.objects.filter(id=exam_id).first()
        if not exam:
            return JsonResponse({'success': False, 'error': 'Examination not found.'})
        from operations.models import ExamSlot
        slots = ExamSlot.objects.filter(examination=exam)
        if not slots.exists():
            exam.published = False
            exam.save()
            return JsonResponse({'success': False, 'error': 'No slots found for this exam.'})
        # Only publish if all slots are generated
        all_generated = all([slot.is_generated for slot in slots])
        if all_generated:
            exam.published = True
            exam.save()
            return JsonResponse({'success': True})
        else:
            exam.published = False
            exam.save()
            return JsonResponse({'success': False, 'error': 'Not all slots have generated seating plan. Publishing revoked.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from operations.models import ExamSlot, FacultyAvailability
from masters.models import Faculty

# AJAX endpoint to get assigned faculty for a slot
@require_GET
def ajax_slot_faculty(request):
    slot_id = request.GET.get('slot_id')
    if not slot_id:
        return JsonResponse({'success': False, 'error': 'Missing slot_id'})
    try:
        slot = ExamSlot.objects.get(id=slot_id)
    except ExamSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slot not found'})
    assignments = FacultyAvailability.objects.filter(exam_slot=slot, is_active=True).select_related('faculty__dept')
    faculty_list = []
    for assign in assignments:
        fac = assign.faculty
        faculty_list.append({
            'faculty_id': fac.faculty_id if fac and fac.faculty_id else 'N/A',
            'faculty_name': fac.faculty_name if fac and fac.faculty_name else 'N/A',
            'email': fac.email if fac and fac.email else 'N/A',
            'dept': fac.dept.dept_name if fac and hasattr(fac, 'dept') and fac.dept and fac.dept.dept_name else 'N/A',
        })
    slot_info = {
        'exam_type': slot.exam_type or 'N/A',
        'mode': slot.mode or 'N/A',
        'exam_date': slot.exam_date.strftime('%Y-%m-%d') if slot.exam_date else 'N/A',
        'start_time': slot.start_time.strftime('%H:%M') if slot.start_time else 'N/A',
        'end_time': slot.end_time.strftime('%H:%M') if slot.end_time else 'N/A',
        'slot_code': slot.slot_code or 'N/A',
    }
    return JsonResponse({'success': True, 'slot': slot_info, 'faculty': faculty_list})
from django.views.decorators.http import require_GET

# AJAX endpoint to get course details for a slot
@require_GET
def ajax_slot_courses(request):
    from operations.models import Exam, ExamSlot, StudentExamMap
    from masters.models import Course
    slot_id = request.GET.get('slot_id')
    if not slot_id:
        return JsonResponse({'success': False, 'error': 'Missing slot_id'})
    try:
        slot = ExamSlot.objects.get(id=slot_id)
    except ExamSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slot not found'})
    exams = Exam.objects.filter(exam_slot=slot).select_related('course')
    # Get academic_year and semester from slot.examination
    academic_year = slot.examination.academic_year if slot.examination else ''
    semester = slot.examination.semester if slot.examination else ''
    course_list = []
    for exam in exams:
        course = exam.course
        if not course:
            continue
        student_count = StudentExamMap.objects.filter(exam=exam).count()
        # Try to get regulation from course's batch if available, else from exam.regulation, else 'N/A'
        regulation = 'N/A'
        if hasattr(course, 'batch') and course.batch:
            regulation = course.batch.batch_code
        elif getattr(exam, 'regulation', None):
            regulation = exam.regulation
        course_list.append({
            'course_code': course.course_code,
            'course_name': course.course_name,
            'regulation': regulation,
            'student_count': student_count,
            'academic_year': academic_year,
            'semester': semester,
        })
    slot_info = {
        'exam_type': slot.exam_type,
        'mode': slot.mode,
        'exam_date': slot.exam_date.strftime('%Y-%m-%d'),
        'start_time': slot.start_time.strftime('%H:%M'),
        'end_time': slot.end_time.strftime('%H:%M'),
        'slot_code': slot.slot_code,
    }
    return JsonResponse({'success': True, 'slot': slot_info, 'courses': course_list})
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Examinations

# AJAX endpoint to edit an examination
@csrf_exempt
def ajax_edit_examination(request):
    import json
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        exam_id = data.get('exam_id')
        try:
            exam_id = int(exam_id)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': 'Invalid exam ID.'})
        exam_name = data.get('examname', '').strip()
        academic_year = data.get('academic_year', '').strip()
        semester = data.get('semester', '').strip()
        start_date = data.get('start_date', '').strip()
        end_date = data.get('end_date', '').strip()
        if not exam_id or not exam_name or not academic_year or not semester or not start_date or not end_date:
            return JsonResponse({'success': False, 'error': 'All fields are required.'})
        exam = Examinations.objects.filter(id=exam_id).first()
        if not exam:
            return JsonResponse({'success': False, 'error': 'Examination not found.'})
        # Validate date order
        from datetime import datetime
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid date format.'})
        if start_dt >= end_dt:
            return JsonResponse({'success': False, 'error': 'Start date must be before end date.'})
        # Check for duplicate exam name (case-insensitive) with same dates, academic_year, and semester (excluding self)
        exists = Examinations.objects.filter(
            exam_name__iexact=exam_name,
            academic_year=academic_year,
            semester=semester,
            start_date=start_date,
            end_date=end_date
        ).exclude(id=exam_id).exists()
        if exists:
            return JsonResponse({'success': False, 'error': 'Another examination with this name, academic year, semester, and dates exists.'})
        exam.exam_name = exam_name
        exam.academic_year = academic_year
        exam.semester = semester
        exam.start_date = start_date
        exam.end_date = end_date
        exam.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

# AJAX endpoint to delete an examination and all related slots and exams
@csrf_exempt
def ajax_delete_examination(request):
    from .models import Examinations, ExamSlot, Exam, StudentExamMap
    import json
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        slot_id = data.get('slot_id')
        exam_id = data.get('exam_id')
        with transaction.atomic():
            if slot_id:
                slot = ExamSlot.objects.filter(id=slot_id).first()
                if not slot:
                    return JsonResponse({'success': False, 'error': 'Slot not found.'})
                exams = Exam.objects.filter(exam_slot=slot)
                for ex in exams:
                    StudentExamMap.objects.filter(exam=ex).delete()
                exams.delete()
                slot.delete()
                return JsonResponse({'success': True})
            elif exam_id:
                exam = Examinations.objects.filter(id=exam_id).first()
                if not exam:
                    return JsonResponse({'success': False, 'error': 'Examination not found.'})
                slots = ExamSlot.objects.filter(examination=exam)
                from .models import FacultyAvailability, RoomAllocation, InvigilationDuty, SeatingPlan
                from django.db import connection
                for slot in slots:
                    exams = Exam.objects.filter(exam_slot=slot)
                    for ex in exams:
                        StudentExamMap.objects.filter(exam=ex).delete()
                    exams.delete()
                    FacultyAvailability.objects.filter(exam_slot=slot).delete()
                    RoomAllocation.objects.filter(exam_slot=slot).delete()
                    InvigilationDuty.objects.filter(exam_slot=slot).delete()
                    SeatingPlan.objects.filter(exam_slot=slot).delete()
                    # Raw SQL delete for faculty_slot_selection
                    with connection.cursor() as cursor:
                        cursor.execute("DELETE FROM faculty_slot_selection WHERE exam_slot_id = %s", [slot.id])
                slots.delete()
                exam.delete()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Missing exam_id or slot_id.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
from django.http import JsonResponse
from .models import ExamSlot

def ajax_exam_slots(request):
    exam_id = request.GET.get('exam_id')
    slots = []
    if exam_id:
        from operations.models import Exam, StudentExamMap
        slot_qs = ExamSlot.objects.filter(examination_id=exam_id).order_by('-exam_date', '-start_time')
        for slot in slot_qs:
            exams = Exam.objects.filter(exam_slot=slot)
            course_count = exams.count()
            student_count = StudentExamMap.objects.filter(exam__in=exams).count() if course_count else 0
            if course_count:
                assignment_status = "Assigned"
            else:
                assignment_status = "Pending"
            # Always initialize assigned_room_count and assigned_faculty_count to 0
            assigned_room_count = 0
            assigned_faculty_count = 0
            if exams.exists():
                from operations.models import RoomAllocation
                assigned_room_count = RoomAllocation.objects.filter(exam_slot=slot).count()
                # Count assigned faculty for this slot
                from operations.models import FacultyAvailability
                assigned_faculty_count = FacultyAvailability.objects.filter(exam_slot=slot, is_active=True).count()
            # Check if generated and all assignments complete
            is_generated = getattr(slot, 'is_generated', False)
            from operations.models import SeatingPlan, InvigilationDuty
            seating_count = SeatingPlan.objects.filter(exam_slot=slot).count()
            invigilation_count = InvigilationDuty.objects.filter(exam_slot=slot).count()
            # If seating/invigilation data is missing, force is_generated to False
            if is_generated and (seating_count == 0 or invigilation_count == 0):
                is_generated = False
            # ...existing code...
            all_assigned = False
            if is_generated:
                # Force all_assigned True for testing
                all_assigned = True
            status = 'Publish' if is_generated and all_assigned else 'Pending'
            slots.append({
                'id': slot.id,
                'exam_type': slot.exam_type,
                'mode': slot.mode,
                'exam_date': slot.exam_date.strftime('%Y-%m-%d'),
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'slot_code': slot.slot_code,
                'assignment_status': assignment_status,
                'course_count': course_count,
                'student_count': student_count,
                'assigned_room_count': assigned_room_count,
                'assigned_faculty_count': assigned_faculty_count,
                'is_generated': is_generated,
                'all_assigned': all_assigned,
                'status': status,
            })
    return JsonResponse({'slots': slots})
from django.http import JsonResponse
from operations.models import StudentCourse
from masters.models import Course
from django.db.models import Count

def ajax_exam_scheduling_groups(request):
    slot_id = request.GET.get('slot_id', '')
    academic_year = ''
    semester = ''
    if slot_id:
        from operations.models import ExamSlot
        slot = ExamSlot.objects.filter(id=slot_id).select_related('examination').first()
        if slot and slot.examination:
            academic_year = slot.examination.academic_year
            semester = slot.examination.semester
    # Debug log for resolved values
    import logging
    logging.info(f"Resolved slot_id={slot_id}, academic_year={academic_year}, semester={semester}")
    from django.db.models import Count, F
    reg_qs = StudentCourse.objects.all()
    if academic_year:
        reg_qs = reg_qs.filter(academic_year=academic_year)
    if semester:
        reg_qs = reg_qs.filter(semester__iexact=semester)

    # Get examination date range for the current slot
    exam_date_range = None
    if slot and slot.examination:
        exam_date_range = (slot.examination.start_date, slot.examination.end_date)

    # Find all exams scheduled in any slot between start_date and end_date (inclusive)
    scheduled_courses = set()
    if exam_date_range:
        from operations.models import ExamSlot, Exam
        slots_in_range = ExamSlot.objects.filter(
            examination=slot.examination,
            exam_date__gte=exam_date_range[0],
            exam_date__lte=exam_date_range[1]
        )
        exams_in_range = Exam.objects.filter(exam_slot__in=slots_in_range)
        for exam in exams_in_range:
            if exam.course:
                scheduled_courses.add((exam.course.course_code, exam.course.course_name))

    groups = reg_qs.values(
        'course__course_code',
        'course__course_name',
        'student__batch__batch_code',
        'academic_year',
        'semester',
        'student_id'
    )
    from collections import defaultdict
    group_map = defaultdict(lambda: {'student_ids': []})
    for reg in groups:
        key = (
            reg['course__course_code'],
            reg['course__course_name'],
            reg['student__batch__batch_code'],
            reg['academic_year'],
            reg['semester']
        )
        # Skip group if course is already scheduled in any slot in the exam date range
        if (reg['course__course_code'], reg['course__course_name']) in scheduled_courses:
            continue
        group = group_map[key]
        group['course_code'] = reg['course__course_code']
        group['course_name'] = reg['course__course_name']
        group['regulation'] = reg['student__batch__batch_code'] or 'N/A'
        group['academic_year'] = reg['academic_year']
        group['semester'] = reg['semester']
        group['student_ids'].append(str(reg['student_id']))
    # Find all students already scheduled for an exam in this slot
    scheduled_student_ids = set()
    if slot:
        from operations.models import Exam, StudentExamMap
        exams_in_slot = Exam.objects.filter(exam_slot=slot)
        student_exam_maps = StudentExamMap.objects.filter(exam__in=exams_in_slot)
        # Ensure all IDs are strings for comparison
        scheduled_student_ids = set(str(sid) for sid in student_exam_maps.values_list('student_id', flat=True))

    seen_keys = set()
    result = []
    for group in group_map.values():
        group['student_count'] = len(group['student_ids'])
        group_key = (group['course_code'], group['regulation'], group['academic_year'], group['semester'])
        # Exclude group if any student is already scheduled in this slot or if group is duplicate
        if any(str(sid) in scheduled_student_ids for sid in group['student_ids']):
            continue
        if group_key in seen_keys:
            continue
        seen_keys.add(group_key)
        result.append(group)
    result.sort(key=lambda g: g['student_count'], reverse=True)
    return JsonResponse({'groups': result})

def ajax_exam_filters(request):
    exams = Examinations.objects.all()
    academic_years = sorted(set(exams.values_list('academic_year', flat=True)))
    semesters = sorted(set(exams.values_list('semester', flat=True)), key=str)
    regulations = []  # Not needed for exam scheduling filters
    return JsonResponse({'academic_years': academic_years, 'semesters': semesters, 'regulations': regulations})

from django.views.decorators.http import require_GET
from django.http import JsonResponse
from operations.models import ExamSlot, RoomAllocation
from masters.models import Room

@require_GET
def ajax_slot_rooms(request):
    import sys
    print("[DEBUG] ajax_slot_rooms endpoint called", file=sys.stdout, flush=True)
    slot_id = request.GET.get('slot_id')
    if not slot_id:
        return JsonResponse({'success': False, 'error': 'Missing slot_id'})
    try:
        slot = ExamSlot.objects.get(id=slot_id)
    except ExamSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slot not found'})

    # Allocated rooms (current)
    allocations = RoomAllocation.objects.filter(exam_slot=slot).select_related('room')
    allocated_rooms = []
    allocated_capacity = 0
    for alloc in allocations:
        room = alloc.room
        allocated_rooms.append({
            'room_no': room.room_code,
            'room_type': room.room_type or '',
            'capacity': room.capacity,
            'block': room.block or '',
        })
        allocated_capacity += room.capacity

    # --- Room Estimator Logic ---
    from operations.models import Exam, StudentExamMap
    from masters.models import Room as MasterRoom
    from operations.allocations import estimate_rooms_optimized

    exams = Exam.objects.filter(exam_slot=slot)
    
    # Get StudentExamMap objects for this slot to pass to the estimator
    students = list(StudentExamMap.objects.filter(exam__in=exams).select_related('exam__course'))
    
    # Get all available rooms
    available_rooms = list(MasterRoom.objects.filter(is_active=True))
    # Run estimator with map objects
    estimated_rooms = estimate_rooms_optimized(students, available_rooms)
    estimated_capacity = sum([room.capacity for room in estimated_rooms])

    slot_info = {
        'exam_type': slot.exam_type,
        'mode': slot.mode,
        'exam_date': slot.exam_date.strftime('%Y-%m-%d'),
        'start_time': slot.start_time.strftime('%H:%M'),
        'end_time': slot.end_time.strftime('%H:%M'),
        'slot_code': slot.slot_code,
    }
    return JsonResponse({
        'success': True,
        'slot': slot_info,
        'rooms': allocated_rooms,
        'allocated_room_count': len(allocated_rooms),
        'allocated_capacity': allocated_capacity,
        'required_room_count': len(estimated_rooms),
        'required_capacity': estimated_capacity
    })
