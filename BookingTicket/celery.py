import eventlet
eventlet.monkey_patch()  # ← THÊM DÒNG NÀY Ở ĐẦU

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BookingTicket.settings')

app = Celery('BookingTicket')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Schedule cho task hủy vé hết hạn
app.conf.beat_schedule = {
    'huy-ve-het-han-moi-phut': {
        'task': 'booking.tasks.huy_ve_het_han',
        'schedule': crontab(minute='*/1'),  # Chạy mỗi 1 phút
    },
}

app.conf.timezone = 'UTC'