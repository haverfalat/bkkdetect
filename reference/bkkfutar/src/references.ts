import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  AgencyAndId,
  ReferencesSchema,
} from './types'
import type { ReferencesMethodResult, TransitReferences } from './types'

export function createReferencesModule(client: FutarClient) {
  function get(options: {
    stopId?: AgencyAndId[]
    routeId?: AgencyAndId[]
    alertId?: AgencyAndId[]
    agencyId?: AgencyAndId[]
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<ReferencesMethodResult, TransitReferences>>>(
      '/api/where/references',
      options as unknown as RequestParams,
      options
    )
  }

  return { get }
}
