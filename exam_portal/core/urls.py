from django.urls import path
from django.shortcuts import redirect
from . import views
from . import ajax

app_name = "core"

def root_redirect(request):
    return redirect('accounts:login')

urlpatterns = [
    path("", root_redirect, name="root"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("student/exams/", views.student_exams, name="student_exams"),
    path("notifications/", views.notifications, name="notifications"),
    path("settings/", views.settings_view, name="settings"),
    path("settings/upload_departments/", views.upload_departments, name="upload_departments"),
    path("settings/upload_programs/", views.upload_programs, name="upload_programs"),
    path("settings/upload_users/", views.upload_users, name="upload_users"),
    path("settings/dept_conflict/", views.dept_conflict, name="dept_conflict"),
    path("settings/program_conflict/", views.program_conflict, name="program_conflict"),
    path("settings/user_conflict/", views.user_conflict, name="user_conflict"),
    path("settings/users_modal/", views.users_modal, name="users_modal"),
    path("settings/departments_modal/", views.departments_modal, name="departments_modal"),
    path("settings/programs_modal/", views.programs_modal, name="programs_modal"),
    path("settings/batches_modal/", views.batches_modal, name="batches_modal"),
    path("ajax/users/", ajax.users_ajax, name="users_ajax"),
    path("ajax/batches/", ajax.batch_ajax, name="batches_ajax"),
    path("ajax/departments/", ajax.department_ajax, name="departments_ajax"),
    path("ajax/programs/", ajax.program_ajax, name="programs_ajax"),
]
