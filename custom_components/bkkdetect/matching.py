"""Explainable boarding evidence; stops do not count as movement or erase it."""

from itertools import pairwise

from .geo import bearing, distance, heading_difference


def boarding_evidence(fixes, vehicle_id, trip_id, geometry, history, options):
    o = options
    latest = fixes[-1]
    recent = [p for p in fixes if latest.timestamp - p.timestamp <= o["movement_window_seconds"]]
    count, total, first, source_times = 0, 0.0, None, set()
    reason = "waiting_for_motion"
    for previous, current in pairwise(recent):
        prior = history.aligned(vehicle_id, previous.timestamp, o["max_time_skew"])
        timed = history.aligned(vehicle_id, current.timestamp, o["max_time_skew"])
        elapsed = current.timestamp - previous.timestamp
        if not prior or not timed:
            # An unavailable sample supplies no evidence. A later bracket may fill it in.
            reason = "missing_timed_vehicle_reports"
            continue
        if prior.get("tripId") != trip_id or timed.get("tripId") != trip_id:
            count, total, first, source_times = 0, 0.0, None, set()
            reason = "different_trip"
            continue
        near = all(
            distance(p.position, v["position"])
            <= o["match_distance"] + min(p.accuracy, o["match_distance"])
            for p, v in ((previous, prior), (current, timed))
        )
        shape_distance, progress = geometry.project(current.position)
        old_distance, old_progress = geometry.project(previous.position)
        route_ok = (
            shape_distance <= o["route_deviation"] + current.accuracy
            and old_distance <= o["route_deviation"] + previous.accuracy
            and progress >= old_progress - current.accuracy - previous.accuracy
        )
        if not near or not route_ok or elapsed <= 0 or elapsed > o["gps_stale_seconds"]:
            count, total, first, source_times = 0, 0.0, None, set()
            reason = (
                "separated_from_vehicle"
                if not near
                else "off_route_or_wrong_direction"
                if not route_ok
                else "gps_report_gap"
            )
            continue
        phone_movement = distance(previous.position, current.position)
        vehicle_movement = distance(prior["position"], timed["position"])
        speed, vehicle_speed = phone_movement / elapsed, vehicle_movement / elapsed
        if max(speed, vehicle_speed) > o["max_speed"]:
            count, total, first, source_times = 0, 0.0, None, set()
            reason = "implausible_speed"
            continue
        first = first or previous
        if (
            min(speed, vehicle_speed) < o["min_speed"]
            or phone_movement <= current.accuracy + previous.accuracy
        ):
            # Waiting at a stop, a cached vehicle ping or GPS jitter isn't a motion segment.
            continue
        # Compare displacements over the SAME time interval, rather than a chord
        # of the phone's path against the vehicle's instantaneous heading at a turn.
        heading_ok = (
            heading_difference(
                bearing(previous.position, current.position),
                bearing(prior["position"], timed["position"]),
            )
            <= o["max_bearing_difference"]
        )
        co_movement = (
            abs(vehicle_movement - phone_movement)
            <= o["match_distance"] + current.accuracy + previous.accuracy
        )
        if not heading_ok or not co_movement:
            count, total, first, source_times = 0, 0.0, None, set()
            reason = "different_motion"
            continue
        count += 1
        total += min(phone_movement, vehicle_movement)
        source_times.update(prior["sample_times"])
        source_times.update(timed["sample_times"])
        reason = "waiting_for_more_motion"
    elapsed = latest.timestamp - first.timestamp if first else 0
    confirmed = (
        count >= o["match_samples"]
        and len(source_times) >= o["match_samples"] + 1
        and total >= o["min_travel"]
        and elapsed >= o["min_match_seconds"]
    )
    return {
        "reason": "matched" if confirmed else reason,
        "matched_segments": count,
        "required_segments": int(o["match_samples"]),
        "independent_vehicle_reports": len(source_times),
        "required_vehicle_reports": int(o["match_samples"]) + 1,
        "travel_meters": round(total),
        "required_travel_meters": o["min_travel"],
        "elapsed_seconds": round(elapsed),
        "required_duration_seconds": o["min_match_seconds"],
        "confirmed": confirmed,
    }, first
