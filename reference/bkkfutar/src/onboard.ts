import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  ListWithReferences,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { OnboardDepartPosition, TransitVehicle } from './types'

export function createOnboardModule(client: FutarClient) {
  function searchDepartVehicles(
    positions: OnboardDepartPosition[],
    options?: {
      includeReferences?: ReferencesSchema[]
    } & EndpointOptions
  ) {
    return client.request<ApiResponse<ListWithReferences<TransitVehicle, OTPTransitReferences>>>(
      '/api/where/onboard-depart-search',
      {} as RequestParams,
      options,
      'POST',
      positions
    )
  }

  return { searchDepartVehicles }
}
