# services.py
from django.conf import settings
from datetime import datetime
from .vnpay_library import VnPayLibrary
from .models import PaymentResponseModel

class VnPayService:
    def __init__(self):
        self.config = settings.VNPAY_CONFIG

    def create_payment_url(self, model, request):
        vnp = VnPayLibrary()
        
        time_now = datetime.now().strftime('%Y%m%d%H%M%S')
        
        vnp.add_request_data("vnp_Version", self.config["Version"])
        vnp.add_request_data("vnp_Command", self.config["Command"])
        vnp.add_request_data("vnp_TmnCode", self.config["TmnCode"])
        vnp.add_request_data("vnp_Amount", str(int(model.amount * 100)))
        vnp.add_request_data("vnp_CreateDate", time_now)
        vnp.add_request_data("vnp_CurrCode", self.config["CurrCode"])
        vnp.add_request_data("vnp_IpAddr", VnPayLibrary.get_ip_address(request))
        vnp.add_request_data("vnp_Locale", self.config["Locale"])
        vnp.add_request_data("vnp_OrderInfo", f"{model.name} {model.order_description} {model.amount}")
        vnp.add_request_data("vnp_OrderType", model.order_type)
        vnp.add_request_data("vnp_ReturnUrl", self.config["ReturnUrl"])
        
        vnp.add_request_data("vnp_TxnRef", model.order_id)  # ✅ ĐÚNG

        # *** THÊM LOG ĐỂ DEBUG ***
        print(f"🔍 DEBUG VNPAY: Mã gửi sang VNPAY = {model.order_id}")

        payment_url = vnp.create_request_url(self.config["BaseUrl"], self.config["HashSecret"])
        return payment_url

    def payment_execute(self, query_dict):
        vnp = VnPayLibrary()
        
        # Nạp dữ liệu từ query parameters vào thư viện
        for key, value in query_dict.items():
            if key.startswith("vnp_"):
                vnp.add_response_data(key, value)
                
        # Lấy các thông tin cần thiết
        vnp_secure_hash = query_dict.get('vnp_SecureHash')
        if not vnp_secure_hash:
            return PaymentResponseModel(
                success=False, payment_method="VnPay", 
                order_description="", order_id="", payment_id="", 
                transaction_id="", token="", vn_pay_response_code=""
            )

        check_signature = vnp.validate_signature(vnp_secure_hash, self.config["HashSecret"])
        
        if not check_signature:
            return PaymentResponseModel(
                success=False, payment_method="VnPay", 
                order_description="", order_id="", payment_id="", 
                transaction_id="", token="", vn_pay_response_code=""
            )

        return PaymentResponseModel(
            success=True,
            payment_method="VnPay",
            order_description=vnp.get_response_data("vnp_OrderInfo"),
            order_id=vnp.get_response_data("vnp_TxnRef"),
            payment_id=vnp.get_response_data("vnp_TransactionNo"),
            transaction_id=vnp.get_response_data("vnp_TransactionNo"),
            token=vnp_secure_hash,
            vn_pay_response_code=vnp.get_response_data("vnp_ResponseCode")
        )