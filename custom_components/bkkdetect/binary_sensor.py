"""Vehicle presence and optional home-route compatibility."""

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import BkkDetectEntity, setup_dynamic


class OnVehicleSensor(BkkDetectEntity, BinarySensorEntity):
    _attr_icon = "mdi:bus"

    def __init__(self, coordinator, tracker):
        super().__init__(coordinator, tracker, "on_vehicle")

    @property
    def is_on(self):
        status = self.record.get("status")
        return (
            None
            if status in ("no_gps", "stale", "uncertain", "ambiguous", "paused")
            else status == "on_transit"
        )


class HomeRouteSensor(BkkDetectEntity, BinarySensorEntity):
    _attr_icon = "mdi:home-import-outline"

    def __init__(self, coordinator, tracker):
        super().__init__(coordinator, tracker, "home_route")

    @property
    def is_on(self):
        return self.record.get("home", {}).get("home_route", False)


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(coordinator, tracker):
        result = [OnVehicleSensor(coordinator, tracker)]
        if coordinator.profile(tracker)["home_arrival_enabled"]:
            result.append(HomeRouteSensor(coordinator, tracker))
        return result

    await setup_dynamic(entry, async_add_entities, factory)
