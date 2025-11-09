# Serverless Image Service for MontyCloud
### Author: Keerthi Sanal

Tech: API Gateway + Lambda (Python 3.9) + S3 + DynamoDB (SAM)
- Presigned PUT for upload, GET for download
- List with filters (user_id, tag, created_at range)
- S3 event Lambda flips status PENDING -> AVAILABLE after upload
- OpenAPI spec + unit tests (pytest + moto)

## Quick Start

```bash
# 1) Install tools
pip install --upgrade awscli aws-sam-cli

# 2) Build (from this folder)
sam build

# 3) Deploy (guided first time)
sam deploy --guided
# Note: SAM will ask to create S3 bucket for artifacts. Accept defaults.
```

### Environment
The template wires env vars automatically:
- `IMAGES_TABLE` (DynamoDB table)
- `IMAGES_BUCKET` (S3 bucket)
- `PRESIGN_TTL_SECONDS` (default 900)

### Usage (cURL)

```bash
API=$(aws cloudformation describe-stacks --stack-name <YOUR_STACK> \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)

# 1) Create upload request
curl -s -X POST "$API/images" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id":"u123",
    "content_type":"image/jpeg",
    "title":"Beach",
    "tags":["sunset","vacation"]
  }' | tee create.json

IMAGE_ID=$(jq -r .image_id create.json)
UPLOAD_URL=$(jq -r .upload_url create.json)

# 2) Upload file to S3
curl -X PUT "$UPLOAD_URL" -H "Content-Type: image/jpeg" --data-binary @photo.jpg

# 3) Get download URL
curl "$API/images/$IMAGE_ID"

# 4) List with filters
curl "$API/images?user_id=u123&tag=sunset&limit=20"

# 5) Delete
curl -X DELETE "$API/images/$IMAGE_ID"
```

### Run Tests Locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt pytest moto[boto3]
pytest -q
```

### Notes
- Add Cognito/JWT authorizer in `template.yaml` if needed.
- Tighten CORS for production.
- Consider KMS CMKs for S3 and DynamoDB if required.
- Lifecycle rules can archive to Glacier.
