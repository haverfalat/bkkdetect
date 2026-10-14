import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  ListWithReferences,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitBikeRentalStation } from './types'

export function createBicyclesModule(client: FutarClient) {
  function getStations(options?: {
    stationId?: string[]
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<ListWithReferences<TransitBikeRentalStation, OTPTransitReferences>>>(
      '/api/where/bicycle-rental',
      options as unknown as RequestParams,
      options
    )
  }

  return { getStations }
}
