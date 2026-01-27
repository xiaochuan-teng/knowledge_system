nohup gunicorn --workers 3 --bind 0.0.0.0:8080 knowledge_system.wsgi:application > gunicorn.log 2>&1 &
