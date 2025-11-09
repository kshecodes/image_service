
from .utils import table

ddb_table = table()

def mark_available(event, context):
    # S3 Put event - update item status to AVAILABLE when object appears
    # Object key looks like images/{user}/{image_id}
    for rec in event.get("Records", []):
        key = rec.get("s3", {}).get("object", {}).get("key")
        if not key:
            continue
        try:

            image_id = key.split("/")[-1]
            ddb_table.update_item(
                Key={"image_id": image_id},
                UpdateExpression="SET #s = :avail",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":avail": "AVAILABLE"},
            )
        except Exception as e:
            # Best-effort; do not raise to avoid retry storms
            print(f"Failed to update status for key={key}: {e}")
    return {"ok": True}
