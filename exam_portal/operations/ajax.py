from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction
from django.db.models import Count, Q, F
from django.utils import timezone
from .models import Examinations, ExamSlot, Exam, SeatingPlan, InvigilationDuty, StudentExamMap, RoomAllocation, FacultyAvailability, StudentCourse
from masters.models import Student, Faculty, Course, Room as MasterRoom
from operations.allocations import estimate_rooms_optimized
import json
import logging

# AJAX endpoint to check slot completion for publish
@require_POST
@csrf_exempt
def ajax_check_exam_publishable(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        exam_id = data.get('exam_id')
        if not exam_id:
            return JsonResponse({'all_completed': False, 'published': False, 'is_locked': False, 'error': 'Missing exam_id'})
        exam = Examinations.objects.filter(id=exam_id).first()
        if not exam:
            return JsonResponse({'all_completed': False, 'published': False, 'is_locked': False, 'error': 'Exam not found'})
        
        slots = ExamSlot.objects.filter(examination=exam)
        all_completed = slots.exists()
        for slot in slots:
            # Check seating plan completion via workflow
            from .models import SlotWorkflow
            workflow = SlotWorkflow.objects.filter(exam_slot=slot).first()
            if not workflow or not workflow.seating_step:
                all_completed = False
                break
        
        return JsonResponse({
            'all_completed': all_completed, 
            'published': exam.published, 
            'is_locked': exam.is_locked,
            'locked_by': exam.locked_by.username if exam.locked_by else None
        })
    except Exception as e:
        return JsonResponse({'all_completed': False, 'published': False, 'error': str(e)})

# AJAX endpoint to publish an examination
@csrf_exempt
def ajax_publish_exam(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        exam_id = data.get('exam_id')
        exam = Examinations.objects.filter(id=exam_id).first()
        if not exam:
            return JsonResponse({'success': False, 'error': 'Examination not found.'})
        
        if exam.is_locked:
            return JsonResponse({'success': False, 'error': 'Examination is locked. Please contact DB Admin.'})

        slots = ExamSlot.objects.filter(examination=exam)
        if not slots.exists():
            return JsonResponse({'success': False, 'error': 'No slots found for this exam.'})
        
        # Verify all slots have seating plans
        from .models import SlotWorkflow
        all_completed = all([SlotWorkflow.objects.filter(exam_slot=s, seating_step=True).exists() for s in slots])
        
        if all_completed:
            exam.published = True
            exam.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Some slots are still incomplete.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# AJAX endpoint to unpublish an examination
@csrf_exempt
def ajax_unpublish_exam(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        exam_id = data.get('exam_id')
        exam = Examinations.objects.filter(id=exam_id).first()
        if not exam:
            return JsonResponse({'success': False, 'error': 'Examination not found.'})
        
        if exam.is_locked:
            return JsonResponse({'success': False, 'error': 'Examination is locked. Please contact DB Admin.'})

        exam.published = False
        exam.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# AJAX endpoint to lock an examination
@csrf_exempt
def ajax_lock_exam(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        exam_id = data.get('exam_id')
        exam = Examinations.objects.filter(id=exam_id).first()
        if not exam:
            return JsonResponse({'success': False, 'error': 'Examination not found.'})
        
        exam.is_locked = True
        exam.locked_by = request.user
        exam.lock_updated_at = timezone.now()
        exam.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# AJAX endpoint to unlock an examination (Superusers only)
@csrf_exempt
def ajax_unlock_exam(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    try:
        if not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Only Superusers (DB Admins) can unlock an examination.'})
            
        data = json.loads(request.body.decode('utf-8'))
        exam_id = data.get('exam_id')
        password = data.get('password')
        
        if not request.user.check_password(password):
            return JsonResponse({'success': False, 'error': 'Incorrect password. Unlock denied.'})
            
        exam = Examinations.objects.filter(id=exam_id).first()
        if not exam:
            return JsonResponse({'success': False, 'error': 'Examination not found.'})
        
        exam.is_locked = False
        exam.locked_by = request.user
        exam.lock_updated_at = timezone.now()
        exam.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

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

# AJAX endpoint to get course details for a slot
@require_GET
def ajax_slot_courses(request):
    slot_id = request.GET.get('slot_id')
    if not slot_id:
        return JsonResponse({'success': False, 'error': 'Missing slot_id'})
    try:
        slot = ExamSlot.objects.get(id=slot_id)
    except ExamSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slot not found'})
    exams = Exam.objects.filter(exam_slot=slot).select_related('course')
    academic_year = slot.examination.academic_year if slot.examination else ''
    semester = slot.examination.semester if slot.examination else ''
    course_list = []
    for exam in exams:
        course = exam.course
        if not course: continue
        student_count = StudentExamMap.objects.filter(exam=exam).count()
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

# AJAX endpoint to edit an examination
@csrf_exempt
def ajax_edit_examination(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        exam_id = data.get('exam_id')
        if not exam_id:
            return JsonResponse({'success': False, 'error': 'Missing exam_id.'})
        exam = Examinations.objects.get(id=exam_id)
        if exam.is_locked:
            return JsonResponse({'success': False, 'error': 'Examination is locked. Please contact DB Admin.'})
        
        exam.exam_name = data.get('examname', '').strip()
        exam.academic_year = data.get('academic_year', '').strip()
        exam.semester = data.get('semester', '').strip()
        exam.start_date = data.get('start_date', '').strip()
        exam.end_date = data.get('end_date', '').strip()
        exam.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# AJAX endpoint to delete an examination and all related slots and exams
@csrf_exempt
def ajax_delete_examination(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method.'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        slot_id = data.get('slot_id')
        exam_id = data.get('exam_id')
        with transaction.atomic():
            if slot_id:
                slot = ExamSlot.objects.filter(id=slot_id).select_related('examination').first()
                if not slot:
                    return JsonResponse({'success': False, 'error': 'Slot not found.'})
                if slot.examination and slot.examination.is_locked:
                    return JsonResponse({'success': False, 'error': 'Examination is locked. Please contact DB Admin.'})
                
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
                if exam.is_locked:
                    return JsonResponse({'success': False, 'error': 'Examination is locked. Please contact DB Admin.'})
                
                slots = ExamSlot.objects.filter(examination=exam)
                for slot in slots:
                    exams = Exam.objects.filter(exam_slot=slot)
                    for ex in exams:
                        StudentExamMap.objects.filter(exam=ex).delete()
                    exams.delete()
                    FacultyAvailability.objects.filter(exam_slot=slot).delete()
                    RoomAllocation.objects.filter(exam_slot=slot).delete()
                    InvigilationDuty.objects.filter(exam_slot=slot).delete()
                    SeatingPlan.objects.filter(exam_slot=slot).delete()
                slots.delete()
                exam.delete()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'error': 'Missing exam_id or slot_id.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# AJAX endpoint to get slots for an examination
@require_GET
def ajax_exam_slots(request):
    exam_id = request.GET.get('exam_id')
    slots = []
    if exam_id:
        reg_type = request.GET.get('registration_type')
        slot_qs = ExamSlot.objects.filter(examination_id=exam_id)
        if reg_type:
            slot_qs = slot_qs.filter(registration_type=reg_type)
        slot_qs = slot_qs.order_by('-exam_date', '-start_time')
        for slot in slot_qs:
            exams = Exam.objects.filter(exam_slot=slot)
            course_count = exams.count()
            student_count = StudentExamMap.objects.filter(exam__in=exams).count() if course_count else 0
            # Use SlotWorkflow or calculate and sync
            from .models import SlotWorkflow
            workflow, created = SlotWorkflow.objects.get_or_create(exam_slot=slot)
            
            # Sync counts to workflow only ONCE when record is created (Initial catch-up)
            if created:
                modified = False
                if course_count > 0:
                    workflow.courses_step = True
                    modified = True
                if RoomAllocation.objects.filter(exam_slot=slot).exists():
                    workflow.rooms_step = True
                    modified = True
                if FacultyAvailability.objects.filter(exam_slot=slot, is_active=True).exists():
                    workflow.faculty_step = True
                    modified = True
                if SeatingPlan.objects.filter(exam_slot=slot).exists():
                    workflow.seating_step = True
                    modified = True
                if modified:
                    workflow.save()

            assignment_status = "Assigned" if workflow.courses_step else "Pending"
            assigned_room_count = RoomAllocation.objects.filter(exam_slot=slot).count()
            assigned_faculty_count = FacultyAvailability.objects.filter(exam_slot=slot, is_active=True).count()
            
            is_generated = workflow.seating_step
            # Physical Record Verification (User Request)
            # Even if seating_step is True, verify counts match
            actual_seating_count = SeatingPlan.objects.filter(exam_slot=slot).count()
            
            if is_generated:
                # If seating plan exists but student count has changed, revert status
                if actual_seating_count < student_count or student_count == 0:
                    is_generated = False
                    workflow.seating_step = False
                    workflow.save()
                
            all_assigned = True if is_generated else False
            status = 'Publish' if is_generated and all_assigned else 'Pending'
            
            slots.append({
                'id': slot.id,
                'exam_type': slot.exam_type,
                'mode': slot.mode,
                'exam_date': slot.exam_date.strftime('%Y-%m-%d'),
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
                'slot_code': slot.slot_code,
                'registration_type': slot.registration_type,
                'assignment_status': assignment_status,
                'course_count': course_count,
                'assigned_room_count': assigned_room_count,
                'assigned_faculty_count': assigned_faculty_count,
                'student_count': student_count,
                'all_assigned': all_assigned,
                'status': status,
                'is_generated': is_generated,
                'courses_completed': workflow.courses_step,
                'rooms_completed': workflow.rooms_step,
                'faculty_completed': workflow.faculty_step,
                'seating_completed': workflow.seating_step,
                'updated_by': workflow.updated_by.username if workflow.updated_by else 'System'
            })
    return JsonResponse({'slots': slots})

# AJAX endpoint to get scheduling groups
@require_GET
def ajax_exam_scheduling_groups(request):
    slot_id = request.GET.get('slot_id', '')
    academic_year = ''
    semester = ''
    slot = None
    if slot_id:
        slot = ExamSlot.objects.filter(id=slot_id).select_related('examination').first()
        if slot and slot.examination:
            academic_year = slot.examination.academic_year
            semester = slot.examination.semester
            
    reg_qs = StudentCourse.objects.all()
    if academic_year:
        reg_qs = reg_qs.filter(academic_year=academic_year)
    if semester:
        reg_qs = reg_qs.filter(semester__iexact=semester)
    
    if slot and hasattr(slot, 'registration_type'):
        reg_qs = reg_qs.filter(registration_type=slot.registration_type)

    exam_date_range = (slot.examination.start_date, slot.examination.end_date) if slot and slot.examination else None
    scheduled_courses = set()
    if exam_date_range:
        # Exclude the current slot when checking for already-scheduled courses
        # This allows courses in the current slot to pass through and be marked as 'checked'
        slots_in_range_others = ExamSlot.objects.filter(
            examination=slot.examination, 
            exam_date__gte=exam_date_range[0], 
            exam_date__lte=exam_date_range[1]
        ).exclude(id=slot_id)
        
        exams_in_range_others = Exam.objects.filter(exam_slot__in=slots_in_range_others)
        for exam in exams_in_range_others:
            if exam.course: scheduled_courses.add((exam.course.course_code, exam.course.course_name))

    groups = reg_qs.values('course__course_code', 'course__course_name', 'student__batch__batch_code', 'academic_year', 'semester', 'registration_type', 'student_id')
    from collections import defaultdict
    group_map = defaultdict(lambda: {'student_ids': []})
    for reg in groups:
        key = (reg['course__course_code'], reg['course__course_name'], reg['student__batch__batch_code'], reg['academic_year'], reg['semester'], reg['registration_type'])
        if (reg['course__course_code'], reg['course__course_name']) in scheduled_courses: continue
        group = group_map[key]
        group.update({
            'course_code': reg['course__course_code'],
            'course_name': reg['course__course_name'],
            'regulation': reg['student__batch__batch_code'] or 'N/A',
            'academic_year': reg['academic_year'],
            'semester': reg['semester'],
            'registration_type': reg['registration_type'] or 'REGULAR'
        })
        group['student_ids'].append(str(reg['student_id']))
        
    scheduled_student_ids = set()
    exams_in_this_slot = []
    if slot:
        exams_in_this_slot = list(Exam.objects.filter(exam_slot=slot).values_list('course__course_code', 'regulation'))
        exams_in_slot_objs = Exam.objects.filter(exam_slot=slot)
        scheduled_student_ids = set(str(sid) for sid in StudentExamMap.objects.filter(exam__in=exams_in_slot_objs).values_list('student_id', flat=True))

    seen_keys = set()
    result = []
    for key, group in group_map.items():
        course_code, _, regulation, _, _, _ = key
        group['student_count'] = len(group['student_ids'])
        group_key = (group['course_code'], group['regulation'], group['academic_year'], group['semester'])
        
        # Check if this group is already in THIS slot
        is_already_here = (course_code, regulation) in exams_in_this_slot
        group['is_already_scheduled'] = is_already_here
        
        # If it's already here, we MUST show it. 
        # Otherwise, check if it's scheduled elsewhere
        if not is_already_here:
            if any(str(sid) in scheduled_student_ids for sid in group['student_ids']): continue
            if group_key in seen_keys: continue
        
        seen_keys.add(group_key)
        result.append(group)
    result.sort(key=lambda g: g['is_already_scheduled'], reverse=True) # Show selected ones first
    return JsonResponse({'groups': result})

# AJAX endpoint to get filters for exam portal
@require_GET
def ajax_exam_filters(request):
    exams = Examinations.objects.all()
    academic_years = sorted(set(exams.values_list('academic_year', flat=True)))
    semesters = sorted(set(exams.values_list('semester', flat=True)), key=str)
    return JsonResponse({'academic_years': academic_years, 'semesters': semesters, 'regulations': []})

# AJAX endpoint to get room details for a slot
@require_GET
def ajax_slot_rooms(request):
    slot_id = request.GET.get('slot_id')
    if not slot_id:
        return JsonResponse({'success': False, 'error': 'Missing slot_id'})
    try:
        slot = ExamSlot.objects.get(id=slot_id)
    except ExamSlot.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Slot not found'})

    allocations = RoomAllocation.objects.filter(exam_slot=slot).select_related('room')
    allocated_rooms = [{
        'room_no': r.room.room_code,
        'room_type': r.room.room_type or '',
        'capacity': r.room.capacity,
        'block': r.room.block or '',
    } for r in allocations]
    allocated_capacity = sum([r['capacity'] for r in allocated_rooms])

    exams = Exam.objects.filter(exam_slot=slot)
    students = list(StudentExamMap.objects.filter(exam__in=exams).select_related('exam__course'))
    available_rooms = list(MasterRoom.objects.filter(is_active=True))
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
