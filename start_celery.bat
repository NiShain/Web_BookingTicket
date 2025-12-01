@echo off
echo ========================================
echo Starting Celery Worker, Beat and Django
echo ========================================


start "Celery Worker" cmd /k "python -m celery -A BookingTicket worker -l info -P eventlet"


timeout /t 3 /nobreak


start "Celery Beat" cmd /k "python -m celery -A BookingTicket beat -l info"


timeout /t 3 /nobreak


start "Django Server" cmd /k "python manage.py runserver"

echo ========================================
echo All services started!
echo ========================================
pause
