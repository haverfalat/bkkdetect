import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  ListWithReferences,
  AgencyAndId,
  ServiceDate,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitRouteDetails, TransitRoute } from './types'

export function createRoutesModule(client: FutarClient) {
  function getDetails(
    routeId: AgencyAndId,
    options?: {
      date?: ServiceDate
      related?: boolean
      includeReferences?: ReferencesSchema[]
    } & EndpointOptions
  ) {
    const params: RequestParams = { routeId }
    if (options?.date !== undefined) params.date = options.date
    if (options?.related !== undefined) params.related = options.related
    return client.request<ApiResponse<EntryWithReferences<TransitRouteDetails, OTPTransitReferences>>>(
      '/api/where/route-details',
      params,
      options
    )
  }

  function getMultiDetails(
    routeId: AgencyAndId[],
    options?: {
      date?: ServiceDate
      related?: boolean
      includeReferences?: ReferencesSchema[]
    } & EndpointOptions
  ) {
    const params: RequestParams = { routeId }
    if (options?.date !== undefined) params.date = options.date
    if (options?.related !== undefined) params.related = options.related
    return client.request<ApiResponse<ListWithReferences<TransitRouteDetails, OTPTransitReferences>>>(
      '/api/where/multi-route-details',
      params,
      options
    )
  }

  function getForStop(
    stopId: AgencyAndId,
    options?: {
      includeReferences?: ReferencesSchema[]
    } & EndpointOptions
  ) {
    const params: RequestParams = { stopId }
    return client.request<ApiResponse<ListWithReferences<TransitRoute, OTPTransitReferences>>>(
      '/api/where/route-details-for-stop',
      params,
      options
    )
  }

  return { getDetails, getMultiDetails, getForStop }
}
