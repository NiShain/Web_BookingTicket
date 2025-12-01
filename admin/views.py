from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, TemplateView ,DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Count, Q
from users.models import KhachHang, NhanVien
from booking.models import Tuyen, Chuyen, Ve, Voucher, VoucherSuDung, Xe, ThanhToan
from django.contrib import messages
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Sum


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_staff
#==================== ADMIN DASHBOARD ====================#
class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'admin/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Tổng vé đã bán (chỉ tính ĐÃ THANH TOÁN)
        ve_da_thanh_toan = Ve.objects.filter(trang_thai='DA_THANH_TOAN').count()
        
        # 2. Tổng vé đã đặt (bao gồm cả CHỜ THANH TOÁN)
        tong_ve_da_ban = Ve.objects.filter(
            trang_thai__in=['DA_THANH_TOAN', 'CHO_THANH_TOAN']
        ).count()
        
        # 3. Doanh thu (chỉ tính từ vé ĐÃ THANH TOÁN)
        doanh_thu = ThanhToan.objects.filter(
            trang_thai='THANH_CONG'
        ).aggregate(
            total=Sum('so_tien')
        )['total'] or 0
        
        # 4. Tổng khách hàng
        tong_khach_hang = KhachHang.objects.count()
        
        # 5. Chuyến xe hôm nay
        today = timezone.now().date()
        chuyen_xe_hom_nay = Chuyen.objects.filter(
            ngay_gio_khoi_hanh__date=today
        ).count()
        
        # 6. Thống kê thêm
        ve_cho_thanh_toan = Ve.objects.filter(trang_thai='CHO_THANH_TOAN').count()
        ve_da_huy = Ve.objects.filter(trang_thai='DA_HUY').count()
        tong_tuyen = Tuyen.objects.count()
        tong_xe = Xe.objects.count()
        
        context.update({
            'tong_ve_da_ban': tong_ve_da_ban,
            've_da_thanh_toan': ve_da_thanh_toan,
            've_cho_thanh_toan': ve_cho_thanh_toan,
            've_da_huy': ve_da_huy,
            'doanh_thu': doanh_thu,
            'tong_khach_hang': tong_khach_hang,
            'chuyen_xe_hom_nay': chuyen_xe_hom_nay,
            'current_date': today,
            'tong_tuyen': tong_tuyen,
            'tong_xe': tong_xe,
        })
        
        return context

#==================== ADMIN TUYẾN ====================#

class AdminTuyenListView(AdminRequiredMixin, ListView):
    model = Tuyen
    template_name = 'admin/tuyen_list.html'
    context_object_name = 'tuyens'
    paginate_by = 10

class AdminTuyenCreateView(AdminRequiredMixin, CreateView):
    model = Tuyen
    template_name = 'admin/tuyen_form.html'
    fields = ['diem_di', 'diem_den', 'khoang_cach']
    success_url = reverse_lazy('admin_panel:admin_tuyen_list')
    extra_context = {'title': 'Thêm Tuyến Mới'}

class AdminTuyenUpdateView(AdminRequiredMixin, UpdateView):
    model = Tuyen
    template_name = 'admin/tuyen_form.html'
    fields = ['diem_di', 'diem_den', 'khoang_cach']
    success_url = reverse_lazy('admin_panel:admin_tuyen_list')
    extra_context = {'title': 'Cập nhật Tuyến'}

class AdminTuyenDeleteView(AdminRequiredMixin, DeleteView):
    model = Tuyen
    template_name = 'admin/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:admin_tuyen_list')


#==================== ADMIN XE ====================#

class AdminXeListView(AdminRequiredMixin, ListView):
    model = Xe
    template_name = 'admin/xe_list.html'
    context_object_name = 'xes'
    paginate_by = 10

class AdminXeCreateView(AdminRequiredMixin, CreateView):
    model = Xe
    template_name = 'admin/xe_form.html'
    fields = ['bien_so', 'loai_xe', 'so_ghe']
    success_url = reverse_lazy('admin_panel:admin_xe_list')

class AdminXeUpdateView(AdminRequiredMixin, UpdateView):
    model = Xe
    template_name = 'admin/xe_form.html'
    fields = ['bien_so', 'loai_xe', 'so_ghe']
    success_url = reverse_lazy('admin_panel:admin_xe_list')

class AdminXeDeleteView(AdminRequiredMixin, DeleteView):
    model = Xe
    template_name = 'admin/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:admin_xe_list')


#==================== ADMIN CHUYẾN ====================#

