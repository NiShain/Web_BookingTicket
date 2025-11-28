# vnpay_library.py
import hashlib
import hmac
import urllib.parse

class VnPayLibrary:
    def __init__(self):
        self._request_data = {}
        self._response_data = {}

    def add_request_data(self, key, value):
        if value:
            self._request_data[key] = str(value)

    def add_response_data(self, key, value):
        if value:
            self._response_data[key] = str(value)

    def get_response_data(self, key):
        return self._response_data.get(key, "")

    def create_request_url(self, base_url, vnp_hash_secret):
        # Sắp xếp dữ liệu theo key (giống SortedList trong C#)
        sorted_data = sorted(self._request_data.items())
        
        query_string = []
        for key, value in sorted_data:
            if value:
                encoded_key = urllib.parse.quote_plus(key)
                encoded_value = urllib.parse.quote_plus(value)
                query_string.append(f"{encoded_key}={encoded_value}")
        
        query_string_str = "&".join(query_string)
        base_url += "?" + query_string_str
        
        # Tạo mã hash
        vnp_secure_hash = self._hmac_sha512(vnp_hash_secret, query_string_str)
        base_url += "&vnp_SecureHash=" + vnp_secure_hash
        
        return base_url

    def validate_signature(self, input_hash, secret_key):
        rsp_raw = self._get_response_data_string()
        my_checksum = self._hmac_sha512(secret_key, rsp_raw)
        return my_checksum == input_hash

    def _hmac_sha512(self, key, data):
        byte_key = key.encode('utf-8')
        byte_data = data.encode('utf-8')
        return hmac.new(byte_key, byte_data, hashlib.sha512).hexdigest()

    def _get_response_data_string(self):
        # Loại bỏ các tham số hash để tính toán lại checksum
        data = self._response_data.copy()
        if 'vnp_SecureHash' in data:
            del data['vnp_SecureHash']
        if 'vnp_SecureHashType' in data:
            del data['vnp_SecureHashType']
            
        sorted_data = sorted(data.items())
        
        query_string = []
        for key, value in sorted_data:
            if value:
                encoded_key = urllib.parse.quote_plus(key)
                encoded_value = urllib.parse.quote_plus(value)
                query_string.append(f"{encoded_key}={encoded_value}")
                
        return "&".join(query_string)

    # Hàm tiện ích lấy IP (giống hàm GetIpAddress C#)
    @staticmethod
    def get_ip_address(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip