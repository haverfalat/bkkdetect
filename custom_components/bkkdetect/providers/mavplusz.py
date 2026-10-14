"""MÁV Plusz OTP adapter following haverfalat/tkt's lib/mavplusz client.

Responses are normalized to the detector's existing model. BKK GTFS identifiers
retain their old spelling so existing configured home routes keep working.
"""

import json
from datetime import datetime
from math import ceil, isfinite
from urllib.parse import quote
from zoneinfo import ZoneInfo

from aiohttp import ClientError, ClientTimeout
from shapely.geometry import Point, box
from shapely.strtree import STRtree

from ..api import BkkError, CachedClient, RateLimited
from ..geo import GEODESIC, distance, epoch, point

VEHICLE_FIELDS = """
vehicleId isEstimated lat lon heading lastUpdated speed
trip { gtfsId routeShortName tripHeadsign serviceDate
  route { gtfsId mode shortName longName } }
"""
TRIP_QUERY = """
query DetectorTrip($id: String!, $date: String) {
  trip(id: $id, serviceDay: $date) {
    gtfsId tripHeadsign route { gtfsId shortName mode }
    tripGeometry { points }
    stoptimes { stop { gtfsId name lat lon } serviceDay
      scheduledArrival realtimeArrival scheduledDeparture realtimeDeparture
      realtime realtimeState pickupType dropoffType }
  }
}
"""
STOP_FIELDS = "gtfsId name lat lon routes { gtfsId shortName longName mode }"
ARRIVALS_QUERY = """
query DetectorDepartures($id: String!, $start: Long, $range: Int) {
  stop(id: $id) {
    stoptimesForPatterns(startTime: $start, timeRange: $range, numberOfDepartures: 50) {
      stoptimes { serviceDay scheduledArrival realtimeArrival scheduledDeparture
        realtimeDeparture realtime realtimeState pickupType dropoffType
        trip { gtfsId route { gtfsId } } }
    }
  }
}
"""
PLAN_QUERY = """
query DetectorPlan($from: String!, $to: String!, $modes: [TransportMode],
  $count: Int, $walk: Float, $locale: String) {
  plan(fromPlace: $from, toPlace: $to, transportModes: $modes,
    numItineraries: $count, walkSpeed: $walk, locale: $locale,
    distributionChannel: "ERTEKESITESI_CSATORNA#INTERNET",
    distributionSubChannel: "ERTEKESITESI_ALCSATORNA#EMMA") {
    itineraries { endTime numberOfTransfers
      legs { mode startTime endTime realTime arrivalDelay
        from { name } to { name }
        route { gtfsId shortName } trip { gtfsId } } }
  }
}
"""


def normalized_id(value):
    return "BKK_" + value[4:] if value and value.startswith("BKK:") else value


def upstream_id(value):
    return "BKK:" + value[4:] if value and value.startswith("BKK_") else value


def service_midnight(value):
    if not value:
        return None
    date = str(value).replace("-", "")
    return int(
        datetime.strptime(date, "%Y%m%d").replace(tzinfo=ZoneInfo("Europe/Budapest")).timestamp()
        * 1000
    )


def stop_time(raw, stop_id=None, route_id=None):
    result = {
        "stopId": stop_id,
        "tripId": normalized_id((raw.get("trip") or {}).get("gtfsId")),
        "routeId": route_id,
        "serviceDate": datetime.fromtimestamp(raw["serviceDay"], ZoneInfo("Europe/Budapest"))
        .date()
        .isoformat(),
        "pickupAllowed": raw.get("pickupType") != "NONE",
        "dropOffAllowed": raw.get("dropoffType") != "NONE",
        "canceled": raw.get("realtimeState") in ("CANCELED", "SKIPPED"),
    }
    for key, field in (("Arrival", "scheduledArrival"), ("Departure", "scheduledDeparture")):
        if raw.get(field) is not None:
            result[key.lower() + "Time"] = raw["serviceDay"] + raw[field]
        realtime = raw.get("realtime" + key)
        if raw.get("realtime") and realtime is not None:
            result["predicted" + key + "Time"] = raw["serviceDay"] + realtime
    return result


