import { createClient, type FutarClientConfig } from './client'
import { createAlertsModule } from './alerts'
import { createArrivalsModule } from './arrivals'
import { createBicyclesModule } from './bicycles'
import { createBookingModule } from './booking'
import { createMetadataModule } from './metadata'
import { createOnboardModule } from './onboard'
import { createPlanningModule } from './planning'
import { createReferencesModule } from './references'
import { createRoutesModule } from './routes'
import { createScheduleModule } from './schedule'
import { createSearchModule } from './search'
import { createStatisticsModule } from './statistics'
import { createStopsModule } from './stops'
import { createTicketingModule } from './ticketing'
import { createTripsModule } from './trips'
import { createVehiclesModule } from './vehicles'

export * from './types'

export interface BkkFutar {
  alerts: ReturnType<typeof createAlertsModule>
  arrivals: ReturnType<typeof createArrivalsModule>
  bicycles: ReturnType<typeof createBicyclesModule>
  booking: ReturnType<typeof createBookingModule>
  metadata: ReturnType<typeof createMetadataModule>
  onboard: ReturnType<typeof createOnboardModule>
  planning: ReturnType<typeof createPlanningModule>
  references: ReturnType<typeof createReferencesModule>
  routes: ReturnType<typeof createRoutesModule>
  schedule: ReturnType<typeof createScheduleModule>
  search: ReturnType<typeof createSearchModule>
  statistics: ReturnType<typeof createStatisticsModule>
  stops: ReturnType<typeof createStopsModule>
  ticketing: ReturnType<typeof createTicketingModule>
  trips: ReturnType<typeof createTripsModule>
  vehicles: ReturnType<typeof createVehiclesModule>
}

export function createBkkFutar(config: FutarClientConfig): BkkFutar {
  const client = createClient(config)

  return {
    alerts: createAlertsModule(client),
    arrivals: createArrivalsModule(client),
    bicycles: createBicyclesModule(client),
    booking: createBookingModule(client),
    metadata: createMetadataModule(client),
    onboard: createOnboardModule(client),
    planning: createPlanningModule(client),
    references: createReferencesModule(client),
    routes: createRoutesModule(client),
    schedule: createScheduleModule(client),
    search: createSearchModule(client),
    statistics: createStatisticsModule(client),
    stops: createStopsModule(client),
    ticketing: createTicketingModule(client),
    trips: createTripsModule(client),
    vehicles: createVehiclesModule(client),
  }
}
