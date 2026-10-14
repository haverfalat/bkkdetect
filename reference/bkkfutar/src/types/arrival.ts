import type { TransitVehicle } from './vehicle'

export interface TransitArrivalsAndDepartures {
  alertIds: string[]
  nearbyStopIds: string[]
  routeIds: string[]
  stopId: string
  stopTimes: TransitScheduleStopTime[]
}

export interface TransitDepartureGroup {
  headsign: string
  routeId: string
  stopTimes: TransitScheduleStopTime[]
}

export interface TransitScheduleStopTime {
  alertIds: string[]
  arrivalTime?: number
  departureTime?: number
  dropOffAllowed?: boolean
  groupIds?: string[]
  mayRequireBooking: boolean
  pickupAllowed?: boolean
  predictedArrivalTime?: number
  predictedDepartureTime?: number
  predictionScheduled?: boolean
  serviceDate: string
  stopHeadsign: string
  stopId: string
  stopSequence?: number
  tripId: string
  uncertain?: boolean
  vehicle?: TransitVehicle
  wheelchairAccessible: boolean
}
