"""Local interactive simulator: real BKK geometry, production detector, optional mock HA tracker."""

from __future__ import annotations

import argparse
import asyncio
import secrets
import socket
import time
from copy import deepcopy
from dataclasses import asdict
from math import isfinite
from pathlib import Path

import polyline
from aiohttp import ClientSession, ClientTimeout, web
from pyproj.enums import TransformDirection

from custom_components.bkkdetect.api import BkkError, Budget
from custom_components.bkkdetect.const import BOUNDS, DEFAULTS
from custom_components.bkkdetect.detection import Fix
from custom_components.bkkdetect.geo import GEODESIC, bearing, epoch
from custom_components.bkkdetect.history import VehicleHistory
from custom_components.bkkdetect.providers import create_client
from custom_components.bkkdetect.transit import TransitTracker

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).parent / "dist"
MOCK = "device_tracker.bkkdetect_simulator"


class Simulator:
    def __init__(self, session):
        env = {}
        if (ROOT / ".env").exists():
            env = dict(
                line.split("=", 1)
                for line in (ROOT / ".env").read_text().splitlines()
                if "=" in line and not line.startswith("#")
            )
        self.session = session
        self.ha_url = env.get("HA_URL", "").rstrip("/")
        self.ha_token = env.get("HA_TOKEN", "")
        self.options = deepcopy(DEFAULTS)
        self.api_options = {**self.options, "api_key": env.get("BKK_API_KEY", "")}
        self.client = create_client(session, self.api_options, Budget())
        self.entity = MOCK
        self.position = None
        self.position_timestamp = None
        self.selected = None
        self.routes = {}
        self.vehicles = []
        self.shape = None
        self.coordinates = []
        self.detail = None
        self.progress = 0
        self.now = time.time()
        self.history = VehicleHistory()
        self.detector = TransitTracker(MOCK, self.options)
        self.result = None
        self.events = []
        self.reports = []
        self.mode = "ha"
        self.lock = asyncio.Lock()
        self.ha_cache = (0, [])
        self.owned = False

    async def ha(self, path, method="GET", body=None, allow_missing=False):
        if not self.ha_url or not self.ha_token:
            raise ValueError("Set HA URL and token in Connections, or in the local .env")
        headers = {
            "Authorization": "Bearer " + self.ha_token,
            "User-Agent": "BKKDetectSimulator/0.3",
            "Content-Type": "application/json",
        }
        async with self.session.request(
            method,
            self.ha_url + "/api/" + path,
            headers=headers,
            json=body,
            timeout=ClientTimeout(total=15),
        ) as response:
            if response.status == 404 and allow_missing:
                return None
            if response.status not in (200, 201):
                raise ValueError(f"HA HTTP {response.status}")
            return await response.json()

    def at(self, progress):
        point = self.shape.line.interpolate(progress)
        lon, lat = self.shape.transformer.transform(
            point.x, point.y, direction=TransformDirection.INVERSE
        )
        return lat, lon

    def move(self, heading, metres):
        if not self.position:
            raise ValueError("Select a vehicle first")
        lon, lat, _ = GEODESIC.fwd(self.position[1], self.position[0], heading, metres)
        self.position = (lat, lon)
        self.position_timestamp = time.time()

    async def vehicles_for(self, point, line):
        if self.client.name == "bkk" and not self.client.key:
            raise ValueError("Set the BKK key in Connections or local .env")
        if self.client.name == "mavplusz":
            data = (
                await self.client.vehicles_for_line(point, line)
                if line
                else await self.client.vehicles(point)
            )
        elif line:
            data = await self.client.search(line)
            ids = [
                r["id"]
                for r in data.get("references", {}).get("routes", {}).values()
                if r.get("shortName", "").casefold() == line.casefold()
            ]
            if not ids:
                raise ValueError("No exact BKK line found. Try 80, 20E, 4, etc.")
            data = await self.client.request("vehicles-for-route", {"routeId": ids}, 25)
        else:
            data = await self.client.request(
                "vehicles-for-location",
                {"lat": round(point[0], 3), "lon": round(point[1], 3), "radius": 1200},
                25,
            )
        self.vehicles = data.get("list", [])
        self.routes.update(data.get("references", {}).get("routes", {}))
        return {"vehicles": [self.public_vehicle(v) for v in self.vehicles]}

    def public_vehicle(self, v):
        route = self.routes.get(v.get("routeId"), {})
        return {
            "id": v["vehicleId"],
            "tripId": v.get("tripId"),
            "lat": v["location"]["lat"],
            "lon": v["location"]["lon"],
            "line": route.get("shortName", v.get("routeId", "?")),
            "mode": route.get("type", v.get("vehicleRouteType", "")),
            "headsign": v.get("label", ""),
            "updatedAt": v.get("lastUpdateTime"),
        }

    async def select(self, vehicle_id):
        vehicle = next((v for v in self.vehicles if v["vehicleId"] == vehicle_id), None)
        if not vehicle or not vehicle.get("tripId"):
            raise ValueError("Refresh vehicles and select a vehicle with a trip")
        detail = await self.client.trip(vehicle["tripId"], vehicle.get("serviceDate"))
        history = VehicleHistory()
        history.pattern(vehicle["tripId"], detail)
        shape = history.patterns[vehicle["tripId"]]["geometry"]
        if shape is None:
            raise ValueError("This BKK trip has no route shape. Select another vehicle.")
        self.history = history
        self.shape = shape
        self.selected = deepcopy(vehicle)
        self.detail = detail
        self.coordinates = list(polyline.decode(detail["entry"]["polyline"]["points"]))
        self.progress = self.shape.project(
            (vehicle["location"]["lat"], vehicle["location"]["lon"])
        )[1]
        # Replay starts at the beginning, even when the selected live bus is at its terminus.
        self.start_progress = 0
        self.position = self.at(self.progress)
        self.reset()
        if self.mode == "replay":
            await self.report_replay()
        return self.snapshot()

    def reset(self):
        self.now = time.time()
        self.progress = getattr(self, "start_progress", 0)
        self.detector = TransitTracker(self.entity, self.options)
        self.history = VehicleHistory()
        if self.selected:
            self.history.pattern(self.selected["tripId"], self.detail)
        self.result = None
        self.events = []
        self.reports = []
        if self.shape:
            self.position = (
                self.at(self.progress)
                if self.mode == "replay"
                else (self.selected["location"]["lat"], self.selected["location"]["lon"])
            )
            self.position_timestamp = epoch(self.selected["lastUpdateTime"])

    async def report_replay(self):
        if not self.selected:
            raise ValueError("Select a vehicle first")
        current = self.at(self.progress)
        ahead = self.at(min(self.shape.line.length, self.progress + 5))
        vehicle = {
            **self.selected,
            "vehicleId": "SIM_" + self.selected["vehicleId"],
            "location": {"lat": current[0], "lon": current[1]},
            "lastUpdateTime": self.now,
            "bearing": bearing(current, ahead),
            "stale": False,
        }
        data = {"list": [vehicle], "references": {"routes": self.routes}}
        self.history.record(data, self.now, self.options)
        fix = Fix(self.position, self.now, 5)
        self.detector.add_fix(fix, self.now)
        self.result, events = await self.detector.evaluate(self.client, self.history, fix, self.now)
        self.events.extend(events)
        self.reports.append(asdict(fix))
        self.reports = self.reports[-500:]

    async def publish(self):
        existing = await self.ha("states/" + self.entity, allow_missing=True)
        if existing and not existing["attributes"].get("bkkdetect_simulator"):
            raise ValueError("This entity already exists and is not owned by the simulator")
        await self.ha(
            "states/" + self.entity,
            "POST",
            {
                "state": "not_home",
                "attributes": {
                    "friendly_name": "BKK Detect Mock Phone",
                    "source_type": "gps",
                    "latitude": self.position[0],
                    "longitude": self.position[1],
                    "gps_accuracy": 5,
                    "gps_timestamp": self.position_timestamp or time.time(),
                    "icon": "mdi:cellphone-wireless",
                    "bkkdetect_simulator": True,
                },
            },
        )
        self.owned = True
        self.reports.append({"position": self.position, "timestamp": time.time(), "accuracy": 5})
        self.reports = self.reports[-500:]

    async def live_status(self):
        if time.monotonic() - self.ha_cache[0] > 5:
            states = await self.ha("states")
            self.ha_cache = (
                time.monotonic(),
                [
                    s
                    for s in states
                    if s["entity_id"] != self.entity
                    and s.get("attributes", {}).get("tracker") == self.entity
                ],
            )
        return self.ha_cache[1]

    def snapshot(self):
        vehicle = None
        if self.selected:
            vehicle = self.public_vehicle(self.selected)
            if self.mode == "replay":
                lat, lon = self.at(self.progress)
                vehicle.update(lat=lat, lon=lon, id="SIM_" + vehicle["id"])
        return {
            "mode": self.mode,
            "provider": self.client.name,
            "entity": self.entity,
            "phone": self.position,
            "vehicle": vehicle,
            "path": self.coordinates,
            "result": self.result,
            "events": self.events[-30:],
            "reports": self.reports[-200:],
            "simulatedTime": self.now,
            "progressMeters": round(self.progress),
            "routeLengthMeters": round(self.shape.line.length) if self.shape else None,
            "budgetUsed": sum(
                stamp > time.monotonic() - 60 for stamp in self.client.budget.requests
            ),
            "budgetLimit": self.api_options["requests_per_minute"],
        }


