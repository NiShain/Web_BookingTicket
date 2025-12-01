import random
import string
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from users.models import KhachHang
from datetime import timedelta

class Tuyen(models.Model):
    diem_di = models.CharField(max_length=100, verbose_name="Điểm đi")
    diem_den = models.CharField(max_length=100, verbose_name="Điểm đến")
    khoang_cach = models.PositiveIntegerField(blank=True, null=True, verbose_name="Khoảng cách (km)")

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
    bien_so = models.CharField(max_length=20, unique=True, verbose_name="Biển số")
    loai_xe = models.CharField(max_length=50, verbose_name="Loại xe")
    so_ghe = models.PositiveIntegerField(verbose_name="Số ghế")

    def clean(self):
        if self.so_ghe <= 0:
            raise ValidationError("Số ghế phải lớn hơn 0.")

    def __str__(self):
        return f"{self.loai_xe} - {self.bien_so}"


class Chuyen(models.Model):
    tuyen = models.ForeignKey(Tuyen, on_delete=models.CASCADE, related_name="chuyens", verbose_name="Tuyến")
    xe = models.ForeignKey(Xe, on_delete=models.CASCADE, related_name="chuyens", verbose_name="Xe")
    ngay_gio_khoi_hanh = models.DateTimeField(verbose_name="Ngày giờ khởi hành")
    ngay_gio_den = models.DateTimeField(blank=True, null=True, verbose_name="Ngày giờ đến")
    tong_so_ve = models.PositiveIntegerField(verbose_name="Tổng số vé")
    gia_ve = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Giá vé")

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
        ('CHO_THANH_TOAN', 'Chờ thanh toán'),
        ('DA_THANH_TOAN', 'Đã thanh toán'),
        ('DA_HUY', 'Đã hủy'),
        ('HET_HAN', 'Hết hạn'),  # THÊM TRẠNG THÁI MỚI
    ]
    
    chuyen = models.ForeignKey(Chuyen, on_delete=models.CASCADE, related_name='ves')
    khach = models.ForeignKey('users.KhachHang', on_delete=models.CASCADE, related_name='ves')
    so_luong = models.IntegerField(default=1, verbose_name="Số lượng vé")
    vi_tri_ghe = models.JSONField(default=list, verbose_name="Vị trí ghế")
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default='CHO_THANH_TOAN')
    ngay_dat = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đặt")
    han_thanh_toan = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Hạn thanh toán"
    )
    
    class Meta:
        verbose_name = "Vé"
        verbose_name_plural = "Vé"
    
    def __str__(self):
        return f"Vé {self.id} - {self.khach.ten} - {self.chuyen}"
    
    def save(self, *args, **kwargs):
        # Tự động set hạn thanh toán = 10 phút sau khi đặt
        if not self.han_thanh_toan and self.trang_thai == 'CHO_THANH_TOAN':
            self.han_thanh_toan = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def kiem_tra_het_han(self):
        """Kiểm tra vé có hết hạn không"""
        if self.trang_thai == 'CHO_THANH_TOAN' and self.han_thanh_toan:
            if timezone.now() > self.han_thanh_toan:
                return True
        return False
    
    def huy_ve_het_han(self):
        """Hủy vé hết hạn và hoàn lại ghế"""
        if self.kiem_tra_het_han():
            # Hoàn lại số vé
            self.chuyen.tong_so_ve += self.so_luong
            self.chuyen.save()
            
            # Đổi trạng thái
            self.trang_thai = 'HET_HAN'
            self.save()
            return True
        return False

class ThanhToan(models.Model):
    TRANG_THAI_CHOICES = [
        ("THANH_CONG", "Thành công"),
        ("THAT_BAI", "Thất bại"),
        ("CHO_XU_LY", "Chờ xử lý"),
        ("CHO_THANH_TOAN", "Chờ thanh toán"), # Thêm trạng thái này nếu chưa có
    ]

    ve = models.OneToOneField(Ve, on_delete=models.CASCADE, related_name="thanh_toan", verbose_name="Vé")
    phuong_thuc = models.CharField(max_length=50, verbose_name="Phương thức")
    trang_thai = models.CharField(max_length=20, choices=TRANG_THAI_CHOICES, default="CHO_XU_LY", verbose_name="Trạng thái")
    ngay_gio = models.DateTimeField(auto_now_add=True, verbose_name="Ngày giờ")
    ma_giao_dich = models.CharField(max_length=100, unique=True, verbose_name="Mã giao dịch")
    so_tien = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Số tiền")

    def __str__(self):
        return f"Thanh toán {self.ma_giao_dich} - {self.trang_thai}"

    class Meta:
        verbose_name = "Thanh toán"
        verbose_name_plural = "Thanh toán"

