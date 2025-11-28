from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid
import random
import string

# -------------------------
# 0. Account
# -------------------------
class Account(AbstractUser):
    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


# -------------------------
# 0.1. Email Verification
# -------------------------
class EmailVerification(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="email_verifications")
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.conf import settings
            expire_hours = getattr(settings, 'EMAIL_VERIFICATION_EXPIRE_HOURS', 24)
            self.expires_at = timezone.now() + timezone.timedelta(hours=expire_hours)
        if self.expires_at and self.created_at:
            if self.expires_at <= self.created_at:
                raise ValidationError("Thời gian hết hạn phải sau thời gian tạo.")
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Email verification for {self.account.username}"


# -------------------------
# 0.2. Password Reset
# -------------------------
class PasswordReset(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="password_resets")
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.conf import settings
            expire_hours = getattr(settings, 'PASSWORD_RESET_EXPIRE_HOURS', 1)
            self.expires_at = timezone.now() + timezone.timedelta(hours=expire_hours)
        if self.expires_at and self.created_at:
            if self.expires_at <= self.created_at:
                raise ValidationError("Thời gian hết hạn phải sau thời gian tạo.")
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Password reset for {self.account.username}"


# -------------------------
# 0.3. Password Change Verification (for authenticated users)
# -------------------------
class PasswordChangeVerification(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="password_change_verifications")
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.conf import settings
            expire_minutes = getattr(settings, 'PASSWORD_CHANGE_EXPIRE_MINUTES', 30)
            self.expires_at = timezone.now() + timezone.timedelta(minutes=expire_minutes)
        if self.expires_at and self.created_at:
            if self.expires_at <= self.created_at:
                raise ValidationError("Thời gian hết hạn phải sau thời gian tạo.")
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Password change verification for {self.account.username}"


# -------------------------
# 0.4. OTP Registration (for new account registration)
# -------------------------
class OTPRegistration(models.Model):
    email = models.EmailField(unique=True, verbose_name="Email đăng ký")
    ten = models.CharField(max_length=100, verbose_name="Họ và tên")
    so_dien_thoai = models.CharField(max_length=15, verbose_name="Số điện thoại")
    cccd = models.CharField(max_length=20, blank=True, null=True, verbose_name="CCCD")
    password_hash = models.CharField(max_length=255, verbose_name="Mật khẩu đã hash")
    otp_code = models.CharField(max_length=6, verbose_name="Mã OTP")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    attempt_count = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.conf import settings
            expire_minutes = getattr(settings, 'OTP_EXPIRE_MINUTES', 10)
            self.expires_at = timezone.now() + timezone.timedelta(minutes=expire_minutes)
        if not self.otp_code:
            self.otp_code = ''.join(random.choices(string.digits, k=6))
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def can_attempt(self):
        """Kiểm tra có thể thử OTP không (tối đa 5 lần)"""
        return self.attempt_count < 5
    
    def verify_otp(self, otp_input):
        """Xác thực mã OTP"""
        if self.is_expired():
            return False, "Mã OTP đã hết hạn"
        
        if not self.can_attempt():
            return False, "Bạn đã nhập sai quá nhiều lần"
        
        if self.otp_code == otp_input:
            self.is_verified = True
            self.save()
            return True, "Xác thực thành công"
        else:
            self.attempt_count += 1
            self.save()
            return False, f"Mã OTP không đúng. Còn {5 - self.attempt_count} lần thử"
    
    def regenerate_otp(self):
        """Tạo lại mã OTP mới"""
        from django.conf import settings
        expire_minutes = getattr(settings, 'OTP_EXPIRE_MINUTES', 10)
        self.otp_code = ''.join(random.choices(string.digits, k=6))
        self.expires_at = timezone.now() + timezone.timedelta(minutes=expire_minutes)
        self.attempt_count = 0
        self.is_verified = False
        self.save()
    
    def __str__(self):
        return f"OTP Registration for {self.email}"

    class Meta:
        verbose_name = "OTP Registration"
        verbose_name_plural = "OTP Registrations"


# -------------------------
# 1. Khách hàng
# -------------------------
class KhachHang(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name="khachhang", null=True, blank=True)
    ten = models.CharField(max_length=100)
    so_dien_thoai = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    cccd = models.CharField(max_length=20, blank=True, null=True, unique=True)
    ngay_sinh = models.DateField(blank=True, null=True)
    dia_chi = models.TextField(blank=True, null=True)

    def clean(self):
        if self.ngay_sinh and self.ngay_sinh > timezone.now().date():
            raise ValidationError("Ngày sinh không được lớn hơn ngày hiện tại.")

    def __str__(self):
        return f"{self.ten} ({self.so_dien_thoai})"

    class Meta:
        verbose_name = "Khách hàng"
        verbose_name_plural = "Khách hàng"
