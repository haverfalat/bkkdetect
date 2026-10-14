"""Bounded persistent evidence journal stored in Home Assistant's .storage."""

import time
from copy import deepcopy

from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .planner import iso


class Journal:
    def __init__(self, hass, entry_id, options):
        self.store = Store(hass, 1, f"{DOMAIN}.{entry_id}.journal", private=True)
        self.options = options
        self.events = []
        self.states = {}

    async def load(self):
        data = await self.store.async_load() or {}
        self.events = data.get("events", [])
        self.states = data.get("states", {})
        self.prune()

    def prune(self):
        cutoff = time.time() - self.options["log_retention_days"] * 86400
        self.events = [e for e in self.events if e.get("recorded_epoch", 0) > cutoff][
            -int(self.options["max_log_records"]) :
        ]

    def append(self, event):
        self.events.append(
            {**deepcopy(event), "recorded_at": iso(time.time()), "recorded_epoch": time.time()}
        )
        self.prune()
        self.store.async_delay_save(self.snapshot, self.options["log_flush_seconds"])

    def snapshot(self):
        return {"events": self.events, "states": self.states}

    async def flush(self):
        await self.store.async_save(self.snapshot())

    def export(self, tracker=None, limit=1000):
        self.prune()
        selected = [e for e in self.events if tracker is None or e.get("tracker") == tracker]
        return {
            "events": selected[-limit:],
            "total": len(selected),
            "retention_days": self.options["log_retention_days"],
        }
