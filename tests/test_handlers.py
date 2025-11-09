import json
import os
import pytest
from moto import mock_aws
import boto3

os.environ["IMAGES_TABLE"] = "Images"
os.environ["IMAGES_BUCKET"] = "test-bucket"
os.environ["PRESIGN_TTL_SECONDS"] = "60"

from app.handlers import create_image, list_images, get_image, delete_image
from app.s3_event_handler import mark_available

@mock_aws
@pytest.fixture(autouse=True)
def _aws_setup():
    # S3
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=os.environ["IMAGES_BUCKET"])

    # DynamoDB
    ddb = boto3.client("dynamodb", region_name="us-east-1")
    ddb.create_table(
        TableName=os.environ["IMAGES_TABLE"],
        AttributeDefinitions=[
            {"AttributeName": "image_id", "AttributeType": "S"},
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        KeySchema=[{"AttributeName": "image_id", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[{
            "IndexName": "GSI1",
            "KeySchema": [
                {"AttributeName": "user_id", "KeyType": "HASH"},
                {"AttributeName": "created_at", "KeyType": "RANGE"},
            ],
            "Projection": {"ProjectionType": "ALL"},
            "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
        }],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
    )
    yield

def _post(body: dict):
    return {"body": json.dumps(body)}

def _get(qs: dict):
    return {"queryStringParameters": qs}

def _path(image_id: str):
    return {"pathParameters": {"image_id": image_id}}

def test_create_image_success():
    evt = _post({
        "user_id": "u1",
        "content_type": "image/png",
        "title": "t",
        "tags": ["a", "b"]
    })
    res = create_image(evt, None)
    assert res["statusCode"] == 201
    body = json.loads(res["body"])
    assert "upload_url" in body
    assert body["expires_in"] == 60

def test_create_image_missing_fields():
    res = create_image(_post({"user_id": "u1"}), None)
    assert res["statusCode"] == 400

def test_list_get_delete_and_s3_event_flow():
    r1 = create_image(_post({"user_id": "u2", "content_type": "image/jpeg", "tags": ["sunset"]}), None)
    assert r1["statusCode"] == 201
    img1 = json.loads(r1["body"])["image_id"]

    r2 = create_image(_post({"user_id": "u2", "content_type": "image/jpeg", "tags": ["city"]}), None)
    assert r2["statusCode"] == 201
    img2 = json.loads(r2["body"])["image_id"]

    # Simulate S3 event for img1 to mark AVAILABLE
    event = {"Records": [{"s3": {"object": {"key": f"images/u2/{img1}"}}}]} 
    mark_available(event, None)

    # list by user
    res = list_images(_get({"user_id": "u2"}), None)
    assert res["statusCode"] == 200
    items = json.loads(res["body"])["items"]
    assert len(items) == 2

    # list with tag filter
    res = list_images(_get({"user_id": "u2", "tag": "sunset"}), None)
    items = json.loads(res["body"])["items"]
    assert len(items) == 1

    # get single
    res = get_image(_path(img1), None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["image_id"] == img1
    assert "download_url" in body

    # delete
    res = delete_image(_path(img1), None)
    assert res["statusCode"] == 204

    # get after delete
    res = get_image(_path(img1), None)
    assert res["statusCode"] == 404

def test_list_requires_user_id():
    res = list_images(_get({}), None)
    assert res["statusCode"] == 400
