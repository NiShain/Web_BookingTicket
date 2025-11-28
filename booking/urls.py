from django.urls import path
from . import views

app_name = 'src'

urlpatterns = [
    # --- URL USER (Khách hàng) ---
    path('danh-sach-tuyens/', views.DanhSachTuyenView.as_view(), name='danh_sach_tuyens'),
    path('danh-sach-chuyen-xe/', views.DanhSachChuyenXeView.as_view(), name='danh_sach_chuyen_xe'),
    path('chuyen/<int:chuyen_id>/chon-ghe/', views.ChonGheView.as_view(), name='chon_ghe'),
    path('payment/success/', views.PaymentSuccessView.as_view(), name='payment-success'),
    path('payment/processing/', views.PaymentProcessingView.as_view(), name='payment-processing'),

    # --- URL ADMIN (Quản trị viên) ---
    
    # 1. Quản lý Tuyến
    path('manage/tuyen/', views.AdminTuyenListView.as_view(), name='admin_tuyen_list'),
    path('manage/tuyen/create/', views.AdminTuyenCreateView.as_view(), name='admin_tuyen_create'),
    path('manage/tuyen/<int:pk>/update/', views.AdminTuyenUpdateView.as_view(), name='admin_tuyen_update'),
    path('manage/tuyen/<int:pk>/delete/', views.AdminTuyenDeleteView.as_view(), name='admin_tuyen_delete'),

    # 2. Quản lý Xe
    path('manage/xe/', views.AdminXeListView.as_view(), name='admin_xe_list'),
    path('manage/xe/create/', views.AdminXeCreateView.as_view(), name='admin_xe_create'),
    path('manage/xe/<int:pk>/update/', views.AdminXeUpdateView.as_view(), name='admin_xe_update'),
    path('manage/xe/<int:pk>/delete/', views.AdminXeDeleteView.as_view(), name='admin_xe_delete'),

    # 3. Quản lý Chuyến
    path('manage/chuyen/', views.AdminChuyenListView.as_view(), name='admin_chuyen_list'),
    path('manage/chuyen/create/', views.AdminChuyenCreateView.as_view(), name='admin_chuyen_create'),
    path('manage/chuyen/<int:pk>/update/', views.AdminChuyenUpdateView.as_view(), name='admin_chuyen_update'),
    path('manage/chuyen/<int:pk>/delete/', views.AdminChuyenDeleteView.as_view(), name='admin_chuyen_delete'),

    # 4. Quản lý Vé (Read-Only)
    path('manage/ve/', views.AdminVeListView.as_view(), name='admin_ve_list'),
    path('manage/ve/<int:pk>/', views.AdminVeDetailView.as_view(), name='admin_ve_detail'),

    # 5. Quản lý Khách hàng (Read-Only)
    path('manage/khach-hang/', views.AdminKhachHangListView.as_view(), name='admin_khachhang_list'),
    path('manage/khach-hang/<int:pk>/', views.AdminKhachHangDetailView.as_view(), name='admin_khachhang_detail'),
]

