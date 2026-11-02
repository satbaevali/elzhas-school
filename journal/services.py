from datetime import date
from django.conf import settings
from .models import Attendance, Group, Student


def current_month_str() -> str:
    """Возвращает текущий месяц в формате 'ГГГГ-ММ', например '2026-11'."""
    today = date.today()
    return f"{today.year:04d}-{today.month:02d}"


def user_groups(user):
    """
    Если вошёл директор (superuser/staff) — возвращает ВСЕ группы.
    Если вошёл учитель — возвращает ТОЛЬКО его группы.
    """
    if user.is_superuser or user.is_staff:
        return Group.objects.select_related("teacher").all()
    if hasattr(user, "teacher"):
        return Group.objects.select_related("teacher").filter(teacher=user.teacher)
    return Group.objects.none()


def student_month_stats(student: Student, month: str) -> dict:
    """
    Считает посещения одного ученика за месяц (month = 'YYYY-MM')
    и сумму к оплате.
    """
    year, mon = map(int, month.split("-"))
    qs = Attendance.objects.filter(
        student=student,
        date__year=year,
        date__month=mon,
    )
    present = qs.filter(status=Attendance.Status.PRESENT).count()
    absent = qs.filter(status=Attendance.Status.ABSENT).count()
    excused = qs.filter(status=Attendance.Status.EXCUSED).count()
    total_marked = present + absent + excused

    lessons_norm = student.group.lessons_in_month(month)
    lesson_price = student.group.monthly_fee / lessons_norm if lessons_norm else 0
    # Оплата за посещённые уроки, но не больше стоимости абонемента
    paid_amount = min(student.group.monthly_fee, round(present * lesson_price))
    rate = round(present / total_marked * 100) if total_marked else 0

    return {
        "present": present,
        "absent": absent,
        "excused": excused,
        "lessons_norm": lessons_norm,
        "paid_amount": paid_amount,
        "rate": rate,
    }


def group_month_report(group: Group, month: str) -> dict:
    """
    Считает сводку по группе за месяц:
    доход, 40% учителю, 60% центру.
    """
    students = group.students.filter(is_active=True)
    lessons_norm = group.lessons_in_month(month)
    total_visits = 0
    revenue = 0

    for s in students:
        st = student_month_stats(s, month)
        total_visits += st["present"]
        revenue += st["paid_amount"]

    t_pct = getattr(settings, "TEACHER_PERCENT", 40)
    c_pct = getattr(settings, "CENTER_PERCENT", 60)

    teacher_share = round(revenue * t_pct / 100)
    center_share = round(revenue * c_pct / 100)

    return {
        "group": group,
        "students_count": students.count(),
        "lessons_norm": lessons_norm,
        "visits": total_visits,
        "revenue": revenue,
        "teacher_share": teacher_share,
        "center_share": center_share,
    }