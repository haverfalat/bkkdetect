"""BkkDetect native integration: autonomous transit discovery, optional arrival estimates."""

from __future__ import annotations

import probatio as vol
from homeassistant.const import EVENT_STATE_CHANGED, Platform
from homeassistant.core import SupportsResponse, callback

from .const import DOMAIN
from .coordinator import BkkDetectCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SELECT, Platform.BUTTON]


async def async_setup_entry(hass, entry):
    coordinator = BkkDetectCoordinator(hass, entry)
    await coordinator.initialize()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    hass.data[DOMAIN]["entries"][entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    @callback
    def tracker_changed(event):
        state = event.data.get("new_state")
        if state and coordinator.selected(state):
            coordinator.ingest(state)
            hass.async_create_task(coordinator.async_request_refresh())

    entry.async_on_unload(hass.bus.async_listen(EVENT_STATE_CHANGED, tracker_changed))
    if not hass.services.has_service(DOMAIN, "export_log"):

        async def export_log(call):
            target = call.data.get("tracker")
            limit = call.data.get("limit", 1000)
            events = []
            for current in hass.data[DOMAIN]["entries"].values():
                events.extend(current.journal.export(target, limit)["events"])
            return {"events": sorted(events, key=lambda e: e["recorded_epoch"])[-limit:]}

        hass.services.async_register(
            DOMAIN,
            "export_log",
            export_log,
            schema=vol.Schema(
                {
                    vol.Optional("tracker"): str,
                    vol.Optional("limit", default=1000): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=10000)
                    ),
                }
            ),
            supports_response=SupportsResponse.ONLY,
        )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_update_options(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    await entry.runtime_data.close()
    hass.data[DOMAIN]["entries"].pop(entry.entry_id, None)
    if not hass.data[DOMAIN]["entries"]:
        hass.services.async_remove(DOMAIN, "export_log")
    return True
