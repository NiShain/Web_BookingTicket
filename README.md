# Web_BookingTicket
Web about Booking Ticket using django_python
To run this web you need to have Virtual Environment
using following command and run it in terminal:
# move to your project folder
cd [...]/your_project
# Create venv
python -m venv venv
# activate venv (using terminal)
venv\Scripts\activate.bat
# install all necessary lib 
python -m pip install Django mysqlclient pillow redis==4.6.0 celery eventlet
# run webapp
.\start_celery.bat