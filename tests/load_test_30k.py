import os
import sys
import time
import threading
import statistics
import concurrent.futures
from typing import List, Dict, Any
import requests
from requests.adapters import HTTPAdapter

sys.path.insert(0, os.path.abspath("."))

from app.database import SessionLocal
from app.models import User, UserRole, CustomerProfile, CylinderInventory, CylinderStatus
from app.auth import hash_password, create_access_token
from app.cache import cache

def setup_benchmark_data(db):
    user = db.query(User).filter(User.email == "bench_user@example.com").first()
    if not user:
        user = User(
            email="bench_user@example.com",
            hashed_password=hash_password("BenchPass123!"),
            full_name="Benchmark Customer",
            phone="9876543210",
            role=UserRole.CUSTOMER,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        profile = CustomerProfile(
            user_id=user.id,
            consumer_number="CN-BENCH-01",
            address="100 Tech Park",
            city="Bengaluru",
            pincode="560100",
            cylinder_quota_limit=50000,
            quota_used_this_year=0
        )
        db.add(profile)

        admin = User(
            email="bench_admin@example.com",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Benchmark Admin",
            phone="9876543299",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)

        for i in range(100):
            cyl = CylinderInventory(
                serial_number=f"CYL-BENCH-{i:04d}",
                cylinder_type="14.2kg",
                status=CylinderStatus.IN_STOCK,
                batch_code="BATCH-BENCH"
            )
            db.add(cyl)
        db.commit()
    else:
        admin = db.query(User).filter(User.email == "bench_admin@example.com").first()

    cust_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    admin_token = create_access_token({"sub": str(admin.id), "role": admin.role.value})
    return {
        "cust_headers": {"Authorization": f"Bearer {cust_token}"},
        "admin_headers": {"Authorization": f"Bearer {admin_token}"}
    }

thread_local = threading.local()

def get_session():
    if not hasattr(thread_local, "session"):
        s = requests.Session()
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=1)
        s.mount("http://", adapter)
        thread_local.session = s
    return thread_local.session

def run_load_test(base_url: str = "http://127.0.0.1:8000", total_requests: int = 30000, concurrency: int = 25) -> Dict[str, Any]:
    db = SessionLocal()
    tokens = setup_benchmark_data(db)
    db.close()

    cust_headers = tokens["cust_headers"]
    admin_headers = tokens["admin_headers"]

    endpoints = [
        ("GET", f"{base_url}/", None, {}),
        ("GET", f"{base_url}/health", None, {}),
        ("GET", f"{base_url}/api/v1/admin/dashboard/overview", None, admin_headers),
        ("GET", f"{base_url}/api/v1/customer/profile", None, cust_headers),
        ("GET", f"{base_url}/api/v1/admin/inventory?limit=20", None, admin_headers),
        ("POST", f"{base_url}/api/v1/admin/logistics/recommend-vehicle", {
            "zone_or_route": "Sector 5",
            "total_cylinders": 8,
            "delivery_count": 6,
            "area_sq_km": 3.0
        }, admin_headers)
    ]

    latencies_ms: List[float] = []
    errors = 0
    start_time = time.perf_counter()

    def send_request(idx: int) -> tuple[float, bool]:
        s = get_session()
        method, url, payload, headers = endpoints[idx % len(endpoints)]
        t0 = time.perf_counter()
        try:
            if method == "GET":
                res = s.get(url, headers=headers, timeout=10.0)
            else:
                res = s.post(url, json=payload, headers=headers, timeout=10.0)
            dt = (time.perf_counter() - t0) * 1000.0
            return dt, (res.status_code < 400)
        except Exception:
            dt = (time.perf_counter() - t0) * 1000.0
            return dt, False

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_request, i) for i in range(total_requests)]
        for f in concurrent.futures.as_completed(futures):
            dt, success = f.result()
            latencies_ms.append(dt)
            if not success:
                errors += 1

    total_duration = time.perf_counter() - start_time
    throughput = round(total_requests / total_duration, 2)
    latencies_sorted = sorted(latencies_ms)

    p50 = round(latencies_sorted[int(len(latencies_sorted) * 0.50)], 2)
    p95 = round(latencies_sorted[int(len(latencies_sorted) * 0.95)], 2)
    p99 = round(latencies_sorted[int(len(latencies_sorted) * 0.99)], 2)
    avg_lat = round(statistics.mean(latencies_ms), 2)
    min_lat = round(min(latencies_ms), 2)
    max_lat = round(max(latencies_ms), 2)
    error_rate = round((errors / total_requests) * 100.0, 2)

    report = {
        "total_requests": total_requests,
        "concurrency": concurrency,
        "duration_seconds": round(total_duration, 2),
        "throughput_req_per_sec": throughput,
        "latencies_ms": {
            "min": min_lat,
            "avg": avg_lat,
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "max": max_lat
        },
        "errors_count": errors,
        "error_rate_pct": error_rate,
        "cache_available": cache.is_available()
    }
    return report

if __name__ == "__main__":
    report = run_load_test(base_url="http://127.0.0.1:8000", total_requests=30000, concurrency=25)
    print("=== 30,000 REQUESTS LOAD TEST REPORT ===")
    for k, v in report.items():
        print(f"{k}: {v}")