class MavPluszClient(CachedClient):
    name = "mavplusz"

    def __init__(self, session, key, options, budget):
        super().__init__(session, "", options, budget)
        self.vehicle_trips = {}

    @property
    def index_url(self):
        router = quote(self.options["mav_router"], safe="")
        return f"{self.options['mav_base_url'].rstrip('/')}/otp2-backend/otp/routers/{router}/index"

    async def _fetch(self, endpoint, params):
        import time

        graphql = endpoint == "graphql"
        url = (
            self.index_url + "/graphql"
            if graphql
            else self.options["mav_base_url"].rstrip("/") + endpoint
        )
        try:
            async with self.session.request(
                "POST" if graphql else "GET",
                url,
                json=params if graphql else None,
                params=None if graphql else params,
                headers={"Accept": "application/json", "User-Agent": "BKKDetect/0.4"},
                timeout=ClientTimeout(total=self.options["request_timeout"]),
            ) as response:
                if response.status == 429:
                    try:
                        retry = float(response.headers.get("Retry-After", 0))
                    except ValueError:
                        retry = 0
                    self.budget.blocked_until = time.monotonic() + max(
                        retry, self.options["backoff_seconds"]
                    )
                    raise RateLimited("MÁV Plusz rate limited; backing off")
                if response.status != 200:
                    raise BkkError(f"MÁV Plusz HTTP {response.status}")
                body = await response.json()
        except TimeoutError, ClientError, ValueError:
            raise BkkError("MÁV Plusz connection failed or invalid response") from None
        if graphql:
            if body.get("errors") or not isinstance(body.get("data"), dict):
                raise BkkError("MÁV Plusz GraphQL request rejected")
            return body["data"]
        return body

    async def query(self, query, variables=None, ttl=0, reserve=0):
        return await self.request(
            "graphql", {"query": query, "variables": variables or {}}, ttl, reserve
        )

    async def metadata(self):
        await self.query("{ __typename }", ttl=300)
        return {"provider": self.name}

    def normalize_vehicles(self, vehicles):
        result, routes = [], {}
        for raw in vehicles:
            trip = raw.get("trip") or {}
            route = trip.get("route") or {}
            stamp = epoch(raw.get("lastUpdated"))
            location = point({"latitude": raw.get("lat"), "longitude": raw.get("lon")})
            if (
                not raw.get("vehicleId")
                or not trip.get("gtfsId")
                or not location
                or not isfinite(stamp)
            ):
                continue
            route_id = normalized_id(route.get("gtfsId"))
            vehicle_id = "MAV:" + raw["vehicleId"]
            self.vehicle_trips[vehicle_id] = {
                "id": trip["gtfsId"],
                "serviceDay": service_midnight(trip.get("serviceDate")),
            }
            routes[route_id] = {
                "id": route_id,
                "shortName": route.get("shortName") or trip.get("routeShortName"),
                "longName": route.get("longName"),
                "type": route.get("mode"),
            }
            result.append(
                {
                    "vehicleId": vehicle_id,
                    "tripId": normalized_id(trip["gtfsId"]),
                    "routeId": route_id,
                    "vehicleRouteType": route.get("mode"),
                    "serviceDate": trip.get("serviceDate"),
                    "location": {"lat": location[0], "lon": location[1]},
                    "lastUpdateTime": stamp,
                    "bearing": raw.get("heading"),
                    "label": trip.get("tripHeadsign", ""),
                    "isEstimated": raw.get("isEstimated"),
                    "stale": raw.get("isEstimated") is not False,
                    "provider": self.name,
                }
            )
        return {"list": result, "references": {"routes": routes}, "provider": self.name}

    def remember(self, vehicles):
        """Restore trip lookups for active vehicles from the persisted journal."""
        for vehicle in vehicles:
            if vehicle.get("provider") == self.name and vehicle.get("tripId"):
                self.vehicle_trips[vehicle["vehicleId"]] = {
                    "id": upstream_id(vehicle["tripId"]),
                    "serviceDay": service_midnight(vehicle.get("serviceDate")),
                }

    async def vehicles_many(self, points):
        """One bounding-area request supplies evidence for every eligible tracker."""
        if not points or not self.options["transit_modes"]:
            return self.normalize_vehicles([])
        corners, areas = [], []
        for lat, lon in points:
            region = []
            for heading in (0, 90, 180, 270):
                x, y, _ = GEODESIC.fwd(lon, lat, heading, self.options["vehicle_radius"])
                corners.append((x, y))
                region.append((x, y))
            areas.append(
                box(
                    min(p[0] for p in region),
                    min(p[1] for p in region),
                    max(p[0] for p in region),
                    max(p[1] for p in region),
                )
            )
        west, south = min(p[0] for p in corners), min(p[1] for p in corners)
        east, north = max(p[0] for p in corners), max(p[1] for p in corners)
        modes = ",".join(self.options["transit_modes"])
        query = f"{{ vehiclePositions(swLat:{south:.6f},swLon:{west:.6f},neLat:{north:.6f},neLon:{east:.6f},modes:[{modes}]) {{ {VEHICLE_FIELDS} }} }}"
        data = await self.query(query, ttl=self.options["vehicle_cache_seconds"])
        result = self.normalize_vehicles(data["vehiclePositions"])
        index = STRtree(areas)
        radius = self.options["vehicle_radius"]
        # A wide shared query can span distant phones. Retain evidence around
        # phones and tracked vehicles, rather than journalling the entire country.
        result["list"] = [
            v
            for v in result["list"]
            if any(
                distance(points[i], (v["location"]["lat"], v["location"]["lon"])) <= radius
                for i in index.query(Point(v["location"]["lon"], v["location"]["lat"]))
            )
        ]
        used_routes = {v["routeId"] for v in result["list"]}
        result["references"]["routes"] = {
            k: v for k, v in result["references"]["routes"].items() if k in used_routes
        }
        return result

    async def vehicles(self, position):
        return await self.vehicles_many([position])

    async def vehicles_by_id(self, ids):
        trips = [self.vehicle_trips[v] for v in ids if v in self.vehicle_trips]
        if not trips:
            return self.normalize_vehicles([])
        data = await self.query(
            f"query DetectorVehicles($trips:[TripKey]) {{ vehiclePositionsForTrips(trips:$trips) {{ {VEHICLE_FIELDS} }} }}",
            {"trips": trips},
            self.options["vehicle_cache_seconds"],
        )
        normalized = self.normalize_vehicles(data["vehiclePositionsForTrips"])
        normalized["list"] = [v for v in normalized["list"] if v["vehicleId"] in ids]
        return normalized

    async def trip(self, trip_id, date=None):
        reserve = min(
            max(0, self.options["requests_per_minute"] - 1), ceil(60 / self.options["poll_seconds"])
        )
        data = await self.query(
            TRIP_QUERY,
            {"id": upstream_id(trip_id), "date": date},
            self.options["vehicle_cache_seconds"],
            reserve,
        )
        trip = data.get("trip")
        if not trip:
            raise BkkError("MÁV Plusz trip unavailable")
        times, stops = [], {}
        for raw in trip.get("stoptimes", []):
            stop = raw["stop"]
            stop_id = normalized_id(stop["gtfsId"])
            stops[stop_id] = {
                "id": stop_id,
                "name": stop["name"],
                "lat": stop["lat"],
                "lon": stop["lon"],
            }
            times.append(stop_time(raw, stop_id))
        return {
            "entry": {"polyline": trip.get("tripGeometry"), "stopTimes": times},
            "references": {"stops": stops},
        }

    async def search(self, text):
        data = await self.query("{ routes { gtfsId shortName longName mode } }", ttl=3600)
        matching = [
            r
            for r in data["routes"]
            if text.casefold() in (r.get("shortName") or "").casefold()
            or text.casefold() in (r.get("longName") or "").casefold()
        ]
        routes = {
            normalized_id(r["gtfsId"]): {
                "id": normalized_id(r["gtfsId"]),
                "shortName": r["shortName"],
                "longName": r.get("longName"),
                "type": r["mode"],
            }
            for r in matching
        }
        if any((r.get("shortName") or "").casefold() == text.casefold() for r in matching):
            return {"references": {"routes": routes, "stops": {}}}
        router = quote(self.options["mav_router"], safe="")
        locations = await self.request(
            f"/otp2-backend/otp/routers/{router}/geocode/stations",
            {"q": text, "limit": 10, "lang": self.options["language"]},
            300,
        )
        queries = []
        for i, feature in enumerate(locations.get("features", [])):
            lon, lat = feature["geometry"]["coordinates"][:2]
            queries.append(
                f"s{i}:stopsByRadius(lat:{lat},lon:{lon},radius:{int(self.options['station_radius'] * 2)})"
                + "{edges{node{stop{"
                + STOP_FIELDS
                + "}}}}"
            )
        stops = {}
        if queries:
            data = await self.query("{" + " ".join(queries) + "}", ttl=300)
            for group in data.values():
                for edge in group["edges"]:
                    raw = edge["node"]["stop"]
                    stop_id = normalized_id(raw["gtfsId"])
                    stops[stop_id] = {
                        "id": stop_id,
                        "name": raw["name"],
                        "lat": raw["lat"],
                        "lon": raw["lon"],
                        "routeIds": [normalized_id(r["gtfsId"]) for r in raw["routes"]],
                    }
        return {"references": {"routes": routes, "stops": stops}}

    async def vehicles_for_line(self, position, line):
        # Fetching the selected route's patterns includes both travel directions.
        routes = (await self.search(line))["references"]["routes"]
        exact = [
            upstream_id(r["id"])
            for r in routes.values()
            if (r.get("shortName") or "").casefold() == line.casefold()
        ]
        if not exact:
            return self.normalize_vehicles([])
        queries = [
            f"r{i}:route(id:{json.dumps(route)})"
            + "{patterns{vehiclePositions{"
            + VEHICLE_FIELDS
            + "}}}"
            for i, route in enumerate(exact)
        ]
        data = await self.query(
            "{" + " ".join(queries) + "}", ttl=self.options["vehicle_cache_seconds"]
        )
        vehicles = [
            v
            for route in data.values()
            if route
            for pattern in route.get("patterns", [])
            for v in pattern.get("vehiclePositions", [])
        ]
        return self.normalize_vehicles(vehicles)

    async def arrivals(self, stop_id, when):
        data = await self.query(
            ARRIVALS_QUERY,
            {
                "id": upstream_id(stop_id),
                "start": int(when),
                "range": int(self.options["timetable_window_minutes"] * 60),
            },
            self.options["vehicle_cache_seconds"],
        )
        times = [
            stop_time(raw, stop_id, normalized_id(raw["trip"]["route"]["gtfsId"]))
            for pattern in (data.get("stop") or {}).get("stoptimesForPatterns", [])
            for raw in pattern["stoptimes"]
        ]
        return {"entry": {"stopTimes": times}, "references": {}}

    async def plan(self, start, end):
        data = await self.query(
            PLAN_QUERY,
            {
                "from": f"{start[0]},{start[1]}",
                "to": f"{end[0]},{end[1]}",
                "modes": [{"mode": m} for m in ["WALK", *self.options["transit_modes"]]],
                "count": self.options["planner_itineraries"],
                "walk": self.options["walking_speed"],
                "locale": self.options["language"],
            },
            self.options["plan_cache_seconds"],
        )
        plans = []
        for raw in (data.get("plan") or {}).get("itineraries", []):
            legs = [
                {
                    **leg,
                    "routeId": normalized_id((leg.get("route") or {}).get("gtfsId")),
                    "routeShortName": (leg.get("route") or {}).get("shortName", ""),
                    "tripId": normalized_id((leg.get("trip") or {}).get("gtfsId")),
                }
                for leg in raw["legs"]
            ]
            plans.append(
                {"endTime": raw["endTime"], "transfers": raw["numberOfTransfers"], "legs": legs}
            )
        return {"entry": {"plan": {"itineraries": plans}}}
