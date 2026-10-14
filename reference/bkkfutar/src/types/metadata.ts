export interface TransitMetadata {
  alertIds: string[]
  boundingPolyLine: string
  completeValidityEnd: string
  completeValidityStart: string
  dayTypes: Record<string, string>
  feedIds: string[]
  lowerLeftLatitude: number
  lowerLeftLongitude: number
  readableTime: string
  time: number
  timeZone: string
  upperRightLatitude: number
  upperRightLongitude: number
  validityEnd: string
  validityStart: string
  internalRequest?: boolean
}
