from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('attendance/', views.attendance_view, name='attendance'),
    path('attendance/mark/<int:student_id>/', views.mark_attendance, name='mark_attendance'),
    path('attendance/mark-all/<int:group_id>/', views.mark_all_present, name='mark_all_present'),

    # Ученики
    path('students/', views.students_view, name='students'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),

    # Учителя и группы (только директор)
    path('teachers/', views.teachers_view, name='teachers'),
    path('teachers/add/', views.add_teacher, name='add_teacher'),
    path('groups/add/', views.add_group, name='add_group'),

    # Отчёт и Excel
    path('report/', views.report_view, name='report'),
    path('report/lessons/<int:group_id>/', views.update_month_lessons, name='update_month_lessons'),
    path('report/excel/', views.export_report_excel, name='export_report_excel'),
]