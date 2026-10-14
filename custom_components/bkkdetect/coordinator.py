"""Discover all trackers and coordinate budgeted vehicle-history collection."""

from __future__ import annotations

import hashlib
import logging
import time
from copy import deepcopy
from datetime import timedelta
from math import isfinite

from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import BkkClient, BkkError, Budget
from .const import DEFAULTS, DOMAIN
from .detection import Fix
from .geo import distance, epoch, point
from .history import VehicleHistory
from .journal import Journal
from .journey import Journey
from .transit import TransitTracker

LOGGER = logging.getLogger(__name__)


class BkkDetectCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        self.options = {**deepcopy(DEFAULTS), **entry.data, **entry.options}
        self.entry = entry
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=self.options["poll_seconds"]),
        )
        domain = hass.data.setdefault(DOMAIN, {"budgets": {}, "entries": {}})
        key_id = hashlib.sha256(self.options["api_key"].encode()).hexdigest()
        self.budget = domain["budgets"].setdefault(key_id, Budget())
        self.budget.limits[entry.entry_id] = int(self.options["requests_per_minute"])
        self.client = BkkClient(
            async_get_clientsession(hass), self.options["api_key"], self.options, self.budget
        )
        self.history = VehicleHistory()
        self.trackers = {}
        self.home_journeys = {}
        self.journal = Journal(hass, entry.entry_id, self.options)
        self.rotation = 0
        self.last_logged_status = {}

    async def initialize(self):
        await self.journal.load()
        now = time.time()
        for event in self.journal.events:
            if (
                event.get("type") == "vehicle_snapshot"
                and event["recorded_epoch"] > now - self.options["history_minutes"] * 60
            ):
                self.history.record(event["data"], event["recorded_epoch"], self.options)

    def selected(self, state):
        includes = self.options["include_trackers"]
        return state.entity_id not in self.options["exclude_trackers"] and (
            state.entity_id in includes
            if includes
            else state.entity_id.startswith("device_tracker.")
        )

    def profile(self, entity_id):
        profile = self.options.get("profiles", {}).get(entity_id, {})
        state = self.hass.states.get(entity_id)
        return {
            **self.options,
            **profile,
            "tracker": entity_id,
            "name": profile.get("name")
            or (state.attributes.get("friendly_name", entity_id) if state else entity_id),
        }

    def extract_fix(self, state, profile):
        position = point(state.attributes)
        stamp = (
            epoch(state.attributes.get(profile["gps_timestamp_attribute"]))
            if profile["gps_timestamp_attribute"]
            else state.last_updated.timestamp()
        )
        try:
            accuracy = max(0, float(state.attributes.get("gps_accuracy", 0)))
        except ValueError, TypeError:
            return None
        if (
            position
            and isfinite(stamp)
            and isfinite(accuracy)
            and state.state not in ("unavailable", "unknown")
        ):
            return Fix(position, stamp, accuracy)
        return None

    @callback
    def ingest(self, state):
        """Capture every source report, including ones occurring between polling cycles."""
        profile = self.profile(state.entity_id)
        memory = self.trackers.setdefault(state.entity_id, TransitTracker(state.entity_id, profile))
        fix = self.extract_fix(state, profile)
        if memory.add_fix(fix, time.time()) and profile["log_positions"]:
            self.journal.append(
                {
                    "type": "tracker_fix",
                    "tracker": state.entity_id,
                    "timestamp": fix.timestamp,
                    "latitude": fix.position[0],
                    "longitude": fix.position[1],
                    "accuracy": fix.accuracy,
                    "state": state.state,
                }
            )

    async def _async_update_data(self):
        now = time.time()
        states = [s for s in self.hass.states.async_all() if self.selected(s)]
        # Rotation prevents one group of trackers monopolizing the shared BKK budget.
        if states:
            offset = self.rotation % len(states)
            states = states[offset:] + states[:offset]
            self.rotation += max(
                1, int(self.options["requests_per_minute"] * self.options["poll_seconds"] / 60)
            )
        data = {}
        # Continue observing an identified vehicle even after the phone leaves its search radius.
        active_ids = sorted(
            {
                m.active["vehicle_id"]
                for m in self.trackers.values()
                if m.active
                and m.fixes
                and now - m.fixes[-1].timestamp < self.options["active_uncertainty_minutes"] * 60
            }
        )
        batch_size = int(self.options["active_vehicle_batch_size"])
        for offset in range(0, len(active_ids), batch_size):
            try:
                vehicles = await self.client.vehicles_by_id(
                    active_ids[offset : offset + batch_size]
                )
                self.history.record(vehicles, now, self.options)
                if self.options["log_vehicles"]:
                    self.journal.append(
                        {
                            "type": "vehicle_snapshot",
                            "data": vehicles,
                            "source": "active_vehicle_ids",
                        }
                    )
            except BkkError as exc:
                self.journal.append(
                    {
                        "type": "api_wait_or_error",
                        "message": str(exc),
                        "source": "active_vehicle_ids",
                    }
                )
                break
        for state in states:
            tracker = state.entity_id
            profile = self.profile(tracker)
            memory = self.trackers.get(tracker)
            if memory is None:
                memory = self.trackers[tracker] = TransitTracker(tracker, profile)
                if tracker in self.journal.states:
                    memory.restore(self.journal.states[tracker], now)
                self.journal.append(
                    {
                        "type": "tracker_discovered",
                        "tracker": tracker,
                        "has_gps": point(state.attributes) is not None,
                    }
                )
            fix = self.extract_fix(state, profile)
            position = fix.position if fix else None
            stamp = fix.timestamp if fix else 0
            accuracy = fix.accuracy if fix else None
            if memory.add_fix(fix, now) and profile["log_positions"]:
                self.journal.append(
                    {
                        "type": "tracker_fix",
                        "tracker": tracker,
                        "timestamp": stamp,
                        "latitude": position[0],
                        "longitude": position[1],
                        "accuracy": accuracy,
                        "state": state.state,
                    }
                )
            previous = memory.fixes[-2] if len(memory.fixes) > 1 else None
            moving = (
                fix
                and previous
                and fix.timestamp > previous.timestamp
                and distance(previous.position, fix.position)
                / max(1, fix.timestamp - previous.timestamp)
                > profile["min_speed"]
            )
            error = None
            interval = (
                profile["poll_seconds"] if moving or memory.active else profile["idle_poll_seconds"]
            )
            if (
                profile["enabled"]
                and fix
                and -30 <= now - fix.timestamp <= profile["gps_stale_seconds"]
                and fix.accuracy <= profile["max_gps_accuracy"]
                and now - memory.last_fetch >= interval
            ):
                try:
                    vehicles = await self.client.vehicles(fix.position)
                    memory.last_fetch = now
                    self.history.record(vehicles, now, profile)
                    if profile["log_vehicles"]:
                        self.journal.append(
                            {"type": "vehicle_snapshot", "tracker": tracker, "data": vehicles}
                        )
                except BkkError as exc:
                    error = str(exc)
                    self.journal.append(
                        {"type": "api_wait_or_error", "tracker": tracker, "message": error}
                    )
            if profile["enabled"]:
                result, events = await memory.evaluate(self.client, self.history, fix, now)
            else:
                result, events = (
                    {
                        "tracker": tracker,
                        "status": "paused",
                        "match": None,
                        "confidence": 0,
                        "updated_at": epoch(now),
                    },
                    [],
                )
            result.update(
                name=profile["name"],
                language=profile["language"],
                home_arrival_enabled=profile["home_arrival_enabled"],
                gps_age_seconds=round(now - stamp) if fix else None,
            )
            if error:
                result["error"] = error
            for event in events:
                self.journal.append(event)
                self.hass.bus.async_fire(f"{DOMAIN}_{event['type']}", deepcopy(event))
                LOGGER.info(
                    "%s: %s on %s", tracker, event["type"], event["journey"]["match"].get("line")
                )
            if self.last_logged_status.get(tracker) != result["status"]:
                self.journal.append(
                    {
                        "type": "detection_status",
                        "tracker": tracker,
                        "status": result["status"],
                        "evidence": result.get("evidence", []),
                        "confidence": result["confidence"],
                    }
                )
                self.last_logged_status[tracker] = result["status"]
            self.journal.states[tracker] = memory.checkpoint()
            if fix and memory.last_processed != fix.timestamp:
                self.journal.append(
                    {
                        "type": "detection_evaluation",
                        "tracker": tracker,
                        "report_timestamp": fix.timestamp,
                        "status": result["status"],
                        "confidence": result["confidence"],
                        "match": result.get("match"),
                        "evidence": result.get("evidence", []),
                        "error": result.get("error"),
                    }
                )
                memory.last_processed = fix.timestamp
            if profile["home_arrival_enabled"]:
                home_state = self.hass.states.get(profile["home_zone"])
                home = point(home_state.attributes) if home_state else None
                if (
                    profile.get("home_latitude") is not None
                    and profile.get("home_longitude") is not None
                ):
                    home = (profile["home_latitude"], profile["home_longitude"])
                if home:
                    journey = self.home_journeys.setdefault(tracker, Journey(profile))
                    # Reuse the primary detector's match; the home feature cannot manufacture a different vehicle match.
                    journey.match = (
                        result.get("match") if result["status"] == "on_transit" else None
                    )
                    if journey.match:
                        journey.match_at = now
                    journey.fixes = memory.fixes.copy()
                    try:
                        home_result = await journey.update(
                            self.client,
                            fix,
                            home,
                            state.state
                            == (
                                "home"
                                if profile["home_zone"] == "zone.home"
                                else home_state.name
                                if home_state
                                else ""
                            ),
                            now,
                        )
                        result["home"] = home_result
                    except BkkError as exc:
                        result["home"] = {
                            "status": "unknown",
                            "error": str(exc),
                            "eta_minutes": None,
                        }
            data[tracker] = result
        # Do not keep deleted/excluded trackers or their coordinates in active memory.
        selected = set(data)
        self.trackers = {key: value for key, value in self.trackers.items() if key in selected}
        self.journal.states = {
            key: value for key, value in self.journal.states.items() if key in selected
        }
        return data

    async def start_route(self, tracker, route_id):
        profile = self.profile(tracker)
        if not profile["home_arrival_enabled"]:
            raise ValueError("Enable the optional home arrival estimates profile first")
        journey = self.home_journeys.setdefault(tracker, Journey(profile))
        journey.start(route_id, time.time())
        self.journal.append(
            {"type": "home_route_selected", "tracker": tracker, "route_id": route_id}
        )
        await self.async_request_refresh()

    async def close(self):
        self.budget.limits.pop(self.entry.entry_id, None)
        await self.journal.flush()
