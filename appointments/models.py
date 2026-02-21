import datetime
import secrets

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class Service(models.Model):
    """Tratamiento o servicio ofrecido en el consultorio."""

    name             = models.CharField(max_length=100, verbose_name="Servicio")
    description      = models.TextField(blank=True,     verbose_name="Descripción")
    duration_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name="Duración (min)",
        help_text="Debe ser múltiplo de 30. Bloquea los slots necesarios en la agenda."
    )
    price   = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name="Precio")
    color   = models.CharField(max_length=7, default="#2d9e94", verbose_name="Color hex")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name        = "Servicio"
        verbose_name_plural = "Servicios"
        ordering            = ['name']

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min)"

    @property
    def slots_required(self):
        """Cuántos slots de 30 min ocupa este servicio."""
        return max(1, (self.duration_minutes + 29) // 30)


class Dentist(models.Model):
    """Dentista o profesional del consultorio."""

    first_name = models.CharField(max_length=50,  verbose_name="Nombre")
    last_name  = models.CharField(max_length=50,  verbose_name="Apellido")
    email      = models.EmailField(unique=True,   verbose_name="Email")
    phone      = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    specialty  = models.CharField(max_length=100, blank=True, verbose_name="Especialidad")
    bio        = models.TextField(blank=True,     verbose_name="Biografía corta")
    services   = models.ManyToManyField(Service, related_name='dentists', verbose_name="Servicios que realiza")
    is_active  = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name        = "Dentista"
        verbose_name_plural = "Dentistas"
        ordering            = ['last_name', 'first_name']

    def __str__(self):
        return self.get_full_name()

    def get_full_name(self):
        return f"Dr. {self.first_name} {self.last_name}"

    @property
    def initials(self):
        return (self.first_name[:1] + self.last_name[:1]).upper()


class WorkSchedule(models.Model):
    """
    Horario de trabajo de un dentista por día de la semana.

    Soporta horario partido (p.ej. invierno 10-14 y 16-20):
      - Franja 1: start_time → end_time           (obligatoria)
      - Franja 2: start_time_2 → end_time_2       (opcional, para el horario de tarde)

    Temporada:
      - SUMMER  →  franja única (start_time / end_time)
      - WINTER  →  franja partida (ambas franjas)
    """

    DAYS = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'),
        (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
    ]

    dentist     = models.ForeignKey(Dentist, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DAYS, verbose_name="Día")

    # Franja 1 (o única en verano)
    start_time  = models.TimeField(verbose_name="Inicio franja 1")
    end_time    = models.TimeField(verbose_name="Fin franja 1")

    # Franja 2 — solo invierno (dejar vacío en verano)
    start_time_2 = models.TimeField(
        null=True, blank=True, verbose_name="Inicio franja 2",
        help_text="Opcional. Rellena solo si hay horario partido (p.ej. tarde de invierno: 16:00)."
    )
    end_time_2   = models.TimeField(
        null=True, blank=True, verbose_name="Fin franja 2",
        help_text="Opcional. Rellena solo si hay horario partido (p.ej. tarde de invierno: 20:00)."
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name        = "Horario de trabajo"
        verbose_name_plural = "Horarios de trabajo"
        unique_together     = ('dentist', 'day_of_week')
        ordering            = ['dentist', 'day_of_week']

    def __str__(self):
        base = f"{self.dentist} — {self.get_day_of_week_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"
        if self.start_time_2 and self.end_time_2:
            base += f" / {self.start_time_2:%H:%M}–{self.end_time_2:%H:%M}"
        return base

    def get_ranges(self) -> list[tuple]:
        """Devuelve lista de tuplas (start, end) con las franjas activas del día."""
        ranges = [(self.start_time, self.end_time)]
        if self.start_time_2 and self.end_time_2:
            ranges.append((self.start_time_2, self.end_time_2))
        return ranges


class BlockedDate(models.Model):
    """Días bloqueados: vacaciones, festivos, ausencias."""

    dentist = models.ForeignKey(
        Dentist, on_delete=models.CASCADE, related_name='blocked_dates',
        null=True, blank=True, verbose_name="Dentista",
        help_text="Vacío = bloquea todo el consultorio ese día."
    )
    date   = models.DateField(verbose_name="Fecha")
    reason = models.CharField(max_length=200, blank=True, verbose_name="Motivo")

    class Meta:
        verbose_name        = "Fecha bloqueada"
        verbose_name_plural = "Fechas bloqueadas"
        ordering            = ['date']

    def __str__(self):
        who = str(self.dentist) if self.dentist else "Todo el consultorio"
        return f"{self.date} — {who}"


class Patient(models.Model):
    """Paciente del consultorio."""

    first_name = models.CharField(max_length=50,  verbose_name="Nombre")
    last_name  = models.CharField(max_length=100, blank=True, verbose_name="Apellido")
    email      = models.EmailField(verbose_name="Email")
    phone      = models.CharField(max_length=25,  verbose_name="Teléfono")
    notes      = models.TextField(blank=True,     verbose_name="Notas del historial")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering            = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class Appointment(models.Model):
    """Cita dental."""

    STATUS_CHOICES = [
        ('pending',     'Pendiente'),
        ('confirmed',   'Confirmada'),
        ('in_progress', 'En progreso'),
        ('completed',   'Completada'),
        ('cancelled',   'Cancelada'),
        ('no_show',     'No se presentó'),
    ]

    patient  = models.ForeignKey(Patient, on_delete=models.CASCADE,  related_name='appointments')
    dentist  = models.ForeignKey(Dentist, on_delete=models.CASCADE,  related_name='appointments')
    service  = models.ForeignKey(Service, on_delete=models.PROTECT,  related_name='appointments')

    date       = models.DateField(verbose_name="Fecha")
    start_time = models.TimeField(verbose_name="Hora inicio")
    end_time   = models.TimeField(verbose_name="Hora fin", editable=False)

    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes          = models.TextField(blank=True, verbose_name="Notas del paciente")
    internal_notes = models.TextField(blank=True, verbose_name="Notas internas")

    confirmation_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Cita"
        verbose_name_plural = "Citas"
        ordering            = ['date', 'start_time']

    def __str__(self):
        return f"{self.patient} → {self.service.name} ({self.date} {self.start_time:%H:%M})"

    # ── Lógica de negocio ────────────────────────────────────────────────────

    def _calc_end_time(self):
        start_dt = datetime.datetime.combine(self.date, self.start_time)
        return (start_dt + datetime.timedelta(minutes=self.service.duration_minutes)).time()

    def clean(self):
        if not all([self.date, self.start_time, self.service_id, self.dentist_id]):
            return

        # 1. No en el pasado
        if self.date < timezone.now().date():
            raise ValidationError("No se pueden agendar citas en el pasado.")

        end_time = self._calc_end_time()

        # 2. Sin conflictos con citas del mismo dentista
        conflicts = Appointment.objects.filter(
            dentist=self.dentist,
            date=self.date,
            status__in=['pending', 'confirmed', 'in_progress'],
            start_time__lt=end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)

        if conflicts.exists():
            c = conflicts.first()
            raise ValidationError(
                f"Conflicto: ya existe una cita de {c.start_time:%H:%M} a {c.end_time:%H:%M}."
            )

        # 3. El dentista ofrece el servicio
        if not self.dentist.services.filter(pk=self.service_id).exists():
            raise ValidationError(f"{self.dentist} no ofrece '{self.service}'.")

        # 4. El dentista trabaja ese día de la semana
        if not self.dentist.schedules.filter(day_of_week=self.date.weekday(), is_active=True).exists():
            raise ValidationError(f"{self.dentist} no trabaja ese día de la semana.")

        # 5. Dentro del horario de la temporada correspondiente a la fecha
        from .availability import _ranges_for_date
        ranges = _ranges_for_date(self.date)
        fits_any_range = any(s <= self.start_time and end_time <= e for s, e in ranges)
        if not fits_any_range:
            ranges_str = "  |  ".join(f"{s:%H:%M}–{e:%H:%M}" for s, e in ranges)
            raise ValidationError(f"La cita está fuera del horario: {ranges_str}.")

        # 5. Fecha no bloqueada
        if BlockedDate.objects.filter(
            models.Q(dentist=self.dentist) | models.Q(dentist__isnull=True),
            date=self.date
        ).exists():
            raise ValidationError("El dentista no está disponible ese día.")

    def save(self, *args, **kwargs):
        self.end_time = self._calc_end_time()
        if not self.confirmation_token:
            self.confirmation_token = secrets.token_urlsafe(32)
        self.full_clean()
        super().save(*args, **kwargs)
