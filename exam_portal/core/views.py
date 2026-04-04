from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
import csv
from django.core.files.storage import default_storage
from masters.models import Department, Program
from django.contrib.auth import get_user_model
import re
from django.contrib.auth.hashers import make_password
from django.db import transaction
from operations.models import StudentExamMap, Exam, ExamSlot, Room

@login_required(login_url='/accounts/login/')
@require_GET
def users_modal(request):
    return render(request, "core/users_modal.html")

@login_required(login_url='/accounts/login/')
@require_GET
def departments_modal(request):
    return render(request, "core/departments_modal.html")

@login_required(login_url='/accounts/login/')
@require_GET
def programs_modal(request):
    return render(request, "core/programs_modal.html")

@login_required(login_url='/accounts/login/')
@require_GET
def batches_modal(request):
    return render(request, "core/batch_modal.html")

@login_required(login_url='/accounts/login/')
def program_conflict(request):
    context = request.session.get('program_conflicts')
    if not context:
        messages.error(request, "No program conflict data to display.")
        return redirect("core:settings")
    if request.method == "POST":
        selected = request.POST.getlist('update_program')
        updated = []
        if not selected:
            messages.error(request, "No programs selected. Please select at least one program to update.")
            return render(request, "core/program_conflict.html", context)
        for row, db_row in context['mismatches']:
            program_code = row[0]
            program_name = row[1]
            if program_code in selected:
                Program.objects.filter(program_code=program_code).update(program_name=program_name)
                updated.append(program_code)
        del request.session['program_conflicts']
        if updated:
            messages.success(request, f"Successfully updated {len(updated)} program(s): {', '.join(updated)}.")
        else:
            messages.info(request, "No programs were updated.")
        return redirect("core:settings")
    return render(request, "core/program_conflict.html", {**context, 'user': request.user})

@login_required(login_url='/accounts/login/')
def user_conflict(request):
    context = request.session.get('user_conflicts')
    if not context:
        messages.error(request, "No user conflict data to display.")
        return redirect("core:settings")
    if request.method == "POST":
        selected = request.POST.getlist('update_user')
        updated = []
        if not selected:
            messages.error(request, "No users selected. Please select at least one user to update.")
            return render(request, "core/user_conflict.html", context)
        User = get_user_model()
        for username, mismatches, new_data in context['mismatches']:
            # new_data is a dict with keys: username, first_name, last_name, email, role
            if username in selected:
                user = User.objects.filter(username=username).first()
                if user:
                    user.email = new_data.get('email', user.email)
                    user.first_name = new_data.get('first_name', user.first_name)
                    user.last_name = new_data.get('last_name', user.last_name)
                    if hasattr(user, "role"):
                        user.role = new_data.get('role', getattr(user, 'role', ''))
                    user.save()
                    updated.append(username)
        del request.session['user_conflicts']
        if updated:
            messages.success(request, f"Successfully updated {len(updated)} user(s): {', '.join(updated)}.")
        else:
            messages.info(request, "No users were updated.")
        return redirect("core:settings")
    return render(request, "core/user_conflict.html", {**context, 'user': request.user})
from django.utils.safestring import mark_safe
@login_required(login_url='/accounts/login/')
def dept_conflict(request):
    context = request.session.get('dept_conflicts')
    if not context:
        messages.error(request, "No department conflict data to display.")
        return redirect("core:settings")
    if request.method == "POST":
        selected = request.POST.getlist('update_dept')
        updated = []
        if not selected:
            messages.error(request, "No departments selected. Please select at least one department to update.")
            return render(request, "core/dept_conflict.html", context)
        for row, db_row in context['mismatches']:
            dept_code = row[0]
            dept_name = row[1]
            if dept_code in selected:
                Department.objects.filter(dept_code=dept_code).update(dept_name=dept_name)
                updated.append(dept_code)
        del request.session['dept_conflicts']
        if updated:
            messages.success(request, f"Successfully updated {len(updated)} department(s): {', '.join(updated)}.")
        else:
            messages.info(request, "No departments were updated.")
        return redirect("core:settings")
    return render(request, "core/dept_conflict.html", {**context, 'user': request.user})

@login_required(login_url='/accounts/login/')
def dashboard(request):
    User = get_user_model()
    admin_users = User.objects.filter(role='admin').count()
    faculty_count = User.objects.filter(role='faculty').count()
    student_count = User.objects.filter(role='student').count()
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    return render(request, "core/dashboard.html", {
        "admin_users": admin_users,
        "faculty_count": faculty_count,
        "student_count": student_count,
        "total_users": total_users,
        "active_users": active_users,
        "user": request.user,
    })

