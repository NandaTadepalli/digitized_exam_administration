from django.urls import path
from . import views, ajax

app_name = "operations"

urlpatterns = [
    path("attendence/", views.attendence, name="attendence"),
    path("exams/", views.exams, name="exams"),
    path("room_alloc_view/", views.room_alloc_view, name="room_alloc_view"),
    path("roomalloc/", views.roomalloc, name="roomalloc"),
    path("roomalloc/content/", views.roomalloc_content, name="roomalloc_content"),
    path("report/", views.report, name="report"),
    path("exam-scheduling/<int:slot_id>/", views.exam_scheduling, name="schedule_exam"),
    path("exam_rooms_alloc/", views.exam_rooms_alloc, name="exam_rooms_alloc"),
    path("exam_faculty_alloc/", views.exam_faculty_alloc, name="exam_faculty_alloc"),
    path("ajax/exam-scheduling/groups/", ajax.ajax_exam_scheduling_groups, name="ajax_exam_scheduling_groups"),
    path("ajax/exam-scheduling/filters/", ajax.ajax_exam_filters, name="ajax_exam_filters"),
    path("ajax_exam_slots/", ajax.ajax_exam_slots, name="ajax_exam_slots"),
    path("examination/", views.examination, name="examination"),
    path("ajax/examinations/", views.ajax_examinations, name="ajax_examinations"),
    path("ajax/delete-examination/", ajax.ajax_delete_examination, name="ajax_delete_examination"),
    path("ajax/edit-examination/", ajax.ajax_edit_examination, name="ajax_edit_examination"),
    path("ajax/slot-courses/", ajax.ajax_slot_courses, name="ajax_slot_courses"),
    path("ajax/slot-rooms/", ajax.ajax_slot_rooms, name="ajax_slot_rooms"),
    path("ajax/slot-faculty/", ajax.ajax_slot_faculty, name="ajax_slot_faculty"),
    path("ajax/generate-seating-plan/", views.ajax_generate_seating_plan, name="ajax_generate_seating_plan"),
    path("ajax/seating-plan/", views.ajax_seating_plan, name="ajax_seating_plan"),
    path("seatingplan/", views.seatingplan, name="seatingplan"),
]
