from django.contrib import admin
from .models import Teacher, Group, Student, Attendance, MonthLessons


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("full_name", "subject", "phone", "user")
    search_fields = ("full_name", "subject", "phone")


class StudentInline(admin.TabularInline):
    """Позволяет добавлять учеников прямо внутри страницы группы."""
    model = Student
    extra = 1


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "teacher", "monthly_fee", "default_lessons", "weekdays_display", "lesson_time")
    list_filter = ("teacher",)
    search_fields = ("name",)
    inlines = [StudentInline]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("full_name", "group", "parent_phone", "is_active", "created_at")
    list_filter = ("group", "is_active")
    search_fields = ("full_name", "parent_phone")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "status", "marked_by")
    list_filter = ("status", "date", "student__group")
    search_fields = ("student__full_name",)
    date_hierarchy = "date"


@admin.register(MonthLessons)
class MonthLessonsAdmin(admin.ModelAdmin):
    list_display = ("group", "month", "lessons")
    list_filter = ("month", "group")