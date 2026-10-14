"""Async BKK adapter using the endpoints in haverfalat/bkkfutar.js.

Python is required by Home Assistant; no Node runtime or external service is used.
Budgets are shared across config entries that use the same BKK key.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout


class BkkError(Exception):
    """Safe error that never contains an API key or response body."""


class RateLimited(BkkError):
    """Request budget exhausted or server asked us to wait."""


class Budget:
    def __init__(self):
        self.requests = deque()
        self.limits: dict[str, int] = {}
        self.blocked_until = 0.0

    def acquire(self, limit: int, reserve: int = 0):
        now = time.monotonic()
        while self.requests and self.requests[0] <= now - 60:
            self.requests.popleft()
        effective = min(self.limits.values(), default=limit)
        if now < self.blocked_until or len(self.requests) >= max(1, effective - reserve):
            raise RateLimited("Vehicle API request budget exhausted; waiting")
        self.requests.append(now)


class CachedClient:
    """Budget and cache shared by the two native async provider adapters."""

    def __init__(self, session: ClientSession, key: str, options: dict, budget: Budget):
        self.session, self.key, self.options, self.budget = session, key, options, budget
        self.cache: dict[str, tuple[float, Any]] = {}
        self.inflight: dict[str, asyncio.Task] = {}

    async def request(
        self, endpoint: str, params: dict | None = None, ttl: float = 0, reserve: int = 0
    ):
        params = params or {}
        cache_key = endpoint + repr(sorted(params.items()))
        cached = self.cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        if cache_key in self.inflight:
            return await asyncio.shield(self.inflight[cache_key])
        self.budget.acquire(int(self.options["requests_per_minute"]), reserve)
        task = asyncio.create_task(self._fetch(endpoint, params))
        self.inflight[cache_key] = task
        try:
            result = await asyncio.shield(task)
            self.cache[cache_key] = (time.monotonic() + ttl, result)
            if len(self.cache) > 500:
                self.cache.pop(next(iter(self.cache)))
            return result
        finally:
            self.inflight.pop(cache_key, None)


class BkkClient(CachedClient):
    name = "bkk"

    async def _fetch(self, endpoint: str, params: dict):
        query = [("key", self.key), ("version", "4")]
        for key, value in params.items():
            if value is None:
                continue
            for item in value if isinstance(value, list) else [value]:
                query.append((key, str(item).lower() if isinstance(item, bool) else str(item)))
        url = self.options["base_url"].rstrip("/") + "/otp/api/where/" + endpoint
        try:
            async with self.session.get(
                url, params=query, timeout=ClientTimeout(total=self.options["request_timeout"])
            ) as response:
                if response.status == 429:
                    try:
                        retry = float(response.headers.get("Retry-After", 0))
                    except ValueError:
                        retry = 0
                    self.budget.blocked_until = time.monotonic() + max(
                        retry, self.options["backoff_seconds"]
                    )
                    raise RateLimited("BKK rate limited; backing off")
                if response.status != 200:
                    raise BkkError(f"BKK HTTP {response.status}")
                body = await response.json()
        except TimeoutError, ClientError, ValueError:
            raise BkkError("BKK connection failed or invalid response") from None
        if body.get("code") != 200 or not isinstance(body.get("data"), dict):
            raise BkkError("BKK API rejected the request")
        return body["data"]

    async def metadata(self):
        return await self.request("metadata", ttl=300)

    async def search(self, query):
        return await self.request("search", {"query": query, "minResult": 10}, 300)

    async def vehicles(self, point):
        return await self.request(
            "vehicles-for-location",
            {
                "lat": round(point[0], 4),
                "lon": round(point[1], 4),
                "radius": self.options["vehicle_radius"],
            },
            self.options["vehicle_cache_seconds"],
        )

    async def trip(self, trip_id, date=None):
        return await self.request(
            "trip-details", {"tripId": trip_id, "date": date}, self.options["vehicle_cache_seconds"]
        )

    async def vehicles_by_id(self, vehicle_ids):
        return await self.request(
            "vehicles", {"vehicleId": sorted(vehicle_ids)}, self.options["vehicle_cache_seconds"]
        )

    async def arrivals(self, stop_id, when):
        return await self.request(
            "arrivals-and-departures-for-stop",
            {
                "stopId": [stop_id],
                "time": int(when),
                "minutesBefore": 1,
                "minutesAfter": self.options["timetable_window_minutes"],
            },
            self.options["vehicle_cache_seconds"],
        )

    async def plan(self, start, end):
        return await self.request(
            "plan-trip",
            {
                "fromPlace": f"{round(start[0], 4)},{round(start[1], 4)}",
                "toPlace": f"{end[0]},{end[1]}",
                "mode": ["WALK", *self.options["transit_modes"]],
                "numItineraries": self.options["planner_itineraries"],
                "showIntermediateStops": True,
            },
            self.options["plan_cache_seconds"],
        )
