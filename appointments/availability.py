"""
Motor de disponibilidad.

Optimizaciones:
  - month_availability carga TODO el mes en 3 queries (citas, fechas bloqueadas,
    horarios) en lugar de una query por día.
  - El horario se determina por la FECHA consultada, no por la BD:
      Verano  (jul-sep): 08:00-15:00
      Invierno (resto):  10:00-14:00 / 16:00-20:00
"""
import calendar
import datetime
from collections import defaultdict

from django.db.models import Q

from .models import BlockedDate, Dentist, Service, WorkSchedule, Appointment

SLOT_MINUTES = 30

_SUMMER_RANGES = [(datetime.time(8,  0), datetime.time(15, 0))]
_WINTER_RANGES = [(datetime.time(10, 0), datetime.time(14, 0)),
                  (datetime.time(16, 0), datetime.time(20, 0))]


def _ranges_for_date(date: datetime.date) -> list[tuple]:
    return _SUMMER_RANGES if 7 <= date.month <= 9 else _WINTER_RANGES


def _time_slots_for_range(start: datetime.time, end: datetime.time) -> list[datetime.time]:
    slots, cur = [], datetime.datetime.combine(datetime.date.min, start)
    end_dt = datetime.datetime.combine(datetime.date.min, end)
    while cur < end_dt:
        slots.append(cur.time())
        cur += datetime.timedelta(minutes=SLOT_MINUTES)
    return slots


def _all_slots_for_date(date: datetime.date) -> list[datetime.time]:
    slots = []
    for start, end in _ranges_for_date(date):
        slots.extend(_time_slots_for_range(start, end))
    return slots


def _slot_fits(slot: datetime.time, duration: int, date: datetime.date) -> bool:
    """La cita cabe entera dentro de alguna franja de la temporada."""
    end = (datetime.datetime.combine(date, slot) + datetime.timedelta(minutes=duration)).time()
    return any(rng_s <= slot and end <= rng_e for rng_s, rng_e in _ranges_for_date(date))


# ─── API pública: slots de un día concreto ────────────────────────────────────

def get_slots(date: datetime.date, service: Service, dentist: Dentist = None) -> list[dict]:
    if dentist:
        return _slots_single_dentist(dentist, date, service)
    return _slots_all_dentists(date, service)


def _slots_single_dentist(dentist: Dentist, date: datetime.date, service: Service) -> list[dict]:
    if not dentist.schedules.filter(day_of_week=date.weekday(), is_active=True).exists():
        return []
    if not dentist.services.filter(pk=service.pk).exists():
        return []
    if BlockedDate.objects.filter(
        Q(dentist=dentist) | Q(dentist__isnull=True), date=date
    ).exists():
        return []

    busy = set(
        Appointment.objects.filter(
            dentist=dentist, date=date,
            status__in=['pending', 'confirmed', 'in_progress'],
        ).values_list('start_time', 'end_time')
    )

    result = []
    for t in _all_slots_for_date(date):
        end = (datetime.datetime.combine(date, t) + datetime.timedelta(minutes=service.duration_minutes)).time()
        available = _slot_fits(t, service.duration_minutes, date) and not any(
            t < b_end and end > b_start for b_start, b_end in busy
        )
        result.append({'time': t, 'available': available,
                       'dentist_id': dentist.pk, 'dentist_name': dentist.get_full_name()})
    return result


