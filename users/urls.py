# users/urls.py
from django.urls import path
# Bỏ import auth_views vì chúng ta đã tự viết view
from . import views 

urlpatterns = [
    # --- 1. Đăng ký & Xác thực ---
    path('register/', views.register_view, name='register'),
    
    path('verify-email/<uuid:token>/', 
         views.verify_email_view, 
         name='verify_email'),

    # THÊM: Đường dẫn để gửi lại email xác thực
    path('resend-verification/', 
         views.resend_verification, 
         name='resend_verification'),

    # --- 2. Đăng nhập & Đăng xuất (Trỏ đến view tùy chỉnh) ---
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # --- 3. Reset Mật khẩu ---
    path('password-reset/', 
         views.password_reset_request_view, 
         name='password_reset_request'),
    
    path('password-reset/confirm/<uuid:token>/', 
         views.password_reset_confirm_view, 
         name='password_reset_confirm'),

    # --- 4. Profile & Dashboard ---
    # THÊM: Đường dẫn cho trang profile
    path('profile/', views.user_profile, name='profile'),
    
    # THÊM: Đường dẫn cho trang dashboard (admin)
    path('dashboard/', views.admin_dashboard, name='dashboard'),
]