"""Vehicle journey identification with retrospective boarding / alighting evidence."""

from dataclasses import asdict
from uuid import uuid4

from .api import BkkError
from .detection import Fix
from .geo import distance
from .matching import boarding_evidence
from .planner import iso


class TransitTracker:
    def __init__(self, tracker, options):
        self.tracker, self.options = tracker, options
        self.fixes = []
        self.active = None
        self.exit_fixes = []
        self.last_processed = None
        self.last_fetch = 0
        self.last_journey = None

    def add_fix(self, fix, now):
        if fix and not any(p.timestamp == fix.timestamp for p in self.fixes):
            self.fixes.append(fix)
            self.fixes.sort(key=lambda p: p.timestamp)
            self.fixes = [
                p for p in self.fixes if p.timestamp > now - self.options["history_minutes"] * 60
            ]
            return True
        return False

    def checkpoint(self):
        return {
            "active": self.active,
            "last_journey": self.last_journey,
            "fixes": [asdict(f) for f in self.fixes],
            "last_fetch": self.last_fetch,
        }

    def restore(self, state, now):
        self.active = state.get("active")
        if self.active and (
            self.active["match"].get("provider", "bkk") != self.options["vehicle_provider"]
            or self.active["match"].get("mode") not in self.options["transit_modes"]
        ):
            self.active = None
        self.last_journey = state.get("last_journey")
        self.fixes = [
            Fix(tuple(p["position"]), p["timestamp"], p["accuracy"])
            for p in state.get("fixes", [])
            if p["timestamp"] > now - self.options["history_minutes"] * 60
        ]

    async def evaluate(self, client, history, fix, now):
        o = self.options
        result = {
            "tracker": self.tracker,
            "status": "no_gps" if not fix else "not_on_transit",
            "confidence": 0,
            "match": None,
            "boarding": None,
            "alighting": None,
            "active_journey": self.active,
            "last_journey": self.last_journey,
            "evidence": [],
            "detection_reason": "no_timestamp_aligned_vehicle",
            "candidates": [],
            "gps_reports": len(self.fixes),
            "vehicle_reports": sum(len(v) for v in history.samples.values()),
            "updated_at": iso(now),
        }
        events = []
        if (
            not fix
            or now - fix.timestamp > o["gps_stale_seconds"]
            or fix.timestamp > now + 30
            or fix.accuracy > o["max_gps_accuracy"]
        ):
            result["status"] = "uncertain" if self.active else "no_gps" if not fix else "stale"
            result["detection_reason"] = (
                "missing_gps" if not fix else "gps_time_or_accuracy_invalid"
            )
            return result, events
        # An active passenger can be motionless while the vehicle waits at a stop.
        if self.active:
            aligned = history.aligned(self.active["vehicle_id"], fix.timestamp, o["max_time_skew"])
            if aligned:
                separation = distance(fix.position, aligned["position"])
                if separation <= o["match_distance"] + min(fix.accuracy, o["match_distance"]):
                    if aligned.get("tripId") and aligned["tripId"] != self.active.get("trip_id"):
                        route = history.routes.get(aligned.get("routeId"), {})
                        self.active["trip_id"] = aligned["tripId"]
                        self.active["match"] = {
                            **self.active["match"],
                            "trip_id": aligned["tripId"],
                            "route_id": aligned.get("routeId"),
                            "line": route.get("shortName", aligned.get("routeId")),
                            "headsign": aligned.get("label", ""),
                        }
                        events.append(
                            {
                                "type": "trip_changed",
                                "tracker": self.tracker,
                                "journey": self.active.copy(),
                            }
                        )
                    self.exit_fixes = []
                    self.active["match"]["distance_meters"] = round(separation)
                    self.active["match"]["time_skew_seconds"] = aligned["time_skew"]
                    self.active["last_matched_at"] = iso(fix.timestamp)
                    result.update(
                        status="on_transit",
                        detection_reason="matched",
                        confidence=self.active["confidence"],
                        match=self.active["match"],
                        boarding=self.active["boarding"],
                        evidence=self.active["match"]["evidence"],
                    )
                    return result, events
                if separation > o["exit_distance"] + fix.accuracy and not any(
                    p.timestamp == fix.timestamp for p in self.exit_fixes
                ):
                    self.exit_fixes = [
                        p
                        for p in self.exit_fixes
                        if fix.timestamp - p.timestamp <= o["gps_stale_seconds"]
                    ]
                    self.exit_fixes.append(fix)
                elif separation <= o["exit_distance"] + fix.accuracy:
                    self.exit_fixes = []
                if len(self.exit_fixes) >= int(o["exit_samples"]):
                    first = self.exit_fixes[0]
                    from .geo import epoch

                    lower = epoch(self.active["last_matched_at"])
                    alighting = {
                        "estimated_at": iso(first.timestamp),
                        "earliest_at": iso(lower),
                        "latest_at": iso(first.timestamp),
                        "confirmed_at": iso(now),
                        "backfilled_seconds": round(now - first.timestamp),
                        "stop": history.nearest_stop(
                            self.active.get("trip_id"), first.position, o["station_radius"]
                        ),
                        "exact": False,
                    }
                    completed = {
                        **self.active,
                        "alighting": alighting,
                        "duration_seconds": max(
                            0,
                            round(first.timestamp - epoch(self.active["boarding"]["estimated_at"])),
                        ),
                    }
                    events.append(
                        {"type": "alighting", "tracker": self.tracker, "journey": completed}
                    )
                    self.last_journey = completed
                    self.active = None
                    self.exit_fixes = []
                    result.update(alighting=alighting, last_journey=completed, active_journey=None)
                else:
                    result.update(
                        status="uncertain",
                        detection_reason="waiting_for_alighting_evidence",
                        boarding=self.active["boarding"],
                        match=self.active["match"],
                    )
                    return result, events
            else:
                # Absence of historic vehicle evidence is not evidence of alighting.
                result.update(
                    status="uncertain",
                    detection_reason="missing_timed_vehicle_reports",
                    boarding=self.active["boarding"],
                    match=self.active["match"],
                )
                return result, events
        matches = []
        fixes = [p for p in self.fixes if p.accuracy <= o["max_gps_accuracy"]]
        if len(fixes) < int(o["match_samples"]) + 1:
            result["detection_reason"] = "insufficient_gps_reports"
            return result, events
        latest = fixes[-1]
        for vehicle_id in history.samples:
            aligned = history.aligned(vehicle_id, latest.timestamp, o["max_time_skew"])
            if not aligned or distance(latest.position, aligned["position"]) > o[
                "match_distance"
            ] + min(latest.accuracy, o["match_distance"]):
                continue
            route = history.routes.get(aligned.get("routeId"), {})
            mode = route.get("type", aligned.get("vehicleRouteType"))
            if mode not in o["transit_modes"]:
                continue
            trip_id = aligned.get("tripId")
            if not trip_id:
                continue
            if trip_id not in history.patterns:
                try:
                    history.pattern(trip_id, await client.trip(trip_id, aligned.get("serviceDate")))
                except BkkError as exc:
                    result["candidates"].append(
                        {
                            "vehicle_id": vehicle_id,
                            "line": route.get("shortName"),
                            "reason": "trip_geometry_unavailable",
                            "error": str(exc),
                        }
                    )
                    continue
            geometry = history.patterns[trip_id]["geometry"]
            if geometry is None:
                # Do not claim route-following evidence without a supplied shape.
                result["candidates"].append(
                    {
                        "vehicle_id": vehicle_id,
                        "line": route.get("shortName"),
                        "reason": "missing_route_geometry",
                    }
                )
                continue
            diagnostics, first = boarding_evidence(fixes, vehicle_id, trip_id, geometry, history, o)
            result["candidates"].append(
                {"vehicle_id": vehicle_id, "line": route.get("shortName"), **diagnostics}
            )
            if not diagnostics["confirmed"]:
                continue
            count = diagnostics["matched_segments"]
            separation = distance(latest.position, aligned["position"])
            confidence = min(0.97, 0.7 + count * 0.05 - separation / 1000)
            match = {
                "vehicle_id": vehicle_id,
                "provider": o["vehicle_provider"],
                "trip_id": trip_id,
                "service_date": aligned.get("serviceDate"),
                "route_id": aligned.get("routeId"),
                "line": route.get("shortName", aligned.get("routeId")),
                "mode": mode,
                "headsign": aligned.get("label", ""),
                "confidence": confidence,
                "evidence": [
                    "timestamp_aligned_vehicle_history",
                    "repeated_co_movement",
                    "route_geometry",
                    "direction",
                    "plausible_speed",
                ],
                "time_skew_seconds": aligned["time_skew"],
                "distance_meters": round(separation),
            }
            matches.append((confidence, match, first, None))
        result["candidates"].sort(key=lambda c: c.get("matched_segments", 0), reverse=True)
        result["candidates"] = result["candidates"][:5]
        if result["candidates"]:
            result["detection_reason"] = result["candidates"][0]["reason"]
        matches.sort(key=lambda m: m[0], reverse=True)
        if len(matches) > 1 and matches[0][0] - matches[1][0] < o["ambiguity_margin"]:
            result["status"] = "ambiguous"
            result["evidence"] = ["multiple_matching_vehicles"]
            result["detection_reason"] = "multiple_matching_vehicles"
            return result, events
        if matches:
            confidence, match, first, _outside = matches[0]
            earlier = []
            for p in fixes:
                if p.timestamp >= first.timestamp:
                    break
                timed = history.aligned(match["vehicle_id"], p.timestamp, o["max_time_skew"])
                if (
                    timed
                    and distance(p.position, timed["position"]) > o["exit_distance"] + p.accuracy
                ):
                    earlier.append(p)
            earliest = earlier[-1].timestamp if earlier else None
            boarding = {
                "estimated_at": iso(first.timestamp),
                "earliest_at": iso(earliest) if earliest is not None else None,
                "interval_basis": "last_separated_report"
                if earliest is not None
                else "before_history_unknown",
                "latest_at": iso(first.timestamp),
                "confirmed_at": iso(now),
                "backfilled_seconds": round(now - first.timestamp),
                "stop": history.nearest_stop(match["trip_id"], first.position, o["station_radius"]),
                "exact": False,
            }
            self.active = {
                "id": uuid4().hex,
                "vehicle_id": match["vehicle_id"],
                "trip_id": match["trip_id"],
                "match": match,
                "confidence": confidence,
                "boarding": boarding,
                "last_matched_at": iso(latest.timestamp),
            }
            events.append(
                {"type": "boarding", "tracker": self.tracker, "journey": self.active.copy()}
            )
            result.update(
                status="on_transit",
                detection_reason="matched",
                confidence=confidence,
                match=match,
                boarding=boarding,
                active_journey=self.active,
                evidence=match["evidence"],
            )
        return result, events
