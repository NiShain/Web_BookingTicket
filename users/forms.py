from django import forms
from .models import Account, KhachHang, OTPRegistration

class RegistrationForm(forms.Form):
    # Các trường cho model KhachHang
    ten = forms.CharField(max_length=100, label="Họ và tên")
    cccd = forms.CharField(max_length=20, label="Căn cước công dân", required=False)
    so_dien_thoai = forms.CharField(max_length=15, label="Số điện thoại")

    # Các trường cho model Account
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, label="Mật khẩu")
    password2 = forms.CharField(label="Xác nhận mật khẩu", widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Account.objects.filter(email=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng.")
        if OTPRegistration.objects.filter(email=email, is_verified=False).exists():
            raise forms.ValidationError("Email này đang trong quá trình xác thực OTP.")
        return email

    def clean_so_dien_thoai(self):
        so_dien_thoai = self.cleaned_data.get('so_dien_thoai')
        if KhachHang.objects.filter(so_dien_thoai=so_dien_thoai).exists():
            raise forms.ValidationError("Số điện thoại này đã được sử dụng.")
        return so_dien_thoai

    def clean_cccd(self):
        cccd = self.cleaned_data.get('cccd')
        if cccd and KhachHang.objects.filter(cccd=cccd).exists():
            raise forms.ValidationError("Số CCCD này đã tồn tại.")
        return cccd

    def clean_password2(self):
        cd = self.cleaned_data
        if cd.get('password') != cd.get('password2'):
            raise forms.ValidationError("Mật khẩu không khớp.")
        return cd.get('password2')


class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        label="Mã OTP",
        widget=forms.TextInput(attrs={
            'placeholder': 'Nhập 6 chữ số',
            'class': 'form-control otp-input',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}'
        })
    )
    
    def clean_otp_code(self):
        otp_code = self.cleaned_data.get('otp_code')
        if not otp_code.isdigit():
            raise forms.ValidationError("Mã OTP phải là 6 chữ số.")
        return otp_code


class CustomPasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label="Email", max_length=254)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not Account.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError("Không tìm thấy tài khoản nào với email này.")
        return email