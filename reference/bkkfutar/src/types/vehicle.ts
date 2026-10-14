import type { TransitVehicleStyleIcon } from './transit'

export interface TransitCoordinatePoint {
  lat: number
  lon: number
}

export interface TransitVehicle {
  bearing?: number
  capacity?: TransitVehicleOccupancy
  congestionLevel: string | null
  deviated: boolean
  label?: string
  lastUpdateTime: number
  licensePlate?: string
  location: TransitCoordinatePoint
  model?: string
  occupancy?: TransitVehicleOccupancy
  routeId?: string
  serviceDate?: string
  stale?: boolean
  status?: string
  stopDistancePercent?: number
  stopId?: string
  stopSequence?: number
  style?: TransitVehicleStyle
  tripId?: string
  vehicleId: string
  vehicleRouteType?: string
  vertex?: string
  wheelchairAccessible: boolean
}

export interface TransitVehicleOccupancy {
  adults?: number
  children?: number
  other?: number
  strollers?: number
  wheelchairs?: number
}

export interface TransitVehicleStyle {
  color?: string
  icon: TransitVehicleStyleIcon
  textColor?: string
}

export interface OnboardDepartPosition {
  accuracy?: number
  lat: number
  lon: number
  speed?: number
  timestamp: number
}
