import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  AgencyAndId,
  ServiceDate,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitAlertDetails, TransitSearch } from './types'

export function createAlertsModule(client: FutarClient) {
  function getAlertDetails(
    alertId: AgencyAndId,
    options?: {
      date?: ServiceDate
      related?: boolean
      includeReferences?: ReferencesSchema[]
    } & EndpointOptions
  ) {
    const params: RequestParams = { alertId }
    if (options?.date !== undefined) params.date = options.date
    if (options?.related !== undefined) params.related = options.related
    return client.request<ApiResponse<EntryWithReferences<TransitAlertDetails, OTPTransitReferences>>>(
      '/api/where/alert-details',
      params,
      options
    )
  }

  function searchAlerts(options?: {
    query?: string
    start?: number
    end?: number
    time?: number
    filterClosed?: boolean
    listView?: boolean
    minResult?: number
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<TransitSearch, OTPTransitReferences>>>(
      '/api/where/alert-search',
      options as RequestParams,
      options
    )
  }

  return { getAlertDetails, searchAlerts }
}
