import type { FutarClient, EndpointOptions } from './client'
import type { StatisticsResponse } from './types'

export function createStatisticsModule(client: FutarClient) {
  function get(options?: EndpointOptions) {
    return client.request<StatisticsResponse>(
      '/api/where/statistics',
      {},
      options
    )
  }

  return { get }
}
