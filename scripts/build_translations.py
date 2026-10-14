"""Build the HA flow translation resources from explicit English/Hungarian labels."""

import json
from pathlib import Path

from custom_components.bkkdetect.const import BOUNDS

FIELDS = {
    "api_key": ("BKK API key", "BKK API-kulcs"),
    "base_url": ("BKK API base URL", "BKK API alap URL"),
    "language": ("Language", "Nyelv"),
    "enabled": ("Enable transit detection", "Járműfelismerés engedélyezése"),
    "include_trackers": (
        "Only these trackers (empty: all device trackers)",
        "Csak ezek a nyomkövetők (üresen: minden eszköz)",
    ),
    "exclude_trackers": ("Excluded trackers", "Kizárt nyomkövetők"),
    "tracker": ("Tracker", "Nyomkövető"),
    "name": ("Display name", "Megjelenített név"),
    "home_arrival_enabled": (
        "Enable optional home arrival estimation",
        "Opcionális hazaérkezés-becslés engedélyezése",
    ),
    "home_zone": ("Destination zone", "Célzóna"),
    "home_radius": ("Home radius (metres)", "Otthon sugara (méter)"),
    "home_latitude": ("Destination latitude (optional)", "Cél szélessége (opcionális)"),
    "home_longitude": ("Destination longitude (optional)", "Cél hosszúsága (opcionális)"),
    "gps_timestamp_attribute": (
        "GPS timestamp attribute (empty: HA report time)",
        "GPS-időbélyeg attribútuma (üresen: HA-jelentés ideje)",
    ),
    "poll_seconds": ("Polling interval (seconds)", "Lekérdezési időköz (másodperc)"),
    "requests_per_minute": (
        "Shared BKK request budget per minute",
        "Közös BKK-kéréskeret percenként",
    ),
    "request_timeout": ("API timeout (seconds)", "API-időkorlát (másodperc)"),
    "vehicle_cache_seconds": ("Vehicle cache (seconds)", "Járműgyorsítótár (másodperc)"),
    "plan_cache_seconds": ("Plan cache (seconds)", "Útvonalgyorsítótár (másodperc)"),
    "backoff_seconds": ("Rate-limit backoff (seconds)", "Várakozás korlátozás után (másodperc)"),
    "vehicle_radius": ("Vehicle search radius (metres)", "Járműkeresési sugár (méter)"),
    "match_distance": ("Vehicle match distance (metres)", "Járműegyezési távolság (méter)"),
    "max_gps_accuracy": ("Maximum GPS error (metres)", "Legnagyobb GPS-hiba (méter)"),
    "max_vehicle_age": (
        "Maximum vehicle report age (seconds)",
        "Járműjelentés legnagyobb kora (másodperc)",
    ),
    "gps_stale_seconds": (
        "GPS becomes stale after (seconds)",
        "GPS elavul ennyi idő után (másodperc)",
    ),
    "history_minutes": ("Matching history window (minutes)", "Egyeztetési előzmény (perc)"),
    "match_samples": ("Required matching motion segments", "Szükséges egyező mozgásszakaszok"),
    "min_speed": ("Minimum transit speed (m/s)", "Legkisebb járműsebesség (m/mp)"),
    "min_travel": ("Minimum matched travel (metres)", "Legkisebb egyező elmozdulás (méter)"),
    "max_speed": ("Maximum plausible speed (m/s)", "Legnagyobb reális sebesség (m/mp)"),
    "max_bearing_difference": (
        "Maximum heading difference (degrees)",
        "Legnagyobb irányeltérés (fok)",
    ),
    "ambiguity_margin": (
        "Ambiguous vehicle confidence margin",
        "Bizonytalan járművek megbízhatósági különbsége",
    ),
    "match_hold_seconds": (
        "Keep recent transit evidence (seconds)",
        "Friss járműészlelés megőrzése (másodperc)",
    ),
    "metro_inference": ("Allow labelled metro inference", "Jelölt metróbecslés engedélyezése"),
    "metro_grace_minutes": (
        "Metro GPS-gap grace (minutes)",
        "Metró GPS-kimaradási türelmi ideje (perc)",
    ),
    "station_radius": ("Station proximity (metres)", "Megálló-közelség (méter)"),
    "walking_speed": ("Walking speed (m/s)", "Gyaloglási sebesség (m/mp)"),
    "route_expiry_minutes": ("Home journey expiry (minutes)", "Hazaút lejárata (perc)"),
    "timetable_window_minutes": (
        "Departure search window (minutes)",
        "Indulási keresési időablak (perc)",
    ),
    "timetable_candidates": ("Departure candidates per leg", "Indulási jelöltek szakaszonként"),
    "planner_itineraries": ("Suggested itinerary alternatives", "Javasolt útvonal-alternatívák"),
    "transit_modes": ("Allowed vehicle types", "Engedélyezett járműtípusok"),
    "idle_poll_seconds": (
        "Stationary tracker lookup interval (seconds)",
        "Álló nyomkövető lekérdezési időköze (másodperc)",
    ),
    "max_time_skew": (
        "Maximum phone/vehicle time mismatch (seconds)",
        "Telefon–jármű legnagyobb időeltérése (másodperc)",
    ),
    "route_deviation": (
        "Maximum deviation from route shape (metres)",
        "Legnagyobb eltérés az útvonal alakjától (méter)",
    ),
    "exit_samples": (
        "Distinct outside reports to confirm alighting",
        "Leszálláshoz szükséges különálló jelentések",
    ),
    "exit_distance": (
        "Alighting separation distance (metres)",
        "Leszállási távolságküszöb (méter)",
    ),
    "log_positions": ("Record tracker location reports", "Nyomkövető-helyjelentések naplózása"),
    "log_vehicles": ("Record BKK vehicle snapshots", "BKK-járműpillanatképek naplózása"),
    "log_retention_days": ("Journal retention (days)", "Naplómegőrzés (nap)"),
    "max_log_records": ("Maximum retained log records", "Megőrzött naplóbejegyzések maximuma"),
    "log_flush_seconds": (
        "Journal flush delay (seconds)",
        "Napló mentési késleltetése (másodperc)",
    ),
    "query": ("BKK search text", "BKK-keresőszöveg"),
    "route_id": ("Route", "Útvonal"),
    "stop_id": ("Stop and direction", "Megálló és irány"),
    "leg_index": ("Leg to remove", "Törlendő szakasz"),
    "transfer_minutes": (
        "Walking and boarding buffer before this leg (minutes)",
        "Séta és felszállási tartalék e szakasz előtt (perc)",
    ),
    "final_walk_minutes": ("Final walk home (minutes)", "Utolsó séta haza (perc)"),
    "confirm": ("Confirm deletion", "Törlés megerősítése"),
    "transit_text": ("Text while on a vehicle", "Szöveg járművön"),
    "text_home": ("Home text", "Otthoni szöveg"),
    "text_away": ("Away text", "Távolléti szöveg"),
    "text_journey": ("Home journey text", "Hazaúti szöveg"),
    "text_inferred": ("Inferred metro text", "Becsült metró szövege"),
    "text_unknown": ("Uncertain location text", "Bizonytalan helyzet szövege"),
}
STEPS = {
    "user": ("BKK transit detection", "BKK-járműfelismerés"),
    "init": ("Configure BKK Detect", "BKK Detect beállítása"),
    "trackers": ("Automatic tracker discovery", "Automatikus nyomkövető-felderítés"),
    "detection": ("Detection and request limits", "Felismerés és kéréskorlátok"),
    "logging": ("Evidence journal", "Észlelési napló"),
    "connections": ("BKK connection and language", "BKK-kapcsolat és nyelv"),
    "profile_select": (
        "Tracker-specific profile / optional home arrival estimates",
        "Nyomkövető-profil / opcionális hazaérkezés-becslés",
    ),
    "profile": ("Tracker profile", "Nyomkövető-profil"),
    "profile_settings": (
        "Name, GPS source and optional destination",
        "Név, GPS-forrás és opcionális cél",
    ),
    "texts": ("Text templates", "Szövegsablonok"),
    "routes": ("Home routes", "Hazaútvonalak"),
    "profile_save": ("Save profile and finish", "Profil mentése és befejezés"),
    "route_new": ("Add a home route", "Hazaútvonal hozzáadása"),
    "route_edit": ("Edit an existing route", "Meglévő útvonal szerkesztése"),
    "route_settings": ("Route settings", "Útvonal beállításai"),
    "route_menu": ("Route: {route}", "Útvonal: {route}"),
    "leg_search": ("Add a leg: search a line", "Szakasz hozzáadása: járatkeresés"),
    "leg_line": ("Select the BKK line", "BKK-járat kiválasztása"),
    "leg_from_search": ("Search boarding stop", "Felszállóhely keresése"),
    "leg_from": ("Select boarding platform", "Felszállóhely és irány kiválasztása"),
    "leg_to_search": ("Search alighting stop", "Leszállóhely keresése"),
    "leg_to": ("Select alighting platform", "Leszállóhely és irány kiválasztása"),
    "leg_remove": ("Remove a leg", "Szakasz törlése"),
    "route_save": ("Save this route", "Útvonal mentése"),
    "route_delete": ("Delete this route", "Útvonal törlése"),
}
ERRORS = {
    "cannot_connect": (
        "Could not reach BKK; check the key or wait if rate limited.",
        "A BKK nem elérhető; ellenőrizd a kulcsot, vagy várj korlátozás esetén.",
    ),
    "no_routes": ("Add a route first.", "Előbb adj hozzá útvonalat."),
    "no_results": (
        "No matching BKK results. Try another query or platform.",
        "Nincs megfelelő BKK-találat. Próbálj más keresést vagy irányt.",
    ),
    "same_stop": (
        "Boarding and alighting stops must differ.",
        "A fel- és leszállóhelynek különböznie kell.",
    ),
    "invalid_route": (
        "Enter a unique route name and add at least one leg.",
        "Adj egyedi útvonalnevet és legalább egy szakaszt.",
    ),
    "coordinates_pair": (
        "Provide both coordinates or leave both empty.",
        "Add meg mindkét koordinátát, vagy hagyd mindkettőt üresen.",
    ),
}
base = Path(__file__).resolve().parents[1] / "custom_components/bkkdetect"
FIELDS.update(
    {
        "active_vehicle_batch_size": (
            "Identified vehicles per request",
            "Azonosított járművek kérésenként",
        ),
        "active_uncertainty_minutes": (
            "Continue vehicle lookup through GPS loss (minutes)",
            "Járműkövetés GPS-kimaradáskor (perc)",
        ),
    }
)
FORM_FIELDS = {
    "user": ["api_key", "language"],
    "trackers": ["enabled", "include_trackers", "exclude_trackers"],
    "detection": [
        k
        for k in BOUNDS
        if not k.startswith("log_") and k not in ("max_log_records", "home_radius")
    ]
    + ["transit_modes", "metro_inference"],
    "logging": [
        "log_positions",
        "log_vehicles",
        "log_retention_days",
        "max_log_records",
        "log_flush_seconds",
    ],
    "connections": ["api_key", "base_url", "language"],
    "profile_select": ["tracker"],
    "profile_settings": [
        "name",
        "language",
        "home_arrival_enabled",
        "home_zone",
        "home_radius",
        "gps_timestamp_attribute",
        "home_latitude",
        "home_longitude",
    ],
    "texts": [
        "transit_text",
        "text_home",
        "text_away",
        "text_journey",
        "text_inferred",
        "text_unknown",
    ],
    "route_edit": ["route_id"],
    "route_settings": ["name", "enabled", "final_walk_minutes"],
    "leg_search": ["query", "transfer_minutes"],
    "leg_line": ["route_id"],
    "leg_from_search": ["query"],
    "leg_from": ["stop_id"],
    "leg_to_search": ["query"],
    "leg_to": ["stop_id"],
    "leg_remove": ["leg_index"],
    "route_delete": ["confirm"],
}
MENUS = {
    "init": ["trackers", "detection", "logging", "connections", "profile_select"],
    "profile": ["profile_settings", "texts", "routes", "profile_save"],
    "routes": ["route_new", "route_edit", "profile"],
    "route_menu": [
        "route_settings",
        "leg_search",
        "leg_remove",
        "route_save",
        "route_delete",
        "routes",
    ],
}
FIELDS["position"] = ("New position in route", "Új hely a szakaszsorrendben")
FIELDS["transit_idle_text"] = (
    "Text when not confirmed on a vehicle",
    "Szöveg bizonyított járműegyezés nélkül",
)
FORM_FIELDS["texts"].append("transit_idle_text")
STEPS.update(
    {
        "leg_add": ("Add a leg / transfer", "Szakasz / átszállás hozzáadása"),
        "leg_edit": ("Edit a leg", "Szakasz szerkesztése"),
        "leg_move": ("Reorder legs", "Szakaszok átrendezése"),
    }
)
FORM_FIELDS.update({"leg_edit": ["leg_index"], "leg_move": ["leg_index", "position"]})
MENUS["route_menu"] = [
    "route_settings",
    "leg_add",
    "leg_edit",
    "leg_move",
    "leg_remove",
    "route_save",
    "route_delete",
    "routes",
]
for index, language in enumerate(("en", "hu")):
    fields = {key: value[index] for key, value in FIELDS.items()}
    steps = {key: {"title": value[index]} for key, value in STEPS.items()}
    for step, keys in FORM_FIELDS.items():
        steps[step]["data"] = {key: fields[key] for key in keys}
    steps["user"]["description"] = (
        "Automatically examines all device trackers. Transit identification is the main feature; home arrival estimation is optional. Trackers without GPS are marked No GPS."
        if index == 0
        else "Alapból minden eszköznyomkövetőt vizsgál. A fő funkció a járműfelismerés; a hazaérkezés-becslés opcionális. GPS nélkül Nincs GPS állapotot jelez."
    )
    steps["route_menu"]["description"] = "{legs}"
    steps["texts"]["description"] = (
        "{name}, {status}, {eta}, {line}, {mode}, {headsign}, {route}, {arrival}, {confidence}, {next_stop}, {transfers}, {vehicle}, {tracker}".replace(
            "{", "`{"
        ).replace("}", "}`")
    )
    # Literal template variables must not be interpreted as translation placeholders.
    steps["texts"]["description"] = (
        "Variables: name, status, eta, line, mode, headsign, route, arrival, confidence, next_stop, transfers, vehicle, tracker. Enclose variable names in braces."
        if index == 0
        else "Változók: name, status, eta, line, mode, headsign, route, arrival, confidence, next_stop, transfers, vehicle, tracker. A változóneveket kapcsos zárójelek közé írd."
    )
    menu = {key: value[index] for key, value in STEPS.items()}
    for step, options in MENUS.items():
        steps[step]["menu_options"] = {key: menu[key] for key in options}
    errors = {key: value[index] for key, value in ERRORS.items()}
    resources = {
        "title": "BKK Detect",
        "config": {
            "step": {"user": steps["user"]},
            "error": errors,
            "abort": {
                "already_configured": "Already configured" if index == 0 else "Már beállítva"
            },
        },
        "options": {"step": steps, "error": errors},
        "entity": {
            "sensor": {
                "transit": {"name": "Transit" if index == 0 else "Jármű"},
                "home_arrival": {"name": "Home arrival" if index == 0 else "Hazaérkezés"},
                "eta": {"name": "Arrival estimate" if index == 0 else "Hazaérkezés-becslés"},
                "boarding": {"name": "Boarding time" if index == 0 else "Felszállás ideje"},
                "alighting": {"name": "Alighting time" if index == 0 else "Leszállás ideje"},
            },
            "binary_sensor": {
                "on_vehicle": {"name": "On vehicle" if index == 0 else "Járművön"},
                "home_route": {"name": "Home route" if index == 0 else "Hazaútvonal"},
            },
            "select": {
                "active_home_route": {
                    "name": "Active home route" if index == 0 else "Aktív hazaútvonal"
                }
            },
            "button": {"refresh": {"name": "Refresh" if index == 0 else "Frissítés"}},
        },
    }
    (base / "translations" / f"{language}.json").write_text(
        json.dumps(resources, ensure_ascii=False, indent=2) + "\n"
    )
    if language == "en":
        (base / "strings.json").write_text(
            json.dumps(resources, ensure_ascii=False, indent=2) + "\n"
        )
