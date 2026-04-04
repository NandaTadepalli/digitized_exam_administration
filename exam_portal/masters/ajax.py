from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import models
from django.utils.html import escape
from .models import Student, Faculty, Room, Course

def ajax(request):
    data_type = request.GET.get('type')
    page_number = request.GET.get('page')
    search = request.GET.get('search', '').strip().lower()
    # --- Student ID Autocomplete AJAX ---
    if data_type == 'student-id-autocomplete':
        query = request.GET.get('q', '').strip()
        students = Student.objects.all()
        if query:
            students = students.filter(student_id__icontains=query) | students.filter(std_name__icontains=query)
        results = [
            {'id': s.student_id, 'name': getattr(s, 'std_name', getattr(s, 'user', None) and s.user.get_full_name() or '')}
            for s in students[:20]
        ]
        return JsonResponse({'results': results})
    department = request.GET.get('department', '').strip()
    # For rooms
    block = request.GET.get('block', '').strip()
    capacity_min = request.GET.get('capacity_min', '').strip()
    capacity_max = request.GET.get('capacity_max', '').strip()
    # For courses
    # No extra filters for now

    # Student Course Registration AJAX
    if data_type == 'coursereg':
        from operations.models import StudentCourse
        course_code = request.GET.get('course', '').strip()
        academic_year = request.GET.get('year', '').strip()
        semester = request.GET.get('semester', '').strip()
        student_id = request.GET.get('student_id', '').strip()
        search = request.GET.get('search', '').strip().lower()
        queryset = StudentCourse.objects.select_related('student', 'course').order_by('id')
        if student_id:
            queryset = queryset.filter(student__student_id__iexact=student_id)
        elif search:
            queryset = queryset.filter(
                models.Q(student__student_id__icontains=search) |
                models.Q(student__std_name__icontains=search) |
                models.Q(course__course_code__icontains=search) |
                models.Q(course__course_name__icontains=search)
            )
        if course_code:
            queryset = queryset.filter(course__course_code=course_code)
        if academic_year:
            queryset = queryset.filter(academic_year=academic_year)
        if semester:
            queryset = queryset.filter(semester=semester)
        paginator = Paginator(queryset, 25)  # Show 25 rows per page
        page_obj = paginator.get_page(page_number)
        rows = []
        for idx, reg in enumerate(page_obj, start=page_obj.start_index()):
            if hasattr(request.user, 'role') and request.user.role.lower() == 'admin':
                rows.append(f"""
                <tr>
                    <td>{idx}</td>
                    <td>{escape(reg.student.student_id)}</td>
                    <td>{escape(getattr(reg.student, 'std_name', getattr(reg.student, 'user', None) and reg.student.user.get_full_name() or ''))}</td>
                    <td>{escape(reg.course.course_code)}</td>
                    <td>{escape(reg.course.course_name)}</td>
                    <td>{escape(reg.academic_year)}</td>
                    <td>{escape(reg.semester)}</td>
                    <td>
                        <button class='edit-coursereg-btn' data-id='{reg.id}'>Edit</button>
                        <button class='delete-coursereg-btn' data-id='{reg.id}'>Delete</button>
                    </td>
                </tr>
                """)
            else:
                rows.append(f"""
                <tr>
                    <td>{idx}</td>
                    <td>{escape(reg.student.student_id)}</td>
                    <td>{escape(getattr(reg.student, 'std_name', getattr(reg.student, 'user', None) and reg.student.user.get_full_name() or ''))}</td>
                    <td>{escape(reg.course.course_code)}</td>
                    <td>{escape(reg.course.course_name)}</td>
                    <td>{escape(reg.academic_year)}</td>
                    <td>{escape(reg.semester)}</td>
                </tr>
                """)
        if not rows:
            if hasattr(request.user, 'role') and request.user.role.lower() == 'admin':
                rows.append("<tr><td colspan='8'>No course registrations found.</td></tr>")
            else:
                rows.append("<tr><td colspan='7'>No course registrations found.</td></tr>")
        table_html = "".join(rows)
        pag = page_obj
        pagination_html = render_pagination(pag)
        return JsonResponse({'table_html': table_html, 'pagination_html': pagination_html})

    if data_type == 'student':
        queryset = Student.objects.select_related('user', 'dept', 'batch').all().order_by('student_id')
        batch = request.GET.get('batch', '').strip()
        if search:
            queryset = queryset.filter(
                models.Q(student_id__icontains=search) |
                models.Q(user__first_name__icontains=search) |
                models.Q(user__last_name__icontains=search)
            )
        if department and department != 'all':
            queryset = queryset.filter(dept__dept_code=department)
        if batch and batch != 'all':
            queryset = queryset.filter(batch__batch_code=batch)
        paginator = Paginator(queryset, 25)
        page_obj = paginator.get_page(page_number)
        rows = []
        for idx, student in enumerate(page_obj, start=page_obj.start_index()):
            if request.user.role == 'faculty':
                rows.append(f"""
                <tr>
                    <td>{idx}</td>
                    <td><a href='/masters/student/{student.id}/detail/' class='student-action-link'>{escape(student.student_id)}</a></td>
                    <td>{escape(student.user.first_name)} {escape(student.user.last_name)}</td>
                    <td>{escape(student.dept.dept_name)}({escape(student.dept.dept_code)})</td>
                    <td>{escape(student.batch.batch_code) if student.batch else '<span style=\"color:red\">Not set</span>'}</td>
                    <td>{escape(student.email)}</td>
                    <td>{escape(student.status)}</td>
                </tr>
                """)
            else:
                rows.append(f"""
                <tr>
                    <td>{idx}</td>
                    <td><a href='/masters/student/{student.id}/detail/' class='student-action-link'>{escape(student.student_id)}</a></td>
                    <td>{escape(student.user.first_name)} {escape(student.user.last_name)}</td>
                    <td>{escape(student.dept.dept_name)}({escape(student.dept.dept_code)})</td>
                    <td>{escape(student.batch.batch_code) if student.batch else '<span style=\"color:red\">Not set</span>'}</td>
                    <td>{escape(student.email)}</td>
                    <td>{escape(student.status)}</td>
                    <td>
                        <a href='/masters/student/{student.id}/detail/' class='student-action-link'><img src='https://img.icons8.com/?size=100&id=fdX9cvS8MtuS&format=png&color=000000' alt='View' title='View details'></a>
                        <a href='/masters/student/{student.id}/edit/' class='student-action-link'><img src='https://img.icons8.com/?size=100&id=kzmsQM0bM3Bl&format=png&color=000000' alt='Edit' title='Edit Details'></a>
                        <button class='student-delete-btn' data-student-id='{student.id}' data-student-name='{escape(student.user.first_name)} {escape(student.user.last_name)}' data-student-reg='{escape(student.student_id)}' data-student-email='{escape(student.email)}' data-student-dept='{escape(student.dept.dept_name)}' data-student-status='{escape(student.status)}' style='background:none;border:none;padding:0;cursor:pointer'><img src='https://img.icons8.com/?size=100&id=99971&format=png&color=000000' alt='Delete' title='Delete Student'></button>
                    </td>
                </tr>
                """)
        if not rows:
            if request.user.role == 'faculty':
                rows.append("<tr><td colspan='7'>No students found.</td></tr>")
            else:
                rows.append("<tr><td colspan='8'>No students found.</td></tr>")
        table_html = "".join(rows)
        pag = page_obj
        pagination_html = render_pagination(pag)
        return JsonResponse({'table_html': table_html, 'pagination_html': pagination_html})

    elif data_type == 'faculty':
        queryset = Faculty.objects.select_related('user', 'dept').all().order_by('faculty_id')
        if search:
            queryset = queryset.filter(
                models.Q(faculty_id__icontains=search) |
                models.Q(user__first_name__icontains=search) |
                models.Q(user__last_name__icontains=search)
            )
        if department and department != 'all':
            queryset = queryset.filter(dept__dept_code=department)
        paginator = Paginator(queryset, 25)
        page_obj = paginator.get_page(page_number)
        rows = []
        for idx, faculty in enumerate(page_obj, start=page_obj.start_index()):
            rows.append(f"""
            <tr>
                <td>{idx}</td>
                <td><a href='/masters/faculty/{faculty.id}/detail/' class='faculty-action-link'>{escape(faculty.faculty_id)}</a></td>
                <td>{escape(faculty.user.first_name)} {escape(faculty.user.last_name)}</td>
                <td>{escape(faculty.dept.dept_name)} ({escape(faculty.dept.dept_code)})</td>
                <td>{escape(faculty.phone_number)}</td>
                <td>{escape(faculty.user.email)}</td>
                <td>
                    <a href='/masters/faculty/{faculty.id}/detail/' class='faculty-action-link'><img src='https://img.icons8.com/?size=100&id=fdX9cvS8MtuS&format=png&color=000000' alt='View' title='View details'></a>
                    <a href='/masters/faculty/{faculty.id}/edit/' class='faculty-action-link'><img src='https://img.icons8.com/?size=100&id=kzmsQM0bM3Bl&format=png&color=000000' alt='Edit' title='Edit Details'></a>
                    <button class='faculty-delete-btn' data-faculty-id='{faculty.id}' data-faculty-name='{escape(faculty.user.first_name)} {escape(faculty.user.last_name)}' data-faculty-email='{escape(faculty.user.email)}' data-faculty-dept='{escape(faculty.dept.dept_name)}' data-faculty-phone='{escape(faculty.phone_number)}' data-faculty-designation='{escape(faculty.designation)}' data-faculty-status='{escape(faculty.status)}' style='background:none;border:none;padding:0;cursor:pointer;'><img src='https://img.icons8.com/?size=100&id=99971&format=png&color=000000' alt='Delete' title='Delete Faculty'></button>
                </td>
            </tr>
            """)
        if not rows:
            rows.append("<tr><td colspan='7'>No faculty found.</td></tr>")
        table_html = "".join(rows)
        pag = page_obj
        pagination_html = render_pagination(pag)
        return JsonResponse({'table_html': table_html, 'pagination_html': pagination_html})

    elif data_type == 'room':
        queryset = Room.objects.all().order_by('room_code')
        if search:
            queryset = queryset.filter(
                models.Q(room_code__icontains=search) |
                models.Q(block__icontains=search)
            )
        if block and block.lower() != 'all' and block:
            queryset = queryset.filter(block=block)
        if capacity_min.isdigit():
            queryset = queryset.filter(capacity__gte=int(capacity_min))
        if capacity_max.isdigit():
            queryset = queryset.filter(capacity__lte=int(capacity_max))
        paginator = Paginator(queryset, 25)
        page_obj = paginator.get_page(page_number)
        rows = []
        for idx, room in enumerate(page_obj, start=page_obj.start_index()):
            rows.append(f"""
            <tr>
                <td>{idx}</td>
                <td>{escape(room.room_code)}</td>
                <td>{escape(room.block)}</td>
                <td>{escape(room.capacity)}</td>
                <td>{'Active' if room.is_active else 'Temporarily Unavailable'}</td>
                <td>
                    <a href='/masters/rooms/{room.id}/detail/' class='room-action-link'><img src='https://img.icons8.com/?size=100&id=fdX9cvS8MtuS&format=png&color=000000' alt='View' title='View details'></a>
                    <a href='/masters/rooms/{room.id}/edit/' class='room-action-link'><img src='https://img.icons8.com/?size=100&id=kzmsQM0bM3Bl&format=png&color=000000' alt='Edit' title='Edit Details'></a>
                    <a href='/masters/rooms/{room.id}/delete/' class='room-action-link'><img src='https://img.icons8.com/?size=100&id=99971&format=png&color=000000' alt='Delete' title='Delete Room'></a>
                </td>
            </tr>
            """)
        if not rows:
            rows.append("<tr><td colspan='7'>No rooms found.</td></tr>")
        table_html = "".join(rows)
        pag = page_obj
        pagination_html = render_pagination(pag)
        return JsonResponse({'table_html': table_html, 'pagination_html': pagination_html})

    elif data_type == 'course':
        queryset = Course.objects.all().order_by('course_code')
        if search:
            queryset = queryset.filter(
                models.Q(course_code__icontains=search) |
                models.Q(course_name__icontains=search)
            )
        paginator = Paginator(queryset, 25)
        page_obj = paginator.get_page(page_number)
        rows = []
        for idx, course in enumerate(page_obj, start=page_obj.start_index()):
            rows.append(f"""
            <tr>
                <td>{idx}</td>
                <td>{escape(course.course_code)}</td>
                <td>{escape(course.course_name)}</td>
                <td>{'Active' if course.is_active else 'Inactive'}</td>
                <td>
                    <a href='#' class='course-action-link edit-course-btn' data-id='{course.id}' data-code='{escape(course.course_code)}' data-name='{escape(course.course_name)}' data-active='{course.is_active}'><img src='https://img.icons8.com/?size=100&id=kzmsQM0bM3Bl&format=png&color=000000' alt='Edit' title='Edit Details'></a>
                    <a href='#' class='course-action-link delete-course-btn' data-id='{course.id}'><img src='https://img.icons8.com/?size=100&id=99971&format=png&color=000000' alt='Delete' title='Delete Student'></a>
                </td>
            </tr>
            """)
        if not rows:
            rows.append("<tr><td colspan='5'>No courses found.</td></tr>")
        table_html = "".join(rows)
        pag = page_obj
        pagination_html = render_pagination(pag)
        return JsonResponse({'table_html': table_html, 'pagination_html': pagination_html})

    return JsonResponse({'error': 'Invalid type'}, status=400)