@login_required(login_url='/accounts/login/')
def notifications(request):
    return render(request, "core/notifications.html", {'user': request.user})

@login_required(login_url='/accounts/login/')
def settings_view(request):
    return render(request, "core/settings.html", {'user': request.user})

@login_required(login_url='/accounts/login/')
def upload_departments(request):
    if request.method == "POST" and request.FILES.get("departments_file"):
        file = request.FILES["departments_file"]
        file_path = default_storage.save("tmp/departments.csv", file)
        error_found = False
        new_count = 0
        exact_duplicate_count = 0
        mismatch_rows = []
        total_rows = 0
        dept_code_to_name = {}
        csv_rows = []
        required_headers = None  # will be set based on header
        try:
            with default_storage.open(file_path, mode="rb") as f:
                text = f.read().decode("utf-8-sig")
                reader = csv.reader(text.splitlines())
                header = next(reader, None)
                valid_headers = [
                    ["dept_code", "dept_name"],
                    ["department_code", "department_name"],
                ]
                header_lower = [h.strip().lower() for h in header] if header else []
                if header_lower == valid_headers[0]:
                    code_idx, name_idx = 0, 1
                    required_headers = valid_headers[0]
                elif header_lower == valid_headers[1]:
                    code_idx, name_idx = 0, 1
                    required_headers = valid_headers[1]
                else:
                    messages.error(
                        request,
                        f"CSV header error: Expected headers {valid_headers[0]} or {valid_headers[1]}.",
                    )
                    error_found = True
                    code_idx = name_idx = None
                if not error_found:
                    dept_code_field = Department._meta.get_field("dept_code")
                    dept_name_field = Department._meta.get_field("dept_name")
                    for row in reader:
                        total_rows += 1
                        if len(row) <= max(code_idx, name_idx):
                            messages.error(
                                request,
                                f"CSV format error: Each row must have {required_headers[0]} and {required_headers[1]}.",
                            )
                            continue
                        dept_code = row[code_idx].strip()
                        dept_name = row[name_idx].strip()
                        if not dept_code or not dept_name:
                            messages.error(
                                request,
                                f"CSV format error: {required_headers[0]} and {required_headers[1]} cannot be empty.",
                            )
                            continue
                        if len(dept_code) > dept_code_field.max_length:
                            messages.error(
                                request,
                                f"CSV format error: {required_headers[0]} '{dept_code}' is too long (max {dept_code_field.max_length}).",
                            )
                            continue
                        if len(dept_name) > dept_name_field.max_length:
                            messages.error(
                                request,
                                f"CSV format error: {required_headers[1]} '{dept_name}' is too long (max {dept_name_field.max_length}).",
                            )
                            continue
                        dept_code_to_name[dept_code] = dept_name
                        csv_rows.append((dept_code, dept_name, row))
            if error_found:
                return redirect("core:settings")
            # Bulk fetch all existing departments in one query
            existing_depts = Department.objects.filter(
                dept_code__in=dept_code_to_name.keys()
            )
            existing_map = {d.dept_code: d.dept_name for d in existing_depts}
            to_create = []
            with transaction.atomic():
                for dept_code, dept_name, orig_row in csv_rows:
                    if dept_code in existing_map:
                        if existing_map[dept_code] == dept_name:
                            exact_duplicate_count += 1
                        else:
                            # orig_row = original CSV row, second list = [dept_code, existing_name]
                            mismatch_rows.append(
                                (orig_row, [dept_code, existing_map[dept_code]])
                            )
                    else:
                        to_create.append(
                            Department(dept_code=dept_code, dept_name=dept_name)
                        )
                        new_count += 1
                if to_create:
                    Department.objects.bulk_create(to_create, batch_size=1000)
        finally:
            # Always remove temp file
            default_storage.delete(file_path)
        if error_found:
            return redirect("core:settings")
        if mismatch_rows:
            if new_count > 0:
                messages.success(
                    request,
                    f"{new_count}/{total_rows} new departments added successfully before conflict.",
                )
            if exact_duplicate_count > 0:
                messages.info(
                    request,
                    f"{exact_duplicate_count}/{total_rows} departments already exist and match exactly.",
                )

            request.session["dept_conflicts"] = {
                "headers": required_headers,
                "mismatches": mismatch_rows,
            }
            return redirect("core:dept_conflict")

        if new_count == 0 and exact_duplicate_count == total_rows:
            messages.info(
                request,
                "No new data found. All the data uploaded already exists and matches exactly.",
            )
        elif new_count > 0 and exact_duplicate_count > 0:
            messages.success(
                request,
                f"{new_count}/{total_rows} new departments added successfully.",
            )
            messages.info(
                request,
                f"{exact_duplicate_count}/{total_rows} departments already exist and match exactly.",
            )
        elif new_count > 0:
            messages.success(
                request, f"All {new_count} departments added successfully."
            )
        elif exact_duplicate_count > 0:
            messages.info(
                request,
                f"All {exact_duplicate_count} departments already exist and match exactly.",
            )
        return redirect("core:settings")
    messages.error(request, "No file uploaded or invalid CSV format.")
    return redirect("core:settings")

