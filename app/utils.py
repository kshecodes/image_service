import json
import os
import uuid
from typing import Any, Dict, Tuple
import boto3

s3 = boto3.client("s3")
ddb_resource = boto3.resource("dynamodb")

def env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"Missing environment variable: {name}")
    return val

def response(status: int, body: Dict[str, Any] | None = None, headers: Dict[str, str] | None = None):
    base = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}
    if headers:
        base.update(headers)
    payload = {
        "statusCode": status,
        "headers": base,
    }
    if body is not None:
        payload["body"] = json.dumps(body)
    return payload

def new_ids(user_id: str) -> Tuple[str, str]:
    image_id = str(uuid.uuid4())
    object_key = f"images/{user_id}/{image_id}"
    return image_id, object_key

def table():
    return ddb_resource.Table(env("IMAGES_TABLE"))

def bucket() -> str:
    return env("IMAGES_BUCKET")

def presign_ttl() -> int:
    try:
        return int(os.environ.get("PRESIGN_TTL_SECONDS", "900"))
    except ValueError:
        return 900
