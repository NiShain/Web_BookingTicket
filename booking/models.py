from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from users.models import KhachHang  # import từ app users

class Tuyen(models.Model):
    diem_di = models.CharField(max_length=100)
    diem_den = models.CharField(max_length=100)
    khoang_cach = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        unique_together = ("diem_di", "diem_den")
        verbose_name = "Tuyến"
        verbose_name_plural = "Tuyến"

    def clean(self):
        if self.diem_di == self.diem_den:
            raise ValidationError("Điểm đi và điểm đến không được trùng nhau.")
        if self.khoang_cach is not None and self.khoang_cach <= 0:
            raise ValidationError("Khoảng cách phải lớn hơn 0.")

    def __str__(self):
        return f"{self.diem_di} → {self.diem_den}"


class Xe(models.Model):
    bien_so = models.CharField(max_length=20, unique=True)
    loai_xe = models.CharField(max_length=50)
    so_ghe = models.PositiveIntegerField()

    def clean(self):
        if self.so_ghe <= 0:
            raise ValidationError("Số ghế phải lớn hơn 0.")

    def __str__(self):
        return f"{self.loai_xe} - {self.bien_so}"


class Chuyen(models.Model):
    tuyen = models.ForeignKey(Tuyen, on_delete=models.CASCADE, related_name="chuyens")
    xe = models.ForeignKey(Xe, on_delete=models.CASCADE, related_name="chuyens")
    ngay_gio_khoi_hanh = models.DateTimeField()
    ngay_gio_den = models.DateTimeField(blank=True, null=True)
    tong_so_ve = models.PositiveIntegerField()
    gia_ve = models.DecimalField(max_digits=10, decimal_places=2)

    def clean(self):
        now = timezone.now()
        if self.ngay_gio_khoi_hanh < now:
            raise ValidationError("Ngày giờ khởi hành không được sớm hơn hiện tại.")
        if self.ngay_gio_den and self.ngay_gio_den < self.ngay_gio_khoi_hanh:
            raise ValidationError("Ngày giờ đến phải sau hoặc bằng ngày giờ khởi hành.")
        if self.tong_so_ve <= 0:
            raise ValidationError("Tổng số vé phải lớn hơn 0.")
        if self.gia_ve <= 0:
            raise ValidationError("Giá vé phải lớn hơn 0.")
        if self.xe and self.tong_so_ve > self.xe.so_ghe:
            raise ValidationError(f"Tổng số vé ({self.tong_so_ve}) vượt quá số ghế của xe ({self.xe.so_ghe}).")

    @property
    def so_ve_con_lai(self):
        da_dat = sum(ve.so_luong for ve in self.ves.filter(trang_thai="DA_THANH_TOAN"))
        return self.tong_so_ve - da_dat

    def __str__(self):
        return f"Chuyến {self.tuyen} - {self.ngay_gio_khoi_hanh.strftime('%d/%m/%Y %H:%M')}"


class Ve(models.Model):
    TRANG_THAI_CHOICES = [
        ("CHO_THANH_TOAN", "Chờ thanh toán"),
        ("DA_THANH_TOAN", "Đã thanh toán"),
        ("DA_HUY", "Đã hủy"),
    ]

    chuyen = models.ForeignKey(Chuyen, on_delete=models.CASCADE, related_name="ves")
    khach = models.ForeignKey(KhachHang, on_delete=models.CASCADE, related_name="ves")
    so_luong = models.PositiveIntegerField()
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default="CHO_THANH_TOAN")
    thoi_gian_dat = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.so_luong <= 0:
            raise ValidationError("Số lượng vé phải lớn hơn 0.")
        if self.so_luong > self.chuyen.so_ve_con_lai:
            raise ValidationError("Số lượng vé vượt quá số vé còn lại của chuyến.")

    def __str__(self):
        return f"Vé {self.id} - {self.khach.ten}"

    class Meta:
        verbose_name = "Vé"
        verbose_name_plural = "Vé"


# -------------------------
# 6. Thanh toán
# -------------------------
class ThanhToan(models.Model):
    TRANG_THAI_CHOICES = [
        ("THANH_CONG", "Thành công"),
        ("THAT_BAI", "Thất bại"),
        ("CHO_XU_LY", "Chờ xử lý"),
    ]

    ve = models.OneToOneField(Ve, on_delete=models.CASCADE, related_name="thanh_toan")
    phuong_thuc = models.CharField(max_length=50)
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default="CHO_XU_LY")
    ngay_gio = models.DateTimeField(auto_now_add=True)
    ma_giao_dich = models.CharField(max_length=100, unique=True)

    @property
    def so_tien(self):
        return self.ve.so_luong * self.ve.chuyen.gia_ve

    def __str__(self):
        return f"Thanh toán {self.ma_giao_dich} - {self.trang_thai}"

    class Meta:
        verbose_name = "Thanh toán"
        verbose_name_plural = "Thanh toán"
