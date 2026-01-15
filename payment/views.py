# views.py
from django.shortcuts import redirect
from django.views import View
from .models import PaymentInformationModel
from .services import VnPayService
from booking.models import ThanhToan
from django.contrib import messages
from django.http import HttpResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from booking.models import ThanhToan, Ve, VoucherSuDung
from .services import VnPayService

class PaymentController(View):
    # Tương ứng với action CreatePaymentUrlVnpay
    def create_payment_url_vnpay(self, request):
        # Giả lập dữ liệu từ model (thực tế bạn lấy từ form hoặc DB)
        payment_info = PaymentInformationModel(
            order_type="other",
            amount=100000,
            order_description="Thanh toan don hang test",
            name="Khach Hang A"
        )
        
        vn_pay_service = VnPayService()
        url = vn_pay_service.create_payment_url(payment_info, request)
        
        return redirect(url)

    # Tương ứng với action PaymentCallbackVnpay
    def payment_callback_vnpay(self, request):
        vn_pay_service = VnPayService()
        
        # Xử lý, validate chữ ký và lấy dữ liệu
        response_model = vn_pay_service.payment_execute(request.GET)
        
        # Lấy mã giao dịch (quan trọng: lấy từ vnp_TxnRef nếu order_id null)
        txn_ref = response_model.order_id or request.GET.get('vnp_TxnRef')

        if response_model.success and response_model.vn_pay_response_code == "00":
            # === THANH TOÁN THÀNH CÔNG ===
            try:
                # Tìm bản ghi thanh toán
                giao_dich = ThanhToan.objects.get(ma_giao_dich=txn_ref)
                
                # Cập nhật trạng thái
                if giao_dich.trang_thai != 'THANH_CONG':
                    giao_dich.trang_thai = 'THANH_CONG'
                    giao_dich.save()
                    
                    # Cập nhật vé
                    ve = giao_dich.ve
                    ve.trang_thai = 'DA_THANH_TOAN'
                    ve.save()

                messages.success(request, f"Thanh toán thành công vé {txn_ref}!")
                
                # Redirect về trang Success (Không cần login vẫn xem được nếu logic view cho phép)
                return redirect(f'/src/payment/success/?vnp_TxnRef={txn_ref}')

            except ThanhToan.DoesNotExist:
                messages.error(request, f"Không tìm thấy giao dịch: {txn_ref}")
                return redirect('home')  # <--- SỬA Ở ĐÂY (Bỏ 'src:')
        else:
            messages.error(request, "Giao dịch thanh toán bị hủy hoặc lỗi.")
            return redirect('home')      # <--- SỬA Ở ĐÂY (Bỏ 'src:')
        
@method_decorator(csrf_exempt, name='dispatch')
class VNPayReturnView(View):
    """Xử lý callback từ VNPAY sau khi thanh toán"""
    
    def get(self, request):
        vnp_service = VnPayService()
        
        # Lấy tất cả params từ VNPAY
        input_data = request.GET
        
        # Validate chữ ký
        if vnp_service.validate_response(input_data):
            # Lấy thông tin giao dịch
            vnp_ResponseCode = input_data.get('vnp_ResponseCode')
            vnp_TxnRef = input_data.get('vnp_TxnRef')
            
            try:
                with transaction.atomic():
                    # Tìm thanh toán
                    thanh_toan = ThanhToan.objects.select_for_update().get(
                        ma_giao_dich=vnp_TxnRef
                    )
                    ve = thanh_toan.ve
                    
                    # ✅ THANH TOÁN THÀNH CÔNG
                    if vnp_ResponseCode == '00':
                        # Cập nhật trạng thái thanh toán
                        thanh_toan.trang_thai = 'THANH_CONG'
                        thanh_toan.save()
                        
                        # Cập nhật trạng thái vé
                        ve.trang_thai = 'DA_THANH_TOAN'
                        ve.save()
                        
                        # ✅ CHỈ BÂY GIỜ MỚI TĂNG voucher.da_su_dung
                        voucher_su_dung = VoucherSuDung.objects.filter(ve=ve).first()
                        if voucher_su_dung:
                            voucher = voucher_su_dung.voucher
                            voucher.da_su_dung += 1
                            voucher.save()
                        
                        return redirect('src:payment_success')
                    
                    # ❌ THANH TOÁN THẤT BẠI
                    else:
                        # Hủy vé và hoàn ghế
                        ve.huy_ve_het_han()
                        
                        thanh_toan.trang_thai = 'THAT_BAI'
                        thanh_toan.save()
                        
                        return redirect('src:payment_failed')
                        
            except ThanhToan.DoesNotExist:
                return HttpResponse('Transaction not found', status=404)
        else:
            return HttpResponse('Invalid signature', status=400)