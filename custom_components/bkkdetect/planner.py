"""Timetable-aware route and transfer estimation."""

from datetime import UTC, datetime
from math import ceil, isfinite

from .geo import distance, epoch


def iso(value):
    return datetime.fromtimestamp(value, UTC).isoformat()


async def automatic_plan(client, start, end, now):
    data = await client.plan(start, end)
    plans = [
        i
        for i in data.get("entry", {}).get("plan", {}).get("itineraries", [])
        if epoch(i.get("endTime")) > now
    ]
    if not plans:
        return None
    plan = min(plans, key=lambda i: epoch(i["endTime"]))
    return {
        "eta_minutes": ceil((epoch(plan["endTime"]) - now) / 60),
        "arrival_time": iso(epoch(plan["endTime"])),
        "source": "suggested_itinerary",
        "home_route": False,
        "transfers": plan.get("transfers", 0),
        "legs": [
            {
                "mode": leg["mode"],
                "line": leg.get("routeShortName", ""),
                "route_id": leg.get("routeId"),
                "trip_id": leg.get("tripId"),
                "from": leg["from"]["name"],
                "to": leg["to"]["name"],
                "departure": iso(epoch(leg["startTime"])),
                "arrival": iso(epoch(leg["endTime"])),
                "realtime": leg.get("realTime", False),
                "delay_seconds": leg.get("arrivalDelay", 0),
                "alerts": leg.get("alertIds", []),
            }
            for leg in plan["legs"]
        ],
    }


async def configured_plan(client, route, start, options, now, leg_index=0, match=None):
    cursor, result = now, []
    for index in range(leg_index, len(route["legs"])):
        leg = route["legs"][index]
        on_board = (
            index == leg_index
            and match
            and match["route_id"] == leg["route_id"]
            and match.get("trip_id")
        )
        if not on_board:
            cursor += (
                distance(start, (leg["from"]["lat"], leg["from"]["lon"])) / options["walking_speed"]
                if index == leg_index
                else leg["transfer_minutes"] * 60
            )
        if on_board:
            choices = [{"tripId": match["trip_id"], "serviceDate": match.get("service_date")}]
        else:
            data = await client.arrivals(leg["from"]["id"], cursor)
            trips = data.get("references", {}).get("trips", {})
            choices = [
                t
                for t in data.get("entry", {}).get("stopTimes", [])
                if not t.get("canceled")
                and t.get("pickupAllowed", True)
                and t.get("routeId", trips.get(t.get("tripId"), {}).get("routeId"))
                == leg["route_id"]
                and epoch(t.get("predictedDepartureTime", t.get("departureTime"))) >= cursor
            ]
            choices.sort(
                key=lambda t: epoch(t.get("predictedDepartureTime", t.get("departureTime")))
            )
            choices = choices[: int(options["timetable_candidates"])]
        chosen = None
        for trip in choices:
            if not trip.get("tripId"):
                continue
            data = await client.trip(trip["tripId"], trip.get("serviceDate"))
            entry = data.get("entry", {})
            stops = entry.get("stopTimes", [])
            board = next((i for i, s in enumerate(stops) if s["stopId"] == leg["from"]["id"]), -1)
            alight = next(
                (i for i, s in enumerate(stops) if s["stopId"] == leg["to"]["id"] and i > board), -1
            )
            if (
                board < 0
                or alight < 0
                or not stops[alight].get("dropOffAllowed", True)
                or (not on_board and not stops[board].get("pickupAllowed", True))
            ):
                continue
            arrival = epoch(
                stops[alight].get("predictedArrivalTime", stops[alight].get("arrivalTime"))
            )
            departure = (
                now
                if on_board
                else epoch(
                    stops[board].get("predictedDepartureTime", stops[board].get("departureTime"))
                )
            )
            if (
                not isfinite(arrival)
                or not isfinite(departure)
                or arrival < departure
                or departure < cursor - 5
            ):
                continue
            scheduled = epoch(stops[alight].get("arrivalTime"))
            chosen = {
                "mode": leg["mode"],
                "line": leg["line"],
                "route_id": leg["route_id"],
                "trip_id": trip["tripId"],
                "from": leg["from"]["name"],
                "to": leg["to"]["name"],
                "departure": iso(departure),
                "arrival": iso(arrival),
                "realtime": "predictedArrivalTime" in stops[alight]
                and not stops[alight].get("predictionScheduled", False),
                "delay_seconds": round(arrival - scheduled) if isfinite(scheduled) else 0,
                "alerts": entry.get("alertIds", []),
            }
            break
        if not chosen:
            return None
        result.append(chosen)
        cursor = epoch(chosen["arrival"])
    cursor += route["final_walk_minutes"] * 60
    return {
        "eta_minutes": max(0, ceil((cursor - now) / 60)),
        "arrival_time": iso(cursor),
        "source": "configured_route_timetable",
        "route_id": route["id"],
        "route_name": route["name"],
        "home_route": bool(match),
        "transfers": max(0, len(result) - 1),
        "legs": result,
    }
