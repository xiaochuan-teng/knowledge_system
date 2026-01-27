# kb/tasks.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.core.management import call_command
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
scheduler = None

def update_vm_status_job():
    """定时任务函数"""
    try:
        print(f"{datetime.now()}: 执行虚拟机状态更新")
        call_command('update_vm_status')
    except Exception as e:
        logger.error(f"定时更新虚拟机状态失败: {e}")

def start_vm_status_scheduler():
    """启动定时任务调度器"""
    global scheduler
    
    if scheduler and scheduler.running:
        return
    
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        update_vm_status_job,
        trigger=IntervalTrigger(minutes=30),  # 每30分钟执行一次
        id='update_vm_status',
        replace_existing=True
    )
    
    try:
        scheduler.start()
        logger.info("APScheduler 已启动，虚拟机状态将每5分钟更新一次")
    except (KeyboardInterrupt, SystemExit):
        if scheduler:
            scheduler.shutdown()

