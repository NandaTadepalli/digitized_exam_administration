from django.urls import path
from . import views
from . import ajax

app_name = "masters"

urlpatterns = [
    # BATCH
    path("batch/upload/", views.batch_upload, name="batch_upload"),
    path("batch/", views.batch_list, name="batch_list"),
    path("faculty/dashboard/", views.faculty_dashboard, name="faculty_dashboard"),

    # Direct invigilation duties route
    path("faculty/invigilation_duties/", views.invigilation_duties, name="invigilation_duties_direct"),

    # STUDENT
    path("student/", views.student, name="student"),
    path("student/content/", views.student_content, name="student_content"),
    path("student/<int:pk>/detail/", views.student_detail, name="student_detail"),
    path("student/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("student/<int:pk>/delete/", views.student_delete, name="student_delete"),
    path("student/upload/", views.student_upload, name="student_upload"),
    path("student/update_conflicts/", views.student_update_conflicts, name="student_update_conflicts"),

    # Central AJAX endpoint for all management pages
    path('ajax/', ajax.ajax, name='ajax'),

    # FACULTY
    path("faculty/", views.faculty, name="faculty"),
    path("faculty/content/", views.faculty_content, name="faculty_content"),
    path("faculty/<int:pk>/detail/", views.faculty_detail, name="faculty_detail"),
    path("faculty/<int:pk>/detail_content/", views.faculty_detail_content, name="faculty_detail_content"),
    path("faculty/<int:pk>/edit/", views.faculty_edit, name="faculty_edit"),
    path("faculty/<int:pk>/delete/", views.faculty_delete, name="faculty_delete"),
    path("faculty/upload/", views.faculty_upload, name="faculty_upload"),
    path("faculty/update_conflicts/", views.faculty_update_conflicts, name="faculty_update_conflicts"),

    # ROOMS
    path("rooms/", views.rooms, name="rooms"),
    path("rooms/upload/", views.room_upload, name="room_upload"),
    path("rooms/content/", views.rooms_content, name="rooms_content"),
    path("rooms/<int:pk>/detail/", views.room_detail, name="room_detail"),
    path("rooms/<int:pk>/detail_content/", views.room_detail_content, name="room_detail_content"),
    path("rooms/<int:pk>/edit/", views.room_edit, name="room_edit"),
    path("rooms/<int:pk>/delete/", views.room_delete, name="room_delete"),
    path("rooms/update_conflicts/", views.room_update_conflicts, name="room_update_conflicts"),

    # COURSES
    path("courses/", views.courses, name="courses"),
    path("courses/<int:pk>/edit/", views.course_edit, name="course_edit"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),
    path("courses/upload/", views.course_upload, name="course_upload"),

    # COURSE REGISTRATION
    path("coursereg/", views.coursereg, name="coursereg"),
    path("coursereg/upload/", views.coursereg_upload, name="coursereg_upload"),
    path("coursereg/conflict/resolve/", views.coursereg_conflict_resolve, name="coursereg_conflict_resolve"),
    path("faculty/invigilation_duties/", views.invigilation_duties, name="invigilation_duties"),

    # FACULTY VIEW SEATING PLAN
    path("faculty/view_seatingplan/", views.facultyview_seatingplan, name="facultyview_seatingplan"),
]
