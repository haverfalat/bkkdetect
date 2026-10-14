import type { TransitVehicle } from './vehicle'
import type { TransitPolyline } from './transit'

export interface TransitTripDetailsOTP {
  alertIds: string[]
  mayRequireBooking: boolean
  nextBlockTripId?: string
  polyline?: TransitPolyline
  serviceDate: string
  stopTimes: TransitTripStopTime[]
  tripId: string
  vehicle?: TransitVehicle
  vertex?: string
}

export interface TransitTripStopTime {
  arrivalTime?: number
  departureTime?: number
  dropOffAllowed?: boolean
  pickupAllowed?: boolean
  predictedArrivalTime?: number
  predictedDepartureTime?: number
  predictionScheduled?: boolean
  requiresBooking: boolean
  shapeDistTraveled?: number
  stopHeadsign: string
  stopId: string
  stopSequence?: number
  transfers?: TransitTransfer[]
  uncertain?: boolean
}

export interface TransitTransfer {
  direction: string
  minTransferTime: number
  otherServiceDate: string
  otherStopId?: string
  otherTripDesc?: string
  otherTripId?: string
  otherTripTime?: TransitTransferStopTime
  status: string
  staySeated: boolean
  transferId: string
}

export interface TransitTransferStopTime {
  predictedTime?: number
  scheduledTime: number
  stopHeadsign?: string
  uncertain?: boolean
}

export interface ReferencesMethodResult {
  errors: ReferencesMethodErrors
}

export interface ReferencesMethodErrors {
  agencyIds: string[]
  alertIds: string[]
  routeIds: string[]
  stopIds: string[]
}

export interface StatisticsResponse {
  result: string
}
