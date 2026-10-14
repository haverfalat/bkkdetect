import type { FutarClient, EndpointOptions, RequestParams } from './client'
import type {
  ApiResponse,
  EntryWithReferences,
  TraverseMode,
  OptimizeType,
  WalkProfile,
  ReferencesSchema,
  OTPTransitReferences,
} from './types'
import type { Response } from './types'

export function createPlanningModule(client: FutarClient) {
  function planTrip(options: {
    fromPlace: string
    toPlace: string
    mode: TraverseMode[]
    date?: string
    time?: string
    arriveBy?: boolean
    numItineraries?: number
    optimize?: OptimizeType
    wheelchair?: boolean
    walkProfile?: WalkProfile
    showIntermediateStops?: boolean
    shouldBuyTickets?: boolean
    triangleSafetyFactor?: number
    triangleSlopeFactor?: number
    triangleTimeFactor?: number
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<Response, OTPTransitReferences>>>(
      '/api/where/plan-trip',
      options as unknown as RequestParams,
      options
    )
  }

  function planAccess(options: {
    fromPlace: string
    toPlace: string
    mode: TraverseMode[]
    date?: string
    time?: string
    arriveBy?: boolean
    numItineraries?: number
    optimize?: OptimizeType
    wheelchair?: boolean
    walkProfile?: WalkProfile
    showIntermediateStops?: boolean
    shouldBuyTickets?: boolean
    triangleSafetyFactor?: number
    triangleSlopeFactor?: number
    triangleTimeFactor?: number
    includeReferences?: ReferencesSchema[]
  } & EndpointOptions) {
    return client.request<ApiResponse<EntryWithReferences<Response, OTPTransitReferences>>>(
      '/api/where/plan-access',
      options as unknown as RequestParams,
      options
    )
  }

  return { planTrip, planAccess }
}