def render_pagination(pag):
    html = "<div class='pagination' style='display: flex; align-items: center; gap: 4px;'>"
    if pag.has_previous():
        html += f"<a href='#' class='page-arrow' data-page='1' style='padding: 2px 8px; font-size: 18px;'>&#171;</a>"
        html += f"<a href='#' class='page-arrow' data-page='{pag.previous_page_number()}' style='padding: 2px 8px; font-size: 18px;'>&#8592;</a>"
    else:
        html += "<span class='page-arrow disabled' style='padding: 2px 8px; color: #bbb; font-size: 18px;'>&#171;</span>"
        html += "<span class='page-arrow disabled' style='padding: 2px 8px; color: #bbb; font-size: 18px;'>&#8592;</span>"
    for i in pag.paginator.page_range:
        if i > pag.number - 5 and i < pag.number + 5:
            if i == pag.number:
                html += f"<span class='page-num current' style='padding: 2px 8px; background: #2563eb; color: #fff; border-radius: 4px; font-weight: bold;'>{i}</span>"
            else:
                html += f"<a href='#' class='page-num' data-page='{i}' style='padding: 2px 8px; color: #2563eb; border-radius: 4px;'>{i}</a>"
    if pag.has_next():
        html += f"<a href='#' class='page-arrow' data-page='{pag.next_page_number()}' style='padding: 2px 8px; font-size: 18px;'>&#8594;</a>"
        html += f"<a href='#' class='page-arrow' data-page='{pag.paginator.num_pages}' style='padding: 2px 8px; font-size: 18px;'>&#187;</a>"
    else:
        html += "<span class='page-arrow disabled' style='padding: 2px 8px; color: #bbb; font-size: 18px;'>&#8594;</span>"
        html += "<span class='page-arrow disabled' style='padding: 2px 8px; color: #bbb; font-size: 18px;'>&#187;</span>"
    html += "</div>"
    return html
