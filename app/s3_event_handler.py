import json
import os
import boto3

from .utils import table

ddb_table = table()

def mark_available(event, context):

    for rec in event.get("Records", []):
        key = rec.get("s3", {}).get("object", {}).get("key")
        if not key:
            continue
        try:
            # image_id is last segment
            image_id = key.split("/")[-1]
            ddb_table.update_item(
                Key={"image_id": image_id},
                UpdateExpression="SET #s = :avail",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":avail": "AVAILABLE"},
            )
        except Exception as e:
            print(f"Failed to update status for key={key}: {e}")
    return {"ok": True}
