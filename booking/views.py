from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, ListView, UpdateView, CreateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from users.models import KhachHang
from django.db import transaction
import json
import uuid  

from .models import Tuyen, Chuyen, Ve, ThanhToan, Xe
from payment.services import VnPayService
from payment.models import PaymentInformationModel

class HomeView(TemplateView):
    """Homepage view with popular routes and upcoming trips."""
    template_name = 'base/home.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        context['tuyen_popular'] = Tuyen.objects.annotate(
            chuyen_count=Count('chuyens')
        ).order_by('-chuyen_count')[:6]

        context['upcoming_chuyen'] = Chuyen.objects.filter(
            ngay_gio_khoi_hanh__gte=now
        ).order_by('ngay_gio_khoi_hanh')[:8]

        return context


class DanhSachTuyenView(ListView):
    """List view for routes (Tuyen) with trip count."""
    model = Tuyen
    template_name = 'booking/danh_sach_tuyens.html'
    context_object_name = 'tuyens'

    def get_queryset(self):
        return Tuyen.objects.annotate(
            chuyen_count=Count('chuyens')
        ).order_by('diem_di', 'diem_den')


class DanhSachChuyenXeView(ListView):
    """List view for trips (Chuyen) with filtering and pagination."""
    model = Chuyen
    template_name = 'booking/danh_sach_chuyen_xe.html'
    context_object_name = 'chuyens'
    paginate_by = 12

    def get_queryset(self):
        now = timezone.now()
        qs = Chuyen.objects.filter(
            ngay_gio_khoi_hanh__gte=now
        ).select_related('tuyen', 'xe').order_by('ngay_gio_khoi_hanh')

        # Filter xử lý gọn gàng hơn
        tuyen_id = self.request.GET.get('tuyen_id')
        if tuyen_id:
            try:
                qs = qs.filter(tuyen__id=int(tuyen_id))
            except (ValueError, TypeError):
                pass
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        tuyen_id = self.request.GET.get('tuyen_id')
        selected_tuyen = None
        if tuyen_id:
            try:
                selected_tuyen = Tuyen.objects.get(pk=int(tuyen_id))
            except (Tuyen.DoesNotExist, ValueError, TypeError):
                pass

        context['selected_tuyen'] = selected_tuyen
        return context


