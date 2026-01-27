#!/bin/bash
# 清理30天前的日志
find /data/knowledge_system/logs -name "*.log" -mtime +30 -delete
echo "$(date): Logs cleaned" >> /data/knowledge_system/logs/clean.log
