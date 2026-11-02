from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from .services import group_month_report, student_month_stats


def build_month_excel(groups, month: str, is_admin: bool = True) -> bytes:
    """Создаёт Excel-файл (.xlsx) с отчётом за месяц и возвращает его байты."""
    wb = Workbook()

    # --- Лист 1: Сводка по группам ---
    ws1 = wb.active
    ws1.title = "Сводка по группам"

    header_fill = PatternFill("solid", fgColor="10B981")
    header_font = Font(bold=True, color="FFFFFF")
    total_fill = PatternFill("solid", fgColor="ECFDF5")
    bold_font = Font(bold=True)

    ws1.append([f"ELZHAS SCHOOL — Отчёт за {month}"])
    ws1["A1"].font = Font(bold=True, size=14)
    ws1.append([])

    headers = ["Группа", "Учитель", "Учеников", "Абонемент (₸)", "Уроков в мес.", "Посещений", "Доход (₸)", "Учителю 40% (₸)"]
    if is_admin:
        headers.append("Центру 60% (₸)")
    ws1.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws1.cell(row=3, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    tot_students = tot_visits = tot_rev = tot_teacher = tot_center = 0

    for g in groups:
        r = group_month_report(g, month)
        tot_students += r["students_count"]
        tot_visits += r["visits"]
        tot_rev += r["revenue"]
        tot_teacher += r["teacher_share"]
        tot_center += r["center_share"]

        row = [
            g.name,
            g.teacher.full_name,
            r["students_count"],
            g.monthly_fee,
            r["lessons_norm"],
            r["visits"],
            r["revenue"],
            r["teacher_share"],
        ]
        if is_admin:
            row.append(r["center_share"])
        ws1.append(row)

    total_row = ["ИТОГО", "", tot_students, "", "", tot_visits, tot_rev, tot_teacher]
    if is_admin:
        total_row.append(tot_center)
    ws1.append(total_row)

    last_row = ws1.max_row
    for col_num in range(1, len(headers) + 1):
        cell = ws1.cell(row=last_row, column=col_num)
        cell.fill = total_fill
        cell.font = bold_font

    for col in ws1.columns:
        ws1.column_dimensions[col[0].column_letter].width = 18

    # --- Лист 2: Посещаемость учеников ---
    ws2 = wb.create_sheet(title="Ученики")
    headers2 = ["Ученик", "Группа", "Учитель", "Был", "Не был", "Уважит.", "Норма уроков", "К оплате (₸)"]
    ws2.append(headers2)

    for col_num in range(1, len(headers2) + 1):
        cell = ws2.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font

    for g in groups:
        for s in g.students.filter(is_active=True):
            st = student_month_stats(s, month)
            ws2.append([
                s.full_name,
                g.name,
                g.teacher.full_name,
                st["present"],
                st["absent"],
                st["excused"],
                st["lessons_norm"],
                st["paid_amount"],
            ])

    for col in ws2.columns:
        ws2.column_dimensions[col[0].column_letter].width = 20

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()