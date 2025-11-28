from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from booking.models import Tuyen, Xe, Chuyen
from users.models import Account, KhachHang


class Command(BaseCommand):
    help = 'Seed sample Tuyen/Xe/Chuyen data for UI testing'

    def handle(self, *args, **options):
        now = timezone.now()

        # --- Seed sample users and customers ---
        sample_users = [
            {"username": "alice", "email": "alice@example.com", "password": "Password123!", "first_name": "Alice"},
            {"username": "bob", "email": "bob@example.com", "password": "Password123!", "first_name": "Bob"},
            {"username": "admin", "email": "admin@example.com", "password": "AdminPass123!", "first_name": "Admin", "is_superuser": True, "is_staff": True},
        ]

        created_accounts = 0
        created_customers = 0
        for u in sample_users:
            acct, created = Account.objects.get_or_create(username=u['username'], defaults={
                'email': u['email'],
                'first_name': u.get('first_name',''),
                'is_staff': u.get('is_staff', False),
                'is_superuser': u.get('is_superuser', False),
            })
            if created:
                acct.set_password(u['password'])
                acct.email_verified = True
                acct.save()
                created_accounts += 1

            # create corresponding KhachHang for non-superusers
            if not acct.is_superuser:
                kh, created_kh = KhachHang.objects.get_or_create(email=u['email'], defaults={
                    'account': acct,
                    'ten': f"{acct.first_name or acct.username} Nguyen",
                    'so_dien_thoai': f"03{10000000 + created_customers}",
                })
                if created_kh:
                    created_customers += 1


        # Sample routes - More comprehensive list
        routes = [
            ("Hà Nội", "Hải Phòng", 120),
            ("Hà Nội", "Quảng Ninh", 250),
            ("Hà Nội", "Thanh Hóa", 160),
            ("Hà Nội", "Vinh", 300),
            ("Hà Nội", "Đà Nẵng", 760),
            ("Hồ Chí Minh", "Vũng Tàu", 120),
            ("Hồ Chí Minh", "Đà Lạt", 300),
            ("Hồ Chí Minh", "Nha Trang", 450),
            ("Hồ Chí Minh", "Cần Thơ", 180),
            ("Đà Nẵng", "Huế", 100),
            ("Đà Nẵng", "Hội An", 30),
            ("Đà Nẵng", "Quy Nhon", 180),
            ("Hải Phòng", "Quảng Ninh", 150),
            ("Thanh Hóa", "Vinh", 140),
            ("Nha Trang", "Đà Lạt", 220),
        ]

        created_routes = []
        for diem_di, diem_den, khoang in routes:
            tuyen, created = Tuyen.objects.get_or_create(
                diem_di=diem_di, diem_den=diem_den,
                defaults={"khoang_cach": khoang}
            )
            created_routes.append(tuyen)

        # Sample vehicles - More variety
        vehicles = [
            ("29A-11111", "Limousine 16 chỗ", 16),
            ("30B-22222", "Giường nằm 40 chỗ", 40),
            ("43C-33333", "Ghế ngồi 29 chỗ", 29),
            ("51D-44444", "Limousine 24 chỗ", 24),
            ("61E-55555", "Giường nằm 34 chỗ", 34),
            ("72F-66666", "Ghế ngồi 45 chỗ", 45),
            ("29G-77777", "Limousine 20 chỗ", 20),
            ("30H-88888", "Giường nằm 36 chỗ", 36),
        ]

        created_vehicles = []
        for bien_so, loai, so_ghe in vehicles:
            xe, created = Xe.objects.get_or_create(
                bien_so=bien_so,
                defaults={"loai_xe": loai, "so_ghe": so_ghe}
            )
            # if existing, ensure so_ghe set
            if not created and xe.so_ghe != so_ghe:
                xe.so_ghe = so_ghe
                xe.save()
            created_vehicles.append(xe)

        # Create multiple trips for each route (5-7 upcoming trips)
        created_trips = []
        for i, tuyen in enumerate(created_routes):
            # Create multiple trips for each route with different vehicles
            for trip_day in range(1, 8):  # Next 7 days
                # pick a vehicle in round-robin
                xe = created_vehicles[(i + trip_day) % len(created_vehicles)]
                
                # Morning trip (8-11 AM)
                morning_time = now + timedelta(days=trip_day, hours=8 + (i % 4))
                ngay_gio_khoi_hanh = morning_time.replace(minute=0, second=0, microsecond=0)
                ngay_gio_den = ngay_gio_khoi_hanh + timedelta(hours=3 + (tuyen.khoang_cach // 100))
                tong_so_ve = min(xe.so_ghe, 50)
                gia_ve = 120000 + (i * 15000) + (trip_day * 2000)

                chuyen_morning, created = Chuyen.objects.get_or_create(
                    tuyen=tuyen,
                    xe=xe,
                    ngay_gio_khoi_hanh=ngay_gio_khoi_hanh,
                    defaults={
                        "ngay_gio_den": ngay_gio_den,
                        "tong_so_ve": tong_so_ve,
                        "gia_ve": gia_ve,
                    }
                )
                created_trips.append(chuyen_morning)
                
                # Evening trip (2-6 PM) for popular routes
                if i < 10:  # Only for first 10 routes
                    xe_evening = created_vehicles[(i + trip_day + 1) % len(created_vehicles)]
                    evening_time = now + timedelta(days=trip_day, hours=14 + (i % 4))
                    ngay_gio_khoi_hanh_evening = evening_time.replace(minute=0, second=0, microsecond=0)
                    ngay_gio_den_evening = ngay_gio_khoi_hanh_evening + timedelta(hours=3 + (tuyen.khoang_cach // 100))
                    tong_so_ve_evening = min(xe_evening.so_ghe, 50)
                    gia_ve_evening = 140000 + (i * 15000) + (trip_day * 2000)

                    chuyen_evening, created = Chuyen.objects.get_or_create(
                        tuyen=tuyen,
                        xe=xe_evening,
                        ngay_gio_khoi_hanh=ngay_gio_khoi_hanh_evening,
                        defaults={
                            "ngay_gio_den": ngay_gio_den_evening,
                            "tong_so_ve": tong_so_ve_evening,
                            "gia_ve": gia_ve_evening,
                        }
                    )
                    created_trips.append(chuyen_evening)

        summary = (
            f"Seeded: {len(created_routes)} routes, {len(created_vehicles)} vehicles, {len(created_trips)} trips.\n"
            f"Accounts created: {created_accounts}, Customers created: {created_customers}"
        )
        self.stdout.write(self.style.SUCCESS(summary))
