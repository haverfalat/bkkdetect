import type { RelativeDirection, AbsoluteDirection, BikeStreetCategory, BicycleStreetDirection } from './enums'

export interface Place {
  arrival?: string
  departure?: string
  lat?: number
  lon?: number
  name: string
  orig?: string
  platformCode?: string
  stopCode?: string
  stopId?: string
  stopIndex?: number
  stopSequence?: number
  ticketingLocation?: TicketingLocation
}

export interface TripPlan {
  date: string
  from: Place
  itineraries: Itinerary[]
  to: Place
  usePatterns?: boolean
}

export interface Itinerary {
  bikeCategoryDistances?: Record<string, number>
  bikeDistance: number
  bikeTime: number
  displayProductRecommendation?: boolean
  displayedLegs?: DisplayedLeg[]
  duration: number
  elevationGained: number
  elevationLost: number
  endTime: string
  generalizedCost: number
  legs: Leg[]
  notAllTicketsAvailable: boolean
  patternDuration?: PatternStatistics
  patternFrequency?: PatternStatistics
  patternItineraries?: Itinerary[]
  startTime: string
  tooSloped: boolean
  transfers: number
  transitTime: number
  waitTimeAdjustedGeneralizedCost: number
  waitingTime: number
  walkDistance: number
  walkLimitExceeded: boolean
  walkTime: number
}

export interface Leg {
  agencyId?: string
  agencyName?: string
  agencyTimeZoneOffset: number
  agencyUrl?: string
  alertIds: string[]
  alightRule?: string
  arrivalDelay: number
  boardRule?: string
  departureDelay: number
  distance: number
  duration: number
  endTime: string
  from: Place
  generalizedCost: number
  hasAlertInPattern?: boolean
  headsign?: string
  interlineWithPreviousLeg?: boolean
  intermediateStops?: Place[]
  legElevation?: ElevationPoint[]
  legGeometry: EncodedPolylineBean
  mode: string
  onBoardAccess?: boolean
  pathway: boolean
  realTime: boolean
  rentedBike?: boolean
  requiresBooking?: boolean
  routeColor?: string
  routeId?: string
  routeIds?: string[]
  routeLongName?: string
  routeShortName?: string
  routeTextColor?: string
  serviceDate?: string
  startTime: string
  staySeated?: boolean
  steps?: WalkStep[]
  timeZone?: object
  to: Place
  transferFromPreviousTrip?: boolean
  transitLeg: boolean
  tripBlockId?: string
  tripId?: string
  tripIds?: string[]
  unknownGeometry?: boolean
  vertex?: string
  wait?: string
}

export interface DisplayedLeg {
  first?: boolean
  last?: boolean
  name: string
  time: number
  type: string
  walkTo: boolean
}

export interface RouteDisplayedLeg extends DisplayedLeg {
  hasAlert: boolean
  routeId: string
  routeIds: string[]
  wait?: string
  wheelchairAccessible: boolean
}

export interface BikeDisplayedLeg extends DisplayedLeg {
  rented: boolean
}

export interface WalkDisplayedLeg extends DisplayedLeg {}
export interface DestinationDisplayedLeg extends DisplayedLeg {}
export interface TicketingDisplayedLeg extends DisplayedLeg {}

export interface WalkStep {
  absoluteDirection?: AbsoluteDirection
  area: boolean
  bicycleCategory?: BikeStreetCategory
  bicycleStreetDirection?: BicycleStreetDirection
  bogusName: boolean
  distance: number
  geometry: EncodedPolylineBean
  lat: number
  lon: number
  relativeDirection?: RelativeDirection
  stayOn: boolean
  streetName: string
  walkingBike?: boolean
}

export interface ElevationPoint {
  distance: number
  elevation: number | null
}

export interface EncodedPolylineBean {
  length: number
  points: string
}

export interface PatternStatistics {
  avg?: number
  max?: number
  min?: number
  text: string
}

export interface PlannerError {
  id: number
  message: string
  missing?: string[]
  noPath: boolean
}

export interface Response {
  error?: PlannerError
  plan?: TripPlan
  requestParameters: Record<string, string>
}

export interface TicketingLocation {
  address?: string
  cashAccepted: boolean
  creditCardsAccepted: boolean
  description?: string
  id: string
  lastModified: string
  lat: number
  lon: number
  openingPeriods?: TicketingPeriod[]
  operator?: string
  passIdCreation: boolean
  place?: string
  products?: string[]
  state?: string
  ticketPassExchange: boolean
  type?: string
  visible: boolean
}

export interface TicketingPeriod {
  closes?: string
  closesSeconds: number
  dayOfWeek: string
  opens?: string
  opensSeconds: number
}

export interface TicketingProduct {
  groupId?: string
  groupName?: string
  id: string
  lastModified: string
  name?: string
  price?: string
  url?: string
  visible: boolean
}

export interface TransitTicketing {
  lastModifiedTime: number
  locations: TicketingLocation[]
  oldestModifiedTime: number
  products: TicketingProduct[]
}