def coordinate(value):
    result = tuple(float(x) for x in value)
    if (
        len(result) != 2
        or not all(isfinite(x) for x in result)
        or abs(result[0]) > 90
        or abs(result[1]) > 180
    ):
        raise ValueError("Invalid coordinates")
    return result


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3211)
    args = parser.parse_args()
    token = secrets.token_urlsafe(24)
    session = ClientSession()
    simulator = Simulator(session)

    @web.middleware
    async def guard(request, handler):
        try:
            if request.path.startswith("/api/"):
                supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
                if not secrets.compare_digest(supplied, token):
                    return web.json_response(
                        {
                            "error": "Open the URL printed by the server (it includes your session token)"
                        },
                        status=401,
                    )
                if (
                    request.headers.get("Origin")
                    and request.headers["Origin"] != f"{request.scheme}://{request.host}"
                ):
                    return web.json_response({"error": "Same-origin requests required"}, status=403)
            return await handler(request)
        except (ValueError, BkkError) as exc:
            return web.json_response({"error": str(exc)}, status=400)
        except Exception:  # noqa: BLE001 - Do not return upstream credentials in error details.
            return web.json_response(
                {"error": "Request failed; check the connection settings"}, status=502
            )

    app = web.Application(middlewares=[guard], client_max_size=65536)

    async def config(request):
        if request.method == "POST":
            data = await request.json()
            simulator.ha_url = data.get("haUrl", simulator.ha_url).rstrip("/")
            if data.get("haToken"):
                simulator.ha_token = data["haToken"]
            if data.get("bkkKey"):
                simulator.api_options["api_key"] = data["bkkKey"]
            provider = data.get("provider", simulator.client.name)
            if provider not in ("mavplusz", "bkk"):
                raise ValueError("Unknown vehicle provider")
            changed = provider != simulator.client.name
            simulator.api_options.update(
                vehicle_provider=provider,
                mav_base_url=data.get("mavBaseUrl", simulator.api_options["mav_base_url"]),
                mav_router=data.get("mavRouter", simulator.api_options["mav_router"]),
            )
            simulator.options["vehicle_provider"] = provider
            simulator.client = create_client(session, simulator.api_options, Budget())
            if changed:
                simulator.selected = None
                simulator.shape = None
                simulator.coordinates = []
                simulator.vehicles = []
                simulator.reset()
        return web.json_response(
            {
                "haUrl": simulator.ha_url,
                "hasHaToken": bool(simulator.ha_token),
                "hasBkkKey": bool(simulator.api_options.get("api_key")),
                "provider": simulator.client.name,
                "mavBaseUrl": simulator.api_options["mav_base_url"],
                "mavRouter": simulator.api_options["mav_router"],
                "entity": simulator.entity,
                "options": {
                    k: simulator.options[k]
                    for k in [
                        "match_samples",
                        "min_travel",
                        "match_distance",
                        "max_time_skew",
                        "route_deviation",
                        "exit_samples",
                        "exit_distance",
                    ]
                },
            }
        )

    async def bootstrap(request):
        center = None
        try:
            home = await simulator.ha("states/zone.home")
            center = [home["attributes"]["latitude"], home["attributes"]["longitude"]]
        except ValueError:
            pass
        if not center:
            if simulator.client.name == "mavplusz":
                raise ValueError(
                    "Set your HA connection or move the map to the area you want to browse"
                )
            metadata = await simulator.client.metadata()
            box = metadata["entry"]
            center = [
                (box["lowerLeftLatitude"] + box["upperRightLatitude"]) / 2,
                (box["lowerLeftLongitude"] + box["upperRightLongitude"]) / 2,
            ]
        return web.json_response({"center": center})

    async def vehicles(request):
        point = coordinate([request.query.get("lat", "47.5"), request.query.get("lon", "19.05")])
        return web.json_response(
            await simulator.vehicles_for(point, request.query.get("line", "").strip())
        )

    async def action(request):
        data = await request.json()
        async with simulator.lock:
            kind = data["action"]
            if kind == "select":
                return web.json_response(await simulator.select(data["id"]))
            if kind == "mode":
                if data["mode"] not in ("replay", "ha"):
                    raise ValueError("Invalid mode")
                simulator.mode = data["mode"]
                simulator.reset()
                if simulator.mode == "replay" and simulator.selected:
                    await simulator.report_replay()
            elif kind == "move":
                if "position" in data:
                    simulator.position = coordinate(data["position"])
                    simulator.position_timestamp = time.time()
                else:
                    simulator.move(
                        float(data["heading"]), max(1, min(500, float(data.get("metres", 10))))
                    )
                if simulator.mode == "ha":
                    await simulator.publish()
            elif kind == "step":
                if simulator.mode == "replay":
                    if not simulator.selected:
                        raise ValueError("Select a vehicle first")
                    delta = max(1, min(60, float(data.get("seconds", 10))))
                    speed = max(0.5, min(40, float(data.get("speed", 10))))
                    simulator.now += delta
                    simulator.progress = min(
                        simulator.shape.line.length - 1, simulator.progress + delta * speed
                    )
                    if data.get("follow"):
                        simulator.position = simulator.at(simulator.progress)
                    await simulator.report_replay()
                else:
                    if data.get("follow") and simulator.selected:
                        live = await simulator.client.vehicles_by_id(
                            [simulator.selected["vehicleId"]]
                        )
                        item = next(iter(live.get("list", [])), None)
                        if (
                            not item
                            or item.get("isEstimated")
                            or time.time() - epoch(item.get("lastUpdateTime"))
                            > simulator.options["max_vehicle_age"]
                        ):
                            raise ValueError(
                                "This vehicle has no fresh measured position. Choose another vehicle."
                            )
                        simulator.selected = item
                        simulator.position = (item["location"]["lat"], item["location"]["lon"])
                        simulator.position_timestamp = epoch(item["lastUpdateTime"])
                    else:
                        simulator.position_timestamp = time.time()
                    if not simulator.position:
                        raise ValueError("Select a vehicle or click the map first")
                    await simulator.publish()
            elif kind == "getoff":
                simulator.move(90, simulator.options["exit_distance"] * 3)
                if simulator.mode == "ha":
                    await simulator.publish()
            elif kind == "reset":
                simulator.reset()
                if simulator.selected and simulator.mode == "replay":
                    await simulator.report_replay()
            elif kind == "delete":
                state = await simulator.ha("states/" + simulator.entity, allow_missing=True)
                if state and state["attributes"].get("bkkdetect_simulator"):
                    await simulator.ha("states/" + simulator.entity, "DELETE")
                simulator.owned = False
            elif kind == "options":
                for key, value in data["values"].items():
                    if key not in BOUNDS:
                        raise ValueError("Unknown detector option")
                    numeric = float(value)
                    if not BOUNDS[key][0] <= numeric <= BOUNDS[key][1]:
                        raise ValueError("Detector option is outside allowed limits")
                    simulator.options[key] = numeric
                simulator.reset()
                if simulator.selected and simulator.mode == "replay":
                    await simulator.report_replay()
            else:
                raise ValueError("Unknown action")
            return web.json_response(simulator.snapshot())

    async def status(request):
        result = simulator.snapshot()
        if simulator.mode == "ha":
            try:
                result["haEntities"] = await simulator.live_status()
            except ValueError as exc:
                result["haError"] = str(exc)
        return web.json_response(result)

    async def index(request):
        return web.FileResponse(ASSETS / "index.html")

    app.router.add_get("/", index)
    app.router.add_route("*", "/api/config", config)
    app.router.add_get("/api/bootstrap", bootstrap)
    app.router.add_get("/api/vehicles", vehicles)
    app.router.add_post("/api/action", action)
    app.router.add_get("/api/status", status)
    app.router.add_static("/assets/", ASSETS)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, args.host, args.port).start()
    print(f"Open: http://127.0.0.1:{args.port}/#token={token}", flush=True)
    if args.host == "0.0.0.0":
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("1.1.1.1", 80))
            address = sock.getsockname()[0]
            print(f"Phone (same Wi-Fi): http://{address}:{args.port}/#token={token}", flush=True)
        finally:
            sock.close()
    try:
        await asyncio.Event().wait()
    finally:
        await runner.cleanup()
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
