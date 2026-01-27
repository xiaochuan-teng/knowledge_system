#!/bin/bash

# 停止现有进程
pkill gunicorn

# 等待进程停止
sleep 2

# 启动 Gunicorn
cd /data/knowledge_system
/usr/local/python3.13/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8080 \
    --access-logfile /data/knowledge_system/logs/gunicorn_access.log \
    --error-logfile /data/knowledge_system/logs/gunicorn_error.log \
    --log-level info \
    --pid /var/run/gunicorn/knowledge_system.pid \
    --daemon \
    knowledge_system.wsgi:application

echo "Server started with PID: $(cat /var/run/gunicorn/knowledge_system.pid)"
