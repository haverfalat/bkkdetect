import type { TranslatedString, TransitRouteStyle, TransitRouteVariant } from './transit'
import type { EffectType } from './enums'

export interface TransitAlert {
  description: TranslatedString
  disableApp?: boolean
  end?: number
  endText?: TranslatedString
  header: TranslatedString
  id: string
  modifiedTime: number
  priority?: number
  routeIds: string[]
  routes: TransitAlertRoute[]
  start?: number
  startText?: TranslatedString
  stopIds: string[]
  timestamp: number
  url?: TranslatedString
  vehicleRouteTypes: string[]
}

export interface TransitAlertRoute {
  affectedEntityDescription?: TranslatedString
  effectType: EffectType
  header: TranslatedString
  routeId: string
  stopIds: string[]
}

export interface TransitAlertDetails {
  routeDetails: TransitRouteDetails[]
}

export interface TransitAlertGroup {
  alertIds?: string[]
  id?: string
  name?: string
}

export interface TransitRouteDetails {
  agencyId: string
  alertIds: string[]
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
  variants: TransitRouteVariant[]
}
