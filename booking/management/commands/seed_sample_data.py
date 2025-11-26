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


        # Sample routes
        routes = [
            ("Hà Nội", "Hải Phòng", 120),
            ("Hà Nội", "Quảng Ninh", 250),
            ("Hà Nội", "Thanh Hóa", 160),
            ("Hồ Chí Minh", "Vũng Tàu", 120),
            ("Đà Nẵng", "Huế", 100),
        ]

        created_routes = []
        for diem_di, diem_den, khoang in routes:
            tuyen, created = Tuyen.objects.get_or_create(
                diem_di=diem_di, diem_den=diem_den,
                defaults={"khoang_cach": khoang}
            )
            created_routes.append(tuyen)

        # Sample vehicles
        vehicles = [
            ("29A-11111", "Limousine 16 chỗ", 16),
            ("30B-22222", "Giường nằm 40 chỗ", 40),
            ("43C-33333", "Ghế ngồi 29 chỗ", 29),
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

        # Create trips for each route (2-3 upcoming trips)
        created_trips = []
        for i, tuyen in enumerate(created_routes):
            # pick a vehicle in round-robin
            xe = created_vehicles[i % len(created_vehicles)]
            # create 2 trips: tomorrow morning and day after afternoon
            trip_times = [now + timedelta(days=1, hours=9 + i), now + timedelta(days=2, hours=15 + i)]
            for j, start in enumerate(trip_times):
                # ensure start is in the future (clean enforces)
                ngay_gio_khoi_hanh = start.replace(minute=0, second=0, microsecond=0)
                ngay_gio_den = ngay_gio_khoi_hanh + timedelta(hours=3)
                tong_so_ve = min(xe.so_ghe, 40)
                gia_ve = 150000 + (i * 20000) + (j * 5000)

                chuyen, created = Chuyen.objects.get_or_create(
                    tuyen=tuyen,
                    xe=xe,
                    ngay_gio_khoi_hanh=ngay_gio_khoi_hanh,
                    defaults={
                        "ngay_gio_den": ngay_gio_den,
                        "tong_so_ve": tong_so_ve,
                        "gia_ve": gia_ve,
                    }
                )
                created_trips.append(chuyen)

        summary = (
            f"Seeded: {len(created_routes)} routes, {len(created_vehicles)} vehicles, {len(created_trips)} trips.\n"
            f"Accounts created: {created_accounts}, Customers created: {created_customers}"
        )
        self.stdout.write(self.style.SUCCESS(summary))
