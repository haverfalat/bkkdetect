import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  ListWithReferences,
  AgencyAndId,
  TraverseMode,
  StopTimeType,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitArrivalsAndDepartures, TransitDepartureGroup } from './types'

export function createArrivalsModule(client: FutarClient) {
  function forLocation(options: {
    lat: number
    lon: number
    latSpan?: number
    lonSpan?: number
    radius?: number
    query?: string
    time?: number
    minutesBefore?: number
    minutesAfter?: number
    limit?: number
    minResult?: number
    groupLimit?: number
    clientLat?: number
    clientLon?: number
    stopId?: AgencyAndId[]
    includeRouteId?: AgencyAndId[]
    includeRouteTypes?: TraverseMode[]
    excludeRouteTypes?: TraverseMode[]
    stopTimeType?: StopTimeType
    onlyDepartures?: boolean
    includeVehicleFromTrip?: boolean
    includeVehicleFromVehicleBlock?: boolean
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<ListWithReferences<TransitDepartureGroup, OTPTransitReferences>>>(
      '/api/where/arrivals-and-departures-for-location',
      options as unknown as RequestParams,
      options
    )
  }

  function forStop(options: {
    stopId: AgencyAndId[]
    lat?: number
    lon?: number
    latSpan?: number
    lonSpan?: number
    radius?: number
    query?: string
    time?: number
    minutesBefore?: number
    minutesAfter?: number
    limit?: number
    minResult?: number
    clientLat?: number
    clientLon?: number
    includeRouteId?: AgencyAndId[]
    includeRouteTypes?: TraverseMode[]
    excludeRouteTypes?: TraverseMode[]
    stopTimeType?: StopTimeType
    onlyDepartures?: boolean
    includeVehicleFromTrip?: boolean
    includeVehicleFromVehicleBlock?: boolean
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<TransitArrivalsAndDepartures, OTPTransitReferences>>>(
      '/api/where/arrivals-and-departures-for-stop',
      options as unknown as RequestParams,
      options
    )
  }

  function onboardingButton(options: {
    lat: number
    lon: number
    latSpan?: number
    lonSpan?: number
    radius?: number
    query?: string
    time?: number
    minutesBefore?: number
    minutesAfter?: number
    limit?: number
    minResult?: number
    groupLimit?: number
    clientLat?: number
    clientLon?: number
    stopId?: AgencyAndId[]
    includeRouteId?: AgencyAndId[]
    includeRouteTypes?: TraverseMode[]
    excludeRouteTypes?: TraverseMode[]
    stopTimeType?: StopTimeType
    onlyDepartures?: boolean
    includeVehicleFromTrip?: boolean
    includeVehicleFromVehicleBlock?: boolean
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<ListWithReferences<TransitDepartureGroup, OTPTransitReferences>>>(
      '/api/where/onboarding-button',
      options as unknown as RequestParams,
      options
    )
  }

  return { forLocation, forStop, onboardingButton }
}
