from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, View
from django.contrib import messages
from django.db import transaction
import uuid  
from datetime import timedelta
from django.http import JsonResponse
from datetime import datetime
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

        # Dữ liệu mặc định
        context['tuyen_popular'] = Tuyen.objects.annotate(
            chuyen_count=Count('chuyens')
        ).order_by('-chuyen_count')[:6]

        context['upcoming_chuyen'] = Chuyen.objects.filter(
            ngay_gio_khoi_hanh__gte=now
        ).order_by('ngay_gio_khoi_hanh')[:8]

        # ✅ XỬ LÝ TÌM KIẾM
        diem_di = self.request.GET.get('diem_di', '').strip()
        diem_den = self.request.GET.get('diem_den', '').strip()
        ngay_di = self.request.GET.get('ngay_gio_khoi_hanh', '').strip()

        # Nếu có tìm kiếm (ít nhất 1 trường)
        if diem_di or diem_den or ngay_di:
            context['is_searching'] = True
            context['search_params'] = {
                'diem_di': diem_di,
                'diem_den': diem_den,
                'ngay_gio_khoi_hanh': ngay_di,
            }

            # Lọc chuyến xe
            chuyens = Chuyen.objects.filter(
                ngay_gio_khoi_hanh__gte=now
            ).select_related('tuyen', 'xe')

            if diem_di:
                chuyens = chuyens.filter(tuyen__diem_di__icontains=diem_di)

            if diem_den:
                chuyens = chuyens.filter(tuyen__diem_den__icontains=diem_den)

            if ngay_di:
                try:
                    ngay_di_date = datetime.strptime(ngay_di, '%Y-%m-%d').date()
                    chuyens = chuyens.filter(ngay_gio_khoi_hanh__date=ngay_di_date)
                except ValueError:
                    pass

            context['search_results'] = chuyens.order_by('ngay_gio_khoi_hanh')[:50]
        else:
            context['is_searching'] = False

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
        """Helper method: Get list of booked seats - BAO GỒM CẢ CHO_THANH_TOAN"""
        booked_seats = []
        
        # LẤY CẢ VÉ ĐÃ THANH TOÁN VÀ ĐANG CHỜ THANH TOÁN
        for ve in chuyen.ves.filter(trang_thai__in=['DA_THANH_TOAN', 'CHO_THANH_TOAN']):
            # Kiểm tra vé chờ thanh toán có hết hạn không
            if ve.trang_thai == 'CHO_THANH_TOAN' and ve.kiem_tra_het_han():
                ve.huy_ve_het_han()  # Tự động hủy và hoàn ghế
                continue  # Bỏ qua vé này, ghế đã được giải phóng
            
            if ve.vi_tri_ghe:
                booked_seats.extend(ve.vi_tri_ghe)
        
        return booked_seats

    def _find_optimal_layout(self, total_seats, seats_per_row, back_range, ideal_back):
        """
        Tìm layout tối ưu cho ghế xe bus.
        
        Args:
            total_seats: Tổng số ghế
            seats_per_row: Số ghế mỗi hàng thường
            back_range: Tuple (min, max) số ghế hàng cuối
            ideal_back: Số ghế hàng cuối lý tưởng
            
        Returns:
            Tuple (normal_rows, last_row_seats)
        """
        min_back, max_back = back_range
        best_layout = None
        min_waste = float('inf')
        
        # Thử tìm layout chia hết hoàn toàn
        for back_seats in range(max_back, min_back - 1, -1):
            if back_seats > total_seats:
                continue
                
            normal_rows_needed = (total_seats - back_seats) / seats_per_row
            if normal_rows_needed == int(normal_rows_needed) and normal_rows_needed >= 1:
                return (int(normal_rows_needed), back_seats)
        
        # Nếu không chia hết, tìm layout gần nhất với lý tưởng
        for back_seats in range(min_back, max_back + 1):
            if back_seats > total_seats:
                continue
                
            normal_rows_needed = (total_seats - back_seats) // seats_per_row
            remaining = total_seats - (normal_rows_needed * seats_per_row + back_seats)
            
            if remaining >= 0 and normal_rows_needed >= 1:
                # Tính "độ lãng phí": ghế dư + khoảng cách với lý tưởng
                waste = remaining + abs(back_seats - ideal_back) * 0.5
                if waste < min_waste:
                    min_waste = waste
                    best_layout = (normal_rows_needed, back_seats)
        
        # Fallback cuối cùng nếu không tìm được
        if best_layout is None:
            normal_rows = max(1, total_seats // (seats_per_row + 1))
            last_seats = total_seats - (normal_rows * seats_per_row)
            # Đảm bảo last_seats trong range hợp lý
            last_seats = max(min_back, min(max_back, last_seats))
            best_layout = (normal_rows, last_seats)
            
        return best_layout

    def _generate_seat_layout(self, so_ghe):
        """Internal method: Generate seat layout structure following real bus layout."""
        if so_ghe <= 0:
            return []
            
        rows = []
        row_labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        seat_counter = 1
        
        # Logic tổng quát và hợp lý cho mọi số lượng ghế (6-49 ghế)
        if so_ghe <= 5:
            # Xe quá nhỏ: 1 hàng đơn giản
            normal_rows = 0
            seats_per_normal_row = 0
            normal_pattern = []
            last_row_seats = so_ghe
            
        elif so_ghe <= 12:
            # Xe mini (6-12 chỗ): 2-3 ghế/hàng, hàng cuối 3-4 ghế
            seats_per_normal_row = 2 if so_ghe <= 8 else 3
            normal_pattern = [0, 1] if seats_per_normal_row == 2 else [0, 1, None, 2]
            
            # Tìm layout tối ưu
            best_layout = self._find_optimal_layout(so_ghe, seats_per_normal_row, (3, 6), 4)
            normal_rows, last_row_seats = best_layout
                
        elif so_ghe <= 20:
            # Xe nhỏ (13-20 chỗ): 3-4 ghế/hàng, hàng cuối 4-5 ghế
            seats_per_normal_row = 3 if so_ghe <= 16 else 4
            normal_pattern = [0, 1, None, 2] if seats_per_normal_row == 3 else [0, 1, None, 2, 3]
            
            # Tìm layout tối ưu
            best_layout = self._find_optimal_layout(so_ghe, seats_per_normal_row, (3, 6), 5)
            normal_rows, last_row_seats = best_layout
                
        else:
            # Xe lớn (21-49 chỗ): 4 ghế/hàng, hàng cuối linh hoạt
            seats_per_normal_row = 4
            normal_pattern = [0, 1, None, 2, 3]
            
            # Xác định khoảng hàng cuối phù hợp theo size xe
            if so_ghe <= 30:
                back_range = (4, 6)
                ideal_back = 5
            elif so_ghe <= 40:
                back_range = (4, 7) 
                ideal_back = 6
            else:
                back_range = (5, 8)
                ideal_back = 6
            
            best_layout = self._find_optimal_layout(so_ghe, seats_per_normal_row, back_range, ideal_back)
            normal_rows, last_row_seats = best_layout
        
        # Tạo các hàng bình thường
        for row_index in range(normal_rows):
            if seat_counter > so_ghe:
                break
                
            row_label = row_labels[row_index] if row_index < len(row_labels) else f'R{row_index + 1}'
            row = []
            
            # Tạo hàng theo pattern bình thường
            seats_added = 0
            for pos in normal_pattern:
                if pos is None:
                    row.append(None)  # Lối đi
                else:
                    if seat_counter <= so_ghe and seats_added < seats_per_normal_row:
                        seat_label = f'{row_label}{seats_added + 1}'
                        row.append(seat_label)
                        seat_counter += 1
                        seats_added += 1
                    else:
                        row.append(None)  # Ghế trống nếu không đủ
            
            rows.append(row)
        
        # Tạo hàng cuối (hàng dài ở phía sau)
        if last_row_seats > 0 and seat_counter <= so_ghe:
            row_index = len(rows)
            row_label = row_labels[row_index] if row_index < len(row_labels) else f'R{row_index + 1}'
            last_row = []
            
            # Tạo hàng cuối với 4-5 ghế liên tiếp (không có lối đi)
            for i in range(last_row_seats):
                if seat_counter <= so_ghe:
                    seat_label = f'{row_label}{i + 1}'
                    last_row.append(seat_label)
                    seat_counter += 1
            
            rows.append(last_row)
        
        return rows

    def get(self, request, *args, **kwargs):
        chuyen = self.get_chuyen()
        now = timezone.now()
        
        if chuyen.ngay_gio_khoi_hanh < now:
            messages.error(request, 'Chuyến xe này đã khởi hành.')
            return redirect('src:danh_sach_chuyen_xe')

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        selected_seats = request.POST.getlist('seats')
        
        if not selected_seats:
            messages.error(request, 'Vui lòng chọn ít nhất một ghế.')
            return self.get(request, *args, **kwargs)
        
        khach_hang = request.user.khachhang
        ma_voucher = request.POST.get('voucher_code')
        txn_ref = str(uuid.uuid4().int)[:10]
        
        try:
            with transaction.atomic():
                # ✅ LOCK HÀNG TRONG DATABASE (ngăn race condition)
                chuyen = Chuyen.objects.select_for_update().select_related(
                    'tuyen', 'xe'
                ).get(pk=self.kwargs['chuyen_id'])
                
                # ✅ LẤY LẠI DANH SÁCH GHẾ ĐÃ ĐẶT (trong transaction)
                booked_seats = []
                for ve in chuyen.ves.filter(
                    trang_thai__in=['DA_THANH_TOAN', 'CHO_THANH_TOAN']
                ).select_for_update():
                    # Kiểm tra vé hết hạn
                    if ve.trang_thai == 'CHO_THANH_TOAN' and ve.kiem_tra_het_han():
                        ve.huy_ve_het_han()
                        continue
                    
                    if ve.vi_tri_ghe:
                        booked_seats.extend(ve.vi_tri_ghe)
                
                # ✅ KIỂM TRA XUNG ĐỘT GHẾ (trong transaction)
                conflict = set(selected_seats) & set(booked_seats)
                if conflict:
                    messages.error(request, f'❌ Ghế {", ".join(conflict)} đã được người khác đặt.')
                    return self.get(request, *args, **kwargs)
                
                # ✅ KIỂM TRA SỐ VÉ CÒN LẠI
                if len(selected_seats) > chuyen.tong_so_ve:
                    messages.error(request, f'❌ Chỉ còn {chuyen.tong_so_ve} ghế trống.')
                    return self.get(request, *args, **kwargs)
                
                # ✅ KIỂM TRA CHUYẾN ĐÃ KHỞI HÀNH CHƯA
                if chuyen.ngay_gio_khoi_hanh <= timezone.now():
                    messages.error(request, '❌ Chuyến xe đã khởi hành.')
                    return redirect('src:danh_sach_chuyen_xe')
                
                # ✅ TRỪ SỐ VÉ NGAY LẬP TỨC
                chuyen.tong_so_ve -= len(selected_seats)
                chuyen.save()
                
                # Tính tiền
                tong_tien = chuyen.gia_ve * len(selected_seats)
                
                # Xử lý voucher
                voucher = None
                so_tien_giam = 0
                
                if ma_voucher:
                    try:
                        voucher = Voucher.objects.select_for_update().get(
                            ma_voucher=ma_voucher
                        )
                        
                        if not voucher.con_hieu_luc():
                            messages.error(request, "❌ Voucher đã hết hạn!")
                            voucher = None
                        elif voucher.khach_hang_duoc_su_dung.exists():
                            if not voucher.khach_hang_duoc_su_dung.filter(id=khach_hang.id).exists():
                                messages.error(request, "❌ Bạn không có quyền sử dụng voucher!")
                                voucher = None
                        elif not voucher.user_con_duoc_dung(khach_hang):
                            messages.error(request, "❌ Bạn đã hết lượt sử dụng voucher!")
                            voucher = None
                        else:
                            so_tien_giam = voucher.tinh_giam_gia(tong_tien)
                            if so_tien_giam > 0:
                                tong_tien -= so_tien_giam
                                messages.success(request, f"✅ Giảm {so_tien_giam:,.0f}đ")
                            else:
                                voucher = None
                    except Voucher.DoesNotExist:
                        messages.error(request, "❌ Mã voucher không tồn tại!")
                
                # Tạo Vé
                ve = Ve.objects.create(
                    chuyen=chuyen,
                    khach=khach_hang,
                    so_luong=len(selected_seats),
                    vi_tri_ghe=selected_seats,
                    trang_thai='CHO_THANH_TOAN',
                    han_thanh_toan=timezone.now() + timedelta(minutes=10)
                )
                
                # Lưu voucher
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
                    so_tien=tong_tien,
                    phuong_thuc='VNPAY',
                    trang_thai='CHO_THANH_TOAN',
                    ma_giao_dich=txn_ref,
                )
                
                # Tạo URL VNPAY
                payment_info = PaymentInformationModel(
                    order_type="billpayment",
                    amount=float(tong_tien),
                    order_description=f"Thanh toan ve {txn_ref}",
                    name=khach_hang.ten,
                    order_id=txn_ref
                )
                
                vnp_service = VnPayService()
                payment_url = vnp_service.create_payment_url(payment_info, request)
                
                # ✅ TRANSACTION COMMIT TẠI ĐÂY (auto)
                # Sau khi commit, Lock được giải phóng
                
        except Chuyen.DoesNotExist:
            messages.error(request, '❌ Không tìm thấy chuyến xe.')
            return redirect('src:danh_sach_chuyen_xe')
        except Exception as e:
            messages.error(request, f'❌ Lỗi: {str(e)}')
            return self.get(request, *args, **kwargs)
        
        if payment_url:
            return redirect(payment_url)
        
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        chuyen = self.get_chuyen()
        booked_seats = self.get_booked_seats(chuyen)

        seat_layout = self._generate_seat_layout(chuyen.xe.so_ghe)

        # *** TÍNH SỐ GHẾ CÒN LẠI DựA TRÊN tong_so_ve ***
        context.update({
            'chuyen': chuyen,
            'booked_seats': booked_seats,
            'seat_layout': seat_layout,
            'so_ghe_con_lai': chuyen.tong_so_ve,  # ĐÃ TRỪ SẴN
        })
        
        # ✅ LẤY DANH SÁCH VOUCHER HỢP LỆ
        khach_hang = self.request.user.khachhang
        now = timezone.now()
        
        # Lấy tất cả voucher đang hoạt động và trong thời hạn
        all_vouchers = Voucher.objects.filter(
            trang_thai=True,
            ngay_bat_dau__lte=now,
            ngay_ket_thuc__gte=now
        ).filter(
            Q(khach_hang_duoc_su_dung__isnull=True) |
            Q(khach_hang_duoc_su_dung=khach_hang)
        ).distinct()
        
        # ✅ LỌC THÊM: Chỉ lấy voucher còn slot và user còn lượt dùng
        valid_vouchers = []
        for voucher in all_vouchers:
            # Kiểm tra còn số lượng không
            if voucher.da_su_dung >= voucher.so_luong:
                continue
            
            # Kiểm tra user còn lượt dùng không
            so_lan_da_dung = voucher.user_da_dung_bao_nhieu_lan(khach_hang)
            if so_lan_da_dung >= voucher.so_lan_su_dung_toi_da_moi_user:
                continue
            
            # Kiểm tra voucher còn hiệu lực (method có sẵn trong model)
            if not voucher.con_hieu_luc():
                continue
            
            valid_vouchers.append(voucher)
        
        context['vouchers'] = valid_vouchers
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


