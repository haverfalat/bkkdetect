import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  ListWithReferences,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitStop } from './types'

export function createStopsModule(client: FutarClient) {
  function forLocation(options: {
    lat?: number
    lon?: number
    latSpan?: number
    lonSpan?: number
    radius?: number
    query?: string
    minResult?: number
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<ListWithReferences<TransitStop, OTPTransitReferences>>>(
      '/api/where/stops-for-location',
      options as RequestParams,
      options
    )
  }

  return { forLocation }
}