@login_required(login_url="/accounts/login/")
def upload_programs(request):
    if request.method == "POST" and request.FILES.get("programs_file"):
        file = request.FILES["programs_file"]
        file_path = default_storage.save("tmp/programs.csv", file)
        error_found = False
        new_count = 0
        exact_duplicate_count = 0
        mismatch_rows = []
        total_rows = 0
        program_code_to_name = {}
        csv_rows = []
        required_headers = ["program_code", "program_name"]
        try:
            with default_storage.open(file_path, mode="rb") as f:
                text = f.read().decode("utf-8-sig")
                reader = csv.reader(text.splitlines())
                header = next(reader, None)
                if not header or [h.strip().lower() for h in header] != required_headers:
                    messages.error(
                        request,
                        f"CSV header error: Expected headers {required_headers}.",
                    )
                    error_found = True
                else:
                    program_code_field = Program._meta.get_field("program_code")
                    program_name_field = Program._meta.get_field("program_name")
                    for row in reader:
                        total_rows += 1
                        if len(row) < 2:
                            messages.error(
                                request,
                                "CSV format error: Each row must have program_code and program_name.",
                            )
                            continue
                        program_code = row[0].strip()
                        program_name = row[1].strip()
                        if not program_code or not program_name:
                            messages.error(
                                request,
                                "Program code and program name cannot be empty.",
                            )
                            continue
                        if len(program_code) > program_code_field.max_length:
                            messages.error(
                                request,
                                f"Program code '{program_code}' is too long (max {program_code_field.max_length}).",
                            )
                            continue
                        if len(program_name) > program_name_field.max_length:
                            messages.error(
                                request,
                                f"Program name '{program_name}' is too long (max {program_name_field.max_length}).",
                            )
                            continue
                        program_code_to_name[program_code] = program_name
                        csv_rows.append((program_code, program_name, row))
            if error_found:
                return redirect("core:settings")
            existing_programs = Program.objects.filter(
                program_code__in=program_code_to_name.keys()
            )
            existing_map = {p.program_code: p.program_name for p in existing_programs}
            to_create = []
            with transaction.atomic():
                for program_code, program_name, orig_row in csv_rows:
                    if program_code in existing_map:
                        if existing_map[program_code] == program_name:
                            exact_duplicate_count += 1
                        else:
                            # Keep your structure: ((program_code, program_name), [program_code, existing_name])
                            mismatch_rows.append(
                                (
                                    (program_code, program_name),
                                    [program_code, existing_map[program_code]],
                                )
                            )
                    else:
                        to_create.append(
                            Program(
                                program_code=program_code, program_name=program_name
                            )
                        )
                        new_count += 1
                if to_create:
                    Program.objects.bulk_create(to_create, batch_size=1000)
        finally:
            default_storage.delete(file_path)
        if error_found:
            return redirect("core:settings")
        if mismatch_rows:
            if new_count > 0:
                messages.success(
                    request,
                    f"{new_count}/{total_rows} new programs added successfully before conflict.",
                )
            if exact_duplicate_count > 0:
                messages.info(
                    request,
                    f"{exact_duplicate_count}/{total_rows} programs already exist and match exactly.",
                )
            request.session["program_conflicts"] = {
                "headers": required_headers,
                "mismatches": mismatch_rows,
            }
            return redirect("core:program_conflict")
        if new_count == 0 and exact_duplicate_count == total_rows:
            messages.info(
                request,
                "No new data found. All the data uploaded already exists and matches exactly.",
            )
        elif new_count > 0 and exact_duplicate_count > 0:
            messages.success(
                request,
                f"{new_count}/{total_rows} new programs added successfully.",
            )
            messages.info(
                request,
                f"{exact_duplicate_count}/{total_rows} programs already exist and match exactly.",
            )
        elif new_count > 0:
            messages.success(
                request, f"All {new_count} programs added successfully."
            )
        elif exact_duplicate_count > 0:
            messages.info(
                request,
                f"All {exact_duplicate_count} programs already exist and match exactly.",
            )
        return redirect("core:settings")
    messages.error(request, "No file uploaded or invalid CSV format.")
    return redirect("core:settings")

