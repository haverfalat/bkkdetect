import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitSearch } from './types'

export function createSearchModule(client: FutarClient) {
  function search(options: {
    query?: string
    lat?: number
    lon?: number
    minResult?: number
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<TransitSearch, OTPTransitReferences>>>(
      '/api/where/search',
      options as RequestParams,
      options
    )
  }

  return { search }
}
