from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Q
# Create your views here.
from datetime import date, datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from .models import MonthLessons
from .excel import build_month_excel

from .models import Attendance, Group, Student, Teacher
from .services import (
    current_month_str,
    group_month_report,
    student_month_stats,
    user_groups,
)




@login_required
def dashboard(request):
    """Главная страница (для директора и учителя)."""
    month = request.GET.get("month") or current_month_str()
    groups = user_groups(request.user)
    students = Student.objects.filter(group__in=groups, is_active=True)

    reports = [group_month_report(g, month) for g in groups]
    total_revenue = sum(r["revenue"] for r in reports)
    teacher_share = sum(r["teacher_share"] for r in reports)
    center_share = sum(r["center_share"] for r in reports)

    # Посещаемость за выбранный месяц
    year, mon = map(int, month.split("-"))
    att_qs = Attendance.objects.filter(
        student__in=students, date__year=year, date__month=mon
    )
    total_marks = att_qs.count()
    present_marks = att_qs.filter(status=Attendance.Status.PRESENT).count()
    att_rate = round(present_marks / total_marks * 100) if total_marks else 0

    # Уроки сегодня
    today = date.today()
    todays_groups = [g for g in groups if g.has_lesson_on(today)]

    context = {
        "page": "dashboard",
        "month": month,
        "today": today,
        "is_admin": request.user.is_superuser or request.user.is_staff,
        "students_count": students.count(),
        "teachers_count": Teacher.objects.count(),
        "groups_count": groups.count(),
        "att_rate": att_rate,
        "total_revenue": total_revenue,
        "teacher_share": teacher_share,
        "center_share": center_share,
        "todays_groups": todays_groups,
        "reports": reports,
    }
    return render(request, "journal/dashboard.html", context)


@login_required
def attendance_view(request):
    """Страница отметки посещаемости."""
    groups = list(user_groups(request.user))
    date_str = request.GET.get("date") or date.today().isoformat()
    try:
        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        selected_date = date.today()
        date_str = selected_date.isoformat()

    month = date_str[:7]

    # Сортируем: сначала группы, у которых в этот день урок по расписанию
    groups.sort(key=lambda g: not g.has_lesson_on(selected_date))

    group_id = request.GET.get("group")
    selected_group = None
    if group_id:
        selected_group = next((g for g in groups if str(g.id) == str(group_id)), None)
    if not selected_group and groups:
        selected_group = groups[0]

    student_rows = []
    counts = {"present": 0, "absent": 0, "excused": 0, "unmarked": 0}

    if selected_group:
        students = selected_group.students.filter(is_active=True)
        att_map = {
            a.student_id: a.status
            for a in Attendance.objects.filter(student__in=students, date=selected_date)
        }
        for s in students:
            st = att_map.get(s.id, "")
            if st in counts:
                counts[st] += 1
            else:
                counts["unmarked"] += 1
            m_stats = student_month_stats(s, month)
            student_rows.append({
                "student": s,
                "status": st,
                "month_present": m_stats["present"],
                "lessons_norm": m_stats["lessons_norm"],
            })

    context = {
        "page": "attendance",
        "groups": groups,
        "selected_group": selected_group,
        "selected_date": selected_date,
        "date_str": date_str,
        "student_rows": student_rows,
        "counts": counts,
    }
    return render(request, "journal/attendance.html", context)


@login_required
@require_POST
def mark_attendance(request, student_id):
    """Отметка одного ученика (Был / Не был / Уважительная)."""
    student = get_object_or_404(Student, id=student_id)
    if student.group not in user_groups(request.user):
        return HttpResponseForbidden("Нет доступа к этой группе")

    date_str = request.POST.get("date") or date.today().isoformat()
    status = request.POST.get("status")

    existing = Attendance.objects.filter(student=student, date=date_str).first()
    # Если нажали на уже выбранную кнопку — снимаем отметку
    if existing and existing.status == status:
        existing.delete()
    elif status in dict(Attendance.Status.choices):
        Attendance.objects.update_or_create(
            student=student,
            date=date_str,
            defaults={"status": status, "marked_by": request.user},
        )

    return redirect(f"/attendance/?group={student.group_id}&date={date_str}")


@login_required
@require_POST
def mark_all_present(request, group_id):
    """Кнопка 'Все пришли'."""
    group = get_object_or_404(Group, id=group_id)
    if group not in user_groups(request.user):
        return HttpResponseForbidden("Нет доступа к этой группе")

    date_str = request.POST.get("date") or date.today().isoformat()
    for s in group.students.filter(is_active=True):
        Attendance.objects.update_or_create(
            student=s,
            date=date_str,
            defaults={"status": Attendance.Status.PRESENT, "marked_by": request.user},
        )
    return redirect(f"/attendance/?group={group.id}&date={date_str}")




@login_required
def students_view(request):
    """Список учеников с поиском, фильтром по группе и % посещаемости."""
    groups = user_groups(request.user)
    group_id = request.GET.get("group", "all")
    q = request.GET.get("q", "").strip()
    month = request.GET.get("month") or current_month_str()

    students = Student.objects.filter(group__in=groups, is_active=True).select_related("group", "group__teacher")
    if group_id != "all":
        students = students.filter(group_id=group_id)
    if q:
        students = students.filter(Q(full_name__icontains=q) | Q(parent_phone__icontains=q))

    rows = []
    for s in students:
        st = student_month_stats(s, month)
        rows.append({"student": s, "stats": st})

    return render(request, "journal/students.html", {
        "page": "students",
        "groups": groups,
        "selected_group": group_id,
        "q": q,
        "month": month,
        "rows": rows,
    })


