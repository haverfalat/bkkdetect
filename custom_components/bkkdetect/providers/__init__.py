"""Selectable vehicle providers; neither requires an external runtime."""

from ..api import BkkClient
from .mavplusz import MavPluszClient


def create_client(session, options, budget):
    provider = MavPluszClient if options["vehicle_provider"] == "mavplusz" else BkkClient
    return provider(session, options.get("api_key", ""), options, budget)
