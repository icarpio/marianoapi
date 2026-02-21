from django.contrib import admin
from django.utils.html import format_html

from .models import Appointment, BlockedDate, Dentist, Patient, Service, WorkSchedule


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display  = ['name', 'duration_minutes', 'slots_required', 'price', 'color_dot', 'is_active']
    list_filter   = ['is_active']
    search_fields = ['name']

    @admin.display(description='Color')
    def color_dot(self, obj):
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;border-radius:50%;background:{};"></span>',
            obj.color
        )


class WorkScheduleInline(admin.TabularInline):
    model   = WorkSchedule
    extra   = 0
    fields  = ['day_of_week', 'start_time', 'end_time', 'start_time_2', 'end_time_2', 'is_active']


@admin.register(Dentist)
class DentistAdmin(admin.ModelAdmin):
    list_display     = ['get_full_name', 'specialty', 'email', 'is_active']
    list_filter      = ['is_active', 'services']
    search_fields    = ['first_name', 'last_name', 'email']
    filter_horizontal = ['services']
    inlines          = [WorkScheduleInline]

    @admin.display(description='Nombre', ordering='last_name')
    def get_full_name(self, obj):
        return obj.get_full_name()


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'email', 'phone', 'created_at']
    search_fields = ['first_name', 'last_name', 'email']
    readonly_fields = ['created_at']


STATUS_COLORS = {
    'pending':     '#f59e0b',
    'confirmed':   '#10b981',
    'in_progress': '#3b82f6',
    'completed':   '#6b7280',
    'cancelled':   '#ef4444',
    'no_show':     '#8b5cf6',
}


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display    = ['id', 'patient', 'service', 'dentist', 'date', 'start_time', 'end_time', 'status_badge']
    list_filter     = ['status', 'date', 'dentist', 'service']
    search_fields   = ['patient__first_name', 'patient__last_name', 'patient__email']
    date_hierarchy  = 'date'
    readonly_fields = ['end_time', 'confirmation_token', 'created_at', 'updated_at']

    @admin.display(description='Estado')
    def status_badge(self, obj):
        color = STATUS_COLORS.get(obj.status, '#999')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:4px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )

    actions = ['mark_confirmed', 'mark_cancelled']

    @admin.action(description='✅ Confirmar citas seleccionadas')
    def mark_confirmed(self, request, queryset):
        n = queryset.filter(status='pending').update(status='confirmed')
        self.message_user(request, f'{n} cita(s) confirmada(s).')

    @admin.action(description='❌ Cancelar citas seleccionadas')
    def mark_cancelled(self, request, queryset):
        n = queryset.exclude(status__in=['completed', 'cancelled']).update(status='cancelled')
        self.message_user(request, f'{n} cita(s) cancelada(s).')


@admin.register(BlockedDate)
class BlockedDateAdmin(admin.ModelAdmin):
    list_display = ['date', 'dentist', 'reason']
    list_filter  = ['dentist']


admin.site.site_header = '🦷 Mariano Api Admin'
admin.site.site_title  = 'Dental Admin'
admin.site.index_title = 'Panel de Control'
