from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import json

from .models import Tuyen, Chuyen, Ve


def home(request):
	"""Render the site homepage with dynamic sections:

	- tuyen_popular: top routes ordered by number of trips (chuyens)
	- upcoming_chuyen: next upcoming trips ordered by departure time
	"""
	# If user is authenticated, redirect to their dashboard
	if request.user.is_authenticated:
		from django.shortcuts import redirect
		return redirect('dashboard')
	
	# For non-authenticated users, show the public home page
	# Popular routes by number of related Chuyen objects
	tuyen_popular = Tuyen.objects.annotate(chuyen_count=Count('chuyens')).order_by('-chuyen_count')[:6]

	# Upcoming trips (from now), next 8
	now = timezone.now()
	upcoming_chuyen = Chuyen.objects.filter(ngay_gio_khoi_hanh__gte=now).order_by('ngay_gio_khoi_hanh')[:8]

	context = {
		'tuyen_popular': tuyen_popular,
		'upcoming_chuyen': upcoming_chuyen,
	}
	
	return render(request, 'base/home.html', context)


def danh_sach_tuyens(request):
	"""View: show list of routes (Tuyen) with number of trips."""
	tuyen_list = Tuyen.objects.annotate(chuyen_count=Count('chuyens')).order_by('diem_di', 'diem_den')
	context = {
		'tuyens': tuyen_list,
	}
	return render(request, 'booking/danh_sach_tuyens.html', context)


def danh_sach_chuyen_xe(request):
	"""View: show list of trips (Chuyen). Supports optional filtering by `tuyen_id` and pagination.

	Context provided to template:
	- chuyens: list of Chuyen objects for current page
	- page_obj: Django Paginator Page instance
	- selected_tuyen: Tuyen instance when filtered, else None
	"""
	now = timezone.now()
	qs = Chuyen.objects.filter(ngay_gio_khoi_hanh__gte=now).select_related('tuyen', 'xe').order_by('ngay_gio_khoi_hanh')

	# optional filter by route
	tuyen_id = request.GET.get('tuyen_id')
	selected_tuyen = None
	if tuyen_id:
		try:
			selected_tuyen = Tuyen.objects.get(pk=int(tuyen_id))
		except (Tuyen.DoesNotExist, ValueError, TypeError):
			selected_tuyen = None
		else:
			qs = qs.filter(tuyen=selected_tuyen)

	# pagination
	from django.core.paginator import Paginator

	per_page = 12
	paginator = Paginator(qs, per_page)
	page_number = request.GET.get('page')
	page_obj = paginator.get_page(page_number)

	context = {
		'chuyens': page_obj.object_list,
		'page_obj': page_obj,
		'selected_tuyen': selected_tuyen,
	}
	return render(request, 'booking/danh_sach_chuyen_xe.html', context)


@login_required
def chon_ghe(request, chuyen_id):
	"""View: Seat selection page for a specific trip.
	
	Displays seat map with booked/available seats.
	POST: saves selected seats to session and redirects to payment.
	"""
	chuyen = get_object_or_404(
		Chuyen.objects.select_related('tuyen', 'xe'),
		pk=chuyen_id
	)
	
	# Check if trip is still available
	now = timezone.now()
	if chuyen.ngay_gio_khoi_hanh < now:
		messages.error(request, 'Chuyến xe này đã khởi hành.')
		return redirect('src:danh_sach_chuyen_xe')
	
	# Get booked seats for this trip
	booked_seats = []
	for ve in chuyen.ves.filter(trang_thai='DA_THANH_TOAN'):
		if ve.vi_tri_ghe:
			booked_seats.extend(ve.vi_tri_ghe)
	
	if request.method == 'POST':
		selected_seats = request.POST.getlist('seats')
		
		if not selected_seats:
			messages.error(request, 'Vui lòng chọn ít nhất một ghế.')
		else:
			# Check if any selected seat is already booked
			conflict = set(selected_seats) & set(booked_seats)
			if conflict:
				messages.error(request, f'Ghế {", ".join(conflict)} đã được đặt.')
			else:
				# Save to session
				request.session['booking_data'] = {
					'chuyen_id': chuyen_id,
					'selected_seats': selected_seats,
				}
				return redirect('src:thanh_toan')
	
	# Generate seat layout based on vehicle capacity
	so_ghe = chuyen.xe.so_ghe
	seat_layout = generate_seat_layout(so_ghe)
	
	context = {
		'chuyen': chuyen,
		'booked_seats': booked_seats,
		'seat_layout': seat_layout,
		'so_ghe_con_lai': chuyen.tong_so_ve - len(booked_seats),
	}
	return render(request, 'booking/chon_ghe.html', context)


