# users/urls.py
from django.urls import path
from . import views 

urlpatterns = [
    # --- 1. Registration & Email Verification ---
    path('register/', views.RegisterView.as_view(), name='register'),
    
    path('verify-email/<uuid:token>/', 
         views.VerifyEmailView.as_view(), 
         name='verify_email'),

    path('resend-verification/', 
         views.ResendVerificationView.as_view(), 
         name='resend_verification'),

    # --- 2. Login & Logout ---
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # --- 3. Password Reset ---
    path('password-reset/', 
         views.PasswordResetRequestView.as_view(), 
         name='password_reset_request'),
    
    path('password-reset/confirm/<uuid:token>/', 
         views.PasswordResetConfirmView.as_view(), 
         name='password_reset_confirm'),

    # --- 4. Profile & Dashboard ---
    path('profile/', views.UserProfileView.as_view(), name='profile'),

    # User dashboard (regular authenticated users)
    path('dashboard/', views.UserDashboardView.as_view(), name='dashboard'),

    # Admin dashboard (staff / superuser)
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),

    # --- 5. Password Change (for authenticated users) ---
    path('password-change/request/', 
         views.PasswordChangeRequestView.as_view(), 
         name='password_change_request'),
    
    path('password-change/confirm/<uuid:token>/', 
         views.PasswordChangeConfirmView.as_view(), 
         name='password_change_confirm'),
]