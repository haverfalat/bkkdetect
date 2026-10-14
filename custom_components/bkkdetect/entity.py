"""Entity identity and dynamic tracker discovery shared by platforms."""

from copy import deepcopy

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class BkkDetectEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, tracker, key):
        super().__init__(coordinator)
        self.tracker = tracker
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{tracker}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{coordinator.entry.entry_id}_{tracker}")},
            "name": f"{coordinator.profile(tracker)['name']} · BKK",
            "manufacturer": "BKK Detect",
            "model": "Transit tracker",
        }

    @property
    def record(self):
        return self.coordinator.data.get(self.tracker, {}) if self.coordinator.data else {}

    @property
    def available(self):
        return super().available and self.tracker in (self.coordinator.data or {})

    @property
    def extra_state_attributes(self):
        return deepcopy(self.record)


async def setup_dynamic(entry, async_add_entities, factory):
    coordinator = entry.runtime_data
    known = set()

    @callback
    def discover():
        added = []
        for tracker in coordinator.data or {}:
            if tracker not in known:
                known.add(tracker)
                added.extend(factory(coordinator, tracker))
        if added:
            async_add_entities(added)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))
