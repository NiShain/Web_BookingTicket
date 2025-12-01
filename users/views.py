# users/views_cbv.py - Class-Based Views for user authentication and profile management
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import FormView, TemplateView, UpdateView, View
from datetime import datetime
import time
from django.db import transaction

from .forms import RegistrationForm, CustomPasswordResetRequestForm, OTPVerificationForm
from .models import Account, KhachHang, EmailVerification, PasswordReset, PasswordChangeVerification, OTPRegistration
from django.contrib.auth.hashers import make_password


# ===============================================
# === HELPER FUNCTIONS
# ===============================================

def send_verification_email(request, account, verification):
	"""Send email verification (helper function)"""
	logger = logging.getLogger(__name__)
	try:
		verification_url = request.build_absolute_uri(
			reverse('verify_email', kwargs={'token': verification.token})
		)
		
		subject = 'Xác thực tài khoản BookingTicket'
		html_message = render_to_string('users/verify_email_body.html', {
			'user': account,
			'ten': getattr(account.khachhang, 'ten', account.get_full_name() or account.username),
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
		logger.info('Email verification sent to %s', account.email)
	except Exception as e:
		logger.exception('Error sending verification email to %s: %s', getattr(account, 'email', '<no-email>'), e)


def send_password_reset_email(request, account, reset_token):
	"""Send password reset email (helper function)"""
	try:
		reset_url = request.build_absolute_uri(
			reverse('password_reset_confirm', kwargs={'token': reset_token.token})
		)
		
		subject = 'Khôi phục mật khẩu BookingTicket'
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


def send_password_change_email(request, account, change_token):
	"""Send password change verification email (helper function)"""
	try:
		change_url = request.build_absolute_uri(
			reverse('password_change_confirm', kwargs={'token': change_token.token})
		)
		
		subject = 'Xác thực đổi mật khẩu - BookingTicket'
		html_message = render_to_string('users/password_change_email.html', {
			'user': account,
			'username': getattr(account.khachhang, 'ten', account.username),
			'change_url': change_url,
			'expire_minutes': getattr(settings, 'PASSWORD_CHANGE_EXPIRE_MINUTES', 30),
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
		print(f"Password change verification email sent to {account.email}")
	except Exception as e:
		print(f"Error sending password change email: {str(e)}")


def send_otp_email(request, otp_registration):
	"""Send OTP email for registration (helper function)"""
	try:
		subject = 'Mã xác thực đăng ký - BookingTicket'
		html_message = render_to_string('users/otp_email.html', {
			'ten': otp_registration.ten,
			'email': otp_registration.email,
			'otp_code': otp_registration.otp_code,
			'expire_minutes': getattr(settings, 'OTP_EXPIRE_MINUTES', 10),
		})
		plain_message = strip_tags(html_message)
		
		send_mail(
			subject=subject,
			message=plain_message,
			from_email=settings.DEFAULT_FROM_EMAIL,
			recipient_list=[otp_registration.email],
			html_message=html_message,
			fail_silently=False,
		)
		print(f"OTP email sent to {otp_registration.email}: {otp_registration.otp_code}")
	except Exception as e:
		print(f"Error sending OTP email: {str(e)}")


# ===============================================
# === AUTHENTICATION VIEWS
# ===============================================

class RegisterView(FormView):
	"""User registration view - Step 1: Collect info and send OTP."""
	template_name = 'users/register.html'
	form_class = RegistrationForm
	success_url = reverse_lazy('otp_verification')
	
	def dispatch(self, request, *args, **kwargs):
		if request.user.is_authenticated:
			return redirect('/')
		return super().dispatch(request, *args, **kwargs)
	
	def form_valid(self, form):
		cd = form.cleaned_data
		
		try:
			with transaction.atomic():
				# Xóa các OTP cũ của email này (nếu có)
				OTPRegistration.objects.filter(email=cd['email']).delete()
				
				# Tạo OTPRegistration mới
				otp_reg = OTPRegistration.objects.create(
					email=cd['email'],
					ten=cd['ten'],
					so_dien_thoai=cd['so_dien_thoai'],
					cccd=cd.get('cccd', ''),
					password_hash=make_password(cd['password'])
				)
				
				# Lưu email vào session để sử dụng ở trang OTP
				self.request.session['otp_email'] = cd['email']
				self.request.session['otp_name'] = cd['ten']
				
				# Gửi email OTP
				transaction.on_commit(lambda: send_otp_email(self.request, otp_reg))
				
			messages.success(self.request, f'Mã xác thực OTP đã được gửi tới {cd["email"]}. Vui lòng kiểm tra hộp thư và nhập mã xác thực.')
			return super().form_valid(form)
			
		except Exception as e:
			messages.error(self.request, 'Đã có lỗi khi gửi mã xác thực. Vui lòng thử lại sau.')
			logging.exception('Error during OTP registration: %s', e)
			return self.form_invalid(form)


class OTPVerificationView(FormView):
	"""OTP verification view - Step 2: Verify OTP and create account."""
	template_name = 'users/otp_verification.html'
	form_class = OTPVerificationForm
	success_url = reverse_lazy('login')
	
	def dispatch(self, request, *args, **kwargs):
		# Kiểm tra có email trong session không
		if 'otp_email' not in request.session:
			messages.error(request, 'Phiên xác thực đã hết hạn. Vui lòng đăng ký lại.')
			return redirect('register')
		
		# Kiểm tra có OTPRegistration tồn tại không
		email = request.session['otp_email']
		if not OTPRegistration.objects.filter(email=email, is_verified=False).exists():
			messages.error(request, 'Không tìm thấy thông tin xác thực. Vui lòng đăng ký lại.')
			return redirect('register')
		
		return super().dispatch(request, *args, **kwargs)
	
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		email = self.request.session.get('otp_email', '')
		name = self.request.session.get('otp_name', '')
		
		try:
			otp_reg = OTPRegistration.objects.get(email=email, is_verified=False)
			context.update({
				'email': email,
				'name': name,
				'can_resend': True,
				'remaining_attempts': 5 - otp_reg.attempt_count,
				'expires_at': otp_reg.expires_at,
			})
		except OTPRegistration.DoesNotExist:
			context['can_resend'] = False
		
		return context
	
	def form_valid(self, form):
		email = self.request.session['otp_email']
		otp_input = form.cleaned_data['otp_code']
		
		try:
			otp_reg = OTPRegistration.objects.get(email=email, is_verified=False)
			success, message = otp_reg.verify_otp(otp_input)
			
			if success:
				# Tạo tài khoản thực sự
				with transaction.atomic():
					# Split full name
					ten_parts = otp_reg.ten.split(' ')
					first_name = ten_parts[0]
					last_name = ' '.join(ten_parts[1:]) if len(ten_parts) > 1 else ''
					
					# Tạo Account
					account = Account.objects.create_user(
						username=otp_reg.email,
						email=otp_reg.email,
						password=None,  # Sẽ set sau
						first_name=first_name,
						last_name=last_name,
						is_active=True,
						email_verified=True,
					)
					
					# Set password từ hash đã lưu
					account.password = otp_reg.password_hash
					account.save()
					
					# Tạo KhachHang
					KhachHang.objects.create(
						account=account,
						ten=otp_reg.ten,
						so_dien_thoai=otp_reg.so_dien_thoai,
						cccd=otp_reg.cccd,
						email=otp_reg.email
					)
					
					# Xóa OTP registration
					otp_reg.delete()
					
					# Xóa session data
					del self.request.session['otp_email']
					del self.request.session['otp_name']
				
				messages.success(self.request, f'Đăng ký thành công! Chào mừng {otp_reg.ten}. Bạn có thể đăng nhập ngay bây giờ.')
				return super().form_valid(form)
			else:
				messages.error(self.request, message)
				return self.form_invalid(form)
				
		except OTPRegistration.DoesNotExist:
			messages.error(self.request, 'Không tìm thấy thông tin xác thực. Vui lòng đăng ký lại.')
			return redirect('register')
	
	def form_invalid(self, form):
		return super().form_invalid(form)


class ResendOTPView(View):
	"""Resend OTP code view."""
	
	def post(self, request):
		if 'otp_email' not in request.session:
			messages.error(request, 'Phiên xác thực đã hết hạn.')
			return redirect('register')
		
		email = request.session['otp_email']
		
		try:
			otp_reg = OTPRegistration.objects.get(email=email, is_verified=False)
			otp_reg.regenerate_otp()
			
			# Gửi email mới
			transaction.on_commit(lambda: send_otp_email(request, otp_reg))
			
			messages.success(request, f'Mã OTP mới đã được gửi tới {email}. Vui lòng kiểm tra hộp thư.')
		except OTPRegistration.DoesNotExist:
			messages.error(request, 'Không tìm thấy thông tin đăng ký.')
			return redirect('register')
		
		return redirect('otp_verification')


class LoginView(FormView):
	"""User login view."""
	template_name = 'users/login.html'
	form_class = AuthenticationForm
	
	def dispatch(self, request, *args, **kwargs):
		# Check for session expiry messages
		if request.GET.get('expired') == '1':
			reason = request.GET.get('reason', 'Timeout')
			expiry_messages = {
				'Timeout': 'Phiên đăng nhập đã hết hạn do không hoạt động.',
			}
			message = expiry_messages.get(reason, 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.')
			messages.warning(request, message)
		
		if request.user.is_authenticated:
			return redirect('/')
		return super().dispatch(request, *args, **kwargs)
	
	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['request'] = self.request
		return kwargs
	
	def form_valid(self, form):
		user = form.get_user()
		
		# Check email verification
		if not user.email_verified and not (user.is_superuser or user.is_staff):
			messages.error(self.request, 'Tài khoản chưa được xác thực email. Vui lòng kiểm tra email.')
			return render(self.request, self.template_name, {
				'form': form,
				'show_resend': True,
				'email': user.email
			})
		
		login(self.request, user)
		
		# Initialize session security
		self.request.session['session_start'] = time.time()
		self.request.session['last_activity'] = time.time()
		self.request.session.modified = True
		
		try:
			ten_hien_thi = user.khachhang.ten
		except KhachHang.DoesNotExist:
			ten_hien_thi = user.username
		
		messages.success(self.request, f'Xin chào {ten_hien_thi}!')
		
		# Redirect based on user role
		next_url = self.request.GET.get('next')
		if next_url:
			return redirect(next_url)
		elif user.is_staff or user.is_superuser:
			return redirect('admin_dashboard')
		else:
			return redirect('dashboard')
	
	def form_invalid(self, form):
		messages.error(self.request, 'Email hoặc mật khẩu không đúng. Vui lòng thử lại.')
		return super().form_invalid(form)


class LogoutView(View):
	"""User logout view."""
	
	def get(self, request, *args, **kwargs):
		logout(request)
		messages.info(request, 'Đã đăng xuất thành công!')
		return redirect('/')


# ===============================================
# === EMAIL VERIFICATION VIEWS
# ===============================================

class VerifyEmailView(View):
	"""Email verification view."""
	
	def get(self, request, token):
		try:
			verification = get_object_or_404(EmailVerification, token=token)
			
			if verification.is_used:
				messages.error(request, 'Link xác thực đã được sử dụng!')
				return redirect('login')
			
			if verification.is_expired():
				messages.error(request, 'Link xác thực đã hết hạn!')
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


class ResendVerificationView(View):
	"""Resend email verification view."""
	template_name = 'users/resend_verification.html'
	
	def get(self, request):
		return render(request, self.template_name)
	
	def post(self, request):
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
		
		return render(request, self.template_name)


# ===============================================
# === PASSWORD RESET VIEWS
# ===============================================

class PasswordResetRequestView(FormView):
	"""Password reset request view."""
	template_name = 'users/password_reset_request.html'
	form_class = CustomPasswordResetRequestForm
	success_url = reverse_lazy('login')
	
	def form_valid(self, form):
		email = form.cleaned_data['email']
		try:
			account = Account.objects.get(email=email, is_active=True)
		except Account.DoesNotExist:
			messages.error(self.request, 'Email không tồn tại hoặc tài khoản chưa được kích hoạt.')
			return self.form_invalid(form)
		
		# Invalidate old tokens
		PasswordReset.objects.filter(account=account, is_used=False).update(is_used=True)
		
		# Create new token
		reset_token = PasswordReset.objects.create(account=account)
		
		# Send email after transaction commit
		transaction.on_commit(lambda: send_password_reset_email(self.request, account, reset_token))
		
		messages.success(self.request, 'Email khôi phục mật khẩu đã được gửi. Vui lòng kiểm tra hộp thư của bạn.')
		return super().form_valid(form)


class PasswordResetConfirmView(FormView):
	"""Password reset confirmation view."""
	template_name = 'users/password_reset_confirm.html'
	form_class = SetPasswordForm
	success_url = reverse_lazy('login')
	
	def dispatch(self, request, *args, **kwargs):
		try:
			self.reset_token = get_object_or_404(PasswordReset, token=kwargs['token'], is_used=False)
		except PasswordReset.DoesNotExist:
			messages.error(request, 'Liên kết khôi phục mật khẩu không hợp lệ hoặc đã được sử dụng.')
			return redirect('password_reset_request')
		
		if self.reset_token.is_expired():
			messages.error(request, 'Liên kết khôi phục mật khẩu đã hết hạn. Vui lòng yêu cầu gửi lại.')
			return redirect('password_reset_request')
		
		return super().dispatch(request, *args, **kwargs)
	
	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['user'] = self.reset_token.account
		return kwargs
	
	def form_valid(self, form):
		form.save()
		self.reset_token.is_used = True
		self.reset_token.save()
		messages.success(self.request, 'Mật khẩu của bạn đã được cập nhật. Vui lòng đăng nhập.')
		return super().form_valid(form)
	
	def form_invalid(self, form):
		messages.error(self.request, 'Vui lòng sửa các lỗi bên dưới.')
		return super().form_invalid(form)


# ===============================================
# === PROFILE & DASHBOARD VIEWS
# ===============================================

class UserProfileView(LoginRequiredMixin, TemplateView):
	"""User profile view with update functionality."""
	template_name = 'users/profile.html'
	
	def get_khach_hang(self):
		"""Get or create KhachHang instance for current user."""
		try:
			return self.request.user.khachhang
		except KhachHang.DoesNotExist:
			return KhachHang.objects.create(
				account=self.request.user,
				ten=f"{self.request.user.first_name} {self.request.user.last_name}".strip() or self.request.user.username,
				email=self.request.user.email,
				so_dien_thoai="",
			)
	
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		khach_hang = self.get_khach_hang()
		
		# Import Ve lazily
		from booking.models import Ve
		ve_da_dat = Ve.objects.filter(khach=khach_hang).order_by('-thoi_gian_dat')[:10]
		
		context.update({
			'khach_hang': khach_hang,
			've_da_dat': ve_da_dat,
		})
		return context
	
	def post(self, request, *args, **kwargs):
		khach_hang = self.get_khach_hang()
		
		khach_hang.ten = request.POST.get('ten', khach_hang.ten)
		khach_hang.so_dien_thoai = request.POST.get('so_dien_thoai', khach_hang.so_dien_thoai)
		khach_hang.cccd = request.POST.get('cccd', khach_hang.cccd)
		khach_hang.dia_chi = request.POST.get('dia_chi', khach_hang.dia_chi)
		
		ngay_sinh = request.POST.get('ngay_sinh')
		if ngay_sinh:
			try:
				khach_hang.ngay_sinh = datetime.strptime(ngay_sinh, '%Y-%m-%d').date()
			except ValueError:
				pass
		
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
		
		return self.get(request, *args, **kwargs)


class AdminDashboardView(UserPassesTestMixin, TemplateView):
	"""Admin dashboard view for staff/superuser."""
	template_name = 'admin/admin_dashboard.html'
	
	def test_func(self):
		return self.request.user.is_staff or self.request.user.is_superuser


class UserDashboardView(LoginRequiredMixin, TemplateView):
	"""User dashboard view with bookings and trip recommendations."""
	template_name = 'users/user_dashboard.html'
	
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		
		try:
			khach_hang = self.request.user.khachhang
		except KhachHang.DoesNotExist:
			khach_hang = None
		
		# Import models lazily
		from booking.models import Ve, Chuyen
		from django.utils import timezone
		from django.db.models import Count
		
		recent_ves = Ve.objects.filter(khach__account=self.request.user).order_by('-ngay_dat')[:10] if khach_hang else []
		
		# Upcoming trips
		upcoming_chuyens = Chuyen.objects.filter(
			ngay_gio_khoi_hanh__gte=timezone.now()
		).order_by('ngay_gio_khoi_hanh')[:8]
		
		# Hot trips (popular routes by trip count)
		hot_chuyens = Chuyen.objects.filter(
			ngay_gio_khoi_hanh__gte=timezone.now()
		).select_related('tuyen', 'xe').annotate(
			route_trip_count=Count('tuyen__chuyens')
		).order_by('-route_trip_count', 'ngay_gio_khoi_hanh')[:8]
		
		context.update({
			'khach_hang': khach_hang,
			'recent_ves': recent_ves,
			'upcoming_chuyens': upcoming_chuyens,
			'hot_chuyens': hot_chuyens,
		})
		return context


# ===============================================
# === PASSWORD CHANGE VIEWS (for authenticated users)
# ===============================================

class PasswordChangeRequestView(LoginRequiredMixin, View):
	"""Request password change - sends verification email."""
	
	def post(self, request):
		account = request.user
		
		# Invalidate old tokens
		PasswordChangeVerification.objects.filter(account=account, is_used=False).update(is_used=True)
		
		# Create new token
		change_token = PasswordChangeVerification.objects.create(account=account)
		
		# Send email
		transaction.on_commit(lambda: send_password_change_email(request, account, change_token))
		
		messages.success(request, 'Email xác thực đã được gửi. Vui lòng kiểm tra hộp thư để tiếp tục đổi mật khẩu.')
		return redirect('profile')


class PasswordChangeConfirmView(LoginRequiredMixin, FormView):
	"""Confirm password change after email verification."""
	template_name = 'users/password_change_confirm.html'
	form_class = SetPasswordForm
	success_url = reverse_lazy('profile')
	
	def dispatch(self, request, *args, **kwargs):
		try:
			self.change_token = get_object_or_404(PasswordChangeVerification, token=kwargs['token'], is_used=False)
		except PasswordChangeVerification.DoesNotExist:
			messages.error(request, 'Link xác thực không hợp lệ hoặc đã được sử dụng.')
			return redirect('profile')
		
		# Check if token belongs to logged-in user
		if self.change_token.account != request.user:
			messages.error(request, 'Link xác thực không hợp lệ.')
			return redirect('profile')
		
		if self.change_token.is_expired():
			messages.error(request, 'Link xác thực đã hết hạn. Vui lòng yêu cầu gửi lại.')
			return redirect('profile')
		
		return super().dispatch(request, *args, **kwargs)
	
	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['user'] = self.request.user
		return kwargs
	
	def form_valid(self, form):
		form.save()
		self.change_token.is_used = True
		self.change_token.save()
		messages.success(self.request, 'Mật khẩu đã được thay đổi thành công!')
		return super().form_valid(form)
	
	def form_invalid(self, form):
		messages.error(self.request, 'Vui lòng sửa các lỗi bên dưới.')
		return super().form_invalid(form)
