# BKK Detect interactive simulator

Run from the repository root:

```sh
uv run --group dev python -m tools.simulator.server --host 0.0.0.0
```

Open the URL printed by the server. On a phone, use the phone URL on the same
Wi-Fi. The ephemeral URL token grants access only to this local simulator.
HA credentials and optional BKK keys stay on the server; `.env` supplies
`HA_URL`, `HA_TOKEN`, and optionally `BKK_API_KEY`. Connections can be changed
for the current session in the UI.

1. Vehicles around the map centre appear automatically. Enter a line such as
   **20E**, **80**, **4** or a train line and click **Find** to filter the list.
2. Click **Follow** next to a vehicle. The mock tracker copies its measured GPS
   position every 15 seconds. No additional Play action is needed. Keep the page
   open while following; updates stop if the browser suspends the page.
3. The panel reads your actual installed HA detector. Detection needs distinct
   moving vehicle/GPS reports and some real travel, usually around a minute
   with frequent reports. Standing next to a stopped vehicle is insufficient.
4. Click **Get off**, **Stay still**, or move the phone with map clicks, dragging
   or arrows. Continuing updates supplies real separation evidence to HA.
5. Use **Stop following** to pause reports, or **Remove mock tracker from HA**
   to remove the separate mock entity.

The default provider is **MÁV Plusz**, including BKK and MÁV vehicles. It needs
no API key. BKK FUTÁR is available in Connections. **Select the same provider
in HA and in the simulator.** Update the native integration to 0.4 before
using MÁV Plusz. An explicit tracker inclusion list must include
`device_tracker.bkkdetect_simulator`.

The mock entity carries `gps_timestamp` from the vehicle's actual telemetry;
HA uses this measurement time rather than treating receipt time as GPS time.
Stale or estimated vehicle positions are not used to follow a vehicle. The page
shows the detector's reason, candidate progress, and API errors when a ride
has not been confirmed. The tool never overwrites a real tracker or changes
integration settings.

The backend retains an optional `replay` mode for local interactive debugging
with a virtual clock and a vehicle moving along an actual trip shape. That mode
runs the same production detector locally and does not write to HA. The normal
UI uses real live HA detection and cannot accelerate real vehicle movement.

Vehicle requests are cached and limited to 12 requests/minute by default.
HA has its own configurable budget; both clients can affect upstream limits.
The page uses vendored Leaflet 1.9.4 and OpenStreetMap tiles. The optional local
tool is separate from the HACS integration package. No test suite is included.
