import datetime

from rest_framework import serializers

from .models import Appointment, BlockedDate, Dentist, Patient, Service, WorkSchedule


# ─── Servicios ────────────────────────────────────────────────────────────────

class ServiceSerializer(serializers.ModelSerializer):
    slots_required = serializers.ReadOnlyField()

    class Meta:
        model  = Service
        fields = ['id', 'name', 'description', 'duration_minutes', 'price', 'color', 'slots_required']


# ─── Dentistas ────────────────────────────────────────────────────────────────

class WorkScheduleSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model  = WorkSchedule
        fields = [
            'day_of_week', 'day_name',
            'start_time', 'end_time',
            'start_time_2', 'end_time_2',   # segunda franja (horario partido)
        ]


class DentistListSerializer(serializers.ModelSerializer):
    """Versión ligera: listados y slots."""
    full_name   = serializers.CharField(source='get_full_name', read_only=True)
    initials    = serializers.ReadOnlyField()
    service_ids = serializers.PrimaryKeyRelatedField(source='services', many=True, read_only=True)

    class Meta:
        model  = Dentist
        fields = ['id', 'full_name', 'specialty', 'initials', 'service_ids']


class DentistDetailSerializer(serializers.ModelSerializer):
    """Versión completa: detalle + horarios."""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    initials  = serializers.ReadOnlyField()
    services  = ServiceSerializer(many=True, read_only=True)
    schedules = WorkScheduleSerializer(many=True, read_only=True)

    class Meta:
        model  = Dentist
        fields = ['id', 'full_name', 'first_name', 'last_name', 'specialty', 'bio', 'initials', 'services', 'schedules']


# ─── Pacientes ────────────────────────────────────────────────────────────────

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Patient
        fields = ['id', 'first_name', 'last_name', 'email', 'phone']


# ─── Citas ────────────────────────────────────────────────────────────────────

class AppointmentCreateSerializer(serializers.Serializer):
    """Serializer para crear una cita desde el frontend (flujo paso a paso)."""

    patient_name  = serializers.CharField(max_length=150)
    patient_email = serializers.EmailField()
    patient_phone = serializers.CharField(max_length=25)

    dentist_id = serializers.PrimaryKeyRelatedField(
        queryset=Dentist.objects.filter(is_active=True), source='dentist'
    )
    service_id = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.filter(is_active=True), source='service'
    )
    date       = serializers.DateField()
    start_time = serializers.TimeField()
    notes      = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        from django.utils import timezone

        dentist, service = data['dentist'], data['service']
        date, start_time = data['date'], data['start_time']

        if date < timezone.now().date():
            raise serializers.ValidationError("No se pueden agendar citas en el pasado.")

        if not dentist.services.filter(pk=service.pk).exists():
            raise serializers.ValidationError(f"{dentist} no ofrece '{service}'.")

        end_time = (
            datetime.datetime.combine(date, start_time)
            + datetime.timedelta(minutes=service.duration_minutes)
        ).time()

        if not dentist.schedules.filter(day_of_week=date.weekday(), is_active=True).exists():
            raise serializers.ValidationError(f"{dentist} no trabaja ese día de la semana.")

        from .availability import _ranges_for_date
        ranges = _ranges_for_date(date)
        fits_any_range = any(s <= start_time and end_time <= e for s, e in ranges)
        if not fits_any_range:
            ranges_str = "  |  ".join(f"{s:%H:%M}–{e:%H:%M}" for s, e in ranges)
            raise serializers.ValidationError(f"Fuera del horario: {ranges_str}.")

        conflicts = Appointment.objects.filter(
            dentist=dentist, date=date,
            status__in=['pending', 'confirmed', 'in_progress'],
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        if conflicts.exists():
            raise serializers.ValidationError("Ese horario ya no está disponible. Elige otro.")

        data['end_time'] = end_time
        return data

    def create(self, validated_data):
        parts = validated_data['patient_name'].split(' ', 1)
        patient, _ = Patient.objects.get_or_create(
            email=validated_data['patient_email'],
            defaults={
                'first_name': parts[0],
                'last_name':  parts[1] if len(parts) > 1 else '',
                'phone':      validated_data['patient_phone'],
            }
        )
        return Appointment.objects.create(
            patient    = patient,
            dentist    = validated_data['dentist'],
            service    = validated_data['service'],
            date       = validated_data['date'],
            start_time = validated_data['start_time'],
            notes      = validated_data.get('notes', ''),
            status     = 'pending',
        )


class AppointmentSerializer(serializers.ModelSerializer):
    patient        = PatientSerializer(read_only=True)
    dentist        = DentistListSerializer(read_only=True)
    service        = ServiceSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = Appointment
        fields = [
            'id', 'patient', 'dentist', 'service',
            'date', 'start_time', 'end_time',
            'status', 'status_display', 'notes','internal_notes',
            'confirmation_token', 'created_at',
        ]


# ─── Disponibilidad ───────────────────────────────────────────────────────────

class TimeSlotSerializer(serializers.Serializer):
    time         = serializers.TimeField(format='%H:%M')
    available    = serializers.BooleanField()
    dentist_id   = serializers.IntegerField(allow_null=True)
    dentist_name = serializers.CharField(allow_null=True)


class CalendarDaySerializer(serializers.Serializer):
    date                  = serializers.DateField()
    has_availability      = serializers.BooleanField()
    available_slots_count = serializers.IntegerField()
