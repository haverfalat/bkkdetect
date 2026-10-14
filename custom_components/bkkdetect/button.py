"""Native refresh control."""

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory

from .entity import BkkDetectEntity, setup_dynamic


class RefreshButton(BkkDetectEntity, ButtonEntity):
    _attr_icon = "mdi:refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, tracker):
        super().__init__(coordinator, tracker, "refresh")

    async def async_press(self):
        await self.coordinator.async_request_refresh()


async def async_setup_entry(hass, entry, async_add_entities):
    await setup_dynamic(entry, async_add_entities, lambda c, t: [RefreshButton(c, t)])
