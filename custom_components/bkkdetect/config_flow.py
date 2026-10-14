"""Native HA setup and options: trackers, detection, journal, home profiles and routes."""

from copy import deepcopy
from uuid import uuid4

import probatio as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BkkError, Budget
from .const import BOUNDS, DEFAULTS, DOMAIN, MODES, TEXTS
from .providers import create_client


def text(password=False):
    return selector.TextSelector(
        selector.TextSelectorConfig(
            type=selector.TextSelectorType.PASSWORD if password else selector.TextSelectorType.TEXT
        )
    )


def number(key, minimum=None, maximum=None):
    low, high = BOUNDS.get(key, (minimum, maximum))
    step = 0.01 if key in ("ambiguity_margin", "min_speed", "walking_speed") else 1
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=low, max=high, step=step, mode=selector.NumberSelectorMode.BOX
        )
    )


def choice(items, multiple=False):
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=items, multiple=multiple, mode=selector.SelectSelectorMode.DROPDOWN
        )
    )


def tracker_selector(multiple=False):
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=["device_tracker", "person"], multiple=multiple)
    )


class BkkDetectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        if user_input:
            try:
                options = {**deepcopy(DEFAULTS), **user_input}
                if options["vehicle_provider"] == "bkk" and not options.get("api_key"):
                    raise BkkError("BKK API key required")
                await create_client(
                    async_get_clientsession(self.hass), options, Budget()
                ).metadata()
            except BkkError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="BKK Detect", data=user_input)
        schema = vol.Schema(
            {
                vol.Required("vehicle_provider", default=DEFAULTS["vehicle_provider"]): choice(
                    ["mavplusz", "bkk"]
                ),
                vol.Optional("api_key", default=""): text(True),
                vol.Required("language", default="en"): choice(["en", "hu"]),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BkkDetectOptionsFlow()


class BkkDetectOptionsFlow(config_entries.OptionsFlow):
    def __init__(self):
        self.draft = None
        self.tracker = None
        self.route = None
        self.editing_route = None
        self.editing_leg = None
        self.leg = {}
        self.results = {}

    async def async_step_init(self, user_input=None):
        if self.draft is None:
            self.draft = {
                **deepcopy(DEFAULTS),
                **self.config_entry.data,
                **deepcopy(dict(self.config_entry.options)),
            }
        return self.async_show_menu(
            step_id="init",
            menu_options=["trackers", "detection", "logging", "connections", "profile_select"],
        )

    def save(self):
        return self.async_create_entry(title="", data=self.draft)

    def client(self):
        coordinator = self.hass.data[DOMAIN]["entries"].get(self.config_entry.entry_id)
        budget = coordinator.budget if coordinator else Budget()
        return create_client(async_get_clientsession(self.hass), self.draft, budget)

    async def async_step_trackers(self, user_input=None):
        if user_input is not None:
            self.draft.update(user_input)
            return self.save()
        return self.async_show_form(
            step_id="trackers",
            data_schema=vol.Schema(
                {
                    vol.Required("enabled", default=self.draft["enabled"]): bool,
                    vol.Optional(
                        "include_trackers", default=self.draft["include_trackers"]
                    ): tracker_selector(True),
                    vol.Optional(
                        "exclude_trackers", default=self.draft["exclude_trackers"]
                    ): tracker_selector(True),
                }
            ),
        )

    async def async_step_detection(self, user_input=None):
        errors = {}
        if user_input is not None:
            if user_input["movement_window_seconds"] < user_input["min_match_seconds"]:
                errors["base"] = "invalid_detection_window"
            else:
                self.draft.update(user_input)
                return self.save()
        keys = [
            k
            for k in BOUNDS
            if not k.startswith("log_") and k not in ("max_log_records", "home_radius")
        ]
        schema = {vol.Required(k, default=self.draft[k]): number(k) for k in keys}
        schema[vol.Required("transit_modes", default=self.draft["transit_modes"])] = choice(
            MODES, True
        )
        schema[vol.Required("metro_inference", default=self.draft["metro_inference"])] = bool
        return self.async_show_form(
            step_id="detection", data_schema=vol.Schema(schema), errors=errors
        )

    async def async_step_logging(self, user_input=None):
        if user_input is not None:
            self.draft.update(user_input)
            return self.save()
        schema = {
            vol.Required(k, default=self.draft[k]): bool for k in ("log_positions", "log_vehicles")
        }
        schema.update(
            {
                vol.Required(k, default=self.draft[k]): number(k)
                for k in ("log_retention_days", "max_log_records", "log_flush_seconds")
            }
        )
        return self.async_show_form(step_id="logging", data_schema=vol.Schema(schema))

    async def async_step_connections(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                candidate = {**self.draft, **user_input}
                if candidate["vehicle_provider"] == "bkk" and not candidate.get("api_key"):
                    raise BkkError("BKK API key required")
                await create_client(
                    async_get_clientsession(self.hass), candidate, Budget()
                ).metadata()
            except BkkError:
                errors["base"] = "cannot_connect"
            else:
                self.draft.update(user_input)
                return self.save()
        return self.async_show_form(
            step_id="connections",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "vehicle_provider", default=self.draft["vehicle_provider"]
                    ): choice(
                        [
                            {"value": "mavplusz", "label": "MÁV Plusz"},
                            {"value": "bkk", "label": "BKK FUTÁR"},
                        ]
                    ),
                    vol.Optional("api_key", default=self.draft.get("api_key", "")): text(True),
                    vol.Required("base_url", default=self.draft["base_url"]): text(),
                    vol.Required("mav_base_url", default=self.draft["mav_base_url"]): text(),
                    vol.Required("mav_router", default=self.draft["mav_router"]): text(),
                    vol.Required("language", default=self.draft["language"]): choice(["en", "hu"]),
                }
            ),
            errors=errors,
        )

    async def async_step_profile_select(self, user_input=None):
        if user_input:
            self.tracker = user_input["tracker"]
            self.draft["profiles"].setdefault(
                self.tracker, {"routes": [], "home_arrival_enabled": False}
            )
            return await self.async_step_profile()
        return self.async_show_form(
            step_id="profile_select",
            data_schema=vol.Schema({vol.Required("tracker"): tracker_selector()}),
        )

    def profile(self):
        return self.draft["profiles"][self.tracker]

    async def async_step_profile(self, user_input=None):
        return self.async_show_menu(
            step_id="profile", menu_options=["profile_settings", "texts", "routes", "profile_save"]
        )

    async def async_step_profile_save(self, user_input=None):
        return self.save()

    async def async_step_profile_settings(self, user_input=None):
        errors = {}
        p = self.profile()
        if user_input is not None:
            has_lat = "home_latitude" in user_input
            has_lon = "home_longitude" in user_input
            if has_lat != has_lon:
                errors["base"] = "coordinates_pair"
            else:
                for key in ("home_latitude", "home_longitude"):
                    p.pop(key, None)
                p.update(user_input)
                return await self.async_step_profile()
        state = self.hass.states.get(self.tracker)
        schema = {
            vol.Required(
                "name", default=p.get("name", state.name if state else self.tracker)
            ): text(),
            vol.Required("language", default=p.get("language", self.draft["language"])): choice(
                ["en", "hu"]
            ),
            vol.Required(
                "home_arrival_enabled", default=p.get("home_arrival_enabled", False)
            ): bool,
            vol.Required(
                "home_zone", default=p.get("home_zone", "zone.home")
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="zone")),
            vol.Required(
                "home_radius", default=p.get("home_radius", self.draft["home_radius"])
            ): number("home_radius"),
            vol.Required(
                "gps_timestamp_attribute", default=p.get("gps_timestamp_attribute", "")
            ): text(),
        }
        for key, low, high in (("home_latitude", -90, 90), ("home_longitude", -180, 180)):
            marker = vol.Optional(key, default=p[key]) if key in p else vol.Optional(key)
            schema[marker] = number(key, low, high)
        return self.async_show_form(
            step_id="profile_settings", data_schema=vol.Schema(schema), errors=errors
        )

    async def async_step_texts(self, user_input=None):
        p = self.profile()
        if user_input is not None:
            p.update(user_input)
            return await self.async_step_profile()
        defaults = TEXTS[p.get("language", self.draft["language"])]
        fields = {
            vol.Required(
                "transit_text", default=p.get("transit_text", "{name} · {line} · {headsign}")
            ): text()
        }
        fields.update(
            {
                vol.Required("text_" + key, default=p.get("text_" + key, value)): text()
                for key, value in defaults.items()
            }
        )
        fields[
            vol.Required("transit_idle_text", default=p.get("transit_idle_text", "{status}"))
        ] = text()
        return self.async_show_form(step_id="texts", data_schema=vol.Schema(fields))

    async def async_step_routes(self, user_input=None):
        return self.async_show_menu(
            step_id="routes", menu_options=["route_new", "route_edit", "profile"]
        )

    async def async_step_route_new(self, user_input=None):
        self.route = {
            "id": uuid4().hex,
            "name": "",
            "enabled": True,
            "final_walk_minutes": 5,
            "legs": [],
        }
        self.editing_route = None
        return await self.async_step_route_settings()

    async def async_step_route_edit(self, user_input=None):
        routes = self.profile()["routes"]
        if not routes:
            return self.async_show_form(
                step_id="route_edit", errors={"base": "no_routes"}, data_schema=vol.Schema({})
            )
        if user_input:
            self.editing_route = user_input["route_id"]
            self.route = deepcopy(next(r for r in routes if r["id"] == self.editing_route))
            return await self.async_step_route_menu()
        return self.async_show_form(
            step_id="route_edit",
            data_schema=vol.Schema(
                {
                    vol.Required("route_id"): choice(
                        [{"value": r["id"], "label": r["name"]} for r in routes]
                    )
                }
            ),
        )

    async def async_step_route_settings(self, user_input=None):
        if user_input is not None:
            self.route.update(user_input)
            return await self.async_step_route_menu()
        return self.async_show_form(
            step_id="route_settings",
            data_schema=vol.Schema(
                {
                    vol.Required("name", default=self.route["name"]): text(),
                    vol.Required("enabled", default=self.route["enabled"]): bool,
                    vol.Required(
                        "final_walk_minutes", default=self.route["final_walk_minutes"]
                    ): number("final_walk_minutes", 0, 120),
                }
            ),
        )

    async def async_step_route_menu(self, user_input=None):
        summary = " → ".join(
            f"{l['line']}: {l['from']['name']} → {l['to']['name']}" for l in self.route["legs"]
        )
        return self.async_show_menu(
            step_id="route_menu",
            menu_options=[
                "route_settings",
                "leg_add",
                "leg_edit",
                "leg_move",
                "leg_remove",
                "route_save",
                "route_delete",
                "routes",
            ],
            description_placeholders={"route": self.route["name"], "legs": summary or "—"},
        )

    async def async_step_leg_add(self, user_input=None):
        self.editing_leg = None
        return await self.async_step_leg_search()

    async def async_step_leg_edit(self, user_input=None):
        if not self.route["legs"]:
            return await self.async_step_route_menu()
        if user_input:
            self.editing_leg = int(user_input["leg_index"])
            return await self.async_step_leg_search()
        return self.async_show_form(
            step_id="leg_edit",
            data_schema=vol.Schema(
                {
                    vol.Required("leg_index"): choice(
                        [
                            {
                                "value": str(i),
                                "label": f"{i + 1}. {l['line']}: {l['from']['name']} → {l['to']['name']}",
                            }
                            for i, l in enumerate(self.route["legs"])
                        ]
                    )
                }
            ),
        )

    async def async_step_leg_move(self, user_input=None):
        if not self.route["legs"]:
            return await self.async_step_route_menu()
        if user_input:
            item = self.route["legs"].pop(int(user_input["leg_index"]))
            self.route["legs"].insert(int(user_input["position"]) - 1, item)
            return await self.async_step_route_menu()
        return self.async_show_form(
            step_id="leg_move",
            data_schema=vol.Schema(
                {
                    vol.Required("leg_index"): choice(
                        [
                            {
                                "value": str(i),
                                "label": f"{i + 1}. {l['line']}: {l['from']['name']} → {l['to']['name']}",
                            }
                            for i, l in enumerate(self.route["legs"])
                        ]
                    ),
                    vol.Required("position", default=1): number(
                        "position", 1, len(self.route["legs"])
                    ),
                }
            ),
        )

    async def async_step_leg_search(self, user_input=None):
        errors = {}
        if user_input:
            try:
                data = await self.client().search(user_input["query"])
                self.results = data.get("references", {}).get("routes", {})
            except BkkError:
                errors["base"] = "cannot_connect"
            else:
                if self.results:
                    self.leg = {"transfer_minutes": user_input["transfer_minutes"]}
                    return await self.async_step_leg_line()
                errors["base"] = "no_results"
        return self.async_show_form(
            step_id="leg_search",
            data_schema=vol.Schema(
                {
                    vol.Required("query"): text(),
                    vol.Required("transfer_minutes", default=3): number("transfer_minutes", 0, 90),
                }
            ),
            errors=errors,
        )

    async def async_step_leg_line(self, user_input=None):
        if user_input:
            route = self.results[user_input["route_id"]]
            self.leg.update(
                route_id=route["id"], line=route.get("shortName", route["id"]), mode=route["type"]
            )
            return await self.async_step_leg_from_search()
        return self.async_show_form(
            step_id="leg_line",
            data_schema=vol.Schema(
                {
                    vol.Required("route_id"): choice(
                        [
                            {
                                "value": r["id"],
                                "label": f"{r.get('shortName', r['id'])} · {r.get('description', r.get('longName', ''))}",
                            }
                            for r in self.results.values()
                            if r.get("type") in MODES
                        ]
                    )
                }
            ),
        )

    async def stop_search(self, step, user_input, following):
        errors = {}
        if user_input:
            try:
                data = await self.client().search(user_input["query"])
                self.results = {
                    key: stop
                    for key, stop in data.get("references", {}).get("stops", {}).items()
                    if self.leg["route_id"] in stop.get("routeIds", [])
                }
            except BkkError:
                errors["base"] = "cannot_connect"
            else:
                if self.results:
                    return await following()
                errors["base"] = "no_results"
        return self.async_show_form(
            step_id=step, data_schema=vol.Schema({vol.Required("query"): text()}), errors=errors
        )

    async def async_step_leg_from_search(self, user_input=None):
        return await self.stop_search("leg_from_search", user_input, self.async_step_leg_from)

    async def async_step_leg_to_search(self, user_input=None):
        return await self.stop_search("leg_to_search", user_input, self.async_step_leg_to)

    def stop_form(self, step):
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema(
                {
                    vol.Required("stop_id"): choice(
                        [
                            {
                                "value": s["id"],
                                "label": f"{s['name']} · {s.get('direction', '')} · {s['id']}",
                            }
                            for s in self.results.values()
                        ]
                    )
                }
            ),
        )

    def selected_stop(self, user_input):
        s = self.results[user_input["stop_id"]]
        return {key: s[key] for key in ("id", "name", "lat", "lon")}

    async def async_step_leg_from(self, user_input=None):
        if user_input:
            self.leg["from"] = self.selected_stop(user_input)
            return await self.async_step_leg_to_search()
        return self.stop_form("leg_from")

    async def async_step_leg_to(self, user_input=None):
        if user_input:
            stop = self.selected_stop(user_input)
            if stop["id"] == self.leg["from"]["id"]:
                return self.async_show_form(
                    step_id="leg_to",
                    data_schema=self.stop_form("leg_to")["data_schema"],
                    errors={"base": "same_stop"},
                )
            self.leg["to"] = stop
            if self.editing_leg is None:
                self.route["legs"].append(deepcopy(self.leg))
            else:
                self.route["legs"][self.editing_leg] = deepcopy(self.leg)
                self.editing_leg = None
            return await self.async_step_route_menu()
        return self.stop_form("leg_to")

    async def async_step_leg_remove(self, user_input=None):
        if user_input:
            self.route["legs"].pop(int(user_input["leg_index"]))
            return await self.async_step_route_menu()
        if not self.route["legs"]:
            return await self.async_step_route_menu()
        return self.async_show_form(
            step_id="leg_remove",
            data_schema=vol.Schema(
                {
                    vol.Required("leg_index"): choice(
                        [
                            {
                                "value": str(i),
                                "label": f"{i + 1}. {l['line']}: {l['from']['name']} → {l['to']['name']}",
                            }
                            for i, l in enumerate(self.route["legs"])
                        ]
                    )
                }
            ),
        )

    async def async_step_route_save(self, user_input=None):
        routes = self.profile()["routes"]
        if (
            not self.route["legs"]
            or not self.route["name"].strip()
            or any(r["name"] == self.route["name"] and r["id"] != self.route["id"] for r in routes)
        ):
            return self.async_show_form(
                step_id="route_save", errors={"base": "invalid_route"}, data_schema=vol.Schema({})
            )
        self.profile()["routes"] = [r for r in routes if r["id"] != self.route["id"]] + [
            deepcopy(self.route)
        ]
        return await self.async_step_profile()

    async def async_step_route_delete(self, user_input=None):
        if user_input is not None:
            if user_input["confirm"]:
                self.profile()["routes"] = [
                    r for r in self.profile()["routes"] if r["id"] != self.route["id"]
                ]
            return await self.async_step_profile()
        return self.async_show_form(
            step_id="route_delete",
            data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
        )
