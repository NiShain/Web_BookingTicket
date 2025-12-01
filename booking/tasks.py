from celery import shared_task
from django.utils import timezone
from .models import Ve

@shared_task
def huy_ve_het_han():
    """
    Task chạy định kỳ mỗi 1 phút để hủy vé hết hạn
    """
    now = timezone.now()
    ve_het_han = Ve.objects.filter(
        trang_thai='CHO_THANH_TOAN',
        han_thanh_toan__lt=now
    )
    
    count = 0
    for ve in ve_het_han:
        if ve.huy_ve_het_han():
            count += 1
    
    return f"Đã hủy {count} vé hết hạn"