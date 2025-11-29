from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Count, Q
from users.models import KhachHang, NhanVien
from booking.models import Tuyen, Chuyen, Ve, Voucher, VoucherSuDung
from django.contrib import messages



class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_active and self.request.user.is_staff
    
class AdminTuyenListView(AdminRequiredMixin, ListView):
    model = Tuyen
    template_name = 'admin/tuyen_list.html'
    context_object_name = 'tuyens'
    paginate_by = 10

class AdminTuyenCreateView(AdminRequiredMixin, CreateView):
    model = Tuyen
    template_name = 'admin/tuyen_form.html'
    fields = ['diem_di', 'diem_den', 'khoang_cach']
    success_url = reverse_lazy('src:admin_tuyen_list')
    extra_context = {'title': 'Thêm Tuyến Mới'}

class AdminTuyenUpdateView(AdminRequiredMixin, UpdateView):
    model = Tuyen
    template_name = 'admin/tuyen_form.html'
    fields = ['diem_di', 'diem_den', 'khoang_cach']
    success_url = reverse_lazy('src:admin_tuyen_list')
    extra_context = {'title': 'Cập nhật Tuyến'}

class AdminTuyenDeleteView(AdminRequiredMixin, DeleteView):
    model = Tuyen
    template_name = 'admin/confirm_delete.html'
    success_url = reverse_lazy('src:admin_tuyen_list')

class AdminXeListView(AdminRequiredMixin, ListView):
    model = Tuyen # Lưu ý: Sửa lại thành Xe khi bạn có model Xe import vào
    # Giả sử bạn đã import Xe:
    # model = Xe 
    template_name = 'admin/xe_list.html'
    context_object_name = 'xes'

    def get_queryset(self):
        # Import Xe cục bộ nếu chưa có ở đầu file
        from booking.models import Xe
        return Xe.objects.all()

class AdminXeCreateView(AdminRequiredMixin, CreateView):
    from booking.models import Xe
    model = Xe
    template_name = 'admin/xe_form.html'
    fields = ['bien_so', 'loai_xe', 'so_ghe']
    success_url = reverse_lazy('src:admin_xe_list')

class AdminXeUpdateView(AdminRequiredMixin, UpdateView):
    from booking.models import Xe
    model = Xe
    template_name = 'admin/xe_form.html'
    fields = ['bien_so', 'loai_xe', 'so_ghe']
    success_url = reverse_lazy('src:admin_xe_list')

class AdminXeDeleteView(AdminRequiredMixin, DeleteView):
    from booking.models import Xe
    model = Xe
    template_name = 'admin/confirm_delete.html'
    success_url = reverse_lazy('src:admin_xe_list')


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
    success_url = reverse_lazy('src:admin_chuyen_list')

class AdminChuyenUpdateView(AdminRequiredMixin, UpdateView):
    model = Chuyen
    template_name = 'admin/chuyen_form.html'
    fields = ['tuyen', 'xe', 'ngay_gio_khoi_hanh', 'ngay_gio_den', 'tong_so_ve', 'gia_ve']
    success_url = reverse_lazy('src:admin_chuyen_list')

class AdminChuyenDeleteView(AdminRequiredMixin, DeleteView):
    model = Chuyen
    template_name = 'admin/confirm_delete.html'
    success_url = reverse_lazy('src:admin_chuyen_list')


#==================== ADMIN TICKETS ====================#

class AdminVeListView(AdminRequiredMixin, ListView):
    model = Ve
    template_name = 'admin/ve_list.html'
    context_object_name = 'ves'
    paginate_by = 20

    def get_queryset(self):
        qs = Ve.objects.select_related('chuyen', 'khach', 'chuyen__tuyen').order_by('-id')
        
        # Tính năng tìm kiếm vé theo tên khách hoặc mã vé (nếu có)
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


#==================== ADMIN CUSTOMERS ====================#

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Lấy lịch sử đặt vé của khách này
        context['history_ves'] = Ve.objects.filter(
            khach=self.object
        ).select_related('chuyen', 'chuyen__tuyen').order_by('-chuyen__ngay_gio_khoi_hanh')
        return context

#==================== ADMIN EMPLOYEES ====================#

class AdminNhanVienListView(AdminRequiredMixin, ListView):
    model = NhanVien
    template_name = 'admin/nhanvien_list.html'
    context_object_name = 'nhanviens'
    paginate_by = 20

class AdminNhanVienCreateView(AdminRequiredMixin, CreateView):
    model = NhanVien
    template_name = 'admin/nhanvien_form.html'
    fields = ['user', 'anh_dai_dien', 'ho_ten', 'ngay_sinh', 'so_dien_thoai', 'chuc_vu', 'trang_thai']
    success_url = reverse_lazy('admin_panel:nhanvien_list')

class AdminNhanVienUpdateView(AdminRequiredMixin, UpdateView):
    model = NhanVien
    template_name = 'admin/nhanvien_form.html'
    fields = ['anh_dai_dien', 'ho_ten', 'ngay_sinh', 'so_dien_thoai', 'chuc_vu', 'trang_thai']
    success_url = reverse_lazy('admin_panel:nhanvien_list')

class AdminNhanVienDeleteView(AdminRequiredMixin, DeleteView):
    model = NhanVien
    template_name = 'admin/confirm_delete.html'
    success_url = reverse_lazy('admin_panel:nhanvien_list')


#==================== ADMIN VOUCHERS ====================#

class AdminVoucherListView(AdminRequiredMixin, ListView):
    model = Voucher
    template_name = 'admin/voucher_list.html'
    context_object_name = 'vouchers'
    paginate_by = 20

class AdminVoucherCreateView(AdminRequiredMixin, CreateView):
    model = Voucher
    template_name = 'admin/voucher_form.html'
    fields = ['ten_voucher', 'mo_ta', 'loai_giam_gia', 'gia_tri_giam', 'giam_toi_da', 
              'gia_tri_don_toi_thieu', 'ngay_bat_dau', 'ngay_ket_thuc', 'so_luong', 
              'khach_hang_duoc_su_dung', 'trang_thai']
    success_url = reverse_lazy('admin_panel:voucher_list')
    
    def form_valid(self, form):
        # Tự động tạo mã voucher
        form.instance.ma_voucher = Voucher.tao_ma_voucher()
        messages.success(self.request, f"Đã tạo voucher: {form.instance.ma_voucher}")
        return super().form_valid(form)

class AdminVoucherUpdateView(AdminRequiredMixin, UpdateView):
    model = Voucher
    template_name = 'admin/voucher_form.html'
    fields = ['ten_voucher', 'mo_ta', 'loai_giam_gia', 'gia_tri_giam', 'giam_toi_da',
              'gia_tri_don_toi_thieu', 'ngay_bat_dau', 'ngay_ket_thuc', 'so_luong',
              'khach_hang_duoc_su_dung', 'trang_thai']
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
            return VoucherSuDung.objects.filter(voucher_id=voucher_id)
        return VoucherSuDung.objects.all()



