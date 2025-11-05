# users/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.decorators import login_required, user_passes_test
from datetime import datetime
import time # Import time để quản lý session

# Import các form và model của bạn
from .forms import RegistrationForm, CustomPasswordResetRequestForm
from .models import Account, KhachHang, EmailVerification, PasswordReset, Ve

# ===============================================
# === HELPER: CÁC HÀM GỬI EMAIL (TỪ AUTH_VIEWS.PY)
# ===============================================

def send_verification_email(request, account, verification):
    """Gửi email xác thực (Logic từ auth_views.py)"""
    try:
        # Đã bỏ 'src:' namespace
        verification_url = request.build_absolute_uri(
            reverse('verify_email', kwargs={'token': verification.token})
        )
        
        subject = 'Xác thực tài khoản BookingTicket'
        # Dùng template path cũ của bạn
        html_message = render_to_string('users/verify_email_body.html', {
            'user': account,
            'ten': account.khachhang.ten,
            'verify_url': verification_url,
            'expire_hours': getattr(settings, 'EMAIL_VERIFICATION_EXPIRE_HOURS', 24),
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[account.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"Email verification sent to {account.email}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        pass

def send_password_reset_email(request, account, reset_token):
    """Gửi email khôi phục mật khẩu (Logic từ auth_views.py)"""
    try:
        # Đã bỏ 'src:' namespace
        reset_url = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'token': reset_token.token})
        )
        
        subject = 'Khôi phục mật khẩu BookingTicket'
        # Dùng template path cũ của bạn
        html_message = render_to_string('users/password_reset_email.html', {
            'user': account,
            'username': account.khachhang.ten,
            'reset_url': reset_url,
            'expire_hours': getattr(settings, 'PASSWORD_RESET_EXPIRE_HOURS', 1),
        })
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[account.email],
            html_message=html_message,
            fail_silently=False,
        )
        print(f"Password reset email sent to {account.email}")
    except Exception as e:
        print(f"Error sending password reset email: {str(e)}")
        pass

# ===============================================
# === 1. ĐĂNG KÝ (GIỮ NGUYÊN FORM, THÊM HELPER)
# ===============================================

def register_view(request):
    """
    Trang đăng ký (Giữ nguyên cấu trúc dùng RegistrationForm)
    """
    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            
            # Tách 'ten'
            ten_parts = cd['ten'].split(' ')
            first_name = ten_parts[0]
            last_name = ' '.join(ten_parts[1:]) if len(ten_parts) > 1 else ''

            account = Account.objects.create_user(
                username=cd['email'], 
                email=cd['email'],
                password=cd['password'],
                first_name=first_name,
                last_name=last_name,
                is_active=False,
                email_verified=False
            )

            KhachHang.objects.create(
                account=account,
                ten=cd['ten'],
                so_dien_thoai=cd['so_dien_thoai'],
                cccd=cd['cccd'],
                email=cd['email'] # Thêm email nếu model KhachHang của bạn có
            )

            # Tạo token và GỌI HELPER
            verification = EmailVerification.objects.create(account=account)
            send_verification_email(request, account, verification)
            
            messages.success(request, f'Đăng ký thành công! Vui lòng kiểm tra email {cd["email"]} để xác thực tài khoản.')
            # Redirect về trang login (không có namespace 'src:')
            return redirect('login')
    else:
        form = RegistrationForm()
        
    # Dùng template path cũ của bạn
    return render(request, 'users/register.html', {'form': form})

# ===============================================
# === 2. ĐĂNG NHẬP (SỬA LỖI & MERGE LOGIC)
# ===============================================

