# kb/apps.py
from django.apps import AppConfig
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class KbConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'kb'
    
    def ready(self):
        """应用启动时启动定时任务"""
        if settings.DEBUG:
            return
            
        try:
            from .tasks import start_vm_status_scheduler
            start_vm_status_scheduler()
            logger.info("虚拟机状态定时任务已启动")
        except Exception as e:
            logger.error(f"启动定时任务失败: {e}")
