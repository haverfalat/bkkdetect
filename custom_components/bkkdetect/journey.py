"""Optional home-arrival state machine consuming the primary transit detector."""

from __future__ import annotations

import re
from math import ceil, isfinite

from .api import BkkError
from .const import STATUS, TEXTS
from .geo import distance, epoch
from .planner import automatic_plan, configured_plan, iso


class Journey:
    def __init__(self, options):
        self.options = options
        self.fixes = []
        self.match = None
        self.match_at = 0
        self.active_route = None
        self.leg_index = 0
        self.route_at = 0
        self.manual = False
        self.estimate = None
        self.final_walk_arrival = None

    def start(self, route_id, now):
        self.active_route = route_id
        self.leg_index = 0
        self.route_at = now
        self.manual = bool(route_id)
        self.match = None
        self.estimate = None
        self.final_walk_arrival = None

    def finish(self, result):
        options = self.options
        language = options["language"]
        status = result["status"]
        estimate = result.get("estimate") or {}
        match = result.get("match") or {}
        result.update(
            {
                "eta_minutes": estimate.get("eta_minutes", result.get("eta_minutes")),
                "arrival_time": estimate.get("arrival_time"),
                "legs": estimate.get("legs", []),
                "source": estimate.get("source"),
                "route_name": estimate.get("route_name"),
                "route_id": self.active_route,
                "leg_index": self.leg_index,
            }
        )
        first = next(iter(result["legs"]), {})
        values = {
            **result,
            "name": options["name"],
            "status": STATUS[language].get(status, status),
            "eta": result["eta_minutes"],
            "line": match.get("line", first.get("line")),
            "mode": match.get("mode", first.get("mode")),
            "headsign": match.get("headsign"),
            "vehicle": match.get("vehicle_id"),
            "next_stop": first.get("to"),
            "transfers": estimate.get("transfers"),
            "route": estimate.get("route_name"),
            "arrival": result["arrival_time"],
            "confidence": round(result["confidence"] * 100),
            "tracker": options["tracker"],
        }
        result.update({key: values.get(key) for key in ("line", "mode", "headsign")})
        result["vehicle_id"] = match.get("vehicle_id")
        result["trip_id"] = match.get("trip_id")
        key = (
            "home"
            if status == "home"
            else "inferred"
            if status == "inferred"
            else "journey"
            if status == "transit"
            else "unknown"
            if status in ("stale", "unknown", "paused")
            else "away"
        )
        template = options.get("text_" + key, TEXTS[language][key])
        result["text"] = re.sub(
            r"\{([a-zA-Z_]+)\}",
            lambda m: str(values.get(m[1]) if values.get(m[1]) is not None else "—"),
            template,
        )[:255]
        result.pop("estimate", None)
        return result

    async def update(self, client, fix, home, home_state, now):
        o = self.options
        result = {
            "status": "unknown",
            "confidence": 0,
            "eta_minutes": None,
            "arrival_time": None,
            "home_route": False,
            "match": None,
            "evidence": [],
            "updated_at": iso(now),
            "gps_age_seconds": round(now - fix.timestamp)
            if fix and isfinite(fix.timestamp)
            else None,
            "gps_accuracy_meters": fix.accuracy if fix else None,
            "tracker": o["tracker"],
        }
        if not o["enabled"]:
            result["status"] = "paused"
            return self.finish(result)
        fresh = (
            fix
            and isfinite(fix.timestamp)
            and -30 <= now - fix.timestamp <= o["gps_stale_seconds"]
            and 0 <= fix.accuracy <= o["max_gps_accuracy"]
        )
        if home_state or (
            fresh and distance(fix.position, home) + fix.accuracy <= o["home_radius"]
        ):
            self.start(None, now)
            self.fixes = []
            result.update(status="home", confidence=1, eta_minutes=0)
            return self.finish(result)
        if self.route_at and now - self.route_at > o["route_expiry_minutes"] * 60:
            self.start(None, now)
        route = next(
            (r for r in o["routes"] if r["id"] == self.active_route and r.get("enabled", True)),
            None,
        )
        if not fresh:
            leg = route["legs"][self.leg_index] if route else None
            last = self.fixes[-1] if self.fixes else None
            if (
                o["metro_inference"]
                and leg
                and leg["mode"] == "SUBWAY"
                and now - self.route_at < o["metro_grace_minutes"] * 60
                and last
                and distance(last.position, (leg["from"]["lat"], leg["from"]["lon"]))
                < o["station_radius"]
                and self.estimate
                and epoch(self.estimate["arrival_time"]) > now
            ):
                result.update(
                    status="inferred",
                    confidence=0.45,
                    home_route=True,
                    evidence=[
                        "established_route",
                        "metro_entry_anchor",
                        "gps_gap",
                        "timetable_estimate",
                    ],
                    estimate={
                        **self.estimate,
                        "eta_minutes": max(
                            0, ceil((epoch(self.estimate["arrival_time"]) - now) / 60)
                        ),
                        "source": "metro_inferred_from_last_timetable",
                    },
                )
            else:
                result["status"] = "stale" if fix else "unknown"
                self.match = None
            return self.finish(result)
        previous = self.fixes[-1] if self.fixes else None
        # Vehicle identity is supplied by the primary timestamp/route-shape detector.
        if now - self.match_at > o["match_hold_seconds"]:
            self.match = None
        if self.match:
            result.update(
                status="transit",
                match=self.match,
                confidence=self.match["confidence"],
                evidence=self.match["evidence"],
            )
            if not route:
                # Resolve direction against trip stop order before marking a home route.
                for candidate in o["routes"]:
                    if not candidate.get("enabled", True):
                        continue
                    for index, leg in enumerate(candidate["legs"]):
                        if leg["route_id"] != self.match["route_id"]:
                            continue
                        try:
                            estimate = await configured_plan(
                                client, candidate, fix.position, o, now, index, self.match
                            )
                        except BkkError:
                            estimate = None
                        if estimate:
                            route = candidate
                            self.active_route, self.leg_index, self.route_at = (
                                candidate["id"],
                                index,
                                now,
                            )
                            result["estimate"] = self.estimate = estimate
                            result["home_route"] = True
                            break
                    if route:
                        break
            elif route["legs"][self.leg_index]["route_id"] != self.match["route_id"]:
                next_leg = next(
                    (
                        i
                        for i, l in enumerate(route["legs"])
                        if i > self.leg_index and l["route_id"] == self.match["route_id"]
                    ),
                    None,
                )
                if next_leg is not None:
                    self.leg_index, self.route_at = next_leg, now
        else:
            speed = (
                distance(previous.position, fix.position)
                / max(1, fix.timestamp - previous.timestamp)
                if previous and fix.timestamp > previous.timestamp
                else 0
            )
            result["status"] = "walking" if 0.5 < speed < o["min_speed"] else "away"
        if route:
            leg = route["legs"][self.leg_index]
            if (
                distance(fix.position, (leg["to"]["lat"], leg["to"]["lon"])) < o["station_radius"]
                and distance(
                    (leg["from"]["lat"], leg["from"]["lon"]), (leg["to"]["lat"], leg["to"]["lon"])
                )
                > o["station_radius"] * 2
            ):
                anchor = next(
                    (
                        p
                        for p in reversed(self.fixes)
                        if p.timestamp < fix.timestamp
                        and distance(p.position, (leg["from"]["lat"], leg["from"]["lon"]))
                        < o["station_radius"]
                    ),
                    None,
                )
                plausible = (
                    anchor
                    and fix.timestamp - anchor.timestamp
                    >= distance(anchor.position, fix.position) / o["max_speed"]
                )
                if (
                    o["metro_inference"]
                    and leg["mode"] == "SUBWAY"
                    and plausible
                    and now - self.route_at < o["metro_grace_minutes"] * 60
                ):
                    result.update(
                        status="inferred",
                        confidence=0.5,
                        evidence=[
                            "metro_entry_and_exit_anchors",
                            "plausible_elapsed_time",
                            "configured_route",
                        ],
                    )
                if self.leg_index < len(route["legs"]) - 1:
                    self.leg_index += 1
                    self.route_at = now
                    self.match = None
                    result["match"] = None
                elif not self.match:
                    self.final_walk_arrival = (
                        self.final_walk_arrival or now + route["final_walk_minutes"] * 60
                    )
                    result["estimate"] = {
                        "eta_minutes": max(0, ceil((self.final_walk_arrival - now) / 60)),
                        "arrival_time": iso(self.final_walk_arrival),
                        "source": "configured_final_walk",
                        "route_name": route["name"],
                        "legs": [],
                        "transfers": 0,
                    }
                    result["home_route"] = True
            if not result.get("estimate"):
                try:
                    estimate = await configured_plan(
                        client, route, fix.position, o, now, self.leg_index, self.match
                    )
                    if estimate:
                        result["estimate"] = self.estimate = estimate
                        result["home_route"] = estimate["home_route"] or self.manual
                except BkkError as error:
                    result["error"] = str(error)
        if not result.get("estimate"):
            try:
                result["estimate"] = await automatic_plan(client, fix.position, home, now)
            except BkkError as error:
                result["error"] = str(error)
        return self.finish(result)
