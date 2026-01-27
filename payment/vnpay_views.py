"""
VNPay payment return handling views.
"""
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
import uuid

from .services import VnPayService
from booking.models import Ve, ThanhToan, TemporaryReservation


class VnPayReturnView(View):
    """Handle VNPay payment return and complete the payment process."""
    
    def get(self, request):
        """Process VNPay return callback."""
        try:
            # Get VNPay service
            vnpay_service = VnPayService()
            
            # Validate payment response
            response = vnpay_service.payment_execute(request.GET)
            
            # Get payment info from session
            payment_info = request.session.get('payment_info')
            if not payment_info:
                messages.error(request, 'Không tìm thấy thông tin thanh toán.')
                return redirect('dashboard')
            
            # Check payment success
            if response.success and response.vn_pay_response_code == "00":
                return self.handle_payment_success(request, payment_info, response)
            else:
                return self.handle_payment_failure(request, payment_info, response)
                
        except Exception as e:
            messages.error(request, f'Có lỗi xảy ra khi xử lý thanh toán: {str(e)}')
            return redirect('dashboard')
    
    def handle_payment_success(self, request, payment_info, response):
        """Handle successful payment."""
        try:
            with transaction.atomic():
                ve_id = payment_info.get('ve_id')
                reservation_id = payment_info.get('reservation_id')
                
                if ve_id:
                    # Payment for existing ticket
                    ve = get_object_or_404(Ve, id=ve_id)
                    ve.trang_thai = 'DA_THANH_TOAN'
                    ve.save()
                    
                    # Create payment record
                    ma_giao_dich = response.transaction_id or f'VNP{uuid.uuid4().hex[:8].upper()}'
                    ThanhToan.objects.create(
                        ve=ve,
                        phuong_thuc='VNPAY',
                        trang_thai='THANH_CONG',
                        ma_giao_dich=ma_giao_dich,
                        so_tien=payment_info['amount']
                    )
                    
                    messages.success(
                        request,
                        f'Thanh toán thành công! Mã giao dịch: {ma_giao_dich}'
                    )
                    
                elif reservation_id:
                    # Create new ticket from reservation
                    reservation = get_object_or_404(TemporaryReservation, id=reservation_id)
                    
                    # Create ticket
                    ve = Ve.objects.create(
                        chuyen_id=payment_info['chuyen_id'],
                        khach=request.user.khachhang,
                        so_luong=payment_info['so_luong'],
                        vi_tri_ghe=payment_info['vi_tri_ghe'],
                        trang_thai='DA_THANH_TOAN'
                    )
                    
                    # Create payment record
                    ma_giao_dich = response.transaction_id or f'VNP{uuid.uuid4().hex[:8].upper()}'
                    ThanhToan.objects.create(
                        ve=ve,
                        phuong_thuc='VNPAY',
                        trang_thai='THANH_CONG',
                        ma_giao_dich=ma_giao_dich,
                        so_tien=payment_info['amount']
                    )
                    
                    # Mark reservation as expired
                    reservation.expire_reservation()
                    
                    # Clear session
                    if 'booking_data' in request.session:
                        del request.session['booking_data']
                    
                    messages.success(
                        request,
                        f'Đặt vé thành công! Mã giao dịch: {ma_giao_dich}'
                    )
                
                # Clear payment session
                if 'payment_info' in request.session:
                    del request.session['payment_info']
                
                return redirect('dashboard')
                
        except Exception as e:
            messages.error(request, f'Có lỗi xảy ra khi hoàn thành thanh toán: {str(e)}')
            return redirect('dashboard')
    
    def handle_payment_failure(self, request, payment_info, response):
        """Handle failed payment."""
        # Clear payment session but keep reservation for retry
        if 'payment_info' in request.session:
            del request.session['payment_info']
        
        # Show error message
        error_msg = self.get_vnpay_error_message(response.vn_pay_response_code)
        messages.error(request, f'Thanh toán thất bại: {error_msg}')
        
        return redirect('dashboard')
    
    def get_vnpay_error_message(self, error_code):
        """Get Vietnamese error message for VNPay error codes."""
        error_messages = {
            '07': 'Trừ tiền thành công. Giao dịch bị nghi ngờ (liên quan tới lừa đảo, giao dịch bất thường).',
            '09': 'Thẻ/Tài khoản của khách hàng chưa đăng ký dịch vụ InternetBanking.',
            '10': 'Khách hàng xác thực thông tin thẻ/tài khoản không đúng quá 3 lần.',
            '11': 'Đã hết hạn chờ thanh toán.',
            '12': 'Thẻ/Tài khoản của khách hàng bị khóa.',
            '13': 'Quý khách nhập sai mật khẩu xác thực giao dịch (OTP).',
            '24': 'Khách hàng hủy giao dịch.',
            '51': 'Tài khoản của quý khách không đủ số dư để thực hiện giao dịch.',
            '65': 'Tài khoản của Quý khách đã vượt quá hạn mức giao dịch trong ngày.',
            '75': 'Ngân hàng thanh toán đang bảo trì.',
            '79': 'KH nhập sai mật khẩu thanh toán quá số lần quy định.',
            '99': 'Các lỗi khác (lỗi còn lại, không có trong danh sách mã lỗi đã liệt kê).',
        }
        
        return error_messages.get(error_code, f'Lỗi không xác định (Mã: {error_code})')