class ChonGheView(LoginRequiredMixin, TemplateView):
    """Seat selection view for a specific trip."""
    template_name = 'booking/chon_ghe.html'

    def get_chuyen(self):
        """Helper method: Get the trip object."""
        return get_object_or_404(
            Chuyen.objects.select_related('tuyen', 'xe'),
            pk=self.kwargs['chuyen_id']
        )

    def get_booked_seats(self, chuyen):
        """Helper method: Get list of booked seats."""
        booked_seats = []
        for ve in chuyen.ves.filter(trang_thai='DA_THANH_TOAN'):
            if ve.vi_tri_ghe:
                booked_seats.extend(ve.vi_tri_ghe)
        return booked_seats

 
    def _generate_seat_layout(self, so_ghe):
        """Internal method: Generate seat layout structure."""
        rows = []
        row_labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        if so_ghe <= 16:
            seats_per_row = 2
            layout_pattern = [0, None, 1]
            last_row_seats = min(4, so_ghe)
        elif so_ghe <= 30:
            seats_per_row = 3
            layout_pattern = [0, 1, None, 2]
            last_row_seats = min(4, so_ghe)
        else:
            seats_per_row = 4
            layout_pattern = [0, 1, None, 2, 3]
            last_row_seats = min(4, so_ghe)

        normal_rows_seats = (so_ghe - last_row_seats) if so_ghe > last_row_seats else 0
        normal_rows_count = normal_rows_seats // seats_per_row
        remaining_for_last = so_ghe - (normal_rows_count * seats_per_row)

        row_index = 0
        seat_index = 0

        while seat_index < normal_rows_count * seats_per_row:
            row = []
            row_label = row_labels[row_index] if row_index < len(row_labels) else f'R{row_index}'

            for pos in layout_pattern:
                if pos is None:
                    row.append(None)
                elif seat_index < normal_rows_count * seats_per_row:
                    seat_label = f'{row_label}{pos + 1}'
                    row.append(seat_label)
                    seat_index += 1
                else:
                    row.append(None)

            if any(seat for seat in row if seat):
                rows.append(row)
            row_index += 1

        if remaining_for_last > 0:
            last_row = []
            row_label = row_labels[row_index] if row_index < len(row_labels) else f'R{row_index}'
            for col in range(1, remaining_for_last + 1):
                seat_label = f'{row_label}{col}'
                last_row.append(seat_label)
            rows.append(last_row)

        return rows

    def get(self, request, *args, **kwargs):
        chuyen = self.get_chuyen()
        now = timezone.now()
        
        # Validation logic giữ nguyên nhưng gọn gàng hơn
        if chuyen.ngay_gio_khoi_hanh < now:
            messages.error(request, 'Chuyến xe này đã khởi hành.')
            return redirect('danh-sach-chuyen') # Sửa tên URL cho đúng chuẩn (giả sử tên url của bạn)

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        chuyen = self.get_chuyen()
        booked_seats = self.get_booked_seats(chuyen)
        selected_seats = request.POST.getlist('seats')

        # 1. Validate ghế
        if not selected_seats:
            messages.error(request, 'Vui lòng chọn ít nhất một ghế.')
            return self.get(request, *args, **kwargs)

        conflict = set(selected_seats) & set(booked_seats)
        if conflict:
            messages.error(request, f'Ghế {", ".join(conflict)} đã được đặt.')
            return self.get(request, *args, **kwargs)

        # 2. Chuẩn bị dữ liệu
        khach_hang = request.user.khachhang
        tong_tien = chuyen.gia_ve * len(selected_seats)
        
        # *** CHỈ TẠO MỘT LẦN VỚI ĐỊNH DẠNG SỐ ***
        txn_ref = str(uuid.uuid4().int)[:10]  # Ví dụ: '1764267851'
        
        payment_url = None

        try:
            with transaction.atomic():
                # Tạo Vé
                ve = Ve.objects.create(
                    chuyen=chuyen,
                    khach=khach_hang,
                    so_luong=len(selected_seats),
                    vi_tri_ghe=selected_seats,
                    trang_thai='CHO_THANH_TOAN'
                )
                
                # *** XÓA DÒNG: txn_ref = f"VE-{uuid.uuid4().hex[:8].upper()}" ***
                
                # Tạo Thanh Toán
                ThanhToan.objects.create(
                    ve=ve,
                    phuong_thuc='VNPAY',
                    trang_thai='CHO_THANH_TOAN',
                    ma_giao_dich=txn_ref,  # Lưu mã số
                    so_tien=tong_tien
                )
                
                # Tạo URL VNPAY
                payment_info = PaymentInformationModel(
                    order_type="billpayment",
                    amount=float(tong_tien),
                    order_description=f"Thanh toan ve {txn_ref}",
                    name=khach_hang.ten,
                    order_id=txn_ref  # Gửi mã số sang VNPAY
                )
                
                vnp_service = VnPayService()
                payment_url = vnp_service.create_payment_url(payment_info, request)

        except Exception as e:
            messages.error(request, f'Lỗi khởi tạo: {str(e)}')
            return self.get(request, *args, **kwargs)

        if payment_url:
            return redirect(payment_url)
            
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chuyen = self.get_chuyen()
        booked_seats = self.get_booked_seats(chuyen)

        seat_layout = self._generate_seat_layout(chuyen.xe.so_ghe)

        context.update({
            'chuyen': chuyen,
            'booked_seats': booked_seats,
            'seat_layout': seat_layout,
            'so_ghe_con_lai': chuyen.tong_so_ve - len(booked_seats),
        })
        return context



    
#====================== ADMIN ======================#
    
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_active and self.request.user.is_staff
    
class AdminTuyenListView(AdminRequiredMixin, ListView):
    model = Tuyen
    template_name = 'booking/admin/tuyen_list.html'
    context_object_name = 'tuyens'
    paginate_by = 10

class AdminTuyenCreateView(AdminRequiredMixin, CreateView):
    model = Tuyen
    template_name = 'booking/admin/tuyen_form.html'
    fields = ['diem_di', 'diem_den', 'khoang_cach']
    success_url = reverse_lazy('src:admin_tuyen_list')
    extra_context = {'title': 'Thêm Tuyến Mới'}

class AdminTuyenUpdateView(AdminRequiredMixin, UpdateView):
    model = Tuyen
    template_name = 'booking/admin/tuyen_form.html'
    fields = ['diem_di', 'diem_den', 'khoang_cach']
    success_url = reverse_lazy('src:admin_tuyen_list')
    extra_context = {'title': 'Cập nhật Tuyến'}

