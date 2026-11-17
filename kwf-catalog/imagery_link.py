from __future__ import annotations

import json
from pathlib import Path


def write_imagery_link(
    export_directory: Path,
    imagery_id: str,
    file_uri: str,
    output: Path,
):
    provenance = json.loads(
        (export_directory / "gcp_export.json").read_text(encoding="utf-8")
    )
    export_id = provenance.get("exportId") or provenance.get("export_id")
    if not export_id:
        raise ValueError("GCP export has no permanent export ID")
    if not imagery_id or not file_uri:
        raise ValueError("Imagery ID and file URI are required")

    document = {
        "schemaVersion": 1,
        "imagery": {
            "id": imagery_id,
            "file_uri": file_uri,
            "gcp_export_id": export_id,
        },
        "gcp_provenance": provenance,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return output
