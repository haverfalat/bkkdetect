# BKK Detect — native Home Assistant integration

**BKK vehicle detection is the main feature. Home arrival estimates are optional.**

This installs directly into Home Assistant as `custom_components/bkkdetect`.
It runs inside HA, uses HA's normal integration setup/options screens, and
creates registered entities with unique IDs. No Node.js service, add-on, HA
access token, or separate configuration website is required.

## Install through HACS

1. In **HACS**, open the **⋮ menu → Custom repositories**.
2. Add **`https://github.com/haverfalat/bkkdetect`**, with type **Integration**.
3. Find **BKK Detect** in HACS and download it.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration → BKK Detect**.
6. Enter your BKK API key and choose English or Hungarian.

All device trackers are examined by default. Optional home routes and arrival
estimates can be enabled later using **Configure → Tracker-specific profile**.

## Manual installation

1. Copy **`custom_components/bkkdetect`** into **`/config/custom_components/bkkdetect`**
   on your HA instance, or extract the release ZIP into `/config`.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → BKK Detect**.
4. Enter your BKK API key and choose English or Hungarian.

If you installed the earlier WhenHome build, remove that integration entry before
adding BKK Detect. The renamed HA domain does not automatically migrate old entries.

Requires **Home Assistant 2026.10.0 or newer**. Release ZIPs are available on
the repository's **Releases** page. The integration runs inside HA and does not
need a Home Assistant access token.

## Default behavior

- Automatically discovers **every `device_tracker.*`**, including newly added
  trackers. GPS-capable trackers are evaluated for transit travel. Trackers
  without GPS receive a `no_gps` status; it cannot locate a phone from a router
  presence sensor.
- Collects timestamped BKK vehicle snapshots into a rolling history and captures
  every HA tracker state change, including reports between polling cycles.
- Matches phone reports to vehicle positions **at their report timestamps**,
  interpolating vehicle positions when appropriate. A live vehicle at the same
  coordinates much later is insufficient evidence.
- Requires repeated co-movement, direction agreement, plausible travel speed,
  and proximity/progress along the **actual BKK trip polyline**. Speed alone or
  a single nearby vehicle does not identify a ride. Parallel matching vehicles
  produce an ambiguous result.
- Once a journey is established, waiting motionless at a traffic light or stop
  does not count as alighting. Alighting requires multiple distinct reports
  separated from the time-aligned vehicle. Missing GPS or missing vehicle
  history produces uncertainty, not an invented exit.
- Backfills boarding to the earliest matched location report, and alighting to
  the first report in the confirmed exit sequence. Records estimated time,
  confirmation time, backfilled seconds, uncertainty interval, nearest observed
  stop, vehicle, trip, line, evidence, and journey duration.

The exact instant or stop is not always observable. Estimates are explicitly
marked `exact: false`; a nearby stop is a candidate, not proof. Vehicle history
starts when the integration runs. BKK's live API cannot reconstruct arbitrary
vehicle positions from before collection began. Sparse phone GPS reports may
leave a ride unconfirmed.

## Configure in HA

Open **BKK Detect → Configure**:

| Menu | Settings |
| --- | --- |
| Automatic tracker discovery | Enable/disable, include only selected trackers, exclusions |
| Detection and request limits | Timing alignment, matching segments, route deviation, GPS error, speed/direction bounds, alighting evidence, caches, request budget |
| Evidence journal | GPS/vehicle recording switches, retention, capacity, flush interval |
| BKK connection and language | API key, API URL, English/Hungarian |
| Tracker-specific profile | Name, language, optional source GPS timestamp attribute, display text, optional home arrival estimates and routes |

An empty inclusion list means all `device_tracker.*` entities. You may also
explicitly include `person.*` entities. Configure a GPS timestamp attribute if
your tracker exposes the phone's original measurement time separately from HA's
`last_updated`; it must be Unix seconds/milliseconds or an ISO timestamp with a
timezone.

## Evidence journal and events

The persistent journal is stored in:

```text
/config/.storage/bkkdetect.<config-entry-id>.journal
```

It records tracker discovery, GPS fixes, vehicle snapshots, status/evidence
changes, request-budget waits/errors, boarding, alighting and optional home-route
selection. Default retention is seven days with a maximum of 20,000 records.
Snapshots and active journeys are restored on restart. Raw API keys and HA
tokens are never included in the journal.

Call **`bkkdetect.export_log`** in **Developer tools → Actions** to return recent
records. Optional fields are `tracker` and `limit` (maximum 10,000).

