from __future__ import annotations

import math
from dataclasses import dataclass

from pyproj import CRS
from pyproj.crs import CompoundCRS
from pyproj.transformer import TransformerGroup


@dataclass
class TransformedControlPoint:
    x: float
    y: float
    z: float
    output_epoch: float | None
    description: str
    operation_accuracy_m: float | None
    grids: list[dict]


def finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def full_crs(horizontal_definition, height_reference):
    horizontal = CRS.from_user_input(horizontal_definition)
    if horizontal.is_compound:
        raise ValueError("Provide separate horizontal and vertical CRS definitions")

    if height_reference == "ellipsoidal":
        return horizontal.to_3d()
    if not height_reference or height_reference == "unknown":
        raise ValueError("Known height reference is required")

    vertical = CRS.from_user_input(height_reference)
    if not vertical.is_vertical:
        raise ValueError("Height reference must be a vertical CRS")
    return CompoundCRS(
        name=f"{horizontal.name} + {vertical.name}",
        components=[horizontal, vertical],
    )


def transform_control_point(
    vertex: dict,
    target_horizontal,
    target_height_reference: str,
    source_definition=None,
    source_height_reference=None,
) -> TransformedControlPoint:
    source = full_crs(
        source_definition or vertex["crs"],
        source_height_reference or vertex.get("vcrs"),
    )
    target = full_crs(target_horizontal, target_height_reference)
    x = finite_number(vertex.get("x"), "x")
    y = finite_number(vertex.get("y"), "y")
    z = finite_number(vertex.get("z"), "z")

    epoch = vertex.get("coordinateEpoch")
    if epoch is not None:
        epoch = finite_number(epoch, "Coordinate epoch")
    dynamic_crs = "DYNAMIC[" in source.to_wkt() or "DYNAMIC[" in target.to_wkt()
    if dynamic_crs and epoch is None:
        raise ValueError("Dynamic CRS transformation requires a coordinate epoch")

    group = TransformerGroup(
        source,
        target,
        always_xy=True,
        allow_ballpark=False,
    )
    if not group.best_available:
        missing = sorted({
            grid.short_name
            for operation in group.unavailable_operations
            for grid in operation.grids
            if not grid.available
        })
        raise ValueError(
            "Best 3D transformation unavailable; missing resources: "
            + ", ".join(missing)
        )
    if not group.transformers:
        raise ValueError("No permitted 3D transformation")

    operation = group.transformers[0]
    if epoch is None:
        tx, ty, tz = operation.transform(x, y, z, errcheck=True)
        output_epoch = None
    else:
        transformed = operation.transform(x, y, z, tt=epoch, errcheck=True)
        tx, ty, tz = transformed[:3]
        output_epoch = transformed[3] if len(transformed) > 3 else epoch

    if not all(math.isfinite(value) for value in (tx, ty, tz)):
        raise ValueError("Transformation produced non-finite coordinates")

    grids = []
    for component in operation.operations:
        for grid in component.grids:
            grids.append({
                "name": grid.short_name,
                "available": grid.available,
                "url": grid.url,
                "package": grid.package_name,
            })

    return TransformedControlPoint(
        x=tx,
        y=ty,
        z=tz,
        output_epoch=output_epoch,
        description=operation.description,
        operation_accuracy_m=(
            operation.accuracy if operation.accuracy >= 0 else None
        ),
        grids=grids,
    )


def accuracy_in_output_units(
    horizontal_accuracy_m,
    vertical_accuracy_m,
    target_horizontal,
    target_height_reference,
):
    horizontal = CRS.from_user_input(target_horizontal)
    complete = full_crs(target_horizontal, target_height_reference)
    h_accuracy = finite_number(horizontal_accuracy_m, "Horizontal accuracy")
    v_accuracy = finite_number(vertical_accuracy_m, "Vertical accuracy")
    if h_accuracy < 0 or v_accuracy < 0:
        raise ValueError("Accuracy cannot be negative")

    horizontal_factor = (
        1.0 if horizontal.is_geographic
        else horizontal.axis_info[0].unit_conversion_factor
    )
    vertical_factor = complete.axis_info[2].unit_conversion_factor
    if not horizontal_factor or not vertical_factor:
        raise ValueError("Output units are unavailable")
    return (
        h_accuracy if horizontal.is_geographic else h_accuracy / horizontal_factor,
        v_accuracy / vertical_factor,
    )