class AdminChuyenListView(AdminRequiredMixin, ListView):
    model = Chuyen
    template_name = 'admin/chuyen_list.html'
    context_object_name = 'chuyens'
    paginate_by = 10

    def get_queryset(self):
        # Hiển thị thêm thông tin số vé đã bán để dễ theo dõi
        return Chuyen.objects.select_related('tuyen', 'xe').annotate(
            so_ve_da_ban=Count('ves', filter=Q(ves__trang_thai='DA_THANH_TOAN'))
        ).order_by('-ngay_gio_khoi_hanh')

class AdminChuyenCreateView(AdminRequiredMixin, CreateView):
    model = Chuyen
    template_name = 'admin/chuyen_form.html'
    fields = ['tuyen', 'xe', 'ngay_gio_khoi_hanh', 'ngay_gio_den', 'tong_so_ve', 'gia_ve']
    success_url = reverse_lazy('admin_panel:admin_chuyen_list')

class AdminChuyenUpdateView(AdminRequiredMixin, UpdateView):
    model = Chuyen
    template_name = 'admin/chuyen_form.html'
    fields = ['tuyen', 'xe', 'ngay_gio_khoi_hanh', 'ngay_gio_den', 'tong_so_ve', 'gia_ve']
    success_url = reverse_lazy('admin_panel:admin_chuyen_list')

class AdminChuyenDeleteView(AdminRequiredMixin, DeleteView):
    model = Chuyen
    template_name = 'admin/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:admin_chuyen_list')


#==================== ADMIN VÉ ====================#

class AdminVeListView(AdminRequiredMixin, ListView):
    model = Ve
    template_name = 'admin/ve_list.html'
    context_object_name = 'ves'
    paginate_by = 20

    def get_queryset(self):
        qs = Ve.objects.select_related('chuyen', 'khach', 'chuyen__tuyen').order_by('-id')
        
        # Tính năng tìm kiếm vé theo tên khách hoặc số điện thoại
        search_query = self.request.GET.get('q')
        if search_query:
            qs = qs.filter(
                Q(khach__ten__icontains=search_query) | 
                Q(khach__sdt__icontains=search_query)
            )
            
        # Tính năng lọc theo trạng thái
        status_filter = self.request.GET.get('status')
        if status_filter:
            qs = qs.filter(trang_thai=status_filter)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Gửi thêm danh sách các trạng thái để làm bộ lọc trên giao diện
        context['status_choices'] = ['DA_THANH_TOAN', 'CHO_THANH_TOAN', 'DA_HUY']
        return context

class AdminVeDetailView(AdminRequiredMixin, DetailView):
    model = Ve
    template_name = 'admin/ve_detail.html'
    context_object_name = 've'


#==================== ADMIN KHÁCH HÀNG ====================#

class AdminKhachHangListView(AdminRequiredMixin, ListView):
    model = KhachHang
    template_name = 'admin/khachhang_list.html'
    context_object_name = 'khachhangs'
    paginate_by = 15
    
    def get_queryset(self):
        # Tìm kiếm khách hàng
        query = self.request.GET.get('q')
        if query:
            return KhachHang.objects.filter(
                Q(ten__icontains=query) | Q(sdt__icontains=query) | Q(email__icontains=query)
            )
        return KhachHang.objects.all()

class AdminKhachHangDetailView(AdminRequiredMixin, DetailView):
    model = KhachHang
    template_name = 'admin/khachhang_detail.html'
    context_object_name = 'khach'
    
    def get_context_data(self, **kwargs):  # ✅ ĐÚNG: Override method của CBV
        context = super().get_context_data(**kwargs)
        context['ves'] = Ve.objects.filter(
            khach=self.object  # self.object = khách hàng hiện tại
        ).select_related(
            'chuyen__tuyen', 'chuyen__xe'
        ).order_by('-ngay_dat')
        return context


#==================== ADMIN NHÂN VIÊN ====================#

