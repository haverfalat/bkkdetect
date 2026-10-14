import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  AgencyAndId,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { TransitSchedule } from './types'

export function createScheduleModule(client: FutarClient) {
  function forStop(options: {
    stopId: AgencyAndId[]
    date?: string
    onlyDepartures?: boolean
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<TransitSchedule, OTPTransitReferences>>>(
      '/api/where/schedule-for-stop',
      options as unknown as RequestParams,
      options
    )
  }

  return { forStop }
}
