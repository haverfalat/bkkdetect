"""Proper registered HA sensors with optional home entities."""

import re
from copy import deepcopy
from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity

from .entity import BkkDetectEntity, setup_dynamic


class TransitSensor(BkkDetectEntity, SensorEntity):
    _attr_icon = "mdi:bus-clock"

    def __init__(self, coordinator, tracker):
        super().__init__(coordinator, tracker, "transit")

    @property
    def native_value(self):
        r = self.record
        o = self.coordinator.profile(self.tracker)
        match = r.get("match") or {}
        hu = o["language"] == "hu"
        labels = {
            "not_on_transit": "Nincs járművön" if hu else "Not on transit",
            "on_transit": "Járművön" if hu else "On transit",
            "uncertain": "Bizonytalan" if hu else "Uncertain",
            "ambiguous": "Több lehetséges jármű" if hu else "Multiple possible vehicles",
            "no_gps": "Nincs GPS" if hu else "No GPS",
            "stale": "Elavult GPS" if hu else "Stale GPS",
            "paused": "Szünetel" if hu else "Paused",
        }
        values = {
            **match,
            **r,
            "name": o["name"],
            "status": labels.get(r.get("status"), "—"),
            "line": match.get("line"),
            "headsign": match.get("headsign"),
            "mode": match.get("mode"),
            "confidence": round(r.get("confidence", 0) * 100),
            "vehicle": match.get("vehicle_id"),
        }
        return re.sub(
            r"\{([a-zA-Z_]+)\}",
            lambda m: str(values.get(m[1]) if values.get(m[1]) is not None else "—"),
            o.get("transit_text", "{name} · {line} · {headsign}")
            if r.get("status") == "on_transit"
            else o.get("transit_idle_text", "{status}"),
        )[:255]


class HomeSensor(BkkDetectEntity, SensorEntity):
    _attr_icon = "mdi:home-clock"

    def __init__(self, coordinator, tracker, eta=False):
        super().__init__(coordinator, tracker, "eta" if eta else "home_arrival")
        self.eta = eta
        if eta:
            self._attr_native_unit_of_measurement = "min"
            self._attr_device_class = SensorDeviceClass.DURATION

    @property
    def native_value(self):
        data = self.record.get("home", {})
        return data.get("eta_minutes") if self.eta else data.get("text")

    @property
    def extra_state_attributes(self):
        return deepcopy(self.record.get("home", {}))


class JourneyTimeSensor(BkkDetectEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, tracker, kind):
        super().__init__(coordinator, tracker, kind)
        self.kind = kind

    @property
    def native_value(self):
        event = self.record.get(self.kind) or (self.record.get("last_journey") or {}).get(self.kind)
        return datetime.fromisoformat(event["estimated_at"]) if event else None


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, tracker):
        sensors = [
            TransitSensor(coordinator, tracker),
            JourneyTimeSensor(coordinator, tracker, "boarding"),
            JourneyTimeSensor(coordinator, tracker, "alighting"),
        ]
        if coordinator.profile(tracker)["home_arrival_enabled"]:
            sensors.extend(
                [HomeSensor(coordinator, tracker), HomeSensor(coordinator, tracker, True)]
            )
        return sensors

    await setup_dynamic(entry, async_add_entities, factory)
