from __future__ import annotations

from kwf_geo import CAPTURES, DERIVED, catalog_observations, normalize_archive
from spatial_exports import export_target_geoparquet


def observations_frame():
    return catalog_observations()


def export_observations(target_crs, output_path, input_path=None):
    source = input_path or DERIVED / "observations.parquet"
    return export_target_geoparquet(source, output_path, target_crs)


if __name__ == "__main__":
    frame = normalize_archive(CAPTURES, DERIVED)
    print(f"Normalized {len(frame)} observations")
