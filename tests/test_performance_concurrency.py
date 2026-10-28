import pytest
from app.models import CylinderInventory, CylinderStatus, Booking
from app.cache import cache
from app.services import redact_sensitive_text
from app.logistics import VehicleAllocationService
from tests.conftest import get_auth_headers

def test_race_safe_booking_single_available_cylinder(client, seed_data, db_session):
    headers1 = get_auth_headers(seed_data["customer"])
    headers2 = get_auth_headers(seed_data["customer2"])

    db_session.query(CylinderInventory).delete()
    single_cylinder = CylinderInventory(
        serial_number="CYL-CONCURRENCY-SINGLE",
        cylinder_type="14.2kg",
        status=CylinderStatus.IN_STOCK,
        batch_code="BATCH-SINGLE"
    )
    db_session.add(single_cylinder)
    db_session.commit()

    res1 = client.post("/api/v1/customer/bookings", json={
        "cylinder_type": "14.2kg",
        "quantity": 1,
        "scheduled_date": "2026-11-10",
        "idempotency_key": "IDEM-KEY-USER1"
    }, headers=headers1)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/customer/bookings", json={
        "cylinder_type": "14.2kg",
        "quantity": 1,
        "scheduled_date": "2026-11-10",
        "idempotency_key": "IDEM-KEY-USER2"
    }, headers=headers2)
    assert res2.status_code == 409
    assert "insufficient" in res2.json()["detail"].lower()

    in_stock_count = db_session.query(CylinderInventory).filter(
        CylinderInventory.status == CylinderStatus.IN_STOCK
    ).count()
    reserved_count = db_session.query(CylinderInventory).filter(
        CylinderInventory.status == CylinderStatus.RESERVED
    ).count()

    assert in_stock_count == 0
    assert reserved_count == 1

def test_booking_idempotency_replay(client, seed_data, db_session):
    headers = get_auth_headers(seed_data["customer"])
    idempotency_key = "IDEMPOTENT-TXN-9988"

    payload = {
        "cylinder_type": "14.2kg",
        "quantity": 1,
        "scheduled_date": "2026-11-12",
        "idempotency_key": idempotency_key
    }

    res1 = client.post("/api/v1/customer/bookings", json=payload, headers=headers)
    assert res1.status_code == 201
    booking1 = res1.json()

    res2 = client.post(
        "/api/v1/customer/bookings",
        json=payload,
        headers={**headers, "X-Idempotency-Key": idempotency_key}
    )
    assert res2.status_code in (200, 201)
    booking2 = res2.json()

    assert booking1["id"] == booking2["id"]
    assert booking1["booking_number"] == booking2["booking_number"]

    total_bookings = db_session.query(Booking).filter(
        Booking.idempotency_key == idempotency_key
    ).count()
    assert total_bookings == 1

def test_redis_cache_hit_and_invalidation(client, seed_data, db_session):
    admin_headers = get_auth_headers(seed_data["admin"])

    res1 = client.get("/api/v1/admin/dashboard/overview", headers=admin_headers)
    assert res1.status_code == 200
    data1 = res1.json()

    cached_val = cache.get("dashboard:overview")
    assert cached_val is not None
    assert cached_val["total_customers"] == data1["total_customers"]

    client.post("/api/v1/admin/inventory", json={
        "serial_number": "CYL-CACHE-TEST-01",
        "cylinder_type": "14.2kg",
        "status": "IN_STOCK",
        "batch_code": "BATCH-CACHE"
    }, headers=admin_headers)

    assert cache.get("dashboard:overview") is None

    res2 = client.get("/api/v1/admin/dashboard/overview", headers=admin_headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["in_stock_cylinders"] == data1["in_stock_cylinders"] + 1

def test_redis_outage_graceful_degradation(client, seed_data):
    admin_headers = get_auth_headers(seed_data["admin"])

    original_client = cache._redis_client
    original_avail = cache._is_redis_available
    try:
        cache._redis_client = None
        cache._is_redis_available = False
        cache._memory_cache.clear()

        res = client.get("/api/v1/admin/dashboard/overview", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "total_customers" in data
    finally:
        cache._redis_client = original_client
        cache._is_redis_available = original_avail

def test_vehicle_allocation_low_density_two_wheeler():
    rec = VehicleAllocationService.recommend_vehicle(
        zone_or_route="Indiranagar Sector 2",
        total_cylinders=3,
        delivery_count=3,
        area_sq_km=10.0,
        has_narrow_access=False,
        has_coordinates=True
    )
    assert rec["recommended_vehicle"] == "TWO_WHEELER"
    assert rec["can_auto_dispatch"] is True

def test_vehicle_allocation_high_density_small_truck():
    rec = VehicleAllocationService.recommend_vehicle(
        zone_or_route="Koramangala 4th Block",
        total_cylinders=22,
        delivery_count=18,
        area_sq_km=2.0,
        has_narrow_access=False,
        has_coordinates=True
    )
    assert rec["recommended_vehicle"] == "SMALL_TRUCK"
    assert rec["can_auto_dispatch"] is True

def test_vehicle_allocation_narrow_access_route():
    rec = VehicleAllocationService.recommend_vehicle(
        zone_or_route="Shivajinagar Old Alleys",
        total_cylinders=4,
        delivery_count=4,
        area_sq_km=2.0,
        has_narrow_access=True,
        has_coordinates=True
    )
    assert rec["recommended_vehicle"] == "TWO_WHEELER"
    assert rec["can_auto_dispatch"] is True

def test_vehicle_allocation_missing_coordinates_fallback():
    rec = VehicleAllocationService.recommend_vehicle(
        zone_or_route="",
        total_cylinders=5,
        delivery_count=5,
        area_sq_km=10.0,
        has_narrow_access=False,
        has_coordinates=False
    )
    assert rec["recommended_vehicle"] == "MANUAL_ASSIGNMENT_REQUIRED"
    assert rec["can_auto_dispatch"] is False

def test_dpdp_privacy_data_redaction():
    text = 'User updated phone 9876543210 and auth token="eyJhbGciOiJIUzI1NiJ9" with aadhaar 1234 5678 9012'
    redacted = redact_sensitive_text(text)
    assert "XXXX-XXXX-XXXX" in redacted
    assert "1234 5678 9012" not in redacted
    assert "[REDACTED]" in redacted

def test_detailed_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "cache_available" in data
    assert "database" in data