@login_required(login_url='/accounts/login/')
def upload_users(request):
    if request.method == "POST" and request.FILES.get("users_file"):
        file = request.FILES["users_file"]
        file_path = default_storage.save("tmp/users.csv", file)

        error_found = False
        new_count = 0
        exact_duplicate_count = 0
        mismatch_rows = []
        total_rows = 0
        user_map = {}
        csv_rows = []

        email_regex = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
        required_headers = ["username", "first_name", "last_name", "email", "role"]
        allowed_roles = {"student", "faculty", "admin", "hod", "dept_exam_controller"}

        try:
            # --- Read & validate CSV ---
            with default_storage.open(file_path, mode="rb") as f:
                text = f.read().decode("utf-8-sig")
                reader = csv.reader(text.splitlines())
                header = next(reader, None)

                if not header or [h.strip().lower() for h in header] != required_headers:
                    messages.error(
                        request,
                        f"CSV header error: Expected headers {required_headers}.",
                    )
                    error_found = True
                else:
                    for idx, row in enumerate(reader, start=2):
                        total_rows += 1
                        if len(row) < 5:
                            messages.error(
                                request,
                                "CSV format error: Each row must have username, "
                                f"first_name, last_name, email, role. (Row {idx})",
                            )
                            continue

                        username = row[0].strip()
                        first_name = row[1].strip()
                        last_name = row[2].strip()
                        email = row[3].strip()
                        role = row[4].strip().lower()

                        if not username or not email:
                            messages.error(
                                request,
                                "Username and email cannot be empty. "
                                f"(Row {idx}, username: {username})",
                            )
                            continue

                        if not email_regex.match(email):
                            messages.error(
                                request,
                                f"Row {idx}: username '{username}' has invalid "
                                f"email id '{email}'",
                            )
                            continue

                        if role not in allowed_roles:
                            messages.error(
                                request,
                                "Invalid role: {role}. Allowed roles: "
                                f"{', '.join(allowed_roles)} "
                                f"(Row {idx}, username: {username})",
                            )
                            continue

                        # For later: check if user already exists, and compare rows
                        user_map[username] = (email, role, row)
                        csv_rows.append(
                            (username, email, role, row, first_name, last_name)
                        )

            User = get_user_model()

            # --- If header was wrong, stop early ---
            if error_found:
                default_storage.delete(file_path)
                return redirect("core:settings")

            # --- Load existing users in one query ---
            existing_users = User.objects.filter(username__in=user_map.keys())
            existing_map = {
                u.username: (u.email, getattr(u, "role", ""), u.first_name, u.last_name)
                for u in existing_users
            }

            def is_valid_mismatch_tuple(t):
                return isinstance(t, tuple) and len(t) == 3

            # --- Prepare bulk list for new users ---
            users_to_create = []

            # Precompute student default password hash ONCE
            student_default_pw_hash = make_password("Test@123")

            with transaction.atomic():
                for (
                    username,
                    email,
                    role,
                    orig_row,
                    first_name,
                    last_name,
                ) in csv_rows:
                    if username in existing_map:
                        # Compare DB row vs CSV row
                        db_email, db_role, db_first_name, db_last_name = existing_map[
                            username
                        ]
                        db_row = [
                            username,
                            db_first_name,
                            db_last_name,
                            db_email,
                            db_role,
                        ]
                        csv_row = [username, first_name, last_name, email, role]

                        if db_row == csv_row:
                            exact_duplicate_count += 1
                        else:
                            mismatches = []
                            fields = [
                                "username",
                                "first_name",
                                "last_name",
                                "email",
                                "role",
                            ]
                            for i, field in enumerate(fields):
                                if db_row[i] != csv_row[i]:
                                    tup = (field, db_row[i], csv_row[i])
                                    if is_valid_mismatch_tuple(tup):
                                        mismatches.append(tup)

                            mismatches = [
                                t for t in mismatches if is_valid_mismatch_tuple(t)
                            ]
                            if mismatches:
                                new_data = {
                                    "username": username,
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "email": email,
                                    "role": role,
                                }
                                mismatch_rows.append((username, mismatches, new_data))
                    else:
                        # NEW USER → don't save one-by-one, collect for bulk_create
                        if role == "student":
                            password_hash = student_default_pw_hash
                        else:
                            password_hash = make_password(f"{username}@{username}")

                        user = User(
                            username=username,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            is_superuser=(role == "admin"),
                            is_staff=role
                            in {
                                "admin",
                                "faculty",
                                "hod",
                                "dept_exam_controller",
                            },
                            is_active=True,
                            role=role,
                            password=password_hash,
                        )
                        users_to_create.append(user)
                        new_count += 1

                # Actually insert all new users in bulk
                if users_to_create:
                    User.objects.bulk_create(users_to_create, batch_size=1000)

        finally:
            # Always clean up the temp file
            default_storage.delete(file_path)

        # --- After DB work, handle conflict flow / messages ---

        if mismatch_rows:
            filtered_mismatch_rows = []
            for entry in mismatch_rows:
                if len(entry) == 3:
                    username, mismatches, new_data = entry
                else:
                    username, mismatches = entry
                    new_data = None
                filtered = [t for t in mismatches if is_valid_mismatch_tuple(t)]
                if filtered:
                    if new_data is not None:
                        filtered_mismatch_rows.append((username, filtered, new_data))
                    else:
                        filtered_mismatch_rows.append((username, filtered))

            if new_count > 0:
                messages.success(
                    request,
                    f"{new_count}/{total_rows} new users added successfully before conflict.",
                )
            if exact_duplicate_count > 0:
                messages.info(
                    request,
                    f"{exact_duplicate_count}/{total_rows} users already exist and match exactly.",
                )

            request.session["user_conflicts"] = {
                "headers": required_headers,
                "mismatches": filtered_mismatch_rows,
            }
            return redirect("core:user_conflict")

        # No conflicts → just show summary messages
        if new_count == 0 and exact_duplicate_count == total_rows:
            messages.info(
                request,
                "No new data found. All the data uploaded already exists and matches exactly.",
            )
        elif new_count > 0 and exact_duplicate_count > 0:
            messages.success(
                request, f"{new_count}/{total_rows} new users added successfully."
            )
            messages.info(
                request,
                f"{exact_duplicate_count}/{total_rows} users already exist and match exactly.",
            )
        elif new_count > 0:
            messages.success(request, f"All {new_count} users added successfully.")
        elif exact_duplicate_count > 0:
            messages.info(
                request,
                f"All {exact_duplicate_count} users already exist and match exactly.",
            )

        return redirect("core:settings")

    messages.error(request, "No file uploaded or invalid CSV format.")
    return redirect("core:settings")

