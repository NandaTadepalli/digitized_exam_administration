from django.shortcuts import render
from .models import ExamSlot, Exam, StudentCourse
from masters.models import Course, Room
from django.contrib import messages

def exam_rooms_alloc(request):
    slot_id = request.GET.get('slot_id') or request.POST.get('slot_id')
    slot = None
    student_count = 0
    # Find overlapping slots
    overlapping_room_ids = []
    if slot_id:
        try:
            slot = ExamSlot.objects.get(id=slot_id)
            # Overlap: same date, time overlaps
            overlapping_slots = ExamSlot.objects.filter(
                exam_date=slot.exam_date,
                start_time__lt=slot.end_time,
                end_time__gt=slot.start_time
            ).exclude(id=slot.id)
            from .models import RoomAllocation
            overlapping_room_ids = RoomAllocation.objects.filter(exam__exam_slot__in=overlapping_slots).values_list('room_id', flat=True)
        except ExamSlot.DoesNotExist:
            pass
    rooms = Room.objects.filter(is_active=True).exclude(id__in=overlapping_room_ids)
    allocated_room_ids = []
    if slot_id:
        try:
            slot = ExamSlot.objects.get(id=slot_id)
            exams = Exam.objects.filter(exam_slot=slot)
            for exam in exams:
                course = exam.course
                regulation = exam.regulation
                academic_year = slot.examination.academic_year if slot.examination else ''
                semester = slot.examination.semester if slot.examination else ''
                students = StudentCourse.objects.filter(course=course, academic_year=academic_year, semester=semester, student__batch__batch_code=regulation)
                student_count += students.count()
            if request.method == "POST":
                from .models import RoomAllocation
                selected_room_ids = set(map(int, request.POST.getlist('selected_rooms')))
                prev_allocs = RoomAllocation.objects.filter(exam=exams.first())
                prev_room_ids = set(prev_allocs.values_list('room_id', flat=True))
                # Find deleted and added rooms
                deleted_ids = prev_room_ids - selected_room_ids
                added_ids = selected_room_ids - prev_room_ids
                # Delete previous allocations
                prev_allocs.delete()
                # Add new allocations
                for room_id in selected_room_ids:
                    try:
                        room_obj = Room.objects.get(id=room_id)
                        RoomAllocation.objects.create(exam=exams.first(), room=room_obj)
                    except Room.DoesNotExist:
                        continue
                # Prepare message
                from masters.models import Room as MasterRoom
                added_rooms = MasterRoom.objects.filter(id__in=added_ids).values_list('room_code', flat=True)
                deleted_rooms = MasterRoom.objects.filter(id__in=deleted_ids).values_list('room_code', flat=True)
                msg = "Room allocations saved."
                if added_rooms:
                    msg += f"<br>Added rooms: {', '.join(added_rooms)}"
                from django.shortcuts import redirect
                from django.urls import reverse
                # Store messages in session to show on exams.html
                request.session['room_alloc_success'] = msg
                if deleted_rooms:
                    request.session['room_alloc_warning'] = f"Deleted rooms: {', '.join(deleted_rooms)}"
                # Build query params for redirect to exams.html
                exam_obj = None
                exam_slot_obj = None
                if exams.exists():
                    exam_obj = exams.first()
                    exam_slot_obj = exam_obj.exam_slot
                params = {}
                if exam_obj and exam_slot_obj:
                    params['exam_id'] = exam_slot_obj.examination.id if exam_slot_obj.examination else ''
                    params['exam_name'] = exam_slot_obj.examination.exam_name if exam_slot_obj.examination else ''
                    params['start_date'] = exam_slot_obj.examination.start_date.strftime('%Y-%m-%d') if exam_slot_obj.examination and exam_slot_obj.examination.start_date else ''
                    params['end_date'] = exam_slot_obj.examination.end_date.strftime('%Y-%m-%d') if exam_slot_obj.examination and exam_slot_obj.examination.end_date else ''
                from urllib.parse import urlencode
                url = reverse('operations:exams')
                if params:
                    url += '?' + urlencode(params)
                return redirect(url)
            # On GET, just fetch allocated_room_ids, do not change allocations
            if request.method == "GET" and exams.exists():
                from .models import RoomAllocation
                allocated_room_ids = list(RoomAllocation.objects.filter(exam=exams.first()).values_list('room_id', flat=True))
        except ExamSlot.DoesNotExist:
            slot = None
    import math
    required_capacity = math.ceil(student_count * 1.1)
    return render(request, "operations/exam_rooms_alloc.html", {
        'slot': slot,
        'rooms': rooms,
        'allocated_room_ids': allocated_room_ids,
        'student_count': student_count,
        'required_capacity': required_capacity
    })

