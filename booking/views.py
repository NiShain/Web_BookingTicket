from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count

from .models import Tuyen, Chuyen


def home(request):
	"""Render the site homepage with dynamic sections:

	- tuyen_popular: top routes ordered by number of trips (chuyens)
	- upcoming_chuyen: next upcoming trips ordered by departure time
	"""
	# Popular routes by number of related Chuyen objects
	tuyen_popular = Tuyen.objects.annotate(chuyen_count=Count('chuyens')).order_by('-chuyen_count')[:6]

	# Upcoming trips (from now), next 8
	now = timezone.now()
	upcoming_chuyen = Chuyen.objects.filter(ngay_gio_khoi_hanh__gte=now).order_by('ngay_gio_khoi_hanh')[:8]

	context = {
		'tuyen_popular': tuyen_popular,
		'upcoming_chuyen': upcoming_chuyen,
	}
	return render(request, 'home.html', context)


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
