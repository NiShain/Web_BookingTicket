from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid

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
