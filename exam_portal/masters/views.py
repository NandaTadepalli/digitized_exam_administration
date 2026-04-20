from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from io import TextIOWrapper
import csv
import unicodedata
import re
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from .models import Batch, Student, Faculty, Room, Department, Course
from accounts.models import User
from operations.models import StudentCourse
from operations.models import InvigilationDuty, ExamSlot, Examinations, Exam, Room
from datetime import datetime, timedelta
import collections

# Faculty dashboard view
@login_required(login_url='/accounts/login/')
def faculty_dashboard(request):
    return render(request, "core/faculty_dashboard.html")

@login_required
def check_id_exists(request):
    """AJAX endpoint to check if an ID exists before submitting forms."""
    entity_type = request.GET.get('type')
    check_id = request.GET.get('id', '').strip()
    
    if not check_id:
        return JsonResponse({'exists': False})
        
    exists = False
    if entity_type == 'student':
        exists = Student.objects.filter(student_id=check_id).exists() or User.objects.filter(username=check_id).exists()
    elif entity_type == 'faculty':
        exists = Faculty.objects.filter(faculty_id=check_id).exists() or User.objects.filter(username=check_id).exists()
        
    return JsonResponse({'exists': exists})

# Invigilation Duties view for faculty
@login_required(login_url='/accounts/login/')
def invigilation_duties(request):
    user = request.user
    # Only allow faculty
    if not hasattr(user, 'role') or user.role.lower() != 'faculty':
        return redirect('core:dashboard')
    from operations.models import InvigilationDuty, ExamSlot, Examinations, Exam, Room
    from masters.models import Course, Faculty
    from datetime import datetime, timedelta
    duties_raw = InvigilationDuty.objects.filter(faculty__user=user).select_related('exam_slot', 'room', 'faculty')
    duties = []
    for duty in duties_raw:
        slot = duty.exam_slot
        # Only show if the exam is published
        if not slot.examination or not slot.examination.published:
            continue
        exam_obj = Exam.objects.filter(exam_slot=slot).select_related('course').first()
        exam_name = slot.examination.exam_name if slot.examination else ''
        course_code = exam_obj.course.course_code if exam_obj and exam_obj.course else ''
        course_name = exam_obj.course.course_name if exam_obj and exam_obj.course else ''
        room_no = duty.room.room_code if duty.room else ''
        exam_date = slot.exam_date if slot.exam_date else None
        start_time = slot.start_time if slot.start_time else None
        end_time = slot.end_time if slot.end_time else None
        duration = ''
        if start_time and end_time:
            # Calculate duration as timedelta
            dt1 = datetime.combine(exam_date, start_time)
            dt2 = datetime.combine(exam_date, end_time)
            diff = dt2 - dt1
            hours = diff.seconds // 3600
            minutes = (diff.seconds // 60) % 60
            if hours and minutes:
                duration = f"{hours} hr {minutes} min"
            elif hours:
                duration = f"{hours} hr"
            elif minutes:
                duration = f"{minutes} min"
            else:
                duration = "-"
        # ISO Timestamps for JavaScript Timers
        start_iso = datetime.combine(exam_date, start_time).isoformat() if exam_date and start_time else ""
        
        # Dynamic Opening Offset: 5m if < 2.5hrs, 10m if >= 2.5hrs
        delay_mins = 5
        duration_hours = 0
        if start_time and end_time:
            dt1_tmp = datetime.combine(exam_date, start_time)
            dt2_tmp = datetime.combine(exam_date, end_time)
            duration_hours = (dt2_tmp - dt1_tmp).total_seconds() / 3600
            if duration_hours >= 2.5:
                delay_mins = 10
        
        open_iso = (datetime.combine(exam_date, start_time) + timedelta(minutes=delay_mins)).isoformat() if exam_date and start_time else ""
        deadline_iso = (datetime.combine(exam_date, start_time) + timedelta(minutes=delay_mins + 30)).isoformat() if exam_date and start_time else ""

        now = datetime.now()
        exam_start = datetime.combine(exam_date, start_time)
        exam_end = datetime.combine(exam_date, end_time)
        exam_start_delay = exam_start + timedelta(minutes=delay_mins)
        exam_start_30m = exam_start_delay + timedelta(minutes=30)

        if now < exam_start:
            att_status = 'UPCOMING'
        elif now <= exam_end:
            att_status = 'ONGOING'
        else:
            att_status = 'COMPLETED'

        duties.append({
            'exam_name': exam_name,
            'faculty_id': duty.faculty.faculty_id,
            'exam_date': exam_date,
            'exam_type': slot.exam_type,
            'course_code': course_code,
            'course_name': course_name,
            'room_no': room_no,
            'start_time': start_time,
            'end_time': end_time,
            'exam_slot': slot.slot_code,
            'duration': duration,
            'start_iso': start_iso,
            'open_iso': open_iso,
            'deadline_iso': deadline_iso,
            'attendance_status': att_status,
            'exam_slot_id': slot.id,
            'room_id': duty.room.id if duty.room else '',
        })
    context = {
        'duties': duties,
        'user': user,
    }
    return render(request, 'masters/invigilation_duties.html', context)

@login_required(login_url='/accounts/login/')
def facultyview_seatingplan(request):
    user = request.user
    if not hasattr(user, 'role') or user.role.lower() != 'faculty':
        return redirect('core:dashboard')
    duties_raw = InvigilationDuty.objects.filter(faculty__user=user).select_related('exam_slot', 'room', 'faculty')
    duties = []
    
    from operations.models import Attendance, Exam, ExamSlot, Room
    from datetime import datetime, timedelta
    
    for duty in duties_raw:
        slot = duty.exam_slot
        if not slot.examination or not slot.examination.published:
            continue
        
        exam_obj = Exam.objects.filter(exam_slot=slot).select_related('course').first()
        exam_name = slot.examination.exam_name if slot.examination else ''
        course_code = exam_obj.course.course_code if exam_obj and exam_obj.course else ''
        course_name = exam_obj.course.course_name if exam_obj and exam_obj.course else ''
        room_no = duty.room.room_code if duty.room else ''
        exam_date = slot.exam_date if slot.exam_date else None
        start_time = slot.start_time if slot.start_time else None
        end_time = slot.end_time if slot.end_time else None
        duration = ''
        
        if start_time and end_time:
            dt1 = datetime.combine(exam_date, start_time)
            dt2 = datetime.combine(exam_date, end_time)
            diff = dt2 - dt1
            hours = diff.seconds // 3600
            minutes = (diff.seconds // 60) % 60
            if hours and minutes:
                duration = f"{hours} hr {minutes} min"
            elif hours:
                duration = f"{hours} hr"
            elif minutes:
                duration = f"{minutes} min"
            else:
                duration = "-"

        # ISO Timestamps for JavaScript Timers
        start_iso = datetime.combine(exam_date, start_time).isoformat() if exam_date and start_time else ""
        
        # Dynamic Opening Offset: 5m if < 2.5hrs, 10m if >= 2.5hrs
        delay_mins = 5
        duration_hours = (dt2 - dt1).total_seconds() / 3600
        if duration_hours >= 2.5:
            delay_mins = 10
            
        open_iso = (datetime.combine(exam_date, start_time) + timedelta(minutes=delay_mins)).isoformat() if exam_date and start_time else ""
        deadline_iso = (datetime.combine(exam_date, start_time) + timedelta(minutes=delay_mins + 30)).isoformat() if exam_date and start_time else ""

        # Attendance Status Logic
        has_posted = Attendance.objects.filter(
            marked_by=duty.faculty, 
            student_exam__exam__exam_slot=slot,
            room=duty.room
        ).exists()

        now = datetime.now()
        exam_start = datetime.combine(exam_date, start_time)
        exam_end = datetime.combine(exam_date, end_time)
        exam_start_delay = exam_start + timedelta(minutes=delay_mins)
        exam_start_30m = exam_start_delay + timedelta(minutes=30)

        if now < exam_start:
            att_status = 'UPCOMING'
            att_label = 'Upcoming'
        elif now <= exam_end:
            att_status = 'ONGOING'
            if has_posted:
                att_label = 'Edit Attendance'
                btn_class = 'btn-warning'
                can_click = True
            elif now < exam_start_delay:
                att_label = 'Opening Soon'
                btn_class = 'btn-secondary disabled'
                can_click = False
            elif now <= exam_start_30m:
                att_label = 'Mark Attendance'
                btn_class = 'btn-secondary'
                can_click = True
            else:
                att_status = 'PENDING'
                att_label = 'Window Closed'
                btn_class = 'btn-danger disabled'
                can_click = False
        else:
            att_status = 'COMPLETED'
            att_label = 'View Attendance'
            btn_class = 'btn-info'
            can_click = True

        # Override can_click if window missed
        if now > exam_start_30m:
             if has_posted:
                 att_label = 'View Attendance'
                 btn_class = 'btn-info'
                 can_click = True
             else:
                 can_click = False
                 att_label = 'Window Closed'
                 btn_class = 'btn-danger disabled'

        duties.append({
            'exam_name': exam_name,
            'faculty_id': duty.faculty.faculty_id,
            'exam_date': exam_date,
            'exam_type': slot.exam_type,
            'course_code': course_code,
            'course_name': course_name,
            'room_no': room_no,
            'start_time': start_time,
            'end_time': end_time,
            'exam_slot': slot.slot_code,
            'duration': duration,
            'start_iso': start_iso,
            'open_iso': open_iso,
            'deadline_iso': deadline_iso,
            'attendance_status': att_status,
            'has_posted': has_posted,
            'attendance_label': att_label,
            'btn_class': btn_class,
            'can_click': can_click,
            'exam_slot_id': slot.id,
            'room_id': duty.room.id if duty.room else '',
        })
    
    context = {
        'duties': duties,
        'user': user,
    }
    return render(request, 'operations/facultyview_seatingplan.html', context)

# Simple batch list view for redirection
@login_required
def batch_list(request):
    batches = Batch.objects.all()
    return render(request, "masters/batch_list.html", {"batches": batches})
@login_required
def batch_upload(request):
    if request.method == "POST" and request.FILES.get("csv_file"):
        from io import TextIOWrapper
        import csv
        import collections
        import unicodedata
        import re
        from .models import Batch

        csv_file = request.FILES["csv_file"]
        success_count = 0
        error_groups = collections.defaultdict(list)

        try:
            decoded_file = TextIOWrapper(csv_file.file, encoding="utf-8")
            
            # Robust delimiter detection
            sample = decoded_file.read(2048)
            decoded_file.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                reader = csv.DictReader(decoded_file, dialect=dialect)
            except Exception:
                reader = csv.DictReader(decoded_file)

            if not reader.fieldnames:
                messages.error(request, "CSV file is missing headers.")
                return redirect("core:settings")

            # Robust header normalization (removes BOM, non-alphanumeric, etc.)
            import unicodedata
            def norm_h(s):
                if not s: return ""
                s = unicodedata.normalize("NFKC", s)
                return re.sub(r'[^a-zA-Z0-9]', '', s).lower()

            def normalize_val(val):
                if not val: return ""
                val = unicodedata.normalize("NFKC", val)
                val = re.sub(r"[\s\u00A0\u200B\u200C\u200D\ufeff]+", " ", val)
                return val.strip().lower()

            h_map = {norm_h(k): k for k in reader.fieldnames}
            
            # Map columns with flexibility
            code_key = h_map.get(norm_h("batch_code")) or h_map.get(norm_h("regulation"))
            adm_key = h_map.get(norm_h("admission_year")) or h_map.get(norm_h("adm_year"))
            grad_key = h_map.get(norm_h("grad_year")) or h_map.get(norm_h("graduation_year"))
            status_key = h_map.get(norm_h("status"))

            if not all([code_key, adm_key, grad_key]):
                messages.error(request, "CSV missing required columns: batch_code, admission_year, grad_year.")
                return redirect("core:settings")

            valid_rows = []
            for i, row in enumerate(reader, start=2):
                code = (row.get(code_key) or "").strip()
                adm = (row.get(adm_key) or "").strip()
                grad = (row.get(grad_key) or "").strip()
                stat = (row.get(status_key) or "ACTIVE").strip()

                if not code or not adm or not grad:
                    error_groups["Missing required fields (batch_code, adm_year, or grad_year)"].append(i)
                    continue

                valid_rows.append({
                    "row_num": i,
                    "code": code,
                    "adm": adm,
                    "grad": grad,
                    "status": stat,
                    "code_norm": normalize_val(code)
                })

            if not valid_rows:
                if error_groups:
                    for msg, rows in error_groups.items():
                        messages.error(request, f"Rows {', '.join(map(str, sorted(rows)))}: {msg}")
                return redirect("core:settings")

            # Bulk fetch
            codes = {r["code"] for r in valid_rows}
            existing_map = {normalize_val(b.batch_code): b for b in Batch.objects.filter(batch_code__in=codes)}

            new_batches = []
            duplicate_codes = []
            mismatch_msgs = []

            for data in valid_rows:
                existing = existing_map.get(data["code_norm"])
                if existing:
                    diffs = []
                    if str(existing.admission_year) != str(data["adm"]):
                        diffs.append(f"Admission Year: {existing.admission_year} vs {data['adm']}")
                    if str(existing.grad_year) != str(data["grad"]):
                        diffs.append(f"Graduation Year: {existing.grad_year} vs {data['grad']}")
                    if existing.status != data["status"]:
                        diffs.append(f"Status: {existing.status} vs {data['status']}")

                    if not diffs:
                        duplicate_codes.append(data["code"])
                    else:
                        mismatch_msgs.append(f"Batch '{data['code']}' (Row {data['row_num']}): {', '.join(diffs)}")
                else:
                    new_batches.append(Batch(
                        batch_code=data["code"],
                        admission_year=data["adm"],
                        grad_year=data["grad"],
                        status=data["status"]
                    ))

            if new_batches:
                with transaction.atomic():
                    Batch.objects.bulk_create(new_batches, batch_size=1000)
                messages.success(request, f"Successfully added {len(new_batches)} new batch(es).")

            if duplicate_codes:
                messages.warning(request, f"Batch data already exist / duplicate data found:<br><br>{', '.join(duplicate_codes)}")

            if mismatch_msgs:
                messages.warning(request, "Found some existing batches with different details: " + "; ".join(mismatch_msgs))

            if error_groups:
                for msg, rows in error_groups.items():
                    messages.error(request, f"{msg}: Rows {', '.join(map(str, sorted(rows)))}")

        except Exception as e:
            messages.error(request, f"Error processing CSV: {e}")

    else:
        messages.error(request, "Please select a valid CSV file to upload.")
    return redirect("core:settings")

    messages.error(request, "No file uploaded.")
    return redirect("core:settings")

# Handle POST from coursereg_conflict.html to break redirect loop
@csrf_exempt
@login_required
def coursereg_conflict_resolve(request):
    if request.method == "POST":
        selected = request.POST.getlist('conflict_rows')
        from django.conf import settings
        conflicts = request.session.get('coursereg_conflicts')
        if not selected:
            messages.warning(request, "No conflicts selected for update.")
            # Try to reload the same conflict page with the same data
            # If conflicts are not in session, fallback to redirect
            if conflicts:
                return render(request, "masters/coursereg_conflict.html", {"conflicts": conflicts})
            else:
                return redirect('masters:coursereg')
        success_count = 0
        fail_count = 0
        for val in selected:
            try:
                sid, ccode, ay, sem = val.split('|')
                student = Student.objects.get(student_id=sid)
                course = Course.objects.get(course_code=ccode)
                # Find the old registration (conflict)
                old_reg = StudentCourse.objects.filter(student=student, course=course).exclude(academic_year=ay, semester=sem).first()
                # To avoid unique constraint error, delete old before creating new
                if old_reg:
                    old_reg.delete()
                StudentCourse.objects.create(student=student, course=course, academic_year=ay, semester=sem, is_active=True)
                success_count += 1
            except Exception as e:
                fail_count += 1
        if success_count:
            messages.success(request, f"{success_count} conflict(s) registered successfully.")
        if fail_count:
            messages.error(request, f"{fail_count} conflict(s) failed to register.")
        # After update, remove session conflicts and redirect
        if 'coursereg_conflicts' in request.session:
            del request.session['coursereg_conflicts']
        return redirect('masters:coursereg')



@login_required
def course_upload(request):
    if request.method == "POST" and request.FILES.get("csv_file"):
        from io import TextIOWrapper
        import csv
        import collections
        import re
        from .models import Course, Department

        csv_file = request.FILES["csv_file"]
        success_count = 0
        error_groups = collections.defaultdict(list)

        try:
            decoded_file = TextIOWrapper(csv_file.file, encoding="utf-8")
            
            # Use sniffer for robust delimiter detection
            sample = decoded_file.read(2048)
            decoded_file.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                reader = csv.DictReader(decoded_file, dialect=dialect)
            except Exception:
                reader = csv.DictReader(decoded_file)

            if not reader.fieldnames:
                messages.error(request, "CSV file is missing headers.")
                return redirect("masters:courses")

            # Robust header normalization
            import unicodedata
            def norm_h(s):
                if not s: return ""
                s = unicodedata.normalize("NFKC", s)
                return re.sub(r'[^a-zA-Z0-9]', '', s).lower()

            h_map = {norm_h(k): k for k in reader.fieldnames}

            # Map the required columns with flexibility
            code_col = h_map.get(norm_h("course_code")) or h_map.get(norm_h("coursecode"))
            name_col = h_map.get(norm_h("course_name")) or h_map.get(norm_h("coursename"))

            if not code_col or not name_col:
                messages.error(request, "CSV must have 'course_code' and 'course_name' columns.")
                return redirect("masters:courses")

            valid_rows = []
            for i, row in enumerate(reader, start=2):
                code = (row.get(code_col) or "").strip()
                name = (row.get(name_col) or "").strip()

                if not code or not name:
                    error_groups["Missing course_code or course_name"].append(i)
                    continue
                
                valid_rows.append({"i": i, "code": code, "name": name})

            if not valid_rows:
                if error_groups:
                    for msg, rows in error_groups.items():
                        messages.warning(request, f"Rows {', '.join(map(str, sorted(rows)))}: {msg}")
                return redirect("masters:courses")

            # Bulk fetch existing courses
            codes_set = {r["code"].lower() for r in valid_rows}
            existing_objs = Course.objects.filter(course_code__in=codes_set)
            existing_map = {c.course_code.lower(): c for c in existing_objs}

            existing_codes = {c.course_code.lower() for c in Course.objects.all()}
            
            new_courses = []
            duplicate_codes = []
            
            for data in valid_rows:
                if data["code"].lower() in existing_codes:
                    duplicate_codes.append(data["code"])
                else:
                    new_courses.append(Course(course_code=data["code"], course_name=data["name"]))

            if new_courses:
                with transaction.atomic():
                    Course.objects.bulk_create(new_courses, batch_size=1000)
                messages.success(request, f"Successfully uploaded {len(new_courses)} new course(s).")

            if duplicate_codes:
                messages.warning(request, f"Course data already exist / duplicate data found:<br><br>{', '.join(duplicate_codes)}")

            if error_groups:
                for msg, rows in error_groups.items():
                    messages.error(request, f"{msg}: Rows {', '.join(map(str, sorted(rows)))}")
        
        except Exception as e:
            messages.error(request, f"Error processing CSV: {e}")
    else:
        messages.error(request, "Please select a valid CSV file to upload.")
    return redirect("masters:courses")


# ===== FACULTY CSV UPLOAD =====
@login_required
def faculty_upload(request):
    if request.method == "POST" and request.FILES.get("csv_file"):
        from io import TextIOWrapper
        import csv
        import unicodedata
        import re
        import collections
        from .models import Department, Faculty
        from accounts.models import User

        csv_file = request.FILES["csv_file"]
        success_count = 0
        error_groups = collections.defaultdict(list)

        try:
            decoded_file = TextIOWrapper(csv_file.file, encoding="utf-8")
            
            # Robust delimiter detection
            sample = decoded_file.read(2048)
            decoded_file.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                reader = csv.DictReader(decoded_file, dialect=dialect)
            except Exception:
                reader = csv.DictReader(decoded_file)

            if not reader.fieldnames:
                messages.error(request, "CSV file is missing headers.")
                return redirect("masters:faculty")

            # Robust header normalization
            import unicodedata
            def norm_h(s):
                if not s: return ""
                s = unicodedata.normalize("NFKC", s)
                return re.sub(r'[^a-zA-Z0-9]', '', s).lower()

            h_map = {norm_h(k): k for k in reader.fieldnames}

            def normalize_val(val):
                if not val:
                    return ""
                val = unicodedata.normalize("NFKC", val)
                val = re.sub(r"[\s\u00A0\u200B\u200C\u200D\uFEFF]+", " ", val)
                return val.strip().lower()

            # Department lookup
            dept_lookup = {
                normalize_val(d.dept_name): d for d in Department.objects.all()
            }

            faculty_id_key = h_map.get(norm_h("faculty_id")) or h_map.get(norm_h("facultyid"))
            faculty_name_key = h_map.get(norm_h("faculty_name")) or h_map.get(norm_h("facultyname"))
            phone_key = h_map.get(norm_h("phone_number")) or h_map.get(norm_h("phone"))
            designation_key = h_map.get(norm_h("designation"))
            status_key = h_map.get(norm_h("status"))
            dept_key = h_map.get(norm_h("dept_name")) or h_map.get(norm_h("department"))

            if not faculty_id_key or not dept_key:
                messages.error(request, "CSV missing required columns: faculty_id, dept_name")
                return redirect("masters:faculty")

            # Map triggers for loop access
            field_map = {
                "faculty_id": faculty_id_key,
                "faculty_name": faculty_name_key,
                "phone_number": phone_key,
                "designation": designation_key,
                "status": status_key,
            }

            mismatches = []

            # --- First pass: validate basic fields, collect rows ---
            valid_rows = []  # rows that passed basic validation (except User/Faculty)
            id_to_rownums = {}  # for error messages per faculty_id

            for i, row in enumerate(reader, start=2):
                faculty_id = (
                    row.get(field_map.get("faculty_id"))
                    if field_map.get("faculty_id")
                    else None
                )
                phone_number = (
                    row.get(field_map.get("phone_number"))
                    if field_map.get("phone_number")
                    else None
                )
                designation = (
                    row.get(field_map.get("designation"))
                    if field_map.get("designation")
                    else None
                )
                status = (
                    row.get(field_map.get("status"))
                    if field_map.get("status")
                    else "ACTIVE"
                )
                dept_name = row.get(dept_key) if dept_key else None
                raw_name = (
                    row.get(field_map.get("faculty_name"))
                    if field_map.get("faculty_name")
                    else None
                )

                row_has_error = False

                if not faculty_id:
                    error_groups["faculty_id is missing in the CSV."].append(i)
                    row_has_error = True

                # Department validation using lookup
                if not dept_name:
                    error_groups["Department name is missing in the CSV."].append(i)
                    row_has_error = True
                    dept = None
                else:
                    norm_dept_name = normalize(dept_name)
                    dept = dept_lookup.get(norm_dept_name)
                    if not dept:
                        error_groups["Departments not found in system"].append(dept_name)
                        row_has_error = True

                if row_has_error or not faculty_id:
                    continue

                valid_rows.append(
                    {
                        "row_num": i,
                        "faculty_id": faculty_id,
                        "phone_number": phone_number,
                        "designation": designation,
                        "status": status,
                        "dept": dept,
                        "raw_name": raw_name,
                    }
                )
                id_to_rownums.setdefault(faculty_id, []).append(i)

            if not valid_rows:
                return redirect("masters:faculty")

            # --- Bulk fetch Users for all faculty_ids ---
            faculty_ids = {r["faculty_id"] for r in valid_rows}
            users_qs = User.objects.filter(username__in=faculty_ids)
            users_map = {u.username: u for u in users_qs}

            # Report missing users
            missing_user_ids = sorted(faculty_ids - set(users_map.keys()))
            if missing_user_ids:
                for fid in missing_user_ids:
                    error_groups["Users not found in system (Not linked to any user)"].append(fid)
                
                # keep only rows which have a User
                valid_rows = [
                    r for r in valid_rows if r["faculty_id"] in users_map
                ]
                if not valid_rows:
                    # Report what we have so far
                    if error_groups:
                        for msg, identifiers in error_groups.items():
                            if identifiers and isinstance(identifiers[0], int):
                                rows_str = ", ".join(map(str, sorted(set(identifiers))))
                                messages.error(request, f"{msg} (Affected Rows: {rows_str})")
                            else:
                                ids_str = ", ".join(sorted(set(map(str, identifiers))))
                                messages.error(request, f"{msg}: {ids_str}")
                    return redirect("masters:faculty")

            # --- Bulk fetch existing Faculty records ---
            existing_faculty_qs = Faculty.objects.filter(
                faculty_id__in={r["faculty_id"] for r in valid_rows}
            )
            existing_faculty_map = {
                f.faculty_id: f for f in existing_faculty_qs
            }

            new_faculty_objects = []
            duplicate_ids = []

            # --- Decide new vs existing; build diffs; collect to create ---
            for r in valid_rows:
                row_num = r["row_num"]
                faculty_id = r["faculty_id"]
                phone_number = r["phone_number"]
                designation = r["designation"]
                status = r["status"] or "ACTIVE"
                dept = r["dept"]
                raw_name = r["raw_name"]

                user = users_map[faculty_id]
                name = raw_name
                if not name:
                    name = f"{user.first_name} {user.last_name}".strip()

                if faculty_id in existing_faculty_map:
                    faculty = existing_faculty_map[faculty_id]
                    diffs = []

                    if faculty.faculty_name != name:
                        diffs.append(("Name", faculty.faculty_name, name))
                    if faculty.email != user.email:
                        diffs.append(("Email", faculty.email, user.email))
                    if faculty.phone_number != phone_number:
                        diffs.append(("Phone Number", faculty.phone_number, phone_number))
                    if faculty.dept != dept:
                        diffs.append(("Department", faculty.dept.dept_name if faculty.dept else "", dept.dept_name if dept else ""))
                    if faculty.status != status:
                        diffs.append(("Status", faculty.status, status))
                    if designation and faculty.designation != designation:
                        diffs.append(("Designation", faculty.designation, designation))

                    if not diffs:
                        duplicate_ids.append(faculty_id)
                    else:
                        mismatches.append({"faculty_id": faculty_id, "diffs": diffs})
                else:
                    # New Faculty → collect for bulk_create
                    new_faculty_objects.append(
                        Faculty(
                            faculty_id=faculty_id,
                            user=user,
                            faculty_name=name,
                            phone_number=phone_number,
                            dept=dept,
                            designation=designation,
                            status=status,
                            email=user.email,
                        )
                    )

            # Summarize duplicates
            if duplicate_ids:
                messages.warning(request, f"Faculty data already exist / duplicate data found:<br><br>{', '.join(duplicate_ids)}")

            # Report grouped errors (Red)
            if error_groups:
                for msg, identifiers in error_groups.items():
                    if identifiers and isinstance(identifiers[0], int):
                        rows_str = ", ".join(map(str, sorted(set(identifiers))))
                        messages.error(request, f"{msg} (Affected Rows: {rows_str})")
                    else:
                        ids_str = ", ".join(sorted(set(map(str, identifiers))))
                        messages.error(request, f"{msg}: {ids_str}")

            if new_faculty_objects:
                with transaction.atomic():
                    Faculty.objects.bulk_create(new_faculty_objects, batch_size=1000)
                messages.success(request, f"Successfully imported {len(new_faculty_objects)} new faculty member(s).")

            if mismatches:
                request.session["faculty_mismatches"] = mismatches
                return redirect("masters:faculty_update_conflicts")

        except Exception as e:
            messages.error(request, f"Error importing CSV: {e}")
    else:
        messages.error(request, "No file uploaded.")

    return redirect("masters:faculty")

@login_required
def faculty_add(request):
    from .models import Faculty, Department
    from accounts.models import User
    departments = Department.objects.all()

    if request.method == "POST":
        faculty_id = request.POST.get("faculty_id", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        dept_id = request.POST.get("department")
        designation = request.POST.get("designation")
        status = request.POST.get("status", "ACTIVE")

        if not faculty_id:
            messages.error(request, "Faculty ID is required.")
            return redirect("masters:faculty_add")
            
        if not first_name or not last_name:
            messages.error(request, "First Name and Last Name are required.")
            return redirect("masters:faculty_add")
            
        if not email:
            messages.error(request, "Email address is required.")
            return redirect("masters:faculty_add")
            
        if not dept_id:
            messages.error(request, "Department selection is mandatory.")
            return redirect("masters:faculty_add")

        if Faculty.objects.filter(faculty_id=faculty_id).exists() or User.objects.filter(username=faculty_id).exists():
            messages.error(request, f"Faculty with ID {faculty_id} already exists. To update, please use the edit view.")
            return redirect("masters:faculty_add")

        try:
            # Create user
            fac_password = f"{faculty_id}@{faculty_id}"
            user = User.objects.create_user(
                username=faculty_id,
                email=email,
                password=fac_password,
                first_name=first_name,
                last_name=last_name,
                role='Faculty'
            )

            # Create Faculty
            dept = Department.objects.get(id=dept_id) if dept_id else None
            Faculty.objects.create(
                faculty_id=faculty_id,
                user=user,
                faculty_name=f"{first_name} {last_name}".strip(),
                dept=dept,
                email=email,
                phone_number=phone,
                designation=designation,
                status=status
            )
            messages.success(request, f"User created successfully. Password is: {fac_password}")
            return redirect("masters:faculty")
        except Exception as e:
            messages.error(request, f"Error adding faculty: {e}")
            return redirect("masters:faculty_add")

    return render(request, "masters/faculty_add.html", {
        "departments": departments,
    })

# AJAX: Edit course

@login_required
def course_add(request):
    from .models import Course
    
    if request.method == "POST":
        course_code = request.POST.get("course_code", "").strip()
        course_name = request.POST.get("course_name", "").strip()
        is_active = request.POST.get("is_active") == "1"
        
        if not course_code or not course_name:
            messages.error(request, "Course code and Course name are strictly required.")
            return redirect("masters:course_add")
            
        if Course.objects.filter(course_code=course_code).exists():
            messages.error(request, f"Course {course_code} already exists. Please edit it instead of creating a duplicate.")
            return redirect("masters:course_add")
            
        try:
            Course.objects.create(
                course_code=course_code,
                course_name=course_name,
                is_active=is_active
            )
            messages.success(request, f"Course {course_code} added successfully.")
            return redirect("masters:courses")
        except Exception as e:
            messages.error(request, f"Error adding course: {e}")
            return redirect("masters:course_add")

    return render(request, "masters/course_add.html")

@csrf_exempt
@login_required
def course_edit(request, pk):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            code = data.get('course_code', '').strip()
            name = data.get('course_name', '').strip()
            is_active = data.get('is_active', True)
            course = Course.objects.get(pk=pk)
            if code:
                course.course_code = code
            if name:
                course.course_name = name
            course.is_active = bool(is_active)
            course.save()
            # Set a session flag for notification
            request.session['course_message'] = 'Course updated successfully.'
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# AJAX: Delete course
@csrf_exempt
@login_required
def course_delete(request, pk):
    if request.method == 'POST':
        try:
            course = Course.objects.get(pk=pk)
            course.delete()
            # Set a session flag for notification
            request.session['course_message'] = 'Course deleted successfully.'
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})
# (already imported at top)

# ===== STUDENTS =====
@login_required
def student(request):
    from .models import Department, Batch
    from django.core.paginator import Paginator
    from django.db import models
    students = Student.objects.select_related('user', 'dept', 'batch').all().order_by('student_id')
    departments = Department.objects.all()
    batches = Batch.objects.all()
    search = request.GET.get('search', '').strip().lower()
    department = request.GET.get('department', '').strip()
    batch = request.GET.get('batch', '').strip()
    if search:
        students = students.filter(
            models.Q(student_id__icontains=search) |
            models.Q(user__first_name__icontains=search) |
            models.Q(user__last_name__icontains=search)
        )
    if department and department != 'all':
        students = students.filter(dept__dept_code=department)
    if batch and batch != 'all':
        students = students.filter(batch__batch_code=batch)
    paginator = Paginator(students, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # Role-based base template
    if hasattr(request.user, 'role') and request.user.role == 'faculty':
        base_template = "core/base_faculty.html"
    else:
        base_template = "core/base_admin.html"
    return render(request, "masters/student.html", {
        "page_obj": page_obj,
        "departments": departments,
        "batches": batches,
        "search": search,
        "selected_department": department,
        "selected_batch": batch,
        "base_template": base_template
    })

@login_required
def student_content(request):
    return render(request, "masters/student_content.html")

@login_required
def student_detail(request, pk):
    from .models import Student
    student = Student.objects.select_related('user', 'dept', 'program').get(pk=pk)
    if hasattr(request.user, 'role'):
        if request.user.role == 'faculty':
            base_template = "core/base_faculty.html"
        elif request.user.role == 'student':
            base_template = "core/base_student.html"
        else:
            base_template = "core/base_admin.html"
    else:
        base_template = "core/base_admin.html" if request.user.is_staff or request.user.is_superuser else "core/base_student.html"
    return render(request, "masters/student_detail.html", {"student": student, "base_template": base_template})

@login_required
def student_add(request):
    from .models import Student, Department, Program, Batch
    from accounts.models import User
    departments = Department.objects.all()
    programs = Program.objects.all()
    batches = Batch.objects.all()
    
    if request.method == "POST":
        student_id = request.POST.get("student_id", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone_number", "").strip()
        parent_phone = request.POST.get("parent_phone_number", "").strip()
        dept_id = request.POST.get("department")
        program_id = request.POST.get("program")
        batch_id = request.POST.get("batch")
        status = request.POST.get("status", "ACTIVE")
        
        if not student_id:
            messages.error(request, "Student ID is required.")
            return redirect("masters:student_add")
            
        if not first_name or not last_name:
            messages.error(request, "First Name and Last Name are required.")
            return redirect("masters:student_add")
            
        if not email:
            messages.error(request, "Email address is required.")
            return redirect("masters:student_add")
            
        if not dept_id or not program_id or not batch_id:
            messages.error(request, "Department, Program, and Regulation/Batch selections are mandatory.")
            return redirect("masters:student_add")
            
        if Student.objects.filter(student_id=student_id).exists() or User.objects.filter(username=student_id).exists():
            messages.error(request, f"Student with ID {student_id} already exists. To update this student, use the edit function.")
            return redirect("masters:student_add")
            
        try:
            # Create user
            stu_password = "Test@123"
            user = User.objects.create_user(
                username=student_id,
                email=email,
                password=stu_password,
                first_name=first_name,
                last_name=last_name,
                role='Student'
            )
            
            # Create Student
            dept = Department.objects.get(id=dept_id) if dept_id else None
            prog = Program.objects.get(id=program_id) if program_id else None
            batch = Batch.objects.get(id=batch_id) if batch_id else None
            
            Student.objects.create(
                student_id=student_id,
                user=user,
                std_name=f"{first_name} {last_name}".strip(),
                program=prog,
                dept=dept,
                email=email,
                phone_number=phone,
                parent_phone_number=parent_phone,
                status=status,
                batch=batch
            )
            messages.success(request, f"User created successfully. Password is: {stu_password}")
            return redirect("masters:student")
        except Exception as e:
            messages.error(request, f"Error adding student: {e}")
            return redirect("masters:student_add")

    if hasattr(request.user, 'role') and request.user.role == 'faculty':
        base_template = "core/base_faculty.html"
    else:
        base_template = "core/base_admin.html"
        
    return render(request, "masters/student_add.html", {
        "departments": departments,
        "programs": programs,
        "batches": batches,
        "base_template": base_template
    })

@login_required
def student_edit(request, pk):
    from .models import Student, Department, Program, Batch
    student = Student.objects.select_related('user', 'dept', 'program', 'batch').get(pk=pk)
    departments = Department.objects.all()
    programs = Program.objects.all()
    batches = Batch.objects.all()
    if request.method == "POST":
        user = student.user
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.email = request.POST.get("email", user.email)
        user.save()
        dept_id = request.POST.get("department")
        program_id = request.POST.get("program")
        batch_id = request.POST.get("batch")
        student.dept_id = dept_id if dept_id else student.dept_id
        student.program_id = program_id if program_id else student.program_id
        student.batch_id = batch_id if batch_id else student.batch_id
        student.email = user.email  # keep in sync
        student.phone_number = request.POST.get("phone_number", student.phone_number)
        student.parent_phone_number = request.POST.get("parent_phone_number", student.parent_phone_number)
        student.status = request.POST.get("status", student.status)
        student.save()
        from django.contrib import messages
        messages.success(request, "Student details updated successfully.")
        return redirect("masters:student_detail", pk=student.pk)
    return render(request, "masters/student_edit.html", {"student": student, "departments": departments, "programs": programs, "batches": batches})

@login_required
def student_delete(request, pk):
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404, redirect
    from .models import Student
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        student.delete()
        # AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": True})
        # Normal form submission
        return redirect("masters:student")
    return render(request, "masters/student_delete.html", {"student": student})

# ===== FACULTY =====
@login_required
def faculty(request):
    from .models import Department
    from django.core.paginator import Paginator
    faculties = Faculty.objects.select_related('user', 'dept').all().order_by('faculty_id')
    departments = Department.objects.all()
    search = request.GET.get('search', '').strip().lower()
    department = request.GET.get('department', '').strip()
    if search:
        faculties = faculties.filter(
            models.Q(faculty_id__icontains=search) |
            models.Q(user__first_name__icontains=search) |
            models.Q(user__last_name__icontains=search)
        )
    if department and department != 'all':
        faculties = faculties.filter(dept__dept_code=department)
    paginator = Paginator(faculties, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "masters/faculty.html", {
        "page_obj": page_obj,
        "departments": departments,
        "search": search,
        "selected_department": department
    })

@login_required
def faculty_content(request):
    return render(request, "masters/faculty_content.html")

@login_required
def faculty_detail(request, pk):
    from django.shortcuts import get_object_or_404
    faculty = get_object_or_404(Faculty.objects.select_related('user', 'dept'), pk=pk)
    if hasattr(request.user, 'role'):
        if request.user.role == 'student':
            base_template = "core/base_student.html"
        elif request.user.role == 'faculty':
            base_template = "core/base_faculty.html"
        else:
            base_template = "core/base_admin.html"
    else:
        base_template = "core/base_admin.html" if request.user.is_staff or request.user.is_superuser else "core/base_faculty.html"
    return render(request, "masters/faculty_detail.html", {"faculty": faculty, "base_template": base_template})

@login_required
def faculty_detail_content(request, pk):
    return render(request, "masters/faculty_detail_content.html", {"pk": pk})

@login_required
def faculty_edit(request, pk):
    from .models import Faculty, Department
    from accounts.models import User
    faculty = Faculty.objects.select_related('user', 'dept').get(pk=pk)
    departments = Department.objects.all()
    user = faculty.user
    if request.method == "POST":
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.email = request.POST.get("email", user.email)
        user.save()
        dept_id = request.POST.get("department")
        if dept_id:
            faculty.dept_id = dept_id
        faculty.phone_number = request.POST.get("phone", faculty.phone_number)
        faculty.designation = request.POST.get("designation", faculty.designation)
        faculty.status = request.POST.get("status", faculty.status)
        faculty.save()
        from django.contrib import messages
        messages.success(request, "Faculty details updated successfully.")
        return redirect("masters:faculty_detail", pk=faculty.pk)
    return render(request, "masters/faculty_edit.html", {"faculty": faculty, "user": user, "departments": departments})

@login_required
def faculty_delete(request, pk):
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404, redirect
    from .models import Faculty
    faculty = get_object_or_404(Faculty, pk=pk)
    user = faculty.user if hasattr(faculty, 'user') else None
    if request.method == "POST":
        faculty.delete()
        # AJAX request
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"success": True})
        # Normal form submission
        return redirect("masters:faculty")
    return render(request, "masters/faculty_delete.html", {"faculty": faculty, "user": user})


# ===== ROOMS =====
from django.contrib import messages
import csv
from io import TextIOWrapper
import unicodedata
import re
from django.shortcuts import redirect

@login_required
def rooms(request):
    from django.core.paginator import Paginator
    unique_blocks = Room.objects.values_list('block', flat=True).distinct()
    unique_room_types = Room.objects.values_list('room_type', flat=True).exclude(room_type__isnull=True).exclude(room_type='').distinct()
    rooms = Room.objects.all().order_by('room_code')
    search = request.GET.get('search', '').strip().lower()
    block = request.GET.get('block', '').strip()
    room_type = request.GET.get('room_type', '').strip()
    capacity_min = request.GET.get('capacity_min', '').strip()
    capacity_max = request.GET.get('capacity_max', '').strip()
    if search:
        rooms = rooms.filter(
            models.Q(room_code__icontains=search) |
            models.Q(block__icontains=search)
        )
    if block and block.lower() != 'all':
        rooms = rooms.filter(block=block)
    if room_type and room_type.lower() != 'all':
        rooms = rooms.filter(room_type=room_type)
    if capacity_min.isdigit():
        rooms = rooms.filter(capacity__gte=int(capacity_min))
    if capacity_max.isdigit():
        rooms = rooms.filter(capacity__lte=int(capacity_max))
    paginator = Paginator(rooms, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, "masters/rooms.html", {
        "page_obj": page_obj,
        "unique_blocks": unique_blocks,
        "unique_room_types": unique_room_types,
        "search": search,
        "selected_block": block,
        "selected_room_type": room_type,
        "capacity_min": capacity_min,
        "capacity_max": capacity_max,
    })


@login_required
def rooms_content(request):
    return render(request, "masters/rooms_content.html")

@login_required
def room_detail(request, pk):
    room = Room.objects.get(pk=pk)
    return render(request, "masters/room_detail.html", {"room": room})

@login_required
def room_detail_content(request, pk):
    return render(request, "masters/room_detail_content.html", {"pk": pk})

@login_required
def room_edit(request, pk):
    room = Room.objects.get(pk=pk)
    if request.method == "POST":
        room.block = request.POST.get("block", room.block)
        room.floor = request.POST.get("floor", room.floor)
        # Capacity is auto-calculated, so update rows/columns
        try:
            room.rows = int(request.POST.get("rowscount", room.rows))
            room.columns = int(request.POST.get("columnscount", room.columns))
        except (TypeError, ValueError):
            pass
        # Checkbox: present if checked, absent if not
        room.is_active = 'is_active' in request.POST
        room.save()
        messages.success(request, "Room updated successfully.")
        return redirect("masters:room_detail", pk=room.pk)
    return render(request, "masters/room_edit.html", {"room": room})

@login_required
def room_delete(request, pk):
    room = Room.objects.get(pk=pk)
    if request.method == "POST":
        room.delete()
        messages.success(request, "Room deleted successfully.")
        return redirect("masters:rooms")
    return render(request, "masters/room_delete.html", {"room": room})

# ===== COURSES =====
@login_required
def courses(request):
    from .models import Course
    from django.core.paginator import Paginator
    search = request.GET.get('search', '').strip().lower()
    courses = Course.objects.all().order_by('course_code')
    if search:
        courses = courses.filter(
            models.Q(course_code__icontains=search) |
            models.Q(course_name__icontains=search)
        )
    paginator = Paginator(courses, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    # Check for session notification
    course_message = request.session.pop('course_message', None)
    context = {"page_obj": page_obj, "search": search}
    if course_message:
        from django.contrib import messages
        messages.success(request, course_message)
    return render(request, "masters/courses.html", context)

# ===== COURSE CSV UPLOAD =====
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
@login_required(login_url='/accounts/login/')
def coursereg(request):
    user = request.user
    # Initialize defaults to prevent UnboundLocalError
    courseregs = StudentCourse.objects.select_related('student', 'course').all()
    courses = Course.objects.order_by('course_code').all()
    registration_types = sorted(set(StudentCourse.objects.values_list('registration_type', flat=True)))
    academic_years = sorted(set(StudentCourse.objects.values_list('academic_year', flat=True)))
    semesters = sorted(set(StudentCourse.objects.values_list('semester', flat=True)), key=str)
    base_template = "core/base_admin.html"

    if hasattr(user, 'role'):
        role = user.role.lower() if user.role else ''
        if role in ['student', 'Student', 'STUDENT']:
            try:
                student = user.student_profile
                courseregs = courseregs.filter(student=student)
                academic_years = sorted(set(courseregs.values_list('academic_year', flat=True)))
                semesters = sorted(set(courseregs.values_list('semester', flat=True)), key=str)
            except Student.DoesNotExist:
                courseregs = StudentCourse.objects.none()
            base_template = "core/base_student.html"
        elif role == 'faculty':
            base_template = "core/base_faculty.html"
        else:
            base_template = "core/base_admin.html"
    else:
        if not (user.is_staff or user.is_superuser):
            base_template = "core/base_student.html"

    return render(request, "masters/coursereg.html", {
        "courseregs": courseregs,
        "courses": courses,
        "academic_years": academic_years,
        "semesters": semesters,
        "registration_types": registration_types,
        "user": user,
        "base_template": base_template
    })

@login_required
@login_required
def coursereg_upload(request):
    if request.method == "POST" and request.FILES.get("csv_file"):
        from io import TextIOWrapper
        import csv
        from .models import Student, Course
        from operations.models import StudentCourse
        from django.db import transaction

        csv_file = request.FILES["csv_file"]
        success_count = 0
        error_groups = collections.defaultdict(list)
        conflict_rows = []
        dup_count = 0

        try:
            # Use TextIOWrapper for robust decoding and universal newlines
            decoded_file = TextIOWrapper(csv_file.file, encoding="utf-8-sig")
            
            # Use sniffer for robust delimiter detection
            sample = decoded_file.read(2048)
            decoded_file.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                reader = csv.DictReader(decoded_file, dialect=dialect)
            except Exception:
                reader = csv.DictReader(decoded_file)

            if not reader.fieldnames:
                messages.error(request, "CSV file is missing headers.")
                return redirect(request.META.get("HTTP_REFERER", "/"))

            def norm_h(s):
                if not s: return ""
                s = unicodedata.normalize("NFKC", s)
                return re.sub(r'[^a-zA-Z0-9]', '', s).lower()

            h_map = {norm_h(k): k for k in reader.fieldnames}
            
            # Map columns with flexibility
            sid_key = h_map.get(norm_h("student_id")) or h_map.get(norm_h("studentid"))
            ccode_key = h_map.get(norm_h("course_code")) or h_map.get(norm_h("coursecode"))
            ay_key = h_map.get(norm_h("academic_year")) or h_map.get(norm_h("academicyear"))
            sem_key = h_map.get(norm_h("semester"))
            reg_key = h_map.get(norm_h("registration_type")) or h_map.get(norm_h("registrationtype"))

            required = [sid_key, ccode_key, ay_key, sem_key]
            if not all(required):
                missing = []
                if not sid_key: missing.append("student_id")
                if not ccode_key: missing.append("course_code")
                if not ay_key: missing.append("academic_year")
                if not sem_key: missing.append("semester")
                messages.error(request, f"CSV missing required columns: {', '.join(missing)}")
                return redirect(request.META.get("HTTP_REFERER", "/"))

            # Update f_map to internal keys for the loop
            f_map = {
                "studentid": sid_key,
                "coursecode": ccode_key,
                "academicyear": ay_key,
                "semester": sem_key,
                "registrationtype": reg_key
            }

            valid_rows = []
            sid_set = set()
            course_set = set()
            total_rows = 0

            for i, row in enumerate(reader, start=2):
                total_rows += 1
                try:
                    sid = (row.get(f_map["studentid"]) or "").strip()
                    ccode = (row.get(f_map["coursecode"]) or "").strip()
                    ay = (row.get(f_map["academicyear"]) or "").strip()
                    sem = (row.get(f_map["semester"]) or "").strip()
                    reg = (row.get(f_map.get("registrationtype", "")) or "REGULAR").strip()

                    if not all([sid, ccode, ay, sem]):
                        error_groups["Missing required values (student_id, course_code, etc.)"].append(i)
                        continue

                    # Normalization for student_id lookup
                    import unicodedata, re
                    sid_norm = unicodedata.normalize("NFKC", sid)
                    sid_norm = re.sub(r"[\s\u00A0\u200B\u200C\u200D\ufeff]+", " ", sid_norm).strip().lower()

                    valid_rows.append({"i": i, "sid": sid, "sid_norm": sid_norm, "ccode": ccode, "ay": ay, "sem": sem, "reg": reg})
                    sid_set.add(sid_norm)
                    course_set.add(ccode.lower())
                except Exception as e:
                    error_groups[f"Malformed row: {e}"].append(i)

            if not valid_rows:
                if error_groups:
                    for msg, rows in error_groups.items():
                        messages.warning(request, f"Rows {', '.join(map(str, sorted(rows)))}: {msg}")
                return redirect(request.META.get("HTTP_REFERER", "/"))

            # Bulk fetch
            students_map = {s.student_id.lower(): s for s in Student.objects.filter(student_id__in=sid_set)}
            courses_map = {c.course_code.lower(): c for c in Course.objects.filter(course_code__in=course_set)}

            # Registration checks
            existing_regs = StudentCourse.objects.filter(
                student__student_id__in=sid_set,
                course__course_code__in=course_set
            ).select_related('student', 'course')

            existing_exact = set((r.student.student_id.lower(), r.course.course_code.lower(), str(r.academic_year), str(r.semester)) for r in existing_regs)
            existing_pairs = {(r.student.student_id.lower(), r.course.course_code.lower()): (r.academic_year, r.semester) for r in existing_regs}

            new_objects = []
            duplicate_pairs = []
            
            for r in valid_rows:
                student = students_map.get(r["sid_norm"])
                course = courses_map.get(r["ccode"].lower())

                if not student:
                    error_groups[f"Student not found in system"].append(r["sid"])
                    continue
                if not course:
                    error_groups[f"Course not found in system"].append(r["ccode"])
                    continue

                key_exact = (r["sid_norm"], r["ccode"].lower(), str(r["ay"]), str(r["sem"]))
                key_pair = (r["sid_norm"], r["ccode"].lower())

                if key_exact in existing_exact:
                    duplicate_pairs.append(f"{r['sid']} ({r['ccode']})")
                    continue
                
                if key_pair in existing_pairs:
                    old_ay, old_sem = existing_pairs[key_pair]
                    conflict_rows.append({
                        "student_id": r["sid"], "course_code": r["ccode"], "academic_year": r["ay"], "semester": r["sem"],
                        "reason": "Already registered for this course in another term",
                        "old_academic_year": old_ay, "old_semester": old_sem,
                        "row_num": r["i"]
                    })
                    continue

                new_objects.append(StudentCourse(
                    student=student, course=course, academic_year=r["ay"], semester=r["sem"],
                    registration_type=r["reg"], is_active=True
                ))

            if new_objects:
                with transaction.atomic():
                    StudentCourse.objects.bulk_create(new_objects, batch_size=1000)
                messages.success(request, f"Successfully uploaded {len(new_objects)} new registration(s).")

            if duplicate_pairs:
                messages.warning(request, f"Registration data already exist / duplicate data found:<br><br>{', '.join(duplicate_pairs)}")

            if error_groups:
                for msg, items in error_groups.items():
                    messages.error(request, f"{msg}: {', '.join(map(str, sorted(set(items))))}")

            # Conflict Handling (Interactive resolution)
            if conflict_rows:
                messages.error(request, f"{len(conflict_rows)} registrations found to have conflicts.")
                request.session["coursereg_conflicts"] = conflict_rows
                return render(request, "masters/coursereg_conflict.html", {"conflicts": conflict_rows})

        except Exception as e:
            messages.error(request, f"Error importing CSV: {e}")
    else:
        messages.error(request, "No file uploaded.")
    return redirect(request.META.get("HTTP_REFERER", "/"))

# Final fallback to ensure HttpResponse is always returned
from django.http import HttpResponse
@login_required
def _coursereg_upload_fallback(*args, **kwargs):
    return HttpResponse("Unexpected error: No response returned.")

@login_required
def display_students(request):
    students = Student.objects.all()
    return render(request, "masters/student.html", {"students": students})

# ===== STUDENT CSV UPLOAD =====
@login_required
def student_upload(request):
    if request.method == "POST" and request.FILES.get("csv_file"):
        from io import TextIOWrapper
        import csv
        import unicodedata
        import re

        csv_file = request.FILES["csv_file"]
        success_count = 0

        try:
            decoded_file = TextIOWrapper(csv_file.file, encoding="utf-8")
            reader = csv.DictReader(decoded_file)

            if not reader.fieldnames:
                messages.error(request, "CSV file is missing headers.")
                return redirect("masters:student")

            # Normalization helper
            def normalize(val):
                if not val:
                    return ""
                val = unicodedata.normalize("NFKC", val)
                val = re.sub(r"[\s\u00A0\u200B\u200C\u200D\uFEFF]+", " ", val)
                val = val.strip().lower()
                return val

            from .models import Department, Program, Batch, Student
            from accounts.models import User

            # In-memory lookups (already good)
            dept_lookup = {
                normalize(d.dept_name): d for d in Department.objects.all()
            }
            program_lookup = {
                normalize(p.program_code): p for p in Program.objects.all()
            }
            batch_lookup = {
                normalize(b.batch_code): b for b in Batch.objects.all()
            }

            field_map = {k.strip().lower(): k for k in reader.fieldnames}
            dept_key = field_map.get("dept_name") or field_map.get("department")
            possible_program_keys = [
                k
                for k in reader.fieldnames
                if k.strip().lower() in ("program", "program_name")
            ]
            batch_key = field_map.get("batch_code") or field_map.get("regulation")

            mismatches = []

            import collections
            error_groups = collections.defaultdict(list)

            # --- First pass: validate row structure and lookups, collect data ---
            valid_rows = []  # each item: dict with row_num, student_id, phones, dept, program, batch
            sid_to_rows = {}  # student_id -> list of row numbers (for error messages)
            seen_sids_in_csv = {} # student_id -> first row_num seen

            for i, row in enumerate(reader, start=2):
                student_id = (
                    normalize(row.get(field_map.get("student_id"))) if field_map.get("student_id") else None
                )
                if student_id:
                    if student_id in seen_sids_in_csv:
                        error_groups["Duplicate IDs found within the CSV file"].append(student_id)
                        continue
                    else:
                        seen_sids_in_csv[student_id] = i
                
                phone_number = (
                    row.get(field_map.get("phone_number"))
                    if field_map.get("phone_number")
                    else None
                )
                parent_phone_number = (
                    row.get(field_map.get("parent_phone_number"))
                    if field_map.get("parent_phone_number")
                    else None
                )
                dept_name = row.get(dept_key) if dept_key else None

                program_name = None
                for k in possible_program_keys:
                    if row.get(k):
                        program_name = row.get(k)
                        break

                batch_code = row.get(batch_key) if batch_key else None

                row_has_error = False

                # Basic validations (no DB queries yet)
                if not student_id:
                    error_groups["student_id is missing in the CSV."].append(i)
                    row_has_error = True

                if not dept_name:
                    error_groups["Department name is missing in the CSV."].append(i)
                    row_has_error = True
                    dept = None
                else:
                    norm_dept_name = normalize(dept_name)
                    dept = dept_lookup.get(norm_dept_name)
                    if not dept:
                        error_groups["Departments not found in system"].append(dept_name)
                        row_has_error = True

                if not program_name:
                    error_groups["Program name is missing in the CSV."].append(i)
                    row_has_error = True
                    program = None
                else:
                    norm_program_name = normalize(program_name)
                    program = program_lookup.get(norm_program_name)
                    if not program:
                        error_groups["Programs not found in system"].append(program_name)
                        row_has_error = True

                if not batch_code:
                    error_groups["Regulation/Batch code is missing in the CSV. Regulation is mandatory."].append(i)
                    row_has_error = True
                    batch = None
                else:
                    norm_batch_code = normalize(batch_code)
                    batch = batch_lookup.get(norm_batch_code)
                    if not batch:
                        error_groups["Regulation/Batch codes not found in system"].append(batch_code)
                        row_has_error = True

                if row_has_error or not student_id:
                    continue

                # Defer User/Student DB lookups to later; just collect row
                valid_rows.append(
                    {
                        "row_num": i,
                        "student_id": student_id,
                        "phone_number": phone_number,
                        "parent_phone_number": parent_phone_number,
                        "dept": dept,
                        "program": program,
                        "batch": batch,
                    }
                )
                sid_to_rows.setdefault(student_id, []).append(i)

            # --- Bulk fetch Users for all student_ids ---
            if valid_rows:
                student_ids = {r["student_id"] for r in valid_rows}
                users_qs = User.objects.filter(username__in=student_ids)
                users_map = {u.username: u for u in users_qs}

                missing_user_ids = sorted(student_ids - set(users_map.keys()))
                for sid in missing_user_ids:
                    error_groups["Users not found in system (Not linked to any user)"].append(sid)
                
                # Filter out rows that don't have a User
                valid_rows = [
                    r for r in valid_rows if r["student_id"] in users_map
                ]

            # If no structurally valid rows, stop
            if not valid_rows:
                # Still output any structural errors found so far
                if error_groups:
                    for msg, identifiers in error_groups.items():
                        if identifiers and isinstance(identifiers[0], int):
                            rows_str = ", ".join(map(str, sorted(set(identifiers))))
                            messages.error(request, f"{msg} (Affected Rows: {rows_str})")
                        else:
                            ids_str = ", ".join(sorted(set(map(str, identifiers))))
                            messages.error(request, f"{msg}: {ids_str}")
                return redirect("masters:student")

            # --- Bulk fetch existing Students ---
            existing_students_qs = Student.objects.filter(
                student_id__in={r["student_id"] for r in valid_rows}
            )
            existing_students_map = {
                s.student_id: s for s in existing_students_qs
            }

            # Collect duplicates separately for Orange styling
            duplicate_ids = []
            new_students = []

            for r in valid_rows:
                sid = r["student_id"]
                user = users_map[sid]
                name = f"{user.first_name} {user.last_name}".strip()
                email = user.email
                phone_number = r["phone_number"]
                parent_phone_number = r["parent_phone_number"]
                dept = r["dept"]
                program = r["program"]
                batch = r["batch"]
                row_num = r["row_num"]

                if sid in existing_students_map:
                    student = existing_students_map[sid]
                    diffs = []

                    if student.std_name != name:
                        diffs.append(("Name", student.std_name, name))
                    if student.email != email:
                        diffs.append(("Email", student.email, email))
                    if student.phone_number != phone_number:
                        diffs.append(
                            (
                                "Phone Number",
                                student.phone_number,
                                phone_number,
                            )
                        )
                    if student.parent_phone_number != parent_phone_number:
                        diffs.append(
                            (
                                "Parent Phone Number",
                                student.parent_phone_number,
                                parent_phone_number,
                            )
                        )
                    if student.dept != dept:
                        diffs.append(
                            (
                                "Department",
                                student.dept.dept_name
                                if student.dept
                                else "",
                                dept.dept_name if dept else "",
                            )
                        )
                    if student.program != program:
                        diffs.append(
                            (
                                "Program",
                                student.program.program_name
                                if student.program
                                else "",
                                program.program_name if program else "",
                            )
                        )
                    if student.batch != batch:
                        diffs.append(
                            (
                                "Regulation",
                                student.batch.batch_code
                                if student.batch
                                else "",
                                batch.batch_code if batch else "",
                            )
                        )
                    if not diffs:
                        duplicate_ids.append(sid)
                    else:
                        mismatches.append({"student_id": sid, "diffs": diffs})
                else:
                    # New student → prepare for bulk_create
                    new_students.append(
                        Student(
                            student_id=sid,
                            user=user,
                            std_name=name,
                            email=email,
                            phone_number=phone_number,
                            parent_phone_number=parent_phone_number,
                            dept=dept,
                            program=program,
                            batch=batch,
                            status="ACTIVE",
                        )
                    )

            # 1. Report Errors (Red)
            if error_groups:
                for msg, identifiers in error_groups.items():
                    if identifiers and isinstance(identifiers[0], int):
                        rows_str = ", ".join(map(str, sorted(set(identifiers))))
                        messages.error(request, f"{msg} (Affected Rows: {rows_str})")
                    else:
                        ids_str = ", ".join(sorted(set(map(str, identifiers))))
                        messages.error(request, f"{msg}: {ids_str}")

            # 2. Report Duplicates (Light Orange Warning)
            if duplicate_ids:
                messages.warning(request, f"Student data already exist / duplicate data found:<br><br>{', '.join(duplicate_ids)}")

            # 3. Report Success (Green)
            if new_students:
                with transaction.atomic():
                    Student.objects.bulk_create(new_students, batch_size=1000)
                messages.success(request, f"Successfully uploaded {len(new_students)} new student(s).")

            if mismatches:
                request.session["student_mismatches"] = mismatches
                return redirect("masters:student_update_conflicts")

        except Exception as e:
            messages.error(request, f"Error importing CSV: {e}")
    else:
        messages.error(request, "No file uploaded.")

    return redirect("masters:student")


@login_required
def student_update_conflicts(request):
    mismatches = request.session.get('student_mismatches', [])
    if request.method == 'POST':
        selected_ids = request.POST.getlist('update_student')
        updated = []
        from .models import Student, Department, Program
        def normalize(val):
            if not val:
                return ""
            import unicodedata, re
            val = unicodedata.normalize("NFKC", val)
            val = re.sub(r"[\s\u00A0\u200B\u200C\u200D\uFEFF]+", " ", val)
            return val.strip().lower()

        if not mismatches:
            messages.error(request, "No student conflicts found to update.")
            return redirect('masters:student_update_conflicts')

        if not selected_ids:
            messages.warning(request, "No students selected for update.")
            return redirect('masters:student_update_conflicts')

        for mismatch in mismatches:
            student_id = mismatch['student_id']
            if student_id in selected_ids:
                student = Student.objects.get(student_id=student_id)
                for field, old, new in mismatch['diffs']:
                    if field == 'Name':
                        student.std_name = new
                    elif field == 'Email':
                        student.email = new
                    elif field == 'Phone Number':
                        student.phone_number = new
                    elif field == 'Parent Phone Number':
                        student.parent_phone_number = new
                    elif field == 'Department':
                        dept = Department.objects.filter(dept_name=new).first()
                        if dept:
                            student.dept = dept
                    elif field == 'Program':
                        program = Program.objects.filter(program_name=new).first()
                        if program:
                            student.program = program
                    elif field == 'Status':
                        student.status = new
                student.save()
                updated.append(student_id)
        if updated:
            for sid in updated:
                messages.success(request, f"{sid} - details updated successfully")
            if 'student_mismatches' in request.session:
                del request.session['student_mismatches']
            return redirect('masters:student')
        else:
            messages.info(request, "No selected students required updating.")
            return redirect('masters:student_update_conflicts')
    return render(request, "masters/student_update_conflicts.html", {"mismatches": mismatches})


@login_required
def faculty_update_conflicts(request):
    mismatches = request.session.get('faculty_mismatches', [])
    if request.method == 'POST':
        selected_ids = request.POST.getlist('update_faculty')
        updated = []
        from .models import Faculty, Department

        if not mismatches:
            messages.error(request, "No faculty conflicts found to update.")
            return redirect('masters:faculty_update_conflicts')

        if not selected_ids:
            messages.warning(request, "No faculty selected for update.")
            return redirect('masters:faculty_update_conflicts')

        for mismatch in mismatches:
            faculty_id = mismatch['faculty_id']
            if faculty_id in selected_ids:
                faculty = Faculty.objects.get(faculty_id=faculty_id)
                for field, old, new in mismatch['diffs']:
                    if field == 'Name':
                        faculty.faculty_name = new
                    elif field == 'Email':
                        pass
                    elif field == 'Phone Number':
                        faculty.phone_number = new
                    elif field == 'Department':
                        dept = Department.objects.filter(dept_name=new).first()
                        if dept:
                            faculty.dept = dept
                    elif field == 'Status':
                        faculty.status = new
                faculty.save()
                updated.append(faculty_id)
        if updated:
            for fid in updated:
                messages.success(request, f"{fid} - details updated successfully")
            if 'faculty_mismatches' in request.session:
                del request.session['faculty_mismatches']
            return redirect('masters:faculty')
        else:
            messages.info(request, "No selected faculty required updating.")
            return redirect('masters:faculty_update_conflicts')
    return render(request, "masters/faculty_update_conflicts.html", {"mismatches": mismatches})


@login_required
def room_add(request):
    from .models import Room
    
    if request.method == "POST":
        room_code = request.POST.get("room_code", "").strip()
        block = request.POST.get("block", "").strip()
        floor = request.POST.get("floor", "").strip()
        rows_str = request.POST.get("rowscount", "0")
        cols_str = request.POST.get("columnscount", "0")
        is_active = request.POST.get("is_active") == "1"
        
        try:
            rows = int(rows_str)
            columns = int(cols_str)
            capacity = rows * columns
        except ValueError:
            messages.error(request, "Rows and columns must be numbers.")
            return redirect("masters:room_add")
            
        if not room_code:
            messages.error(request, "Room code is required.")
            return redirect("masters:room_add")
            
        if not block or not floor:
            messages.error(request, "Block and Floor are strictly required.")
            return redirect("masters:room_add")
            
        if rows <= 0 or columns <= 0:
            messages.error(request, "Room rows and columns must be strictly positive numbers.")
            return redirect("masters:room_add")
            
        if Room.objects.filter(room_code=room_code).exists():
            messages.error(request, f"Room {room_code} already exists. Proceed to edit it instead.")
            return redirect("masters:room_add")
            
        try:
            Room.objects.create(
                room_code=room_code,
                block=block,
                floor=floor,
                rows=rows,
                columns=columns,
                capacity=capacity,
                room_type="Theory", # default assignment
                is_active=is_active
            )
            messages.success(request, f"Room {room_code} added successfully.")
            return redirect("masters:rooms")
        except Exception as e:
            messages.error(request, f"Error adding room: {e}")
            return redirect("masters:room_add")

    return render(request, "masters/room_add.html")

# ===== ROOM CSV UPLOAD =====
@login_required
def room_upload(request):
    if request.method == "POST" and request.FILES.get("csv_file"):
        from io import TextIOWrapper
        import csv
        import collections
        from .models import Room

        csv_file = request.FILES["csv_file"]
        success_count = 0
        error_groups = collections.defaultdict(list)

        try:
            decoded_file = TextIOWrapper(csv_file.file, encoding="utf-8")
            
            # Robust delimiter detection
            sample = decoded_file.read(2048)
            decoded_file.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
                reader = csv.DictReader(decoded_file, dialect=dialect)
            except Exception:
                reader = csv.DictReader(decoded_file)

            if not reader.fieldnames:
                messages.error(request, "CSV file is missing headers.")
                return redirect("masters:rooms")

            # Robust header normalization
            import unicodedata
            def norm_h(s):
                if not s: return ""
                s = unicodedata.normalize("NFKC", s)
                return re.sub(r'[^a-zA-Z0-9]', '', s).lower()

            h_map = {norm_h(k): k for k in reader.fieldnames}
            
            # Map columns with flexibility
            code_key = h_map.get(norm_h("room_code")) or h_map.get(norm_h("roomcode")) or h_map.get(norm_h("room_id")) or h_map.get(norm_h("roomid"))
            block_key = h_map.get(norm_h("block"))
            floor_key = h_map.get(norm_h("floor"))
            rows_key = h_map.get(norm_h("rows"))
            cols_key = h_map.get(norm_h("columns"))
            type_key = h_map.get(norm_h("room_type")) or h_map.get(norm_h("roomtype"))

            field_map = {
                "roomcode": code_key,
                "block": block_key,
                "floor": floor_key,
                "rows": rows_key,
                "columns": cols_key,
                "roomtype": type_key
            }

            required_fields = ["roomcode", "block", "floor", "rows", "columns"]
            missing_cols = [f for f in required_fields if not field_map[f]]

            if missing_cols:
                messages.error(request, f"CSV missing required columns: {', '.join(missing_cols)}")
                return redirect("masters:rooms")

            mismatches = []
            valid_rows = []

            for i, row in enumerate(reader, start=2):
                code = (row.get(field_map["roomcode"]) or "").strip()
                block = (row.get(field_map["block"]) or "").strip()
                floor = (row.get(field_map["floor"]) or "").strip()
                r_val = (row.get(field_map["rows"]) or "").strip()
                c_val = (row.get(field_map["columns"]) or "").strip()
                type_val = (row.get(field_map.get("roomtype", "")) or "").strip()

                if not all([code, block, floor, r_val, c_val]):
                    error_groups["Missing required room data"].append(i)
                    continue

                try:
                    rows_int = int(r_val)
                    cols_int = int(c_val)
                    valid_rows.append({
                        "row_num": i, "code": code, "block": block, 
                        "floor": floor, "rows": rows_int, "columns": cols_int,
                        "room_type": type_val
                    })
                except ValueError:
                    error_groups["Rows and Columns must be integers"].append(i)

            if not valid_rows:
                if error_groups:
                    for msg, rows in error_groups.items():
                        messages.warning(request, f"Rows {', '.join(map(str, sorted(rows)))}: {msg}")
                return redirect("masters:rooms")

            # Bulk fetch
            codes_set = {r["code"] for r in valid_rows}
            existing_map = {r.room_code.lower(): r for r in Room.objects.filter(room_code__in=codes_set)}            
            duplicate_rooms = []
            new_rooms = []
            for data in valid_rows:
                existing = existing_map.get(data["code"].lower())
                if existing:
                    diffs = []
                    if existing.rows != data["rows"]: diffs.append(f"Rows: {existing.rows} vs {data['rows']}")
                    if existing.columns != data["columns"]: diffs.append(f"Columns: {existing.columns} vs {data['columns']}")
                    if (existing.floor or "") != data["floor"]: diffs.append(f"Floor: {existing.floor} vs {data['floor']}")
                    if (existing.block or "") != data["block"]: diffs.append(f"Block: {existing.block} vs {data['block']}")
                    if (existing.room_type or "") != data["room_type"]: diffs.append(f"Type: {existing.room_type} vs {data['room_type']}")

                    if diffs:
                        mismatches.append({"room_code": data["code"], "diffs": diffs})
                    else:
                        duplicate_rooms.append(data["code"])
                else:
                    new_rooms.append(Room(
                        room_code=data["code"], block=data["block"], floor=data["floor"],
                        rows=data["rows"], columns=data["columns"],
                        room_type=data["room_type"],
                        capacity=data["rows"] * data["columns"]
                    ))

            if new_rooms:
                with transaction.atomic():
                    Room.objects.bulk_create(new_rooms, batch_size=1000)
                messages.success(request, f"Successfully added {len(new_rooms)} new room(s).")

            if duplicate_rooms:
                messages.warning(request, f"Room data already exist / duplicate data found:<br><br>{', '.join(duplicate_rooms)}")

            if error_groups:
                for msg, rows in error_groups.items():
                    messages.error(request, f"{msg}: Affected Rows {', '.join(map(str, sorted(rows)))}")

            if mismatches:
                request.session["room_mismatches"] = mismatches
                return redirect("masters:room_update_conflicts")

        except Exception as e:
            messages.error(request, f"Error processing CSV: {e}")
    else:
        messages.error(request, "Please select a valid CSV file to upload.")
    return redirect("masters:rooms")


@login_required
def room_update_conflicts(request):
    mismatches = request.session.get('room_mismatches', [])
    if request.method == 'POST':
        selected_ids = request.POST.getlist('update_room')
        updated = []
        from .models import Room

        if not mismatches:
            messages.error(request, "No room conflicts found to update.")
            return redirect('masters:room_update_conflicts')

        if not selected_ids:
            messages.warning(request, "No rooms selected for update.")
            return redirect('masters:room_update_conflicts')

        for mismatch in mismatches:
            room_code = mismatch['room_code']
            if room_code in selected_ids:
                room = Room.objects.get(room_code=room_code)
                for field, old, new in mismatch['diffs']:
                    if field == 'Rows':
                        room.rows = int(new)
                    elif field == 'Columns':
                        room.columns = int(new)
                    elif field == 'Floor':
                        room.floor = new
                    elif field == 'Block':
                        room.block = new
                    elif field == 'Room Type':
                        room.room_type = new
                    # Capacity is auto-computed; do not set directly
                room.save()
                updated.append(room_code)
        if updated:
            for rc in updated:
                messages.success(request, f"{rc} - details updated successfully")
            if 'room_mismatches' in request.session:
                del request.session['room_mismatches']
            return redirect('masters:rooms')
        else:
            messages.info(request, "No selected rooms required updating.")
            return redirect('masters:room_update_conflicts')
    return render(request, "masters/room_update_conflicts.html", {"mismatches": mismatches})