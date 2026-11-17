from __future__ import annotations

from pyproj import CRS
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info


def _site_corners_covered(crs: CRS, bounds):
    area = crs.area_of_use
    if area is None:
        return False
    west, south, east, north = bounds
    longitude_ok = (
        area.west <= west <= east <= area.east
        if area.west <= area.east
        else west >= area.west and east <= area.east
    )
    return longitude_ok and area.south <= south and north <= area.north


def select_target(
    project: dict,
    explicit_horizontal: str | None,
    explicit_vertical: str | None,
    source_horizontal: str,
    site_bounds: tuple[float, float, float, float],
):
    horizontal = explicit_horizontal or project.get("defaultCrs")
    vertical = explicit_vertical or project.get("defaultVcrs")
    if vertical in (None, "", "unknown"):
        raise ValueError("Select a known target height reference")
    if horizontal:
        registry = project.get("crsRegistry", {})
        if isinstance(registry, list):
            registry = {
                entry["id"]: entry
                for entry in registry
                if isinstance(entry, dict) and isinstance(entry.get("id"), str)
            }
        definition = registry.get(horizontal, horizontal)
        if isinstance(definition, dict):
            definition = definition.get("definition")
        target = CRS.from_user_input(definition)
        if not _site_corners_covered(target, site_bounds):
            raise ValueError("Target CRS area of use does not cover the site")
        return horizontal, vertical

    source = CRS.from_user_input(source_horizontal)
    geodetic = source.geodetic_crs
    if geodetic is None:
        raise ValueError("Source geodetic CRS could not be established")
    west, south, east, north = site_bounds
    if east - west > 6 or north - south > 8:
        raise ValueError("Site is too large for automatic local UTM selection")
    center_lon = (west + east) / 2
    center_lat = (south + north) / 2
    if not -80 <= center_lat <= 84:
        raise ValueError("UTM is not appropriate for this latitude")

    candidates = query_utm_crs_info(
        datum_name=geodetic.name,
        area_of_interest=AreaOfInterest(
            west_lon_degree=center_lon,
            south_lat_degree=center_lat,
            east_lon_degree=center_lon,
            north_lat_degree=center_lat,
        ),
    )
    suitable = [
        CRS.from_authority(item.auth_name, item.code)
        for item in candidates
        if _site_corners_covered(
            CRS.from_authority(item.auth_name, item.code), site_bounds
        )
    ]
    if len(suitable) != 1:
        raise ValueError(
            "No unambiguous same-datum UTM target; select one explicitly"
        )
    return suitable[0].to_string(), vertical


def select_metric_crs(source_horizontal: str, site_bounds):
    source = CRS.from_user_input(source_horizontal)
    geodetic = source.geodetic_crs
    if geodetic is None:
        raise ValueError("Source geodetic CRS could not be established")
    west, south, east, north = site_bounds
    center_lon = (west + east) / 2
    center_lat = (south + north) / 2
    candidates = query_utm_crs_info(
        datum_name=geodetic.name,
        area_of_interest=AreaOfInterest(
            west_lon_degree=center_lon,
            south_lat_degree=center_lat,
            east_lon_degree=center_lon,
            north_lat_degree=center_lat,
        ),
    )
    suitable = [
        CRS.from_authority(item.auth_name, item.code)
        for item in candidates
        if _site_corners_covered(
            CRS.from_authority(item.auth_name, item.code), site_bounds
        )
    ]
    if len(suitable) != 1:
        raise ValueError("Could not select an unambiguous local metric CRS")
    return suitable[0].to_string()
