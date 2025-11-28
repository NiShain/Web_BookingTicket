# views.py
from django.shortcuts import redirect
from django.views import View
from .models import PaymentInformationModel
from .services import VnPayService
from booking.models import ThanhToan
from django.contrib import messages

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