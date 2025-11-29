from django.urls import path
from . import views

app_name = 'src'

urlpatterns = [
    path('danh-sach-tuyens/', views.DanhSachTuyenView.as_view(), name='danh_sach_tuyens'),
    path('danh-sach-chuyen-xe/', views.DanhSachChuyenXeView.as_view(), name='danh_sach_chuyen_xe'),
    path('chuyen/<int:chuyen_id>/chon-ghe/', views.ChonGheView.as_view(), name='chon_ghe'),
    path('payment/success/', views.PaymentSuccessView.as_view(), name='payment-success'),
    path('payment/processing/', views.PaymentProcessingView.as_view(), name='payment-processing'),
]

