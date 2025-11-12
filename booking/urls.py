from django.urls import path
from .views import (
    AdminChuyenCreateView, AdminChuyenDeleteView, AdminChuyenListView, AdminChuyenUpdateView,
    AdminTuyenCreateView, AdminTuyenDeleteView, AdminTuyenListView, AdminTuyenUpdateView,
    AdminXeCreateView, AdminXeDeleteView, AdminXeListView, AdminXeUpdateView,
    AdminPaymentListView, AdminVeListView
)

urlpatterns = [
    path('tuyen/', AdminTuyenListView.as_view(), name='tuyen-list'),
    path('tuyen/create/', AdminTuyenCreateView.as_view(), name='tuyen-create'),
    path('tuyen/<int:pk>/update/', AdminTuyenUpdateView.as_view(), name='tuyen-update'),
    path('tuyen/<int:pk>/delete/', AdminTuyenDeleteView.as_view(), name='tuyen-delete'),

    
    path('chuyen/', AdminChuyenListView.as_view(), name='chuyen-list'),
    path('chuyen/create/', AdminChuyenCreateView.as_view(), name='chuyen-create'),
    path('chuyen/<int:pk>/update/', AdminChuyenUpdateView.as_view(), name='chuyen-update'),
    path('chuyen/<int:pk>/delete/', AdminChuyenDeleteView.as_view(), name='chuyen-delete'),

    
    path('xe/', AdminXeListView.as_view(), name='xe-list'),
    path('xe/create/', AdminXeCreateView.as_view(), name='xe-create'),
    path('xe/<int:pk>/update/', AdminXeUpdateView.as_view(), name='xe-update'),
    path('xe/<int:pk>/delete/', AdminXeDeleteView.as_view(), name='xe-delete'),

    
    path('payment/', AdminPaymentListView.as_view(), name='payment-list'),
    path('ve/', AdminVeListView.as_view(), name='ve-list'),
]
