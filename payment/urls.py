# urls.py
from django.urls import path
from .views import PaymentController

payment_controller = PaymentController()

urlpatterns = [
   path('create_payment', payment_controller.create_payment_url_vnpay, name='create_payment'),
    path('callback_vnpay', payment_controller.payment_callback_vnpay, name='payment_callback'),
]