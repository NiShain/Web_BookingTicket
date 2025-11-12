from django.shortcuts import render
from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Tuyen, Chuyen, Xe, Ve, ThanhToan
from django.urls import reverse_lazy
#============== ADMIN ==================
class StaffRequiredMixins(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

class AdminTuyenListView(LoginRequiredMixin,StaffRequiredMixins,ListView):
    model = Tuyen
    template_name = "bookingticket/admin/tuyen_list.html"
    context_object_name = "danh_sach_tuyen"
    paginate_by = 10

class AdminXeListView(LoginRequiredMixin,StaffRequiredMixins,ListView):
    model = Xe 
    template_name = "bookingticket/admin/xe_list.html"
    context_object_name = "danh_sach_xe"

class AdminChuyenListView(LoginRequiredMixin,StaffRequiredMixins,ListView):
    model = Chuyen
    template_name = "bookingticket/admin/chuyen_list.html"
    context_object_name = "danh_sach_chuyen"
    paginate_by = 10

class AdminVeListView(LoginRequiredMixin,StaffRequiredMixins,ListView):
    model = Ve
    template_name = "bookingticket/admin/ve_list.html"
    context_object_name = "danh_sach_ve"
    paginate_by = 20

class AdminPaymentListView(LoginRequiredMixin,StaffRequiredMixins,ListView):
    model = ThanhToan
    template_name = "bookingticket/admin/payment_list.html"
    context_object_name = "danh_sach_thanh_toan"
    paginate_by = 20

class AdminTuyenCreateView(LoginRequiredMixin,StaffRequiredMixins,CreateView):
    model = Tuyen
    template_name = "bookingticket/admin/tuyen_form.html"
    fields = ['diem_di', 'diem_den', 'khoang_cach']
    success_url = reverse_lazy('tuyen-list')
    
class AdminChuyenCreateView(LoginRequiredMixin, StaffRequiredMixins, CreateView):
    model = Chuyen
    template_name = "bookingticket/admin/chuyen_form.html"
    fields = ['tuyen', 'xe', 'ngay_gio_khoi_hanh', 'ngay_gio_den', 'tong_so_ve', 'gia_ve']
    success_url = reverse_lazy('chuyen-list')
    
class AdminXeCreateView(LoginRequiredMixin, StaffRequiredMixins, CreateView):
    model = Xe
    template_name = "bookingticket/admin/xe_form.html"
    fields = ['bien_so', 'loai_xe', 'so_ghe']
    success_url = reverse_lazy('xe-list')
    
class AdminTuyenUpdateView(LoginRequiredMixin, StaffRequiredMixins,UpdateView):
    model = Tuyen
    template_name = "bookingticket/admin/tuyen_form.html"   
    fields = ['diem_di', 'diem_den', 'khoang_cach']
    success_url = reverse_lazy('tuyen-list')
    
class AdminChuyenUpdateView(LoginRequiredMixin, StaffRequiredMixins, UpdateView):
    model = Chuyen
    template_name = "bookingticket/admin/chuyen_form.html"
    fields = ['tuyen', 'xe', 'ngay_gio_khoi_hanh', 'ngay_gio_den', 'tong_so_ve', 'gia_ve']
    success_url = reverse_lazy('chuyen-list')
    
class AdminXeUpdateView(LoginRequiredMixin, StaffRequiredMixins, UpdateView):
    
    model = Xe
    template_name = "bookingticket/admin/xe_form.html"
    fields = ['bien_so', 'loai_xe', 'so_ghe']
    success_url = reverse_lazy('xe-list')
class AdminTuyenDeleteView(LoginRequiredMixin, StaffRequiredMixins, DeleteView):
    model = Tuyen
    template_name = "bookingticket/admin/tuyen_confirm_delete.html"
    success_url = reverse_lazy('tuyen-list')
    
class AdminChuyenDeleteView(LoginRequiredMixin, StaffRequiredMixins, DeleteView):
    model = Chuyen
    template_name = "bookingticket/admin/chuyen_confirm_delete.html"
    success_url = reverse_lazy('chuyen-list')
    
class AdminXeDeleteView(LoginRequiredMixin, StaffRequiredMixins, DeleteView):
    
#================== USERS ==================================

    model = Xe
    template_name = "bookingticket/admin/xe_confirm_delete.html"
    success_url = reverse_lazy('xe-list')