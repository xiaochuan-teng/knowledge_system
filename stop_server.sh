#!/bin/bash

if [ -f /var/run/gunicorn/knowledge_system.pid ]; then
    kill $(cat /var/run/gunicorn/knowledge_system.pid)
    rm /var/run/gunicorn/knowledge_system.pid
    echo "Server stopped"
else
    echo "PID file not found, killing all gunicorn processes"
    pkill gunicorn
fi
