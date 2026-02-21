from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Establece el módulo de configuración para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'virtual_pet.settings')

app = Celery('virtual_pet')

# Configuración de Celery para usar los ajustes de Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Configuración personalizada de Celery
app.conf.update(
    broker_url=os.environ.get('REDIS_URL'),  # URL del broker Redis, asegurate que esté bien configurado
    broker_transport_options={
        'visibility_timeout': 3600,  # Tiempo en segundos para mantener la tarea visible
        'socket_timeout': 120,  # Reduces el timeout a 1 minuto (ajústalo si es necesario)
        'socket_connect_timeout': 120,  # Timeout de la conexión a Redis (1 minuto)
    },
    broker_connection_retry_on_startup=True,  # Intentar reconectar al iniciar
    task_acks_late=True,  # Para que Celery confirme la tarea después de ejecutarla
    worker_prefetch_multiplier=1,  # Número de tareas que un worker obtiene antes de ser procesada
    broker_heartbeat=10,  # Enviar "latidos" de vida al broker cada 10 segundos
    broker_connection_timeout=10,  # Timeout de conexión al broker (10 segundos)
    worker_max_tasks_per_child=100,  # Reinicia el worker después de procesar 100 tareas (para evitar problemas de memoria)
    worker_cancel_long_running_tasks_on_connection_loss=True,  # No cancelar tareas largas si se pierde la conexión
)

# Configuración de las tareas programadas
app.conf.beat_schedule = {
    'decrease_pet_values': {
        'task': 'pets.tasks.decrease_pet_values',
        'schedule': crontab(minute='*/5'),  # Ejecución cada 10 minutos
        'args': (),  # Argumentos para la tarea
    },
    'update_pet_state': {
        'task': 'pets.tasks.update_pet_state',
        'schedule': crontab(minute='*'),  # Ejecutar cada minuto
        'args': (),  # Argumentos para la tarea
    },
}

# Habilitar la autodetección de tareas
app.autodiscover_tasks()

#worker: celery -A virtual_pet worker --loglevel=info --pool=threads --concurrency=2
#beat: celery -A virtual_pet beat --loglevel=info
# purge - celery -A virtual_pet purge
#cada 30 minutos - crontab(minute='*/30')
#cada dos horas - crontab(minute=0, hour='*/2')

#verificar tareas activas -  celery -A virtual_pet inspect active_queues
#verificar tareas automaticas - celery -A virtual_pet inspect registered



