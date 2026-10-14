import type { TransitAlertGroup } from './alert'

export interface TransitSearch {
  alertGroups?: TransitAlertGroup[]
  alertIds?: string[]
  query?: string
  routeIds?: string[]
  stopIds?: string[]
}