class AdminTuyenDeleteView(AdminRequiredMixin, DeleteView):
    model = Tuyen
    template_name = 'booking/admin/confirm_delete.html'
    success_url = reverse_lazy('src:admin_tuyen_list')

class AdminXeListView(AdminRequiredMixin, ListView):
    model = Tuyen # Lưu ý: Sửa lại thành Xe khi bạn có model Xe import vào
    # Giả sử bạn đã import Xe:
    # model = Xe 
    template_name = 'booking/admin/xe_list.html'
    context_object_name = 'xes'

    def get_queryset(self):
        # Import Xe cục bộ nếu chưa có ở đầu file
        from .models import Xe
        return Xe.objects.all()

class AdminXeCreateView(AdminRequiredMixin, CreateView):
    from .models import Xe
    model = Xe
    template_name = 'booking/admin/xe_form.html'
    fields = ['bien_so', 'loai_xe', 'so_ghe']
    success_url = reverse_lazy('src:admin_xe_list')

class AdminXeUpdateView(AdminRequiredMixin, UpdateView):
    from .models import Xe
    model = Xe
    template_name = 'booking/admin/xe_form.html'
    fields = ['bien_so', 'loai_xe', 'so_ghe']
    success_url = reverse_lazy('src:admin_xe_list')

class AdminXeDeleteView(AdminRequiredMixin, DeleteView):
    from .models import Xe
    model = Xe
    template_name = 'booking/admin/confirm_delete.html'
    success_url = reverse_lazy('src:admin_xe_list')


class AdminChuyenListView(AdminRequiredMixin, ListView):
    model = Chuyen
    template_name = 'booking/admin/chuyen_list.html'
    context_object_name = 'chuyens'
    paginate_by = 10

    def get_queryset(self):
        # Hiển thị thêm thông tin số vé đã bán để dễ theo dõi
        return Chuyen.objects.select_related('tuyen', 'xe').annotate(
            so_ve_da_ban=Count('ves', filter=Q(ves__trang_thai='DA_THANH_TOAN'))
        ).order_by('-ngay_gio_khoi_hanh')

class AdminChuyenCreateView(AdminRequiredMixin, CreateView):
    model = Chuyen
    template_name = 'booking/admin/chuyen_form.html'
    fields = ['tuyen', 'xe', 'ngay_gio_khoi_hanh', 'ngay_gio_den', 'tong_so_ve', 'gia_ve']
    success_url = reverse_lazy('src:admin_chuyen_list')

class AdminChuyenUpdateView(AdminRequiredMixin, UpdateView):
    model = Chuyen
    template_name = 'booking/admin/chuyen_form.html'
    fields = ['tuyen', 'xe', 'ngay_gio_khoi_hanh', 'ngay_gio_den', 'tong_so_ve', 'gia_ve']
    success_url = reverse_lazy('src:admin_chuyen_list')

class AdminChuyenDeleteView(AdminRequiredMixin, DeleteView):
    model = Chuyen
    template_name = 'booking/admin/confirm_delete.html'
    success_url = reverse_lazy('src:admin_chuyen_list')


#==================== ADMIN TICKETS ====================#

class AdminVeListView(AdminRequiredMixin, ListView):
    model = Ve
    template_name = 'booking/admin/ve_list.html'
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
    template_name = 'booking/admin/ve_detail.html'
    context_object_name = 've'


#==================== ADMIN CUSTOMERS ====================#

class AdminKhachHangListView(AdminRequiredMixin, ListView):
    model = KhachHang
    template_name = 'booking/admin/khachhang_list.html'
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
    template_name = 'booking/admin/khachhang_detail.html'
    context_object_name = 'khach'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Lấy lịch sử đặt vé của khách này
        context['history_ves'] = Ve.objects.filter(
            khach=self.object
        ).select_related('chuyen', 'chuyen__tuyen').order_by('-chuyen__ngay_gio_khoi_hanh')
        return context

class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'booking/payment_success.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Lấy mã giao dịch từ URL (nếu VNPAY trả về vnp_TxnRef)
        txn_ref = self.request.GET.get('vnp_TxnRef') or self.request.GET.get('order_id')
        
        if txn_ref:
            try:
                # Tìm vé dựa trên mã giao dịch trong bảng ThanhToan
                thanh_toan = ThanhToan.objects.get(ma_giao_dich=txn_ref)
                context['ve'] = thanh_toan.ve
            except ThanhToan.DoesNotExist:
                pass
        return context

class PaymentProcessingView(TemplateView):
    template_name = 'booking/payment_processing.html'