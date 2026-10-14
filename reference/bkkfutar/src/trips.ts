import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  AgencyAndId,
  ServiceDate,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitTripDetailsOTP } from './types'

export function createTripsModule(client: FutarClient) {
  function getDetails(options: {
    tripId?: AgencyAndId
    vehicleId?: AgencyAndId
    date?: ServiceDate
    ifModifiedSince?: number
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<TransitTripDetailsOTP, OTPTransitReferences>>>(
      '/api/where/trip-details',
      options as unknown as RequestParams,
      options
    )
  }

  return { getDetails }
}
