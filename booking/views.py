from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.contrib import messages
from django.db import transaction
import uuid  

from .models import Tuyen, Chuyen, Ve, ThanhToan, Xe
from payment.services import VnPayService
from payment.models import PaymentInformationModel
from booking.models import Voucher, VoucherSuDung

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

        # Xử lý voucher
        ma_voucher = request.POST.get('voucher_code')
        voucher = None
        so_tien_giam = 0
        
        if ma_voucher:
            try:
                voucher = Voucher.objects.get(ma_voucher=ma_voucher)
                
                # Kiểm tra voucher còn hiệu lực
                if not voucher.con_hieu_luc():
                    messages.error(request, "❌ Voucher đã hết hạn hoặc hết lượt sử dụng!")
                    voucher = None
                
                # Kiểm tra user có quyền dùng voucher không
                elif voucher.khach_hang_duoc_su_dung.exists():  # Nếu có chỉ định user
                    if not voucher.khach_hang_duoc_su_dung.filter(id=khach_hang.id).exists():
                        messages.error(request, "❌ Bạn không có quyền sử dụng voucher này!")
                        voucher = None
                
                # Kiểm tra user đã dùng voucher này quá số lần cho phép chưa
                elif not voucher.user_con_duoc_dung(khach_hang):
                    messages.error(request, "❌ Bạn đã sử dụng hết lượt voucher này!")
                    voucher = None
                
                # Tính tiền giảm
                else:
                    so_tien_giam = voucher.tinh_giam_gia(tong_tien)
                    if so_tien_giam > 0:
                        tong_tien -= so_tien_giam
                        messages.success(request, f"✅ Áp dụng voucher thành công! Giảm {so_tien_giam:,.0f}đ")
                    else:
                        messages.warning(request, "⚠️ Đơn hàng chưa đủ điều kiện áp dụng voucher!")
                        voucher = None
                        
            except Voucher.DoesNotExist:
                messages.error(request, "❌ Mã voucher không tồn tại!")
        
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
                
                # Lưu lịch sử voucher
                if voucher and so_tien_giam > 0:
                    VoucherSuDung.objects.create(
                        voucher=voucher,
                        khach_hang=khach_hang,
                        ve=ve,
                        so_tien_giam=so_tien_giam
                    )
                    voucher.da_su_dung += 1
                    voucher.save()
                
                # Tạo Thanh Toán
                ThanhToan.objects.create(
                    ve=ve,
                    so_tien=tong_tien,  # Đã trừ voucher
                    phuong_thuc='VNPAY',
                    trang_thai='CHO_THANH_TOAN',
                    ma_giao_dich=txn_ref,  # Lưu mã số
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
        
        # Lấy danh sách voucher khả dụng cho user hiện tại
        khach_hang = self.request.user.khachhang
        vouchers = Voucher.objects.filter(
            trang_thai=True,
            ngay_bat_dau__lte=timezone.now(),
            ngay_ket_thuc__gte=timezone.now()
        ).filter(
            Q(khach_hang_duoc_su_dung__isnull=True) |  # Voucher cho tất cả
            Q(khach_hang_duoc_su_dung=khach_hang)      # Voucher cho user này
        ).distinct()
        
        context['vouchers'] = vouchers
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
