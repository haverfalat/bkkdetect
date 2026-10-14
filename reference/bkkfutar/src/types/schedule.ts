import type { TransitScheduleStopTime } from './arrival'

export interface TransitSchedule {
  alertIds: string[]
  date: string
  nearbyStopIds: string[]
  routeIds: string[]
  schedules: TransitRouteSchedule[]
  serviceDate: string
  stopId: string
}

export interface TransitRouteSchedule {
  alertIds: string[]
  directions: TransitRouteScheduleForDirection[]
  routeId: string
}

export interface TransitRouteScheduleForDirection {
  directionId?: string
  groups: Record<string, TransitScheduleGroup>
  stopTimes: TransitScheduleStopTime[]
}

export interface TransitScheduleGroup {
  description: string
  groupId: string
  headsign: string
}