@login_required
@require_POST
def add_student(request):
    """Добавление нового ученика."""
    group = get_object_or_404(Group, id=request.POST.get("group_id"))
    if group not in user_groups(request.user):
        return HttpResponseForbidden("Нет доступа к этой группе")

    full_name = request.POST.get("full_name", "").strip()
    parent_phone = request.POST.get("parent_phone", "").strip()
    if full_name:
        Student.objects.create(full_name=full_name, parent_phone=parent_phone, group=group)
    return redirect("students")


@login_required
@require_POST
def delete_student(request, student_id):
    """Удаление (скрытие) ученика."""
    student = get_object_or_404(Student, id=student_id)
    if student.group not in user_groups(request.user):
        return HttpResponseForbidden("Нет доступа")
    student.is_active = False
    student.save()
    return redirect("students")


@login_required
def teachers_view(request):
    """Страница учителей и групп (только для директора)."""
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponseForbidden("Только для директора")

    month = request.GET.get("month") or current_month_str()
    teachers_data = []
    for t in Teacher.objects.select_related("user").prefetch_related("groups__students"):
        t_groups = list(t.groups.all())
        students_count = sum(g.students.filter(is_active=True).count() for g in t_groups)
        salary = sum(group_month_report(g, month)["teacher_share"] for g in t_groups)
        teachers_data.append({
            "teacher": t,
            "groups": t_groups,
            "students_count": students_count,
            "salary": salary,
        })

    return render(request, "journal/teachers.html", {
        "page": "teachers",
        "month": month,
        "teachers_data": teachers_data,
        "all_teachers": Teacher.objects.all(),
        "error": request.GET.get("error"),
    })


@login_required
@require_POST
def add_teacher(request):
    """Директор создаёт учителя + сразу логин и пароль для входа."""
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponseForbidden("Только для директора")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "").strip()
    full_name = request.POST.get("full_name", "").strip()
    subject = request.POST.get("subject", "").strip()
    phone = request.POST.get("phone", "").strip()

    if not (username and password and full_name):
        return redirect("/teachers/?error=Заполните+логин,+пароль+и+ФИО")
    if User.objects.filter(username=username).exists():
        return redirect("/teachers/?error=Такой+логин+уже+занят")

    user = User.objects.create_user(username=username, password=password)
    Teacher.objects.create(user=user, full_name=full_name, subject=subject, phone=phone)
    return redirect("teachers")


@login_required
@require_POST
def add_group(request):
    """Директор создаёт новую группу."""
    if not (request.user.is_superuser or request.user.is_staff):
        return HttpResponseForbidden("Только для директора")

    teacher = get_object_or_404(Teacher, id=request.POST.get("teacher_id"))
    Group.objects.create(
        name=request.POST.get("name", "").strip(),
        teacher=teacher,
        monthly_fee=int(request.POST.get("monthly_fee") or 25000),
        default_lessons=int(request.POST.get("default_lessons") or 12),
        lesson_time=request.POST.get("lesson_time") or "15:00",
        mon="mon" in request.POST,
        tue="tue" in request.POST,
        wed="wed" in request.POST,
        thu="thu" in request.POST,
        fri="fri" in request.POST,
        sat="sat" in request.POST,
        sun="sun" in request.POST,
    )
    return redirect("teachers")

@login_required
def report_view(request):
    """Страница месячного отчёта 40/60."""
    month = request.GET.get("month") or current_month_str()
    groups = user_groups(request.user)
    is_admin = request.user.is_superuser or request.user.is_staff

    reports = [group_month_report(g, month) for g in groups]
    totals = {
        "students": sum(r["students_count"] for r in reports),
        "visits": sum(r["visits"] for r in reports),
        "revenue": sum(r["revenue"] for r in reports),
        "teacher": sum(r["teacher_share"] for r in reports),
        "center": sum(r["center_share"] for r in reports),
    }

    return render(request, "journal/report.html", {
        "page": "report",
        "month": month,
        "is_admin": is_admin,
        "reports": reports,
        "totals": totals,
    })


@login_required
@require_POST
def update_month_lessons(request, group_id):
    """Изменение числа уроков группы в выбранном месяце."""
    group = get_object_or_404(Group, id=group_id)
    if group not in user_groups(request.user):
        return HttpResponseForbidden("Нет доступа")

    month = request.POST.get("month") or current_month_str()
    lessons = int(request.POST.get("lessons") or group.default_lessons)
    if lessons > 0:
        MonthLessons.objects.update_or_create(
            group=group, month=month, defaults={"lessons": lessons}
        )
    return redirect(f"/report/?month={month}")


@login_required
def export_report_excel(request):
    """Скачивание Excel-отчёта за месяц."""
    month = request.GET.get("month") or current_month_str()
    groups = user_groups(request.user)
    is_admin = request.user.is_superuser or request.user.is_staff

    data = build_month_excel(groups, month, is_admin=is_admin)
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="ELZHAS_report_{month}.xlsx"'
    return response