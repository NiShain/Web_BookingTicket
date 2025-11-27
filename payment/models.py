from django.db import models
from dataclasses import dataclass

@dataclass
class PaymentInformationModel:
    order_type: str
    amount: float
    order_description: str
    name: str

@dataclass
class PaymentResponseModel:
    order_description: str
    transaction_id: str
    order_id: str
    payment_method: str
    payment_id: str
    success: bool
    token: str
    vn_pay_response_code: str