from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
import calendar


class Teacher(models.Model):
    """Учитель. Связан с аккаунтом (User), чтобы входить по логину и паролю."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,      # удалили аккаунт → удалился учитель
        related_name="teacher",
        verbose_name="Аккаунт",
    )
    full_name = models.CharField("ФИО", max_length=150)
    subject = models.CharField("Предмет", max_length=100)
    phone = models.CharField("Телефон", max_length=20, blank=True)

    class Meta:
        verbose_name = "Учитель"
        verbose_name_plural = "Учителя"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Group(models.Model):
    """Группа: у неё один учитель, абонемент и расписание."""
    name = models.CharField("Название", max_length=100)
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,      # нельзя удалить учителя, пока у него есть группы
        related_name="groups",
        verbose_name="Учитель",
    )
    monthly_fee = models.PositiveIntegerField("Абонемент в месяц, ₸")
    default_lessons = models.PositiveSmallIntegerField(
        "Уроков в месяц (по умолчанию)",
        default=12,
        validators=[MinValueValidator(1)],
    )
    lesson_time = models.TimeField("Время урока")

    # Дни занятий: галочка = в этот день есть урок
    mon = models.BooleanField("Пн", default=False)
    tue = models.BooleanField("Вт", default=False)
    wed = models.BooleanField("Ср", default=False)
    thu = models.BooleanField("Чт", default=False)
    fri = models.BooleanField("Пт", default=False)
    sat = models.BooleanField("Сб", default=False)
    sun = models.BooleanField("Вс", default=False)

    class Meta:
        verbose_name = "Группа"
        verbose_name_plural = "Группы"
        ordering = ["lesson_time", "name"]

    def __str__(self):
        return self.name

    def weekdays(self):
        """Номера дней с уроками: 0 = понедельник ... 6 = воскресенье."""
        flags = [self.mon, self.tue, self.wed, self.thu, self.fri, self.sat, self.sun]
        return [i for i, on in enumerate(flags) if on]

    def weekdays_display(self):
        """Например: 'Пн, Ср, Пт'."""
        names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        return ", ".join(names[i] for i in self.weekdays())

    def has_lesson_on(self, day):
        """Есть ли урок в эту дату по расписанию."""
        return day.weekday() in self.weekdays()

    def lessons_in_month(self, month: str) -> int:
        """
        1. Если директор вручную указал число уроков для этого месяца (например, из-за праздников) — берём его.
        2. Иначе АВТОМАТИЧЕСКИ считаем по календарю, сколько раз дни занятий (например, Пн-Ср-Пт)
           выпадают в этом месяце!
        """
        custom = self.month_lessons.filter(month=month).first()
        if custom:
            return custom.lessons
        active_days = set(self.weekdays())  # например, {0, 2, 4} для Пн, Ср, Пт
        if not active_days:
            return self.default_lessons
        year, mon = map(int, month.split("-"))
        _, days_in_month = calendar.monthrange(year, mon)
        # Считаем каждый день месяца, который совпадает с расписанием группы
        count = sum(
            1 for day in range(1, days_in_month + 1)
            if calendar.weekday(year, mon, day) in active_days
        )
        return count or self.default_lessons


class Student(models.Model):
    """Ученик. Состоит в одной группе."""
    full_name = models.CharField("ФИО", max_length=150)
    parent_phone = models.CharField("Телефон родителя", max_length=20, blank=True)
    group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name="students",
        verbose_name="Группа",
    )
    created_at = models.DateField("Дата добавления", auto_now_add=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Ученик"
        verbose_name_plural = "Ученики"
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Attendance(models.Model):
    """Отметка посещаемости: один ученик + одна дата = одна запись."""

    class Status(models.TextChoices):
        PRESENT = "present", "Был"
        ABSENT = "absent", "Не был"
        EXCUSED = "excused", "Уважительная"

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,      # удалили ученика → удалились его отметки
        related_name="attendances",
        verbose_name="Ученик",
    )
    date = models.DateField("Дата")
    status = models.CharField("Статус", max_length=10, choices=Status.choices)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Кто отметил",
    )

    class Meta:
        verbose_name = "Посещаемость"
        verbose_name_plural = "Посещаемость"
        ordering = ["-date"]
        constraints = [
            # Нельзя отметить одного ученика дважды за один день
            models.UniqueConstraint(fields=["student", "date"], name="unique_attendance_per_day"),
        ]
        indexes = [models.Index(fields=["date"])]

    def __str__(self):
        return f"{self.student} — {self.date} — {self.get_status_display()}"


class MonthLessons(models.Model):
    """Число уроков группы в конкретном месяце (если отличается от обычного)."""
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="month_lessons",
        verbose_name="Группа",
    )
    month = models.CharField(
        "Месяц",
        max_length=7,
        validators=[RegexValidator(r"^\d{4}-\d{2}$", "Формат: ГГГГ-ММ, например 2026-11")],
    )
    lessons = models.PositiveSmallIntegerField("Уроков", validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "Уроки в месяце"
        verbose_name_plural = "Уроки в месяце"
        constraints = [
            models.UniqueConstraint(fields=["group", "month"], name="unique_group_month"),
        ]

    def __str__(self):
        return f"{self.group} — {self.month}: {self.lessons}"