The integration fires **`bkkdetect_boarding`** and **`bkkdetect_alighting`** HA
events. Each includes the source tracker and journey evidence. These can trigger
automations without parsing display text. A journey includes:

```text
id, vehicle_id, trip_id, match.line, match.mode, match.headsign,
boarding.estimated_at, boarding.confirmed_at, boarding.earliest_at,
boarding.latest_at, boarding.backfilled_seconds, boarding.stop,
alighting.estimated_at, alighting.confirmed_at, alighting.backfilled_seconds,
duration_seconds, confidence, match.evidence
```

## Entities and cards

Each tracker gets a **Transit** sensor and **On vehicle** binary sensor. The
Transit sensor attributes contain current evidence and active/last journeys.
When GPS or matching evidence is uncertain, the binary sensor is unknown.
Boarding/alighting timestamp sensors and refresh buttons are available as
disabled-by-default entities; enable them in the entity settings if wanted.

Choose the created Transit sensor in HA's native **Tile** card editor. Your
original tracker stays untouched. Entity IDs are assigned by HA and remain
editable through its entity registry; use the actual IDs shown there.

## Optional home arrival estimates

Home estimation is **off by default**. In a tracker's profile, enable it and
choose a home zone or custom coordinates. Define any number of home routes:

1. Add a route and give it a name and final walking time.
2. Add each leg by searching/selecting a BKK line, boarding platform and
   alighting platform. Add walking/boarding buffers for transfers.
3. Save the route, then **Save profile and finish**.

This creates home-text, ETA, home-route compatibility and route-selector
entities. Predictions, transfer buffers, missed connections, trip direction
and final walking time determine the ETA. Automatically suggested itineraries
remain distinct from observed/selected home journeys.

For an underground first leg, explicitly select the saved route in the route
selector. Established metro journeys with an entry anchor can survive a bounded
GPS gap using the last timetable, labelled as inferred. GPS entry/exit jumps
must have plausible elapsed time. Missing GPS alone does not prove a metro ride.

Text templates support `{name}`, `{status}`, `{eta}`, `{line}`, `{mode}`,
`{headsign}`, `{route}`, `{arrival}`, `{confidence}`, `{next_stop}`,
`{transfers}`, `{vehicle}` and `{tracker}`. They are plain text, not executable
JavaScript/Jinja. All destinations, routes and templates are configured in HA.

An optional detailed **BKK Detect** dashboard card is included in
`custom_components/bkkdetect/www/bkkdetect-card.js`. Copy it to
`/config/www/bkkdetect-card.js`, add `/local/bkkdetect-card.js` as a JavaScript
module dashboard resource, and use it with the optional home-text sensor:

```yaml
type: custom:bkkdetect-card
entity: sensor.your_actual_home_arrival_entity
language: hu
show_details: true
show_confidence: true
```

The integration and native tile cards do not depend on this JavaScript file.

## Request limits

All trackers and UI searches share one sliding-minute BKK budget. Lookups are
cached, duplicate in-flight requests are coalesced, HTTP 429 respects
`Retry-After` and the configured backoff, and idle trackers use a slower lookup
interval. Round-robin processing prevents trackers at the end of the list from
permanently losing the request budget. API failures do not fabricate journeys.

## Development and provenance

```sh
uv sync --group dev
uv run ruff format custom_components scripts
uv run python scripts/package_release.py
```

The native async Python BKK adapter follows the API endpoints and response
models in [haverfalat/bkkfutar.js](https://github.com/haverfalat/bkkfutar.js),
commit `e7effda8a3cee19b03edded2ee5b22df9ad867ca`. Python is used because HA
integrations cannot import a JavaScript npm library. The upstream TypeScript sources are retained under `reference/bkkfutar` as an API reference, not a runtime dependency. The standalone Node app and all project tests have been removed.

Geospatial operations use pinned upstream packages instead of handwritten math:

- **pyproj / PROJ** supplies WGS84 geodesic distance, bearing, interpolation and coordinate transformations. [API documentation](https://pyproj4.github.io/pyproj/stable/api/geod.html).
- **Shapely / GEOS** measures distance from the route and progress along it in a metric projection. [Linear referencing documentation](https://shapely.readthedocs.io/en/stable/manual.html#linear-referencing-methods).
- **polyline** decodes BKK's encoded route shapes. [Package source](https://github.com/frederickjansen/polyline).

Home Assistant installs these dependencies from the integration manifest. The remaining comparisons, timing windows and confirmation rules are integration-specific and configurable in HA. No tests or test dependencies are included.
