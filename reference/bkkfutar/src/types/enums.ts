export type AbsoluteDirection =
  | 'NORTH' | 'NORTHEAST' | 'EAST' | 'SOUTHEAST'
  | 'SOUTH' | 'SOUTHWEST' | 'WEST' | 'NORTHWEST'

export type RelativeDirection =
  | 'DEPART' | 'HARD_LEFT' | 'LEFT' | 'SLIGHTLY_LEFT' | 'CONTINUE'
  | 'SLIGHTLY_RIGHT' | 'RIGHT' | 'HARD_RIGHT' | 'CIRCLE_CLOCKWISE'
  | 'CIRCLE_COUNTERCLOCKWISE' | 'ELEVATOR' | 'UTURN_LEFT' | 'UTURN_RIGHT'

export type BicycleStreetDirection =
  | 'BIDIRECTIONAL' | 'ONEWAY_WITH_TRAFFIC' | 'ONEWAY_AGAINST_TRAFFIC'

export type BikeStreetCategory =
  | 'CYCLEWAY' | 'CYCLELANE' | 'LOW_TRAFFIC' | 'OTHER' | 'PEDESTRIAN'

export type CongestionLevel = 'UNKNOWN' | 'CONGESTION'

export type DayOfWeek = 'MON' | 'TUE' | 'WED' | 'THU' | 'FRI' | 'SAT' | 'SUN' | 'HOL' | 'O247'

export type DisplayedLegType = 'bike' | 'destination' | 'route' | 'ticketing' | 'walk'

export type EffectType = 'NO_SERVICE' | 'WARNING'

export type Message =
  | 'PLAN_OK' | 'SYSTEM_ERROR' | 'GRAPH_UNAVAILABLE'
  | 'PLANNER_SERVICE_UNAVAILABLE' | 'OUTSIDE_BOUNDS'
  | 'PATH_NOT_FOUND' | 'NO_TRANSIT_TIMES' | 'REQUEST_TIMEOUT'
  | 'BOGUS_PARAMETER' | 'GEOCODE_FROM_NOT_FOUND'
  | 'GEOCODE_TO_NOT_FOUND' | 'GEOCODE_FROM_TO_NOT_FOUND'
  | 'TOO_CLOSE' | 'LOCATION_NOT_ACCESSIBLE' | 'MISSING_MODE'
  | 'GEOCODE_FROM_AMBIGUOUS' | 'GEOCODE_TO_AMBIGUOUS'
  | 'GEOCODE_FROM_TO_AMBIGUOUS' | 'UNDERSPECIFIED_TRIANGLE'
  | 'TRIANGLE_NOT_AFFINE' | 'TRIANGLE_OPTIMIZE_TYPE_NOT_SET'
  | 'TRIANGLE_VALUES_NOT_SET'

export type OptimizeType = 'BEST' | 'WALK' | 'TRANSFERS'

export type PlaceType =
  | 'CUSTOMER_CENTER' | 'CASHIER' | 'VENDING_MACHINE' | 'RESELLER'

export type TicketingState = 'PLANNED' | 'OPERATIONAL' | 'INOPERATIVE'

export type TransferDirection = 'FEEDER' | 'FETCHER'

export type TransferStatus = 'NO_DATA' | 'OK' | 'WAIT' | 'ABORTED'

export type TransitEntityType = 'STOP' | 'STATION' | 'ROUTE' | 'RELATED_ALERT'

export type TransitRouteStyleIconType = 'BOX' | 'CIRCLE'

export type TransitStopStyleType = 'PRIORITY'

export type TraverseMode =
  | 'BICYCLE' | 'CAR' | 'WALK' | 'BUS' | 'CABLE_CAR' | 'COACH'
  | 'FERRY' | 'FUNICULAR' | 'GONDOLA' | 'RAIL' | 'SUBURBAN_RAILWAY'
  | 'SUBWAY' | 'TRAM' | 'TROLLEYBUS' | 'LOCAL' | 'TRANSIT'

export type VehicleStatus = 'INCOMING_AT' | 'STOPPED_AT' | 'IN_TRANSIT_TO'

export type WalkProfile = 'SLOW' | 'MID' | 'FAST'

export type WaitTime = 'short' | 'long'
