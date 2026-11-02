import random
from datetime import date, time, timedelta
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from journal.models import Attendance, Group, Student, Teacher


class Command(BaseCommand):
    help = "Заполняет базу демо-данными (директор, 4 учителя, 6 групп, 30 учеников, посещаемость)"

    def handle(self, *args, **options):
        random.seed(42)

        # 1. Аккаунт директора
        admin_user, created = User.objects.get_or_create(
            username="director",
            defaults={"is_staff": True, "is_superuser": True},
        )
        if created:
            admin_user.set_password("director2026")
            admin_user.save()

        # 2. Учителя (логин, ФИО, предмет, телефон)
        teachers_spec = [
            ("aigerim", "Айгерим Сапарова", "Английский язык", "+7 701 123 45 67"),
            ("erlan", "Ерлан Жумабеков", "Математика", "+7 705 234 56 78"),
            ("dinara", "Динара Касымова", "Казахский язык", "+7 707 345 67 89"),
            ("arman", "Арман Нурланов", "Робототехника", "+7 747 456 78 90"),
        ]
        teachers = {}
        for username, full_name, subject, phone in teachers_spec:
            u, _ = User.objects.get_or_create(username=username)
            u.set_password("teacher2026")
            u.save()
            t, _ = Teacher.objects.get_or_create(
                user=u,
                defaults={"full_name": full_name, "subject": subject, "phone": phone},
            )
            teachers[username] = t

        # 3. Группы
        groups_spec = [
            ("English A1", "aigerim", 25000, 12, time(15, 0), dict(mon=True, wed=True, fri=True)),
            ("English B1", "aigerim", 30000, 12, time(17, 0), dict(tue=True, thu=True, sat=True)),
            ("Математика 5 кл", "erlan", 20000, 8, time(14, 0), dict(tue=True, thu=True)),
            ("Подготовка к ЕНТ", "erlan", 35000, 12, time(18, 0), dict(mon=True, wed=True, fri=True)),
            ("Қазақ тілі", "dinara", 18000, 8, time(16, 0), dict(mon=True, thu=True)),
            ("Robotics Kids", "arman", 28000, 8, time(11, 0), dict(wed=True, sat=True)),
        ]
        groups = []
        for name, t_key, fee, lessons, l_time, days in groups_spec:
            g, _ = Group.objects.get_or_create(
                name=name,
                teacher=teachers[t_key],
                defaults={
                    "monthly_fee": fee,
                    "default_lessons": lessons,
                    "lesson_time": l_time,
                    **days,
                },
            )
            groups.append(g)

        # 4. 30 учеников
        student_names = [
            "Алихан Ержанов", "Аружан Бекова", "Нурсултан Абенов", "Томирис Кайратова",
            "Даниял Ахметов", "Айым Серикова", "Ернур Талгатов", "Мадина Оспанова",
            "Бекзат Муратов", "Жансая Ермекова", "Асылжан Омаров", "Камила Нурланова",
            "Санжар Бейсенов", "Амина Жаксылыкова", "Темирлан Исаев", "Аяулым Дауренова",
            "Рамазан Сейткали", "Дильназ Мухтарова", "Адиль Кенжебаев", "Сабина Алиева",
            "Нурислам Габдуллин", "Асель Канатова", "Ислам Жунусов", "Малика Сагинтаева",
            "Арсен Байжанов", "Зарина Абдрахманова", "Алдияр Касенов", "Инкар Смагулова",
            "Мирас Есенов", "Абылай Нургалиев",
        ]
        students = []
        for idx, s_name in enumerate(student_names):
            grp = groups[idx % len(groups)]
            phone = f"+7 70{idx % 8 + 1} {100 + idx * 7:03d} {10 + idx:02d} {20 + idx:02d}"
            st, _ = Student.objects.get_or_create(
                full_name=s_name,
                group=grp,
                defaults={"parent_phone": phone},
            )
            students.append(st)

        # 5. Посещаемость за последние 45 дней
        today = date.today()
        start_day = today - timedelta(days=45)
        cur = start_day
        while cur <= today:
            for g in groups:
                if g.has_lesson_on(cur):
                    for s in g.students.filter(is_active=True):
                        r = random.random()
                        status = (
                            Attendance.Status.PRESENT if r < 0.85
                            else Attendance.Status.ABSENT if r < 0.94
                            else Attendance.Status.EXCUSED
                        )
                        Attendance.objects.get_or_create(
                            student=s,
                            date=cur,
                            defaults={"status": status, "marked_by": g.teacher.user},
                        )
            cur += timedelta(days=1)

        self.stdout.write(self.style.SUCCESS(
            "✅ Демо-данные успешно созданы!\n"
            "   Директор: логин director | пароль director2026\n"
            "   Учителя:  логин aigerim, erlan, dinara, arman | пароль teacher2026"
        ))