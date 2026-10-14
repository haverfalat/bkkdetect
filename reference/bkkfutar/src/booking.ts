import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type { AgencyAndId, ServiceDate } from './types'

export function createBookingModule(client: FutarClient) {
  function redirect(options: {
    boardStopId: AgencyAndId
    alightStopId: AgencyAndId
    routeId: AgencyAndId
    tripId: AgencyAndId
    agencyId: AgencyAndId
    serviceDate: ServiceDate
    directionId?: string
  } & EndpointOptions) {
    return client.request<string>(
      '/api/where/booking-redirect',
      options as unknown as RequestParams,
      options
    )
  }

  return { redirect }
}
