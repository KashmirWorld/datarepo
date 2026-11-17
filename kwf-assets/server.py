from __future__ import annotations

import os
import re
import secrets

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


BUCKET = os.environ.get("KWF_ASSET_BUCKET")
ACCESS_TOKEN = os.environ.get("KWF_ASSET_SERVICE_TOKEN")
if not BUCKET or not ACCESS_TOKEN:
    raise RuntimeError(
        "Set KWF_ASSET_BUCKET and KWF_ASSET_SERVICE_TOKEN before starting "
        "the KWF asset service."
    )

ENDPOINT = os.environ.get("KWF_S3_ENDPOINT")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
MAX_BYTES = int(os.environ.get("KWF_ASSET_MAX_BYTES", "100000000"))

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    config=Config(signature_version="s3v4"),
)

app = FastAPI(title="KWF original asset service")
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")


def authorized(authorization: str = Header(default="")):
    expected = f"Bearer {ACCESS_TOKEN}"
    if not secrets.compare_digest(authorization, expected):
        raise HTTPException(401, "Invalid asset-service credential")


def identifier(value: str):
    if not IDENTIFIER.fullmatch(value):
        raise HTTPException(400, "Invalid identifier")
    return value


class AssetRequest(BaseModel):
    project_id: str
    asset_id: str
    mime_type: str
    byte_count: int = Field(gt=0)
    sha256: str


def object_key(request: AssetRequest):
    project = identifier(request.project_id)
    asset = identifier(request.asset_id)
    if not SHA256.fullmatch(request.sha256):
        raise HTTPException(400, "Invalid SHA-256")
    if request.mime_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(400, "Unsupported image format")
    if request.byte_count > MAX_BYTES:
        raise HTTPException(413, "Asset exceeds configured size limit")
    extension = "jpg" if request.mime_type == "image/jpeg" else "png"
    return (
        f"projects/{project}/originals/"
        f"{asset}-{request.sha256}.{extension}"
    )


@app.post("/assets/upload", dependencies=[Depends(authorized)])
def upload_url(request: AssetRequest):
    key = object_key(request)
    parameters = {
        "Bucket": BUCKET,
        "Key": key,
        "ContentType": request.mime_type,
        "ContentLength": request.byte_count,
        "Metadata": {
            "sha256": request.sha256,
            "asset-id": request.asset_id,
            "project-id": request.project_id,
        },
    }
    url = s3.generate_presigned_url(
        "put_object",
        Params=parameters,
        ExpiresIn=900,
    )
    return {
        "object_key": key,
        "upload_url": url,
        "headers": {
            "Content-Type": request.mime_type,
            "x-amz-meta-sha256": request.sha256,
            "x-amz-meta-asset-id": request.asset_id,
            "x-amz-meta-project-id": request.project_id,
        },
    }


@app.post("/assets/complete", dependencies=[Depends(authorized)])
def complete_upload(request: AssetRequest):
    key = object_key(request)
    try:
        result = s3.head_object(Bucket=BUCKET, Key=key)
    except ClientError as error:
        raise HTTPException(409, "Asset is not available") from error
    if result["ContentLength"] != request.byte_count:
        raise HTTPException(409, "Stored asset size does not match")
    if result.get("Metadata", {}).get("sha256") != request.sha256:
        raise HTTPException(409, "Stored asset metadata does not match")
    return {
        "object_key": key,
        "byte_count": result["ContentLength"],
        "etag": result.get("ETag"),
    }


@app.get("/assets/download", dependencies=[Depends(authorized)])
def download_url(project_id: str, object_key: str):
    project = identifier(project_id)
    prefix = f"projects/{project}/originals/"
    if not object_key.startswith(prefix) or ".." in object_key:
        raise HTTPException(400, "Asset does not belong to this project path")
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": object_key},
        ExpiresIn=300,
    )
    return {"download_url": url}
