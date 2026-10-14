import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitMetadata } from './types'

export function createMetadataModule(client: FutarClient) {
  function get(options?: {
    time?: number
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<TransitMetadata, OTPTransitReferences>>>(
      '/api/where/metadata',
      options as RequestParams,
      options
    )
  }

  return { get }
}