def login_view(request):
    """
    Trang đăng nhập (Sửa lỗi và merge logic từ auth_views.py)
    """
    # Check for session expiry messages (Logic từ auth_views.py)
    if request.GET.get('expired') == '1':
        reason = request.GET.get('reason', 'Timeout')
        expiry_messages = {
            'Timeout': 'Phiên đăng nhập đã hết hạn do không hoạt động.',
            # ... (các messages khác từ auth_views.py)
        }
        message = expiry_messages.get(reason, 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.')
        messages.warning(request, message)

    if request.user.is_authenticated:
        return redirect('/')
    
    # SỬA LỖI: Bỏ khoảng trắng trong ' POST' và dùng request.POST
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user() # Dùng form để lấy user

            # Logic kiểm tra email_verified (từ auth_views.py)
            if not user.email_verified and not (user.is_superuser or user.is_staff):
                messages.error(request, 
                    'Tài khoản chưa được xác thực email. Vui lòng kiểm tra email.')
                # Dùng template path cũ và thêm context
                return render(request, 'users/login.html', {
                    'form': form, 
                    'show_resend': True, 
                    'email': user.email
                })
            
            login(request, user)
            
            # Initialize session security (Logic từ auth_views.py)
            request.session['session_start'] = time.time()
            request.session['last_activity'] = time.time()
            request.session.modified = True
            
            try:
                ten_hien_thi = user.khachhang.ten
            except KhachHang.DoesNotExist:
                ten_hien_thi = user.username

            messages.success(request, f'Xin chào {ten_hien_thi}!')
            
            # Redirect dựa trên quyền (Logic từ auth_views.py, bỏ 'src:')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            elif user.is_staff or user.is_superuser:
                # Giả sử bạn có URL tên 'dashboard'
                return redirect('dashboard') 
            else:
                # Giả sử bạn có URL tên 'home'
                return redirect('home')
        else:
            messages.error(request, 'Email hoặc mật khẩu không đúng. Vui lòng thử lại.')
    else:
        form = AuthenticationForm()
        
    # SỬA LỖI: Dùng 'request' thay vì 'render'
    return render(request, 'users/login.html', {'form': form})

# ===============================================
# === 3. ĐĂNG XUẤT (MERGE LOGIC)
# ===============================================

def logout_view(request):
    """Đăng xuất (Logic từ auth_views.py, bỏ 'src:')"""
    logout(request)
    messages.info(request, 'Đã đăng xuất thành công!')
    # Giả sử bạn có URL tên 'home'
    return redirect('home')

# ===============================================
# === 4. XÁC THỰC EMAIL (MERGE LOGIC)
# ===============================================

def verify_email_view(request, token):
    """Xác thực email (Logic từ auth_views.py, bỏ 'src:')"""
    try:
        verification = get_object_or_404(EmailVerification, token=token)
        
        if verification.is_used:
            messages.error(request, 'Link xác thực đã được sử dụng!')
            return redirect('login')
        
        if verification.is_expired():
            messages.error(request, 'Link xác thực đã hết hạn!')
            # Giả sử bạn có URL tên 'resend_verification'
            return redirect('resend_verification')
        
        account = verification.account
        account.is_active = True
        account.email_verified = True
        account.save()
        
        verification.is_used = True
        verification.save()
        
        messages.success(request, 'Xác thực email thành công! Bạn có thể đăng nhập.')
        return redirect('login')
        
    except EmailVerification.DoesNotExist:
        messages.error(request, 'Link xác thực không hợp lệ!')
        return redirect('login')

# Thêm view Gửi lại email (từ auth_views.py, bỏ 'src:')
def resend_verification(request):
    """Gửi lại email xác thực"""
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            account = Account.objects.get(email=email, is_active=False)
            EmailVerification.objects.filter(account=account, is_used=False).update(is_used=True)
            verification = EmailVerification.objects.create(account=account)
            send_verification_email(request, account, verification)
            
            messages.success(request, f'Email xác thực đã được gửi lại tới {email}')
            return redirect('login')
        except Account.DoesNotExist:
            messages.error(request, 'Email không tồn tại hoặc tài khoản đã được kích hoạt!')
    
    # Dùng template path của bạn
    return render(request, 'users/resend_verification.html')


# ===============================================
# === 5. RESET MẬT KHẨU (GIỮ FORM, MERGE LOGIC)
# ===============================================

def password_reset_request_view(request):
    """
    Trang yêu cầu reset (Giữ CustomPasswordResetRequestForm, merge logic)
    """
    if request.method == 'POST':
        form = CustomPasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            account = Account.objects.get(email=email, is_active=True)
            
            # Vô hiệu hóa token cũ (Logic từ auth_views.py)
            PasswordReset.objects.filter(account=account, is_used=False).update(is_used=True)
            
            # Tạo token mới
            reset_token = PasswordReset.objects.create(account=account)
            
            # GỌI HELPER
            send_password_reset_email(request, account, reset_token)
            
            messages.success(request, f'Email khôi phục đã được gửi tới {email}.')
            return redirect('login')
    else:
        form = CustomPasswordResetRequestForm()
        
    # Dùng template path cũ
    return render(request, 'users/password_reset_form.html', {'form': form})


def password_reset_confirm_view(request, token):
    """
    Trang đặt lại MK (Giữ SetPasswordForm, merge logic kiểm tra token)
    """
    try:
        # Logic kiểm tra token (từ auth_views.py)
        reset_obj = get_object_or_404(PasswordReset, token=token)
        
        if reset_obj.is_used:
            messages.error(request, 'Link khôi phục đã được sử dụng!')
            return redirect('login')
        
        if reset_obj.is_expired():
            messages.error(request, 'Link khôi phục đã hết hạn!')
            return redirect('password_reset_request') # Dùng tên URL cũ
            
        account = reset_obj.account

        if request.method == 'POST':
            # Giữ nguyên logic dùng SetPasswordForm (tốt hơn)
            form = SetPasswordForm(user=account, data=request.POST) 
            if form.is_valid():
                form.save() 
                reset_obj.is_used = True 
                reset_obj.save()
                messages.success(request, 'Đổi mật khẩu thành công! Bạn có thể đăng nhập.')
                return redirect('login')
        else:
            form = SetPasswordForm(user=account)
            
        # Dùng template path cũ
        return render(request, 'users/password_reset_confirm.html', {
            'form': form,
            'token': token,
            'account': account
        })

    except PasswordReset.DoesNotExist:
        messages.error(request, 'Token không hợp lệ hoặc không tồn tại.')
        return redirect('login')

# ===============================================
# === 6. PROFILE & ADMIN (TỪ AUTH_VIEWS.PY)
# ===============================================

@login_required
def user_profile(request):
   
    try:
        khach_hang = request.user.khachhang
    except KhachHang.DoesNotExist:
        khach_hang = KhachHang.objects.create(
            account=request.user,
            ten=f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username,
            email=request.user.email,
            so_dien_thoai="",
        )
    
    ve_da_dat = Ve.objects.filter(khach=khach_hang).order_by('-thoi_gian_dat')[:10]
    
    if request.method == 'POST':
        
        khach_hang.ten = request.POST.get('ten', khach_hang.ten)
        khach_hang.so_dien_thoai = request.POST.get('so_dien_thoai', khach_hang.so_dien_thoai)
        khach_hang.cccd = request.POST.get('cccd', khach_hang.cccd)
        khach_hang.dia_chi = request.POST.get('dia_chi', khach_hang.dia_chi)
        
        ngay_sinh = request.POST.get('ngay_sinh')
        if ngay_sinh:
            try:
                khach_hang.ngay_sinh = datetime.strptime(ngay_sinh, '%Y-%m-%d').date()
            except ValueError: pass
        
        new_email = request.POST.get('email', request.user.email)
        if new_email != request.user.email:
            if not Account.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                request.user.email = new_email
                khach_hang.email = new_email
                request.user.save()
            else:
                messages.error(request, 'Email đã được sử dụng bởi tài khoản khác!')
                
        khach_hang.save()
        messages.success(request, 'Cập nhật thông tin thành công!')
        return redirect('profile') # Đổi 'src:profile' thành 'profile'
    
    context = {
        'khach_hang': khach_hang,
        've_da_dat': ve_da_dat,
    }
    # Dùng template path của bạn (nếu có)
    return render(request, 'users/profile.html', context)
