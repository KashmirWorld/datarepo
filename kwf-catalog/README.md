# KWF geospatial catalog

The catalog normalizes immutable Field Atlas snapshots and legacy GeoJSON into
WGS 84 mapping features and GeoParquet. Original coordinates, CRS, dimensional
WKB, observation timestamps, revisions, and asset references remain in the
derived table.

Run the catalog from the repository root:

```powershell
python kwf-catalog/kwf_geo.py normalize
python kwf-catalog/kwf_geo.py export-crs --target-crs EPSG:32615 --output C:\data\observations-utm15.parquet
python kwf-catalog/kwf_geo.py gcps --project-id PROJECT_ID --site-boundary C:\data\site.geojson
```

`export-crs` transforms from stored source geometry and does not put projected
coordinates in GeoJSON. GCP export requires a matching, explicit height
reference for source and target; unavailable non-ballpark vertical operations
are rejected. Target CRS coverage and transformation provenance are validated.

The current Habitat Mapper integration consumes the generated browser dataset;
it requires running normalization after new source batches arrive. The separate
`kwf-assets` service is only a component and is not deployed or connected to the
mobile uploader/viewer. Photo capture and preference-backed storage remain
pilot limitations; this catalog does not claim full-resolution capture,
durable database migration, or production object-storage delivery.
