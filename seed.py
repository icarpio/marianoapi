"""
Datos iniciales de la clinica dental.
Ejecutar con: python manage.py shell < seed.py

Horario de la clinica:
  - Invierno (oct-mar): 10:00-14:00 y 16:00-20:00  (horario partido)
  - Verano  (abr-sep):  08:00-15:00                 (franja unica)

El seed carga el horario ACTUAL segun el mes del sistema.
Puedes cambiar manualmente desde el admin (/admin/) cuando cambie la temporada.
"""
import os, django, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from appointments.models import Service, Dentist, WorkSchedule

def t(hhmm: str) -> datetime.time:
    h, m = hhmm.split(':')
    return datetime.time(int(h), int(m))

print("Cargando datos iniciales...")

# ── Detectar temporada actual ─────────────────────────────────────────────────
mes_actual = datetime.date.today().month
es_verano  = 7 <= mes_actual <= 9   # abril-septiembre

if es_verano:
    print("  Temporada: VERANO (08:00-15:00)")
    franja_l_v = dict(start_time=t('08:00'), end_time=t('15:00'),
                      start_time_2=None, end_time_2=None)
else:
    print("  Temporada: INVIERNO (10:00-14:00 / 16:00-20:00)")
    franja_l_v = dict(start_time=t('10:00'), end_time=t('14:00'),
                      start_time_2=t('16:00'), end_time_2=t('20:00'))

# ── Servicios ─────────────────────────────────────────────────────────────────
SERVICES = [
    dict(name="Limpieza Dental",       description="Limpieza profunda con ultrasonido y pulido.",      duration_minutes=60,  price=80,    color="#2d9e94"),
    dict(name="Consulta / Revision",   description="Diagnostico completo y plan de tratamiento.",       duration_minutes=30,  price=40,    color="#6366f1"),
    dict(name="Blanqueamiento",        description="Blanqueamiento dental con luz LED.",                 duration_minutes=90,  price=250,   color="#f59e0b"),
    dict(name="Extraccion Simple",     description="Extraccion de pieza dental sin complicaciones.",    duration_minutes=45,  price=70,    color="#ef4444"),
    dict(name="Endodoncia",            description="Tratamiento de conducto radicular.",                 duration_minutes=120, price=450,   color="#8b5cf6"),
    dict(name="Urgencia Dental",       description="Atencion inmediata de emergencias dentales.",       duration_minutes=30,  price=60,    color="#f97316"),
    dict(name="Ortodoncia - Consulta", description="Evaluacion inicial y plan de ortodoncia.",          duration_minutes=60,  price=50,    color="#14b8a6"),
]

svc_map = {}
for s in SERVICES:
    obj, created = Service.objects.update_or_create(name=s['name'], defaults=s)
    svc_map[s['name']] = obj
    print(f"  {'[+]' if created else '[=]'} {obj}")

# ── Dentistas ─────────────────────────────────────────────────────────────────
# dias: 0=lun, 1=mar, 2=mie, 3=jue, 4=vie, 5=sab
DENTISTS = [
    {
        'first_name': 'Maria',  'last_name': 'Gonzalez',
        'email':      'mgonzalez@seattledental.com',
        'specialty':  'Odontologia General',
        'bio':        'Mas de 10 anos de experiencia en odontologia general y preventiva.',
        'services':   ['Limpieza Dental', 'Consulta / Revision', 'Extraccion Simple', 'Urgencia Dental'],
        'days':       [0, 1, 2, 3, 4],   # lunes a viernes
    },
    {
        'first_name': 'Carlos', 'last_name': 'Ramirez',
        'email':      'cramirez@seattledental.com',
        'specialty':  'Endodoncia',
        'bio':        'Especialista en tratamientos de conducto con tecnicas minimamente invasivas.',
        'services':   ['Consulta / Revision', 'Endodoncia', 'Extraccion Simple', 'Urgencia Dental'],
        'days':       [0, 1, 2, 4],      # lun mar mie vie (libre jueves)
    },
    {
        'first_name': 'Sofia',  'last_name': 'Hernandez',
        'email':      'shernandez@seattledental.com',
        'specialty':  'Estetica Dental',
        'bio':        'Experta en blanqueamiento, carillas y estetica dental avanzada.',
        'services':   ['Limpieza Dental', 'Blanqueamiento', 'Consulta / Revision', 'Ortodoncia - Consulta'],
        'days':       [1, 2, 3, 4],      # mar mie jue vie (libre lunes)
    },
]

for d in DENTISTS:
    dentist, created = Dentist.objects.update_or_create(
        email=d['email'],
        defaults={k: v for k, v in d.items() if k not in ('services', 'days', 'email')}
    )
    dentist.services.set([svc_map[s] for s in d['services'] if s in svc_map])

    for day in d['days']:
        WorkSchedule.objects.update_or_create(
            dentist=dentist, day_of_week=day,
            defaults={**franja_l_v, 'is_active': True}
        )
    print(f"  {'[+]' if created else '[=]'} {dentist}")

print()
print("Listo.")
print()
print("Horarios cargados (lunes a viernes):")
print("  Invierno (oct-mar): 10:00-14:00 / 16:00-20:00")
print("  Verano   (abr-sep): 08:00-15:00")
print()
print("Para cambiar de temporada manualmente:")
print("  Admin -> Horarios de trabajo -> editar franjas")
print("  O vuelve a ejecutar este script (detecta el mes actual automaticamente)")
print()
print("Siguiente paso:")
print("  python manage.py createsuperuser")
print("  python manage.py runserver")
