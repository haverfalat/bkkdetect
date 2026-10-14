export interface TransitBikeRentalStation {
  bikes: number
  code: string
  id: string
  lat: number
  lon: number
  name: string
  spaces: number
  style: TransitBikeRentalStationStyle
  type?: string
}

export interface TransitBikeRentalStationStyle {
  icon: TransitBikeRentalStationStyleIcon
}

export interface TransitBikeRentalStationStyleIcon {
  name: string
}
