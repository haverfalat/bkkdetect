"""Native HA selector for optionally starting / ending a configured home route."""

from homeassistant.components.select import SelectEntity

from .entity import BkkDetectEntity, setup_dynamic


class HomeRouteSelect(BkkDetectEntity, SelectEntity):
    _attr_icon = "mdi:routes"

    def __init__(self, coordinator, tracker):
        super().__init__(coordinator, tracker, "active_home_route")
        self.routes = [r for r in coordinator.profile(tracker)["routes"] if r.get("enabled", True)]
        self.automatic = (
            "Automatikus" if coordinator.profile(tracker)["language"] == "hu" else "Automatic"
        )
        self._attr_options = [self.automatic, *[r["name"] for r in self.routes]]

    @property
    def current_option(self):
        journey = self.coordinator.home_journeys.get(self.tracker)
        return next(
            (r["name"] for r in self.routes if journey and r["id"] == journey.active_route),
            self.automatic,
        )

    async def async_select_option(self, option):
        route = next((r for r in self.routes if r["name"] == option), None)
        await self.coordinator.start_route(self.tracker, route["id"] if route else None)


async def async_setup_entry(hass, entry, async_add_entities):
    await setup_dynamic(
        entry,
        async_add_entities,
        lambda coordinator, tracker: (
            [HomeRouteSelect(coordinator, tracker)]
            if coordinator.profile(tracker)["home_arrival_enabled"]
            else []
        ),
    )
