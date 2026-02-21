web: gunicorn  marianoapi.wsgi:application
celery -A marianoapi worker --loglevel=info
celery -A marianoapi beat --loglevel=info