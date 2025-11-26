from django.urls import path
from . import views

app_name = 'src'

urlpatterns = [
	path('danh-sach-tuyens/', views.danh_sach_tuyens, name='danh_sach_tuyens'),
	path('danh-sach-chuyen-xe/', views.danh_sach_chuyen_xe, name='danh_sach_chuyen_xe'),
]