@login_required(login_url='/accounts/login/')
def student_dashboard(request):
    return render(request, "core/student_dashboard.html", {"user": request.user})

@login_required(login_url='/accounts/login/')
def student_exams(request):
    user = request.user
    student_id = getattr(user, 'student_profile', None)
    if not student_id:
        return render(request, "operations/student_exam.html", {"exams": []})
    student_id = user.student_profile.student_id
    exam_maps = StudentExamMap.objects.filter(student__student_id=student_id).select_related('exam', 'exam__exam_slot', 'exam__exam_slot__examination', 'exam__course')
    exams = []
    for smap in exam_maps:
        exam = smap.exam
        slot = exam.exam_slot if exam else None
        examination = slot.examination if slot and slot.examination else None
        # Only show exams if the parent examination is published
        if not examination or not getattr(examination, 'published', False):
            continue
        exam_name = examination.exam_name if examination else ''
        exam_date = examination.start_date if examination else ''
        start_time = slot.start_time if slot else ''
        end_time = slot.end_time if slot else ''
        duration = ''
        if slot and slot.start_time and slot.end_time:
            from datetime import datetime, timedelta
            try:
                st = slot.start_time
                et = slot.end_time
                if isinstance(st, str):
                    st = datetime.strptime(st, '%H:%M:%S').time()
                if isinstance(et, str):
                    et = datetime.strptime(et, '%H:%M:%S').time()
                duration_td = datetime.combine(exam_date, et) - datetime.combine(exam_date, st)
                total_seconds = duration_td.total_seconds()
                hours = int(total_seconds // 3600)
                mins = int((total_seconds % 3600) // 60)
                duration = f"{hours} hrs {mins} mins"
            except Exception:
                duration = ''
        room_alloc = Room.objects.filter(seatingplan__student_exam=smap).first()
        exams.append({
            "exam_name": exam_name,
            "exam_date": exam_date,
            "exam_type": slot.exam_type if slot else '',
            "exam_slot": slot.slot_code if slot else '',
            "student_university_id": student_id,
            "course_code": exam.course.course_code if exam and exam.course else '',
            "course_name": exam.course.course_name if exam and exam.course else '',
            "room_no": room_alloc.room_code if room_alloc else '',
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
        })
    return render(request, "operations/student_exam.html", {"exams": exams})
