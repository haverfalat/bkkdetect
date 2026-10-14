import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  ListWithReferences,
  AgencyAndId,
  ServiceDate,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitVehicle } from './types'

export function createVehiclesModule(client: FutarClient) {
  function getForTrip(
    tripId: AgencyAndId[],
    options?: {
      date?: ServiceDate[]
      ifModifiedSince?: number
      includeReferences?: ReferencesSchema[]
    } & EndpointOptions
  ) {
    const params: RequestParams = { tripId }
    if (options?.date) params.date = options.date
    if (options?.ifModifiedSince !== undefined) params.ifModifiedSince = options.ifModifiedSince
    return client.request<ApiResponse<ListWithReferences<TransitVehicle, OTPTransitReferences>>>(
      '/api/where/vehicle-for-trip',
      params,
      options
    )
  }

  function getById(
    vehicleId: AgencyAndId[],
    options?: {
      ifModifiedSince?: number
      includeReferences?: ReferencesSchema[]
    } & EndpointOptions
  ) {
    const params: RequestParams = { vehicleId }
    if (options?.ifModifiedSince !== undefined) params.ifModifiedSince = options.ifModifiedSince
    return client.request<ApiResponse<ListWithReferences<TransitVehicle, OTPTransitReferences>>>(
      '/api/where/vehicles',
      params,
      options
    )
  }

  function forLocation(options: {
    lat?: number
    lon?: number
    latSpan?: number
    lonSpan?: number
    radius?: number
    query?: string
    ifModifiedSince?: number
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<ListWithReferences<TransitVehicle, OTPTransitReferences>>>(
      '/api/where/vehicles-for-location',
      options as unknown as RequestParams,
      options
    )
  }

  function forRoute(
    routeId: AgencyAndId[],
    options?: {
      related?: boolean
      ifModifiedSince?: number
      includeReferences?: ReferencesSchema[]
    } & EndpointOptions
  ) {
    const params: RequestParams = { routeId }
    if (options?.related !== undefined) params.related = options.related
    if (options?.ifModifiedSince !== undefined) params.ifModifiedSince = options.ifModifiedSince
    return client.request<ApiResponse<ListWithReferences<TransitVehicle, OTPTransitReferences>>>(
      '/api/where/vehicles-for-route',
      params,
      options
    )
  }

  function forStop(
    stopId: AgencyAndId,
    options?: {
      ifModifiedSince?: number
      includeReferences?: ReferencesSchema[]
    } & EndpointOptions
  ) {
    const params: RequestParams = { stopId }
    if (options?.ifModifiedSince !== undefined) params.ifModifiedSince = options.ifModifiedSince
    return client.request<ApiResponse<ListWithReferences<TransitVehicle, OTPTransitReferences>>>(
      '/api/where/vehicles-for-stop',
      params,
      options
    )
  }

  return { getForTrip, getById, forLocation, forRoute, forStop }
}
