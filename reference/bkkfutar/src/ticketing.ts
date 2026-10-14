import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitTicketing } from './types'

export function createTicketingModule(client: FutarClient) {
  function getLocations(options?: {
    ifModifiedSince?: number
    full?: boolean
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<TransitTicketing, OTPTransitReferences>>>(
      '/api/where/ticketing-locations',
      options as unknown as RequestParams,
      options
    )
  }

  return { getLocations }
}
