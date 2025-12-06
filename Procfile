web: python manage.py migrate && gunicorn extractor_project.wsgi --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120

