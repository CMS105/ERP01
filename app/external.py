import math
from typing import Dict, Any, Optional

class RoutingServiceClient:
    @staticmethod
    def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r * c, 2)

    @classmethod
    def get_route_estimate(
        cls,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float
    ) -> Dict[str, Any]:
        try:
            dist_km = cls.calculate_haversine_distance(origin_lat, origin_lon, dest_lat, dest_lon)
            avg_speed_kmh = 25.0
            duration_minutes = round((dist_km / avg_speed_kmh) * 60.0 + 5.0, 1)
            return {
                "distance_km": dist_km,
                "duration_minutes": duration_minutes,
                "provider": "deterministic_fallback",
                "is_fallback": True
            }
        except Exception:
            return {
                "distance_km": 5.0,
                "duration_minutes": 20.0,
                "provider": "default_estimate",
                "is_fallback": True
            }

routing_client = RoutingServiceClient()
