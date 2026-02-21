import datetime

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .availability import get_slots, month_availability
from .models import Appointment, Dentist, Service
from .serializers import (
    AppointmentCreateSerializer,
    AppointmentSerializer,
    CalendarDaySerializer,
    DentistDetailSerializer,
    DentistListSerializer,
    ServiceSerializer,
    TimeSlotSerializer,
)


# ─── Servicios ────────────────────────────────────────────────────────────────

class ServiceListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    """
    GET /api/services/
    Lista todos los servicios activos.
    """
    queryset         = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer


class ServiceDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    """
    GET /api/services/<id>/
    """
    queryset         = Service.objects.filter(is_active=True)
    serializer_class = ServiceSerializer


# ─── Dentistas ────────────────────────────────────────────────────────────────

class DentistListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    """
    GET /api/dentists/
    GET /api/dentists/?service_id=X        → filtra por servicio
    GET /api/dentists/?service_id=X&detail=1 → incluye horarios
    """
    def get_queryset(self):
        qs = Dentist.objects.filter(is_active=True).prefetch_related('services', 'schedules')
        if sid := self.request.query_params.get('service_id'):
            qs = qs.filter(services__id=sid)
        return qs

    def get_serializer_class(self):
        return DentistDetailSerializer if self.request.query_params.get('detail') else DentistListSerializer


class DentistDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    """
    GET /api/dentists/<id>/
    """
    queryset         = Dentist.objects.filter(is_active=True)
    serializer_class = DentistDetailSerializer


