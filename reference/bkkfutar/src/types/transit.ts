export interface TranslatedString {
  someTranslation?: string
  translations: Record<string, string>
}

export interface TransitAgency {
  id: string
  lang?: string
  name: string
  phone?: string
  timezone: string
  url: string
}

export interface TransitStop {
  alertIds?: string[]
  code?: string
  description?: string
  direction: string
  id: string
  lat: number
  locationSubType?: string
  locationType: number
  lon: number
  name: string
  parentStationId?: string
  platformCode?: string
  routeIds: string[]
  stopColorType?: string
  style: TransitStopStyle
  type?: string
  vertex?: string
  wheelchairBoarding: boolean
}

export interface TransitTrip {
  bikesAllowed: boolean
  blockId?: string
  directionId?: string
  id: string
  routeId: string
  serviceId: string
  shapeId: string
  tripHeadsign: string
  tripShortName?: string
  wheelchairAccessible: boolean
}

export interface TransitRoute {
  agencyId: string
  bikesAllowed: boolean
  color: string
  description?: string
  iconDisplayText?: string
  iconDisplayType?: string
  id: string
  longName?: string
  shortName?: string
  sortOrder: number
  style: TransitRouteStyle
  textColor: string
  type: string
  url?: string
}

export interface TransitRouteStyle {
  color: string
  groupId: number
  icon: TransitRouteStyleIcon
  stop?: TransitStopStyle
  vehicleIcon: TransitVehicleStyleIcon
}

export interface TransitRouteStyleIcon {
  text: string
  textColor: string
  type: string
}

export interface TransitRouteVariant {
  bookableStopIds: string[]
  direction?: string
  headsign: string
  mayRequireBooking: boolean
  name?: string
  patternId?: string
  polyline: TransitPolyline
  routeId?: string
  stopIds: string[]
  type?: string
}

export interface TransitStopStyle {
  colors: string[]
  image?: string
  type?: string
}

export interface TransitPolyline {
  length: number
  levels: string
  points: string
}

export interface TransitVehicleStyleIcon {
  color?: string
  name?: string
  secondaryColor?: string
}

export type TransitReferences = OTPTransitReferences | MobileTransitReferences

export interface OTPTransitReferences {
  agencies?: Record<string, TransitAgency>
  alerts?: Record<string, TransitAlert>
  routes?: Record<string, TransitRoute>
  stops?: Record<string, TransitStop>
  trips?: Record<string, TransitTrip>
}

export interface MobileTransitReferences {
  agencies?: TransitAgency[]
  alerts?: TransitAlert[]
  routes?: TransitRoute[]
  stops?: TransitStop[]
  trips?: TransitTrip[]
}

import type { TransitAlert } from './alert'