class HuyVeView(LoginRequiredMixin, View):
    """View xử lý hủy vé"""
    
    def post(self, request, ve_id):
        try:
            # Lấy vé của user hiện tại
            ve = Ve.objects.select_related('chuyen').get(
                id=ve_id,
                khach=request.user.khachhang
            )
            
            # Kiểm tra và hủy
            if ve.co_the_huy():
                if ve.huy_ve():
                    messages.success(request, f'✅ Đã hủy vé thành công! Hoàn lại {ve.so_luong} ghế.')
                    
                    # Nếu là AJAX request
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': 'Hủy vé thành công!'
                        })
                else:
                    messages.error(request, '❌ Không thể hủy vé.')
            else:
                messages.error(request, '❌ Vé không thể hủy (đã khởi hành hoặc đã hủy trước đó).')
                
        except Ve.DoesNotExist:
            messages.error(request, '❌ Không tìm thấy vé.')
        except Exception as e:
            messages.error(request, f'❌ Lỗi: {str(e)}')
        
        # Redirect về trang lịch sử đặt vé
        return redirect('src:lich_su_dat_ve')


class LichSuDatVeView(LoginRequiredMixin, ListView):
    """Danh sách vé đã đặt của khách hàng"""
    model = Ve
    template_name = 'booking/lich_su_dat_ve.html'
    context_object_name = 'ves'
    paginate_by = 10
    
    def get_queryset(self):
        return Ve.objects.filter(
            khach=self.request.user.khachhang
        ).select_related('chuyen__tuyen', 'chuyen__xe').order_by('-ngay_dat')
