# bkkfutar.js

A TypeScript client library for the BKK FUTAR API. It covers every endpoint in the OpenAPI specification and provides full type definitions for all request parameters and response types.

## Table of Contents

- [Installation](#installation)
- [Setup](#setup)
- [Response format](#response-format)
- Modules
  - [futar.alerts](#futanalerts) - Alert and disruption information
  - [futar.arrivals](#futararrivals) - Arrivals and departures for stops and locations
  - [futar.bicycles](#futarbicycles) - MOL Bubi bike-sharing station information
  - [futar.booking](#futarbooking) - Booking redirects for demand-responsive services
  - [futar.metadata](#futarmetadata) - Server metadata
  - [futar.onboard](#futaronboard) - On-vehicle departure search
  - [futar.planning](#futarplanning) - Trip planning
  - [futar.references](#futarreferences) - ID-based reference lookup
  - [futar.routes](#futaroutes) - Route details
  - [futar.schedule](#futarschedule) - Timetable schedules for stops
  - [futar.search](#futarsearch) - Combined search across stops, routes, alerts
  - [futar.statistics](#futarstatistics) - Health check endpoint
  - [futar.stops](#futarstops) - Stop lookup by location
  - [futar.ticketing](#futarticketing) - Ticket sales locations and products
  - [futar.trips](#futartrips) - Trip (journey instance) details
  - [futar.vehicles](#futarvehicles) - Real-time vehicle positions
- [Common options](#common-options)
- [Error handling](#error-handling)
- [TypeScript](#typescript)
- [Development](#development)

## Installation

```bash
npm install bkkfutar.js
```

## Setup

You need an API key to use the FUTAR API. Get one at https://opendata.bkk.hu/keys for free. Pass it to `createBkkFutar` along with any default options you want to set.

```ts
import { createBkkFutar } from 'bkkfutar.js';

const futar = createBkkFutar({
  apiKey: 'your-api-key-here',
  dialect: 'otp',
  version: '2',
});
```

The second argument to every function lets you override these defaults per-request.

### Configuration options

| Option     | Type                  | Default                                | Description                |
| ---------- | --------------------- | -------------------------------------- | -------------------------- |
| apiKey     | string                | (required)                             | Your FUTAR API key         |
| dialect    | 'otp' or 'mobile'     | 'otp'                                  | The reference dialect      |
| version    | '2', '3', '4', or '5' | '2'                                    | API version                |
| appVersion | string                | undefined                              | Client application version |
| baseUrl    | string                | 'https://futar.bkk.hu/api/query/v1/ws' | Base URL for all requests  |

## Response format

Every endpoint returns a FUTAR API response. The common shape is:

```ts
interface ApiResponse<T> {
  code: number;
  currentTime: number;
  data: T;
  status: string;
  text: string;
  version: number;
}
```

The `data` field contains either:

- `EntryWithReferences` (single entity with references)
- `ListWithReferences` (list of entities with references)

Both carry a `references` object with related agencies, routes, stops, trips, and alerts that were included in the response.

## Modules

The client is split into 16 modules, one for each area of the API.

---

### futar.alerts

Alert and disruption information.

**getAlertDetails(alertId, options?)**

Returns details for a specific alert, including all affected routes.

```ts
const result = await futar.alerts.getAlertDetails('BKK_bkkinfo-75694', {
  date: '20210707',
  related: true,
});
```

Options:

- `date`: Service date string (YYYYMMDD). Defaults to today.
- `related`: Include related routes.
- `includeReferences`: Control which reference types to include.

**searchAlerts(options?)**

Search for alerts matching a query or within a time range.

```ts
const result = await futar.alerts.searchAlerts({
  query: 'BKK_bkkinfo-75694',
  start: 1625695260,
  end: 1625740980,
  filterClosed: true,
  minResult: 5,
});
```

Options:

- `query`: Search term matched against alert headers, descriptions, and IDs.
- `start`, `end`: Time range in epoch seconds.
- `time`: Evaluation time. Defaults to server time.
- `filterClosed`: Exclude alerts that ended before the current time. Default true.
- `listView`: Filter alerts for the alert list view.
- `minResult`: Minimum number of results. Default 5.

---

### futar.arrivals

Arrivals and departures for stops and locations.

**forLocation(options)**

Get arrivals and departures grouped by route and headsign for a geographic area.

```ts
const result = await futar.arrivals.forLocation({
  lat: 47.4973,
  lon: 19.0646,
  radius: 200,
  minutesBefore: 5,
  minutesAfter: 30,
  limit: 60,
});
```

Required options: `lat`, `lon`.

Key options:

- `lat`, `lon`: Center of the search area.
- `latSpan`, `lonSpan`: Bounding box size. If omitted, `radius` is used.
- `radius`: Search radius in meters. Default 100.
- `time`: Evaluation time in epoch seconds. Defaults to server time.
- `minutesBefore`, `minutesAfter`: Time window around `time`. Defaults 2 and 30.
- `limit`: Max stop times per group. Default 60.
- `minResult`: Minimum results. Default 5.
- `groupLimit`: Max schedule stop times per group. Default 4.
- `stopId`: Filter by specific stop IDs.
- `includeRouteId`: Ensure at least one departure per listed route.
- `includeRouteTypes`, `excludeRouteTypes`: Filter by vehicle type (BUS, TRAM, SUBWAY, etc.).
- `stopTimeType`: 'ARRIVAL', 'DEPARTURE', or 'ARRIVAL_AND_DEPARTURE'.
- `query`: Free text search filter.
- `onlyDepartures`: Deprecated. Default true.
- `includeVehicleFromTrip`, `includeVehicleFromVehicleBlock`: Include vehicle data.

**forStop(options)**

Get arrivals and departures for one or more stops.

```ts
const result = await futar.arrivals.forStop({
  stopId: ['BKK_F01029'],
  minutesBefore: 5,
  minutesAfter: 30,
});
```

Required options: `stopId`.

Accepts the same options as `forLocation` except `groupLimit`.

**onboardingButton(options)**

Same as `forLocation` but returns data formatted for the onboarding button UI. Same parameters.

---

### futar.bicycles

MOL Bubi bike-sharing station information.

**getStations(options?)**

Get all bike rental stations, optionally filtered by station ID.

```ts
const result = await futar.bicycles.getStations();
const filtered = await futar.bicycles.getStations({ stationId: ['42711896'] });
```

Options:

- `stationId`: Filter by specific station IDs.

---

### futar.booking

Booking redirects for demand-responsive services.

**redirect(options)**

Get a redirect URL to a booking page for a specific trip.

```ts
const url = await futar.booking.redirect({
  boardStopId: 'BKK_064215',
  alightStopId: 'BKK_064215',
  routeId: 'BKK_0650',
  tripId: 'BKK_ADF5443',
  agencyId: 'BKK_BKK',
  serviceDate: '20220130',
  directionId: '1',
});
```

Required options: all except `directionId`.

Returns a 302 redirect URL as a string.

---

### futar.metadata

Server metadata.

**get(options?)**

Returns server metadata including active alert IDs, bounding area, day types, and validity dates.

```ts
const result = await futar.metadata.get({ time: 1625666578 });
```

Options:

- `time`: Evaluation time in epoch seconds.

---

### futar.onboard

On-vehicle departure search.

**searchDepartVehicles(positions, options?)**

Send GPS position data to find vehicles matching the passenger's route.

```ts
const result = await futar.onboard.searchDepartVehicles([
  { lat: 47.4973, lon: 19.0646, timestamp: 1644829176, accuracy: 100, speed: 8 },
]);
```

This is a POST endpoint. The first argument is an array of `OnboardDepartPosition` objects:

- `lat`, `lon`: Position coordinates (required).
- `timestamp`: Epoch seconds (required).
- `accuracy`: Accuracy in meters.
- `speed`: Speed in m/s.

---

### futar.planning

Trip planning.

**planTrip(options)**

Plan a journey from one place to another using public transport.

```ts
const result = await futar.planning.planTrip({
  fromPlace: 'BKK Kozponti Ugyfelszolgalat::47.4985022,19.0551266',
  toPlace: 'Mechwart liget::BKK:CSF00195',
  mode: ['TRANSIT', 'WALK'],
  date: '2021-07-09',
  time: '11:35',
  arriveBy: false,
  numItineraries: 5,
  optimize: 'BEST',
  wheelchair: false,
  showIntermediateStops: true,
  walkProfile: 'MID',
});
```

Required options: `fromPlace`, `toPlace`, `mode`.

`fromPlace` and `toPlace` format: `name::location` where location is `lat,lon` or a geocoder vertex ID.

`mode` is an array of TraverseMode values: TRANSIT, WALK, BUS, TRAM, SUBWAY, RAIL, etc. For bike rental, use `['BICYCLE', 'WALK']`.

Other options:

- `date`, `time`: When to depart (or arrive if `arriveBy` is true).
- `arriveBy`: Plan for arrival by the given time. Default false.
- `numItineraries`: Max itineraries to return.
- `optimize`: 'BEST', 'WALK', or 'TRANSFERS'.
- `wheelchair`: Require wheelchair-accessible routes.
- `walkProfile`: 'SLOW', 'MID', or 'FAST'.
- `showIntermediateStops`: Include intermediate stops in legs.
- `shouldBuyTickets`: Whether ticket purchase happens before boarding.
- `triangleSafetyFactor`, `triangleSlopeFactor`, `triangleTimeFactor`: Bicycle triangle routing factors (must sum to 1).

**planAccess(options)**

Same as `planTrip` but for accessibility-focused planning. Same parameters.

---

### futar.references

ID-based reference lookup.

**get(options)**

Look up agencies, routes, stops, alerts, and trip references by ID.

```ts
const result = await futar.references.get({
  stopId: ['BKK_F00001'],
  routeId: ['BKK_3040'],
  alertId: ['BKK_bkkinfo-81404'],
  agencyId: ['BKK_BKK'],
});
```

Options: all optional.

- `stopId`, `routeId`, `alertId`, `agencyId`: Arrays of IDs to look up.

---

### futar.routes

Route details.

**getDetails(routeId, options?)**

Get details for a single route including its variants.

```ts
const result = await futar.routes.getDetails('BKK_3040', {
  date: '20210707',
  related: true,
});
```

Options:

- `date`: Service date. Defaults to today.
- `related`: Include related routes.

**getMultiDetails(routeId, options?)**

Get details for multiple routes at once.

```ts
const result = await futar.routes.getMultiDetails(['BKK_3040', 'BKK_3060'], {
  date: '20210707',
  related: true,
});
```

**getForStop(stopId, options?)**

Get all routes serving a specific stop, including sibling stops.

```ts
const result = await futar.routes.getForStop('BKK_F01294');
```

---

### futar.schedule

Timetable schedules for stops.

**forStop(options)**

Get the schedule for one or more stops on a given date.

```ts
const result = await futar.schedule.forStop({
  stopId: ['BKK_F01294'],
  date: '20210708',
  onlyDepartures: false,
});
```

Options:

- `stopId`: One or more stop IDs (required).
- `date`: Service date string.
- `onlyDepartures`: Exclude arrival times. Default true.

---

### futar.search

Combined search across stops, routes, and alerts.

**search(options)**

Search for stops, routes, and alerts that match a query string.

```ts
const result = await futar.search.search({
  query: 'BKK_bkkinfo-75694',
  lat: 47.4973,
  lon: 19.0646,
  minResult: 5,
});
```

Options:

- `query`: Search term.
- `lat`, `lon`: Map view center for relevance-based results.
- `minResult`: Minimum number of results. Default 5.

---

### futar.statistics

Simple health check endpoint.

**get(options?)**

Returns a simple `{ result: 'OK' }` response for connectivity testing.

```ts
const result = await futar.statistics.get();
```

---

### futar.stops

Stop lookup by location.

**forLocation(options)**

Find stops near a geographic location.

```ts
const result = await futar.stops.forLocation({
  lat: 47.4973,
  lon: 19.0646,
  radius: 200,
  query: 'Deak',
  minResult: 5,
});
```

Options:

- `lat`, `lon`: Center coordinates.
- `latSpan`, `lonSpan`: Bounding box. Falls back to `radius`.
- `radius`: Search radius in meters. Default 100.
- `query`: Free text search filter.
- `minResult`: Minimum results. Default 5.

---

### futar.ticketing

Ticket sales locations and products.

**getLocations(options?)**

Get ticket vending machines, customer service points, and ticket products.

```ts
const result = await futar.ticketing.getLocations({
  ifModifiedSince: 1625685137,
  full: false,
});
```

Options:

- `ifModifiedSince`: Only return data modified after this epoch timestamp. Returns 304 (throws error) if nothing changed.
- `full`: Return full data if modified since `ifModifiedSince`.

---

### futar.trips

Trip (journey instance) details.

**getDetails(options)**

Get detailed information about a specific trip, including all stop times and transfers.

```ts
const result = await futar.trips.getDetails({
  tripId: 'BKK_C23556161',
  date: '20210708',
});

// Or look up by vehicle:
const result2 = await futar.trips.getDetails({
  vehicleId: 'BKK_4510',
  date: '20210708',
});
```

Options:

- `tripId`: Look up by trip ID.
- `vehicleId`: Look up by vehicle ID (the trip this vehicle is running).
- `date`: Service date. Required when using `tripId`.
- `ifModifiedSince`: Only return data if modified after this time.

---

### futar.vehicles

Real-time vehicle positions.

**getForTrip(tripId, options?)**

Get vehicles for specific trips.

```ts
const result = await futar.vehicles.getForTrip(['BKK_C3135012112'], {
  date: ['20210708'],
});
```

Options:

- `date`: Service dates corresponding to each trip ID.
- `ifModifiedSince`: Conditional request.

**getById(vehicleId, options?)**

Get vehicles by their vehicle IDs.

```ts
const result = await futar.vehicles.getById(['BKK_2035']);
```

Options:

- `ifModifiedSince`: Conditional request.

**forLocation(options)**

Get vehicles in a geographic area.

```ts
const result = await futar.vehicles.forLocation({
  lat: 47.4973,
  lon: 19.0646,
  radius: 500,
  query: 'BKK_4510',
});
```

Options:

- `lat`, `lon`, `latSpan`, `lonSpan`, `radius`: Geographic bounds.
- `query`: Filter by vehicle ID, license plate, or type.
- `ifModifiedSince`: Conditional request.

If `lat` and `lon` are omitted, returns all vehicles.

**forRoute(routeId, options?)**

Get vehicles currently running on specific routes.

```ts
const result = await futar.vehicles.forRoute(['BKK_3040', 'BKK_3060'], {
  related: true,
});
```

Options:

- `related`: Include vehicles on related routes.
- `ifModifiedSince`: Conditional request.

**forStop(stopId, options?)**

Get vehicles for trips that serve a specific stop.

```ts
const result = await futar.vehicles.forStop('BKK_F01081');
```

Options:

- `ifModifiedSince`: Conditional request.

---

## Common options

A set of common options can be passed to every endpoint:

| Option            | Type              | Description                                                                                                                          |
| ----------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| dialect           | 'otp' or 'mobile' | Override the client-level dialect                                                                                                    |
| version           | ApiVersion        | Override the client-level API version                                                                                                |
| appVersion        | string            | Override the client-level app version                                                                                                |
| includeReferences | string[]          | Control references in the response. Values: 'true', 'false', 'compact', 'agencies', 'routes', 'trips', 'stops', 'alerts', 'stations' |

These are set at the client level and can be overridden per-request.

```ts
const futar = createBkkFutar({
  apiKey: 'your-key',
  dialect: 'otp',
  version: '2',
  appVersion: '1.1.abc',
});

// Override per request:
const result = await futar.metadata.get({
  dialect: 'mobile',
  includeReferences: ['routes', 'stops'],
});
```

## Error handling

The library throws an error when the API returns a non-OK status:

```ts
try {
  const result = await futar.stops.forLocation({ lat: 47.5, lon: 19.06 });
} catch (err) {
  // HTTP 400, 404, etc.
  console.error(err.message);
}
```

304 Not Modified responses throw an error with the message 'NOT_MODIFIED'.

404 Not Found responses throw an error for unknown IDs.

## TypeScript

All types are exported from the package:

```ts
import {
  type BkkFutar,
  type FutarClientConfig,
  type ApiResponse,
  type TransitStop,
  type TransitRoute,
  type TransitVehicle,
  type Leg,
  type Itinerary,
  type Place,
  // ... and many more
} from 'bkkfutar.js';
```

## Development

```bash
# Build
npm run build

# The futar-openapi.yaml file in the project root contains the
# complete API specification that this library is based on.
```