class AdminNhanVienListView(AdminRequiredMixin, ListView):
    model = NhanVien
    template_name = 'admin/nhanvien_list.html'
    context_object_name = 'nhanviens'
    paginate_by = 20
    
    def get_queryset(self):
        qs = NhanVien.objects.all()
        
        # Tìm kiếm
        search_query = self.request.GET.get('q')
        if search_query:
            qs = qs.filter(
                Q(ho_ten__icontains=search_query) | 
                Q(so_dien_thoai__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        # Lọc theo chức vụ
        chuc_vu = self.request.GET.get('chuc_vu')
        if chuc_vu:
            qs = qs.filter(chuc_vu=chuc_vu)
        
        # Lọc theo trạng thái
        trang_thai = self.request.GET.get('trang_thai')
        if trang_thai == '1':
            qs = qs.filter(trang_thai=True)
        elif trang_thai == '0':
            qs = qs.filter(trang_thai=False)
        
        return qs.order_by('-ngay_vao_lam')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Thêm thống kê
        from django.db.models import Sum
        all_nv = NhanVien.objects.filter(trang_thai=True)
        context['tong_luong'] = all_nv.aggregate(Sum('luong_co_ban'))['luong_co_ban__sum'] or 0
        context['so_tai_xe'] = all_nv.filter(chuc_vu='TAI_XE').count()
        return context

class AdminNhanVienCreateView(AdminRequiredMixin, CreateView):
    model = NhanVien
    template_name = 'admin/nhanvien_form.html'
    fields = ['anh_dai_dien', 'ho_ten', 'ngay_sinh', 'so_dien_thoai', 'email', 'dia_chi', 
              'chuc_vu', 'luong_co_ban', 'trang_thai', 'ghi_chu']
    success_url = reverse_lazy('admin_panel:nhanvien_list')
    
    def form_valid(self, form):
        messages.success(self.request, f"✅ Đã thêm nhân viên: {form.instance.ho_ten}")
        return super().form_valid(form)

class AdminNhanVienUpdateView(AdminRequiredMixin, UpdateView):
    model = NhanVien
    template_name = 'admin/nhanvien_form.html'
    fields = ['anh_dai_dien', 'ho_ten', 'ngay_sinh', 'so_dien_thoai', 'email', 'dia_chi', 
              'chuc_vu', 'luong_co_ban', 'trang_thai', 'ghi_chu']
    success_url = reverse_lazy('admin_panel:nhanvien_list')
    
    def form_valid(self, form):
        messages.success(self.request, f"✅ Đã cập nhật nhân viên: {form.instance.ho_ten}")
        return super().form_valid(form)

class AdminNhanVienDeleteView(AdminRequiredMixin, DeleteView):
    model = NhanVien
    template_name = 'admin/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:nhanvien_list')


#==================== ADMIN VOUCHER ====================#

class AdminVoucherListView(AdminRequiredMixin, ListView):
    model = Voucher
    template_name = 'admin/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

class AdminVoucherCreateView(AdminRequiredMixin, CreateView):
    model = Voucher
    template_name = 'admin/voucher_form.html'
    fields = [
        'ten_voucher', 'mo_ta', 'loai_giam_gia', 'gia_tri_giam', 
        'giam_toi_da', 'gia_tri_don_toi_thieu', 'ngay_bat_dau', 
        'ngay_ket_thuc', 'so_luong', 'so_lan_su_dung_toi_da_moi_user',
        'khach_hang_duoc_su_dung',
        'trang_thai'
    ]
    success_url = reverse_lazy('admin_panel:voucher_list')
    
    def form_valid(self, form):
        # Tự động tạo mã voucher ngẫu nhiên
        form.instance.ma_voucher = Voucher.tao_ma_voucher()
        messages.success(self.request, f"✅ Đã tạo voucher: {form.instance.ma_voucher}")
        return super().form_valid(form)

class AdminVoucherUpdateView(AdminRequiredMixin, UpdateView):
    model = Voucher
    template_name = 'admin/voucher_form.html'
    fields = [
        'ten_voucher', 'mo_ta', 'loai_giam_gia', 'gia_tri_giam', 
        'giam_toi_da', 'gia_tri_don_toi_thieu', 'ngay_bat_dau', 
        'ngay_ket_thuc', 'so_luong', 'so_lan_su_dung_toi_da_moi_user',
        'khach_hang_duoc_su_dung',
        'trang_thai'
    ]
    success_url = reverse_lazy('admin_panel:voucher_list')

class AdminVoucherDeleteView(AdminRequiredMixin, DeleteView):
    model = Voucher
    template_name = 'admin/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:voucher_list')

class AdminVoucherHistoryView(AdminRequiredMixin, ListView):
    """Xem lịch sử sử dụng voucher"""
    model = VoucherSuDung
    template_name = 'admin/voucher_history.html'
    context_object_name = 'histories'
    paginate_by = 50
    
    def get_queryset(self):
        voucher_id = self.kwargs.get('pk')
        if voucher_id:
            return VoucherSuDung.objects.filter(voucher_id=voucher_id).select_related(
                'voucher', 'khach_hang', 've'
            ).order_by('-ngay_su_dung')
        return VoucherSuDung.objects.select_related(
            'voucher', 'khach_hang', 've'
        ).order_by('-ngay_su_dung')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        voucher_id = self.kwargs.get('pk')
        if voucher_id:
            context['voucher'] = Voucher.objects.get(pk=voucher_id)
        return context