# ─── Disponibilidad ───────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def available_slots(request):
    """
    GET /api/availability/slots/?date=YYYY-MM-DD&service_id=X[&dentist_id=Y]

    Devuelve todos los time-slots del día con su estado (available: true/false).
    Si no se especifica dentist_id, combina todos los dentistas del servicio.
    """
    raw_date   = request.query_params.get('date')
    service_id = request.query_params.get('service_id')

    if not raw_date or not service_id:
        return Response({'error': 'date y service_id son requeridos.'}, status=400)

    try:
        date = datetime.date.fromisoformat(raw_date)
    except ValueError:
        return Response({'error': 'Formato de fecha inválido. Usa YYYY-MM-DD.'}, status=400)

    service = get_object_or_404(Service, pk=service_id, is_active=True)
    dentist = None
    if did := request.query_params.get('dentist_id'):
        dentist = get_object_or_404(Dentist, pk=did, is_active=True)

    slots = get_slots(date, service, dentist)

    return Response({
        'date':    date,
        'service': ServiceSerializer(service).data,
        'slots':   TimeSlotSerializer(slots, many=True).data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def calendar_month_view(request):
    """
    GET /api/availability/calendar/?year=2024&month=10&service_id=X[&dentist_id=Y]

    Devuelve disponibilidad por día del mes (para pintar el calendario).
    """
    try:
        year  = int(request.query_params.get('year',  datetime.date.today().year))
        month = int(request.query_params.get('month', datetime.date.today().month))
    except (ValueError, TypeError):
        return Response({'error': 'year y month deben ser enteros.'}, status=400)

    service_id = request.query_params.get('service_id')
    if not service_id:
        return Response({'error': 'service_id es requerido.'}, status=400)

    service = get_object_or_404(Service, pk=service_id, is_active=True)
    dentist = None
    if did := request.query_params.get('dentist_id'):
        dentist = get_object_or_404(Dentist, pk=did, is_active=True)

    days = month_availability(year, month, service, dentist)

    return Response({
        'year':    year,
        'month':   month,
        'service': ServiceSerializer(service).data,
        'days':    CalendarDaySerializer(days, many=True).data,
    })


# ─── Citas ────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def create_appointment(request):
    serializer = AppointmentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    appointment = serializer.save()

    # 🔥 IMPORTANTE: usar el serializer completo para responder
    response_serializer = AppointmentSerializer(appointment)

    return Response(response_serializer.data, status=201)


@api_view(['GET'])
@permission_classes([AllowAny])
def appointment_by_token(request, token):
    """
    GET /api/appointments/<token>/
    Consulta de una cita por su token de confirmación.
    """
    appt = get_object_or_404(Appointment, confirmation_token=token)
    return Response(AppointmentSerializer(appt).data)


@api_view(['POST'])
@permission_classes([AllowAny])
def cancel_appointment(request, token):
    """
    POST /api/appointments/<token>/cancel/
    Cancela una cita por su token.
    """
    appt = get_object_or_404(Appointment, confirmation_token=token)

    if appt.status in ['completed', 'cancelled']:
        return Response(
            {'error': f'No se puede cancelar: estado actual es "{appt.get_status_display()}".'},
            status=400
        )

    appt.status = 'cancelled'
    appt.save(update_fields=['status', 'updated_at'])
    return Response({
        'message':     'Cita cancelada exitosamente.',
        'appointment': AppointmentSerializer(appt).data,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def patient_appointments(request):
    """
    GET /api/appointments/patient/?email=juan@email.com
    Historial de citas de un paciente filtrado por email.
    """
    email = request.query_params.get('email')
    if not email:
        return Response({'error': 'El parámetro email es requerido.'}, status=400)

    appts = (
        Appointment.objects
        .filter(patient__email=email)
        .select_related('patient', 'dentist', 'service')
        .order_by('-date', '-start_time')
    )
    return Response(AppointmentSerializer(appts, many=True).data)

@api_view(['PATCH'])
@permission_classes([AllowAny])
def update_appointment(request, token):
    """
    PATCH /api/appointments/<token>/update/
    Permite cambiar status e internal_notes de una cita.
    """
    appt = get_object_or_404(Appointment, confirmation_token=token)

    allowed = {'status', 'internal_notes'}
    data    = {k: v for k, v in request.data.items() if k in allowed}

    if 'status' in data:
        valid = [s for s, _ in Appointment.STATUS_CHOICES]
        if data['status'] not in valid:
            return Response({'error': f'Estado inválido. Opciones: {valid}'}, status=400)

    for field, value in data.items():
        setattr(appt, field, value)
    appt.save(update_fields=list(data.keys()) + ['updated_at'])

    return Response(AppointmentSerializer(appt).data)


# ─── Internal  ────────────────────────────────────────────────────────────────────

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def dentist_book(request):
    """
    Herramienta interna para que el dentista cree citas a sus pacientes.

    GET  /api/internal/book/?email=juan@email.com
         → devuelve historial del paciente (para autocompletar)

    POST /api/internal/book/
    {
      "patient_name":  "Juan Pérez",
      "patient_email": "juan@email.com",
      "patient_phone": "555-1234",
      "dentist_id":    1,
      "service_id":    2,
      "date":          "2026-03-15",
      "start_time":    "10:00",
      "notes":         "Revisión post-endodoncia"
    }
    """
    if request.method == 'GET':
        email = request.query_params.get('email', '').strip()
        if not email:
            return Response([])
        appts = (
            Appointment.objects
            .filter(patient__email=email)
            .select_related('patient', 'dentist', 'service')
            .order_by('-date')[:5]
        )
        return Response(AppointmentSerializer(appts, many=True).data)

    # POST — misma lógica que create_appointment
    serializer = AppointmentCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    appt = serializer.save()
    return Response(AppointmentSerializer(appt).data, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([AllowAny])
def dentist_day_appointments(request):
    """
    GET /api/internal/agenda/?dentist_id=1&date=2026-02-20
    Devuelve todas las citas de un dentista en un día concreto.
    """
    dentist_id = request.query_params.get('dentist_id')
    raw_date   = request.query_params.get('date')

    if not dentist_id or not raw_date:
        return Response({'error': 'dentist_id y date son requeridos.'}, status=400)

    try:
        date = datetime.date.fromisoformat(raw_date)
    except ValueError:
        return Response({'error': 'Formato de fecha inválido. Usa YYYY-MM-DD.'}, status=400)

    dentist = get_object_or_404(Dentist, pk=dentist_id, is_active=True)
    appts = (
        Appointment.objects
        .filter(dentist=dentist, date=date)
        .exclude(status='cancelled')
        .select_related('patient', 'dentist', 'service')
        .order_by('start_time')
    )
    return Response({
        'dentist':      DentistListSerializer(dentist).data,
        'date':         date,
        'appointments': AppointmentSerializer(appts, many=True).data,
    })