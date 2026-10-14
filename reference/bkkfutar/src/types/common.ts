export type AgencyAndId = string

export type Dialect = 'otp' | 'mobile'

export type ApiVersion = '2' | '3' | '4' | '5'

export type ServiceDate = string

export type ReferencesSchema = 'true' | 'false' | 'compact' | 'agencies' | 'routes' | 'trips' | 'stops' | 'alerts' | 'stations'

export type StopTimeType = 'ARRIVAL' | 'DEPARTURE' | 'ARRIVAL_AND_DEPARTURE'

export type Status =
  | 'OK' | 'NOT_MODIFIED' | 'MOVED_TEMPORARILY' | 'INVALID_VALUE'
  | 'OUTSIDE_BOUNDS' | 'BOGUS_PARAMETER' | 'TOO_CLOSE'
  | 'LOCATION_NOT_ACCESSIBLE' | 'MISSING_MODE' | 'LIMIT_EXCEEDED'
  | 'NO_ROUTE_ID_PROVIDED' | 'NOT_FOUND' | 'PATH_NOT_FOUND'
  | 'NO_TRANSIT_TIMES' | 'NOT_OPERATING' | 'REQUEST_TIMEOUT'
  | 'ERROR_NO_GRAPH' | 'UNKNOWN_ERROR' | 'ERROR_BIKE_RENTAL_SERVICE'
  | 'ERROR_TICKETING_SERVICE' | 'ERROR_TRANSIT_INDEX_SERVICE'
  | 'ERROR_PATCH_SERVICE' | 'PLANNER_SERVICE_UNAVAILABLE'

export interface ApiResponse<T> {
  code: number
  currentTime: number
  data: T
  status: Status
  text: string
  version: number
}

export interface EntryWithReferences<TEntry, TRef> {
  class: 'entryWithReferences'
  entry: TEntry
  limitExceeded: boolean
  references: TRef
}

export interface ListWithReferences<TItem, TRef> {
  class: 'listWithReferences'
  list: TItem[]
  limitExceeded: boolean
  outOfRange: boolean
  missingIds: string[]
  references: TRef
}
