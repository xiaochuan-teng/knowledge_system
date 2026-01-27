# knowledge_system/__init__.py
import pymysql
#from __future__ import absolute_import, unicode_literals
# 这确保 Celery 应用在 Django 启动时就被加载
#from .celery import app as celery_app

#__all__ = ('celery_app',)

pymysql.install_as_MySQLdb()

print("pymysql已配置为MySQL驱动")