class Voucher(models.Model):
    LOAI_GIAM_GIA_CHOICES = [
        ('PHAN_TRAM', 'Phần trăm'),
        ('SO_TIEN', 'Số tiền cố định'),
    ]
    
    ma_voucher = models.CharField(max_length=20, unique=True, verbose_name="Mã voucher")
    ten_voucher = models.CharField(max_length=200, verbose_name="Tên voucher")
    mo_ta = models.TextField(blank=True, verbose_name="Mô tả")
    
    loai_giam_gia = models.CharField(max_length=20, choices=LOAI_GIAM_GIA_CHOICES, default='PHAN_TRAM')
    gia_tri_giam = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Giá trị giảm")
    
    giam_toi_da = models.DecimalField(max_digits=10, decimal_places=0, blank=True, null=True, verbose_name="Giảm tối đa (đ)")
    gia_tri_don_toi_thieu = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Giá trị đơn tối thiểu")
    
    ngay_bat_dau = models.DateTimeField(verbose_name="Ngày bắt đầu")
    ngay_ket_thuc = models.DateTimeField(verbose_name="Ngày kết thúc")
    
    so_luong = models.IntegerField(default=100, verbose_name="Số lượng voucher")
    da_su_dung = models.IntegerField(default=0, verbose_name="Đã sử dụng")
    so_lan_su_dung_toi_da_moi_user = models.IntegerField(default=1, verbose_name="Số lần dùng/user")
    
    khach_hang_duoc_su_dung = models.ManyToManyField(
        KhachHang, 
        blank=True, 
        related_name='vouchers_nhan', 
        verbose_name="Khách hàng được sử dụng"
    )
    
    trang_thai = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    ngay_tao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Voucher"
        verbose_name_plural = "Vouchers"
        ordering = ['-ngay_tao']
    
    def __str__(self):
        return f"{self.ma_voucher} - {self.ten_voucher}"
    
    def clean(self):
        """Validate dữ liệu voucher"""
        # Kiểm tra ngày bắt đầu và ngày kết thúc không được để trống
        if not self.ngay_bat_dau:
            raise ValidationError({'ngay_bat_dau': "Ngày bắt đầu không được để trống."})
        
        if not self.ngay_ket_thuc:
            raise ValidationError({'ngay_ket_thuc': "Ngày kết thúc không được để trống."})
        
        # Kiểm tra ngày bắt đầu < ngày kết thúc
        if self.ngay_bat_dau >= self.ngay_ket_thuc:
            raise ValidationError({'ngay_ket_thuc': "Ngày kết thúc phải sau ngày bắt đầu."})
        
        # Kiểm tra giá trị giảm hợp lệ
        if self.gia_tri_giam is not None and self.gia_tri_giam <= 0:
            raise ValidationError({'gia_tri_giam': "Giá trị giảm phải lớn hơn 0."})
        
        if self.loai_giam_gia == 'PHAN_TRAM' and self.gia_tri_giam and self.gia_tri_giam > 100:
            raise ValidationError({'gia_tri_giam': "Giảm giá theo phần trăm không được vượt quá 100%."})
        
        # Kiểm tra số lượng
        if self.so_luong is not None and self.so_luong <= 0:
            raise ValidationError({'so_luong': "Số lượng voucher phải lớn hơn 0."})
    
    @staticmethod
    def tao_ma_voucher(length=8, prefix="FUTA"):
        """Tạo mã voucher ngẫu nhiên
        VD: FUTA12AB34CD
        """
        characters = string.ascii_uppercase + string.digits
        random_part = ''.join(random.choices(characters, k=length))
        return f"{prefix}{random_part}"
    
    def con_hieu_luc(self):
        """Kiểm tra voucher còn hiệu lực không"""
        now = timezone.now()
        
        # Debug: In ra để kiểm tra
        print(f"Voucher: {self.ma_voucher}")
        print(f"Trạng thái: {self.trang_thai}")
        print(f"Thời gian hiện tại: {now}")
        print(f"Ngày bắt đầu: {self.ngay_bat_dau}")
        print(f"Ngày kết thúc: {self.ngay_ket_thuc}")
        print(f"Đã dùng/Tổng: {self.da_su_dung}/{self.so_luong}")
        
        return (
            self.trang_thai and 
            self.ngay_bat_dau <= now <= self.ngay_ket_thuc and 
            self.da_su_dung < self.so_luong
        )
    
    def user_da_dung_bao_nhieu_lan(self, khach_hang):
        """Kiểm tra user đã dùng voucher này bao nhiêu lần"""
        return self.lich_su_su_dung.filter(khach_hang=khach_hang).count()
    
    def user_con_duoc_dung(self, khach_hang):
        """Kiểm tra user còn được dùng voucher không"""
        return self.user_da_dung_bao_nhieu_lan(khach_hang) < self.so_lan_su_dung_toi_da_moi_user
    
    def tinh_giam_gia(self, tong_tien):
        """Tính số tiền được giảm"""
        if not self.con_hieu_luc():
            return Decimal('0')
        
        if tong_tien < self.gia_tri_don_toi_thieu:
            return Decimal('0')
        
        if self.loai_giam_gia == 'PHAN_TRAM':
            giam = tong_tien * (self.gia_tri_giam / 100)
            if self.giam_toi_da:
                giam = min(giam, self.giam_toi_da)
            return giam.quantize(Decimal('1'))
        else:  # SO_TIEN
            return min(self.gia_tri_giam, tong_tien)


class VoucherSuDung(models.Model):
    """Lịch sử sử dụng voucher"""
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='lich_su_su_dung')
    khach_hang = models.ForeignKey(KhachHang, on_delete=models.CASCADE)
    ve = models.ForeignKey('Ve', on_delete=models.CASCADE, related_name='voucher_da_dung')
    so_tien_giam = models.DecimalField(max_digits=10, decimal_places=0)
    ngay_su_dung = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.voucher.ma_voucher} - {self.khach_hang.ten} - {self.so_tien_giam}đ"
    
    class Meta:
        verbose_name = "Lịch sử voucher"
        verbose_name_plural = "Lịch sử vouchers"
        ordering = ['-ngay_su_dung']
        # unique_together = ('voucher', 'khach_hang')  # Bỏ comment nếu muốn mỗi user chỉ dùng 1 lần