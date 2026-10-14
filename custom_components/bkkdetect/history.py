"""Timestamp-aligned vehicle history; geometry uses polyline, PROJ and GEOS."""

from bisect import bisect_left
import polyline
from pyproj.exceptions import ProjError
from shapely.errors import GEOSException
from .geo import RouteShape, distance, epoch, interpolate


class VehicleHistory:
    def __init__(self):
        self.samples = {}
        self.routes = {}
        self.patterns = {}

    def record(self, data, now, options):
        self.routes.update(data.get("references", {}).get("routes", {}))
        cutoff = now - options["history_minutes"] * 60
        for vehicle in data.get("list", []):
            timestamp = epoch(vehicle.get("lastUpdateTime"))
            if (
                timestamp < cutoff
                or timestamp > now + 30
                or now - timestamp > options["max_vehicle_age"]
                or vehicle.get("stale")
                or not vehicle.get("location")
            ):
                continue
            values = self.samples.setdefault(vehicle["vehicleId"], [])
            if not any(v["timestamp"] == timestamp for v in values):
                values.append({**vehicle, "timestamp": timestamp})
                values.sort(key=lambda v: v["timestamp"])
        self.samples = {
            key: [v for v in values if v["timestamp"] > cutoff]
            for key, values in self.samples.items()
            if values and values[-1]["timestamp"] > cutoff
        }
        live_trips = {v.get("tripId") for values in self.samples.values() for v in values}
        self.patterns = {key: value for key, value in self.patterns.items() if key in live_trips}

    def aligned(self, vehicle_id, timestamp, skew):
        samples = self.samples.get(vehicle_id, [])
        if not samples:
            return None
        index = bisect_left([s["timestamp"] for s in samples], timestamp)
        nearby = samples[max(0, index - 1) : index + 1]
        nearest = min(nearby, key=lambda s: abs(s["timestamp"] - timestamp))
        if abs(nearest["timestamp"] - timestamp) > skew:
            return None
        if 0 < index < len(samples):
            a, b = samples[index - 1], samples[index]
            if b["timestamp"] - a["timestamp"] <= skew * 2 and a.get("tripId") == b.get("tripId"):
                f = (timestamp - a["timestamp"]) / (b["timestamp"] - a["timestamp"])
                position = interpolate(
                    (a["location"]["lat"], a["location"]["lon"]),
                    (b["location"]["lat"], b["location"]["lon"]),
                    f,
                )
                return {**nearest, "position": position, "time_skew": 0, "interpolated": True}
        return {
            **nearest,
            "position": (nearest["location"]["lat"], nearest["location"]["lon"]),
            "time_skew": abs(nearest["timestamp"] - timestamp),
            "interpolated": False,
        }

    def pattern(self, trip_id, data):
        entry = data.get("entry", {})
        encoded = (entry.get("polyline") or {}).get("points")
        try:
            coordinates = polyline.decode(encoded) if encoded else []
            geometry = RouteShape(coordinates) if len(coordinates) >= 2 else None
        except IndexError, TypeError, ValueError, ProjError, GEOSException:
            geometry = None
        self.patterns[trip_id] = {
            "geometry": geometry,
            "stop_times": entry.get("stopTimes", []),
            "stops": data.get("references", {}).get("stops", {}),
        }

    def nearest_stop(self, trip_id, position, radius):
        pattern = self.patterns.get(trip_id, {})
        stops = pattern.get("stops", {})
        options = []
        for item in pattern.get("stop_times", []):
            stop = stops.get(item["stopId"])
            if stop and "lat" in stop and "lon" in stop:
                options.append((distance(position, (stop["lat"], stop["lon"])), stop))
        if not options:
            return None
        separation, stop = min(options, key=lambda pair: pair[0])
        if separation > radius:
            return None
        return {
            "id": stop["id"],
            "name": stop["name"],
            "distance_meters": round(separation),
            "basis": "nearest_observed_stop",
            "exact": False,
        }
