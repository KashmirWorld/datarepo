from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
from pyproj import CRS
from shapely import from_wkb
from shapely.ops import transform as transform_geometry

from kwf_geo import transformer


def original_wkb(observation: dict) -> bytes:
    vertices = observation.get("vertices")
    if not isinstance(vertices, list) or not vertices:
        raise ValueError("Geometry has no vertices")

    crs_ids = {vertex.get("crs") for vertex in vertices}
    if len(crs_ids) != 1:
        raise ValueError("One geometry cannot mix source CRSs")

    height_references = {vertex.get("vcrs", "unknown") for vertex in vertices}
    preserve_z = (
        len(height_references) == 1
        and "unknown" not in height_references
        and all(vertex.get("z") is not None for vertex in vertices)
    )
    coordinates = [
        (vertex["x"], vertex["y"], vertex["z"])
        if preserve_z
        else (vertex["x"], vertex["y"])
        for vertex in vertices
    ]

    from shapely.geometry import LineString, Point, Polygon

    kind = observation.get("shape")
    if kind == "Point":
        if len(coordinates) != 1:
            raise ValueError("Point requires one vertex")
        geometry = Point(coordinates[0])
    elif kind == "LineString":
        geometry = LineString(coordinates)
    elif kind == "Polygon":
        geometry = Polygon(coordinates)
    else:
        raise ValueError(f"Unsupported shape: {kind}")

    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("Invalid source geometry")
    return geometry.wkb


def export_target_geoparquet(
    input_path: Path,
    output_path: Path,
    target_crs: str,
) -> Path:
    frame = gpd.read_parquet(input_path)
    target = CRS.from_user_input(target_crs)
    if not (target.is_projected or target.is_geographic):
        raise ValueError("Target must be a horizontal CRS")

    geometries = []
    transforms = []
    for _, row in frame.iterrows():
        source = CRS.from_user_input(row["source_crs_wkt"])
        source_geometry = from_wkb(row["source_wkb"])
        operation = transformer(source, target)
        converted = transform_geometry(
            lambda x, y, z=None: operation.transform(x, y, errcheck=True),
            source_geometry,
        )
        if converted.is_empty or not converted.is_valid:
            raise ValueError(f"Invalid target geometry for record {row['id']}")
        geometries.append(converted)
        transforms.append(operation.description)

    output = frame.copy()
    output = output.set_geometry(
        gpd.GeoSeries(geometries, index=frame.index, crs=target),
        crs=target,
    )
    output["export_crs"] = target.to_string()
    output["export_transform_description"] = transforms
    bounds = output.geometry.bounds
    output["min_x"] = bounds["minx"]
    output["min_y"] = bounds["miny"]
    output["max_x"] = bounds["maxx"]
    output["max_y"] = bounds["maxy"]
    centers = output.geometry.centroid
    output["center_x"] = centers.x
    output["center_y"] = centers.y

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(output_path, index=False, schema_version="1.0.0")
    output_path.with_suffix(".export.json").write_text(
        json.dumps({
            "input": str(input_path),
            "targetCrs": target.to_string(),
            "targetWkt": target.to_wkt(),
            "geometryDimensions": 2,
            "sourceGeometryPreserved": True,
            "records": [
                {"id": row["id"], "transformation": transform}
                for (_, row), transform in zip(frame.iterrows(), transforms)
            ],
        }, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return output_path
