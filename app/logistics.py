from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.config import settings
from app.models import DeliveryAssignment, Booking, User, StaffProfile, UserRole

class VehicleAllocationService:
    @staticmethod
    def recommend_vehicle(
        zone_or_route: str,
        total_cylinders: int,
        delivery_count: int,
        area_sq_km: Optional[float] = 10.0,
        has_narrow_access: Optional[bool] = False,
        has_coordinates: Optional[bool] = True
    ) -> Dict[str, Any]:
        if not zone_or_route or not has_coordinates or total_cylinders <= 0 or delivery_count <= 0:
            return {
                "zone_or_route": zone_or_route or "UNKNOWN",
                "recommended_vehicle": "MANUAL_ASSIGNMENT_REQUIRED",
                "vehicle_capacity": 0,
                "density_score": 0.0,
                "trips_required": 0,
                "explanation": "Insufficient or missing geographic/coordinate information. Manual review required.",
                "can_auto_dispatch": False
            }

        effective_area = max(1.0, area_sq_km or 10.0)
        density_score = round(delivery_count / effective_area, 2)

        two_wheeler_cap = settings.LOGISTICS_TWO_WHEELER_MAX_CAPACITY
        truck_cap = settings.LOGISTICS_SMALL_TRUCK_MAX_CAPACITY
        high_density_threshold = settings.LOGISTICS_HIGH_DENSITY_THRESHOLD

        if has_narrow_access:
            if total_cylinders <= two_wheeler_cap:
                return {
                    "zone_or_route": zone_or_route,
                    "recommended_vehicle": "TWO_WHEELER",
                    "vehicle_capacity": two_wheeler_cap,
                    "density_score": density_score,
                    "trips_required": 1,
                    "explanation": "Narrow access route with small payload suitable for two-wheeler dispatch.",
                    "can_auto_dispatch": True
                }
            elif total_cylinders <= two_wheeler_cap * 3:
                trips = (total_cylinders + two_wheeler_cap - 1) // two_wheeler_cap
                return {
                    "zone_or_route": zone_or_route,
                    "recommended_vehicle": "TWO_WHEELER",
                    "vehicle_capacity": two_wheeler_cap,
                    "density_score": density_score,
                    "trips_required": trips,
                    "explanation": f"Narrow access prohibits trucks. {trips} two-wheeler shuttle trips recommended.",
                    "can_auto_dispatch": True
                }
            else:
                return {
                    "zone_or_route": zone_or_route,
                    "recommended_vehicle": "MANUAL_ASSIGNMENT_REQUIRED",
                    "vehicle_capacity": 0,
                    "density_score": density_score,
                    "trips_required": 0,
                    "explanation": "Large delivery volume in narrow-access area exceeds safe two-wheeler shuttle limits. Manual staging required.",
                    "can_auto_dispatch": False
                }

        if total_cylinders > truck_cap * 2:
            return {
                "zone_or_route": zone_or_route,
                "recommended_vehicle": "MANUAL_ASSIGNMENT_REQUIRED",
                "vehicle_capacity": truck_cap,
                "density_score": density_score,
                "trips_required": (total_cylinders + truck_cap - 1) // truck_cap,
                "explanation": "Volume exceeds standard dispatch capacity. Manual fleet planning required.",
                "can_auto_dispatch": False
            }

        if total_cylinders <= two_wheeler_cap and density_score < high_density_threshold:
            return {
                "zone_or_route": zone_or_route,
                "recommended_vehicle": "TWO_WHEELER",
                "vehicle_capacity": two_wheeler_cap,
                "density_score": density_score,
                "trips_required": 1,
                "explanation": "Low load and dispersed route optimal for agile two-wheeler delivery.",
                "can_auto_dispatch": True
            }

        trips = max(1, (total_cylinders + truck_cap - 1) // truck_cap)
        return {
            "zone_or_route": zone_or_route,
            "recommended_vehicle": "SMALL_TRUCK",
            "vehicle_capacity": truck_cap,
            "density_score": density_score,
            "trips_required": trips,
            "explanation": f"High density ({density_score} stops/sq km) or aggregate load ({total_cylinders} cyl) optimal for small truck.",
            "can_auto_dispatch": True
        }

    @staticmethod
    def get_route_summaries(db: Session) -> List[Dict[str, Any]]:
        staff = db.query(StaffProfile).filter(StaffProfile.is_on_duty == True).all()
        zones = set(s.assigned_hub_zone for s in staff)
        results = []
        for zone in zones:
            pending_count = db.query(DeliveryAssignment).filter(
                DeliveryAssignment.status == "ASSIGNED"
            ).count()
            rec = VehicleAllocationService.recommend_vehicle(
                zone_or_route=zone,
                total_cylinders=max(1, pending_count),
                delivery_count=max(1, pending_count),
                area_sq_km=8.0
            )
            results.append(rec)
        return results
