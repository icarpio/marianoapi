from django.urls import path
from . import views

urlpatterns = [
    # Servicios
    path('services/',          views.ServiceListView.as_view(),   name='service-list'),
    path('services/<int:pk>/', views.ServiceDetailView.as_view(), name='service-detail'),

    # Dentistas
    path('dentists/',          views.DentistListView.as_view(),   name='dentist-list'),
    path('dentists/<int:pk>/', views.DentistDetailView.as_view(), name='dentist-detail'),

    # Disponibilidad
    path('availability/slots/',    views.available_slots,       name='slots'),
    path('availability/calendar/', views.calendar_month_view,   name='calendar'),

    # Citas
    path('appointments/',                    views.create_appointment,   name='create-appointment'),
    path('appointments/patient/',            views.patient_appointments, name='patient-appointments'),
    path('appointments/<str:token>/',        views.appointment_by_token, name='appointment-detail'),
    path('appointments/<str:token>/cancel/', views.cancel_appointment,   name='cancel-appointment'),
    path('appointments/<str:token>/update/', views.update_appointment, name='appointment-update'),
    # Dentist Follow_up
    path('internal/book/', views.dentist_book, name='dentist-book'),
    path('internal/agenda/', views.dentist_day_appointments, name='dentist-agenda'),
]
