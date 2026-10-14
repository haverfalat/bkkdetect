"""Geodesics and metric route geometry delegated to PROJ and GEOS."""

from datetime import datetime
from math import isfinite, remainder

from pyproj import CRS, Geod, Transformer
from shapely.geometry import LineString, Point

GEODESIC = Geod(ellps="WGS84")


def inverse(a, b):
    """Forward bearing, reverse bearing and distance in metres from PROJ."""
    return GEODESIC.inv(a[1], a[0], b[1], b[0])


def distance(a, b):
    return inverse(a, b)[2]


def bearing(a, b):
    return inverse(a, b)[0] % 360


def heading_difference(a, b):
    return abs(remainder(a - b, 360))


def interpolate(a, b, fraction):
    heading, _, length = inverse(a, b)
    lon, lat, _ = GEODESIC.fwd(a[1], a[0], heading, length * fraction)
    return lat, lon


class RouteShape:
    """Cached metric geometry anchored to the actual route's coordinates."""

    def __init__(self, coordinates):
        origin = coordinates[0]
        local = CRS.from_dict(
            {"proj": "aeqd", "lat_0": origin[0], "lon_0": origin[1], "datum": "WGS84", "units": "m"}
        )
        self.transformer = Transformer.from_crs("EPSG:4326", local, always_xy=True)
        self.line = LineString([self.transformer.transform(lon, lat) for lat, lon in coordinates])

    def project(self, position):
        location = Point(*self.transformer.transform(position[1], position[0]))
        return self.line.distance(location), self.line.project(location)


def epoch(value):
    if isinstance(value, datetime):
        return value.timestamp()
    try:
        numeric = float(value)
        return numeric / 1000 if numeric > 1e12 else numeric
    except ValueError, TypeError:
        try:
            parsed = datetime.fromisoformat(str(value))
            return parsed.timestamp() if parsed.tzinfo else float("nan")
        except ValueError:
            return float("nan")


def point(attributes):
    try:
        lat, lon = float(attributes["latitude"]), float(attributes["longitude"])
        if isfinite(lat) and isfinite(lon) and abs(lat) <= 90 and abs(lon) <= 180:
            return lat, lon
    except KeyError, TypeError, ValueError:
        pass
    return None
