#!/usr/bin/env bash
# Build the ingest image and create or update the two Cloud Run Jobs. Creates billable resources.
#
#   PROJECT=esg-investing-xxxx REGION=asia-east2 scripts/cloud/deploy_jobs.sh
#   gcloud run jobs execute esgx-documents --project "$PROJECT" --region "$REGION"
#   gcloud run jobs execute esgx-emissions --project "$PROJECT" --region "$REGION"
#   gcloud storage rsync -r gs://$BUCKET/processed data/processed     # bring the key figures home
#   .venv/bin/python scripts/ingest_hk_stream.py --steps merge
#
# One-off setup this script expects (see brain/teknik/Molnkörning – Cloud Run Jobs.md):
#   bucket gs://$BUCKET with raw/universe_hsci.parquet and raw/hkex_stock_map.parquet uploaded,
#   secret "moonshot-api-key", service account $SA with storage.objectAdmin on the bucket and
#   secretmanager.secretAccessor on the secret, Artifact Registry repository $REPO.
set -euo pipefail

: "${PROJECT:?set PROJECT to the GCP project id}"
REGION="${REGION:-asia-east2}"            # Hong Kong: closest to HKEXnews
BUCKET="${BUCKET:-$PROJECT-data}"
REPO="${REPO:-esgx}"
SA="${SA:-esgx-jobs@$PROJECT.iam.gserviceaccount.com}"
IMAGE="$REGION-docker.pkg.dev/$PROJECT/$REPO/ingest:$(git rev-parse --short HEAD)"
DOC_TASKS="${DOC_TASKS:-20}"              # shards for the download job
DOC_PARALLEL="${DOC_PARALLEL:-5}"         # x 4 workers each = 20 concurrent downloads from HKEXnews
EM_TASKS="${EM_TASKS:-20}"                # shards for the extraction job
EM_PARALLEL="${EM_PARALLEL:-5}"           # x 2 workers each = 10 concurrent model calls; raise with the Kimi rate limit

gcloud builds submit --project "$PROJECT" --tag "$IMAGE" .

common=(--project "$PROJECT" --region "$REGION" --image "$IMAGE" --service-account "$SA"
        --add-volume "name=data,type=cloud-storage,bucket=$BUCKET"
        --add-volume-mount "volume=data,mount-path=/data"
        --memory 2Gi --cpu 1 --max-retries 2)

gcloud run jobs deploy esgx-documents "${common[@]}" \
  --tasks "$DOC_TASKS" --parallelism "$DOC_PARALLEL" --task-timeout 2h \
  --args="--steps,documents,--index,hsci,--workers,4"

gcloud run jobs deploy esgx-emissions "${common[@]}" \
  --tasks "$EM_TASKS" --parallelism "$EM_PARALLEL" --task-timeout 3h \
  --set-secrets "MOONSHOT_API_KEY=moonshot-api-key:latest" \
  --args="--steps,emissions,--index,hsci,--workers,2"
