# KWF original asset service

This service issues short-lived S3-compatible upload and download URLs. It
requires HTTPS at its deployment boundary and does not store S3 credentials in
Field Atlas.

Set `KWF_ASSET_BUCKET`, `KWF_ASSET_SERVICE_TOKEN`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, and `AWS_DEFAULT_REGION` in the service environment.
`KWF_S3_ENDPOINT` is optional for compatible non-AWS storage, and
`KWF_ASSET_MAX_BYTES` defaults to 100 MB. Never commit these values or embed
the service token in an application build.

Run locally with:

```powershell
python -m pip install -r kwf-assets/requirements.txt
python -m uvicorn server:app --app-dir kwf-assets
```

The shared service token is suitable only for a controlled internal deployment.
Multi-user or multi-project deployments need project-scoped authorization.
The `complete` endpoint checks object metadata and byte count; it does not
re-download and independently recompute the asset checksum.