def generate_seat_layout(so_ghe):
	"""Generate seat layout structure based on total seats and vehicle type.
	
	Returns list of rows, each row contains seat objects with position labels.
	Different layouts for different vehicle capacities:
	- 16 seats: Limousine 1+1 layout (single seat left, aisle, single seat right) + last row with remaining seats
	- 29 seats: Standard bus 2+1 layout (2 seats left, aisle, 1 seat right) + last row with remaining seats
	- 40 seats: Sleeper bus 2+2 layout (2 seats left, aisle, 2 seats right) + last row with remaining seats
	"""
	rows = []
	row_labels = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
	
	# Determine layout based on seat count
	if so_ghe <= 16:
		# Limousine: 1+1 layout (2 seats per row)
		seats_per_row = 2
		layout_pattern = [0, None, 1]  # Left 1, aisle, right 1
		last_row_seats = min(4, so_ghe)  # Last row can have up to 4 seats
	elif so_ghe <= 30:
		# Standard bus 29 seats: 2+1 layout (3 seats per row)
		seats_per_row = 3
		layout_pattern = [0, 1, None, 2]  # Left 2, aisle, right 1
		last_row_seats = min(4, so_ghe)  # Last row can have up to 4 seats
	else:
		# Sleeper bus: 2+2 layout (4 seats per row)
		seats_per_row = 4
		layout_pattern = [0, 1, None, 2, 3]  # Left 2, aisle, right 2
		last_row_seats = min(4, so_ghe)  # Last row can have up to 4 seats
	
	# Calculate how many seats for normal rows and last row
	normal_rows_seats = (so_ghe - last_row_seats) if so_ghe > last_row_seats else 0
	normal_rows_count = normal_rows_seats // seats_per_row
	remaining_for_last = so_ghe - (normal_rows_count * seats_per_row)
	
	row_index = 0
	seat_index = 0
	
	# Generate normal rows
	while seat_index < normal_rows_count * seats_per_row:
		row = []
		row_label = row_labels[row_index] if row_index < len(row_labels) else f'R{row_index}'
		
		for pos in layout_pattern:
			if pos is None:
				row.append(None)  # Aisle marker
			elif seat_index < normal_rows_count * seats_per_row:
				seat_label = f'{row_label}{pos + 1}'
				row.append(seat_label)
				seat_index += 1
			else:
				row.append(None)
		
		if any(seat for seat in row if seat):
			rows.append(row)
		row_index += 1
	
	# Generate last row with remaining seats (centered layout)
	if remaining_for_last > 0:
		last_row = []
		row_label = row_labels[row_index] if row_index < len(row_labels) else f'R{row_index}'
		
		# Create a full-width layout for last row
		for col in range(1, remaining_for_last + 1):
			seat_label = f'{row_label}{col}'
			last_row.append(seat_label)
		
		rows.append(last_row)
	
	return rows


@login_required
def thanh_toan(request):
	"""View: Payment confirmation page.
	
	GET: Display booking summary and payment form.
	POST: Process payment and create ticket.
	"""
	booking_data = request.session.get('booking_data')
	
	if not booking_data:
		messages.error(request, 'Không tìm thấy thông tin đặt vé.')
		return redirect('src:danh_sach_chuyen_xe')
	
	chuyen = get_object_or_404(
		Chuyen.objects.select_related('tuyen', 'xe'),
		pk=booking_data['chuyen_id']
	)
	
	selected_seats = booking_data['selected_seats']
	so_luong = len(selected_seats)
	tong_tien = chuyen.gia_ve * so_luong
	
	if request.method == 'POST':
		phuong_thuc = request.POST.get('phuong_thuc', 'CHUYEN_KHOAN')
		
		try:
			# Get customer info
			khach_hang = request.user.khachhang
			
			# Create ticket
			ve = Ve.objects.create(
				chuyen=chuyen,
				khach=khach_hang,
				so_luong=so_luong,
				vi_tri_ghe=selected_seats,
				trang_thai='DA_THANH_TOAN'  # Auto-confirm for now
			)
			
			# Create payment record
			from .models import ThanhToan
			import uuid
			
			ma_giao_dich = f'TXN{uuid.uuid4().hex[:12].upper()}'
			thanh_toan = ThanhToan.objects.create(
				ve=ve,
				phuong_thuc=phuong_thuc,
				trang_thai='THANH_CONG',
				ma_giao_dich=ma_giao_dich
			)
			
			# Clear session
			del request.session['booking_data']
			
			messages.success(request, f'Đặt vé thành công! Mã giao dịch: {ma_giao_dich}')
			return redirect('dashboard')
			
		except Exception as e:
			messages.error(request, f'Có lỗi xảy ra: {str(e)}')
	
	context = {
		'chuyen': chuyen,
		'selected_seats': selected_seats,
		'so_luong': so_luong,
		'tong_tien': tong_tien,
	}
	return render(request, 'booking/thanh_toan.html', context)