def _slots_all_dentists(date: datetime.date, service: Service) -> list[dict]:
    dentists = list(
        Dentist.objects
        .filter(services=service, is_active=True,
                schedules__day_of_week=date.weekday(), schedules__is_active=True)
        .distinct()
        .prefetch_related('schedules', 'services')
    )
    if not dentists:
        return []

    dentist_ids = [d.pk for d in dentists]

    # 1 query: todas las citas del día para estos dentistas
    busy_by_dentist = defaultdict(list)
    for appt in Appointment.objects.filter(
        dentist_id__in=dentist_ids, date=date,
        status__in=['pending', 'confirmed', 'in_progress'],
    ).values('dentist_id', 'start_time', 'end_time'):
        busy_by_dentist[appt['dentist_id']].append((appt['start_time'], appt['end_time']))

    # 1 query: fechas bloqueadas del día
    blocked_all = BlockedDate.objects.filter(date=date, dentist__isnull=True).exists()
    blocked_dentists = set(
        BlockedDate.objects.filter(date=date, dentist_id__in=dentist_ids)
        .values_list('dentist_id', flat=True)
    )

    all_slots = _all_slots_for_date(date)
    merged: dict[datetime.time, dict] = {}

    for d in dentists:
        if blocked_all or d.pk in blocked_dentists:
            continue
        busy = busy_by_dentist[d.pk]
        for t in all_slots:
            end = (datetime.datetime.combine(date, t) + datetime.timedelta(minutes=service.duration_minutes)).time()
            available = _slot_fits(t, service.duration_minutes, date) and not any(
                t < b_end and end > b_start for b_start, b_end in busy
            )
            if t not in merged:
                merged[t] = {'time': t, 'available': False, 'dentist_id': None, 'dentist_name': None}
            if available and not merged[t]['available']:
                merged[t].update(available=True, dentist_id=d.pk, dentist_name=d.get_full_name())

    return sorted(merged.values(), key=lambda x: x['time'])


# ─── API pública: disponibilidad de todo el mes ───────────────────────────────

def month_availability(year: int, month: int, service: Service, dentist: Dentist = None) -> list[dict]:
    today    = datetime.date.today()
    num_days = calendar.monthrange(year, month)[1]
    month_start = datetime.date(year, month, 1)
    month_end   = datetime.date(year, month, num_days)

    # ── 3 queries para todo el mes ──────────────────────────────────────────

    # 1. Dentistas válidos con sus días de trabajo
    if dentist:
        dentists = [dentist] if dentist.services.filter(pk=service.pk).exists() else []
    else:
        dentists = list(
            Dentist.objects
            .filter(services=service, is_active=True)
            .prefetch_related('schedules')
        )

    # working_days[dentist_id] = set of weekdays (0=Mon..6=Sun)
    working_days: dict[int, set] = {
        d.pk: {s.day_of_week for s in d.schedules.all() if s.is_active}
        for d in dentists
    }

    # 2. Todas las citas del mes para estos dentistas
    dentist_ids = [d.pk for d in dentists]
    busy_by_dentist_day: dict[tuple, list] = defaultdict(list)
    for appt in Appointment.objects.filter(
        dentist_id__in=dentist_ids,
        date__gte=month_start, date__lte=month_end,
        status__in=['pending', 'confirmed', 'in_progress'],
    ).values('dentist_id', 'date', 'start_time', 'end_time'):
        busy_by_dentist_day[(appt['dentist_id'], appt['date'])].append(
            (appt['start_time'], appt['end_time'])
        )

    # 3. Fechas bloqueadas del mes
    blocked_clinic: set[datetime.date] = set(
        BlockedDate.objects.filter(
            date__gte=month_start, date__lte=month_end, dentist__isnull=True
        ).values_list('date', flat=True)
    )
    blocked_dentist_day: set[tuple] = set(
        BlockedDate.objects.filter(
            date__gte=month_start, date__lte=month_end, dentist_id__in=dentist_ids
        ).values_list('dentist_id', 'date')
    )

    # ── Calcular disponibilidad por día ─────────────────────────────────────
    result = []
    for day in range(1, num_days + 1):
        d = datetime.date(year, month, day)

        if d < today or d in blocked_clinic:
            result.append({'date': d, 'has_availability': False, 'available_slots_count': 0})
            continue

        all_slots   = _all_slots_for_date(d)
        weekday     = d.weekday()
        duration    = service.duration_minutes
        has_avail   = False
        avail_count = 0

        for dent in dentists:
            if weekday not in working_days[dent.pk]:
                continue
            if (dent.pk, d) in blocked_dentist_day:
                continue

            busy = busy_by_dentist_day[(dent.pk, d)]
            for t in all_slots:
                if not _slot_fits(t, duration, d):
                    continue
                end = (datetime.datetime.combine(d, t) + datetime.timedelta(minutes=duration)).time()
                if not any(t < b_end and end > b_start for b_start, b_end in busy):
                    has_avail = True
                    avail_count += 1
                    break  # con un slot libre basta para marcar el día
            if has_avail:
                break  # con un dentista libre basta

        result.append({'date': d, 'has_availability': has_avail, 'available_slots_count': avail_count})

    return result
