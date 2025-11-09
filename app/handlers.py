import json
from typing import Any, Dict, List
import boto3
from boto3.dynamodb.conditions import Key

from .models import CreateImageRequest, now_iso
from .utils import response, new_ids, table, bucket, presign_ttl, s3

ddb_table = table()

# --- POST /images ---
def create_image(event, context):
    try:
        body = json.loads(event.get("body") or "{}")
        req = CreateImageRequest.from_json(body)
        image_id, object_key = new_ids(req.user_id)

        item = {
            "image_id": image_id,
            "user_id": req.user_id,
            "bucket": bucket(),
            "object_key": object_key,
            "content_type": req.content_type,
            "title": req.title,
            "description": req.description,
            "tags": req.tags,
            "status": "PENDING",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        ddb_table.put_item(Item=item)

        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": bucket(),
                "Key": object_key,
                "ContentType": req.content_type,
            },
            ExpiresIn=presign_ttl(),
        )
        return response(201, {
            "image_id": image_id,
            "upload_url": url,
            "object_key": object_key,
            "expires_in": presign_ttl(),
        })
    except ValueError as ve:
        return response(400, {"message": str(ve)})
    except Exception as e:
        return response(500, {"message": "Internal server error"})

# --- GET /images ---
def list_images(event, context):
    params = event.get("queryStringParameters") or {}
    user_id = params.get("user_id")
    if not user_id:
        return response(400, {"message": "'user_id' query parameter is required"})

    created_from = params.get("created_from")
    created_to = params.get("created_to")
    tag = params.get("tag")
    limit = int(params.get("limit") or 50)

    index_name = "GSI1"
    key_cond = Key("user_id").eq(user_id)
    if created_from or created_to:
        if created_from and created_to:
            key_cond = key_cond & Key("created_at").between(created_from, created_to)
        elif created_from:
            key_cond = key_cond & Key("created_at").gte(created_from)
        else:
            key_cond = key_cond & Key("created_at").lte(created_to)

    resp = ddb_table.query(
        IndexName=index_name,
        KeyConditionExpression=key_cond,
        Limit=limit,
        ScanIndexForward=False,
        ProjectionExpression="#id, user_id, title, tags, created_at",
        ExpressionAttributeNames={"#id": "image_id"},
    )

    items: List[Dict[str, Any]] = resp.get("Items", [])
    if tag:
        items = [it for it in items if tag in (it.get("tags") or [])]

    return response(200, {"items": items, "next_token": resp.get("LastEvaluatedKey")})

# --- GET /images/{image_id} ---
def get_image(event, context):
    image_id = (event.get("pathParameters") or {}).get("image_id")
    if not image_id:
        return response(400, {"message": "Missing path parameter 'image_id'"})

    resp = ddb_table.get_item(Key={"image_id": image_id})
    item = resp.get("Item")
    if not item:
        return response(404, {"message": "Image not found"})

    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": item["bucket"], "Key": item["object_key"]},
        ExpiresIn=presign_ttl(),
    )
    meta = {
        "content_type": item.get("content_type"),
        "title": item.get("title"),
        "description": item.get("description"),
        "tags": item.get("tags"),
        "created_at": item.get("created_at"),
        "status": item.get("status"),
    }
    return response(200, {"image_id": image_id, "download_url": url, "expires_in": presign_ttl(), "metadata": meta})

# --- DELETE /images/{image_id} ---
def delete_image(event, context):
    image_id = (event.get("pathParameters") or {}).get("image_id")
    if not image_id:
        return response(400, {"message": "Missing path parameter 'image_id'"})

    resp = ddb_table.get_item(Key={"image_id": image_id})
    item = resp.get("Item")
    if not item:
        return response(404, {"message": "Image not found"})

    s3.delete_object(Bucket=item["bucket"], Key=item["object_key"])
    ddb_table.delete_item(Key={"image_id": image_id})

    return response(204)