def exam_faculty_alloc(request):
    slot_id = request.GET.get('slot_id')
    slot = None
    faculties = []
    total_students = 0
    allocated_faculty = 0
    if slot_id:
        try:
            slot = ExamSlot.objects.get(id=slot_id)
            exams = Exam.objects.filter(exam_slot=slot)
            from operations.models import FacultyCourse
            from masters.models import Faculty
            found_assignment = False
            for exam in exams:
                academic_year = slot.examination.academic_year if slot.examination else ''
                semester = slot.examination.semester if slot.examination else ''
                # Count students for this exam
                from operations.models import StudentCourse
                students = StudentCourse.objects.filter(course=exam.course, academic_year=academic_year, semester=semester)
                total_students += students.count()
                faculty_courses = FacultyCourse.objects.filter(course=exam.course, academic_year=academic_year, semester=semester, is_active=True)
                for fc in faculty_courses:
                    faculty_obj = fc.faculty
                    faculties.append({
                        'id': faculty_obj.faculty_id,
                        'name': faculty_obj.faculty_name,
                        'department': faculty_obj.dept.dept_name if faculty_obj.dept else '',
                        'course': exam.course.course_name if exam.course else '',
                        'role': faculty_obj.designation if hasattr(faculty_obj, 'designation') else ''
                    })
                    found_assignment = True
            allocated_faculty = len(faculties)
            # If no assignments found, show all active faculty
            if not found_assignment:
                from masters.models import Faculty
                active_faculty = Faculty.objects.filter(status='ACTIVE')
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
    import math
    required_faculty = math.ceil(total_students / 50) if total_students > 0 else 0
    return render(request, "operations/exam_faculty_alloc.html", {
        'slot': slot,
        'faculties': faculties,
        'required_faculty': required_faculty,
        'allocated_faculty': allocated_faculty
    })
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

def ajax_examinations(request):
    from .models import Examinations
    page = int(request.GET.get('page', 1))
    per_page = 10
    exams = Examinations.objects.order_by('-start_date', '-end_date', 'exam_name')
    paginator = Paginator(exams, per_page)
    page_obj = paginator.get_page(page)
    results = []
    for idx, exam in enumerate(page_obj.object_list, start=1 + (page_obj.number-1)*per_page):
        results.append({
            'number': idx,
            'exam_id': exam.id,
            'exam_name': exam.exam_name,
            'academic_year': getattr(exam, 'academic_year', ''),
            'semester': getattr(exam, 'semester', ''),
            'start_date': exam.start_date.strftime('%Y-%m-%d'),
            'end_date': exam.end_date.strftime('%Y-%m-%d'),
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
    exam_id = request.GET.get('exam_id')
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
            'Slot Code': slot_code
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
                'q_end_date': q_end_date
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
                'q_end_date': q_end_date
            })
        if exam_date_obj < today:
            messages.error(request, "Exam date must be today or later.")
            return render(request, "operations/exams.html", {
                'form_data': form_data,
                'slot_list': slot_list,
                'exam_status': exam_status,
                'examname': examname,
                'q_start_date': q_start_date,
                'q_end_date': q_end_date
            })

        try:
            start_time_obj = datetime.datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = datetime.datetime.strptime(end_time, "%H:%M").time()
        except ValueError:
            messages.error(request, "Invalid time format.")
            return render(request, "operations/exams.html", {
                'form_data': request.POST
            })
        if start_time_obj >= end_time_obj:
            messages.error(request, "Start time should be before end time.")
            return render(request, "operations/exams.html", {
                'form_data': request.POST
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
                mode=mode_db
            ).exists()
            if clash_exists:
                messages.error(request, "An exam slot with the same date, start time, end time, slot code, exam type, and mode already exists. Please choose a different time or slot.")
            else:
                slot = ExamSlot(
                    examination=exam_obj,
                    exam_type=exam_type_db,
                    mode=mode_db,
                    exam_date=exam_date,
                    start_time=start_time,
                    end_time=end_time,
                    slot_code=slot_code_db
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
        'q_end_date': q_end_date
    })

def roomalloc(request):
    return render(request, "operations/roomalloc.html")

@login_required
def roomalloc_content(request):
    return render(request, "operations/roomalloc_content.html")

def report(request):
    return render(request, "operations/report.html")

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
                    student__batch__batch_code=regulation
                ).select_related('student')
                logging.info(f"StudentCourse Query: course={course_code}, academic_year={filter_academic_year}, semester={filter_semester}, batch_code={regulation}")
                logging.info(f"Scheduling group {group}: Found {students.count()} students.")
                logging.info(f"Student IDs: {[reg.student.id for reg in students]}")
                for reg in students:
                    StudentExamMap.objects.create(
                        exam=exam,
                        student=reg.student,
                        attempt_type="REGULAR",
                        status="REGISTERED"
                    )
                created += 1
            except Exception as e:
                import logging
                logging.exception(f"Error scheduling exam for group {group}: {e}")
                messages.error(request, f"Error scheduling exam for group {group}: {e}")
        from django.shortcuts import redirect
        if created:
            messages.success(request, f"Scheduled {created} exam(s) successfully.")
            return redirect('exam_scheduling', slot_id=slot_id)
        else:
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
