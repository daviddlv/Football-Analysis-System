#!/bin/sh
gcloud functions deploy video-analyzer \
    --gen2 \
    --runtime=python310 \
    --timeout=60s \
    --project=${PROJECT_ID} \
    --region=us-central1 \
    --memory=12GB \
    --source=. \
    --entry-point=handler \
    --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
    --trigger-event-filters="bucket=${BUCKET_NAME}"
