#!/usr/bin/env bash
# Build the app image with Cloud Build and deploy it as one Cloud Run service.
#
#   deploy/cloud-run.sh                 # private: only signed-in project members can call it
#   PUBLIC=1 deploy/cloud-run.sh        # public: anyone with the URL can open the site
#
# Prerequisites: gcloud authenticated, and Cloud Run, Cloud Build and Artifact Registry
# enabled in the project. The image contains the data snapshot from engine/data and
# engine/outputs; no bucket or API key is needed to serve scores and recommendations.
set -euo pipefail

PROJECT="${PROJECT:-esg-investing-erikjin}"
REGION="${REGION:-asia-east2}"
SERVICE="${SERVICE:-green-street}"

access=(--no-allow-unauthenticated)
[[ "${PUBLIC:-0}" == "1" ]] && access=(--allow-unauthenticated)

cd "$(dirname "$0")/.."
gcloud run deploy "$SERVICE" --project "$PROJECT" --region "$REGION" --source . \
  --memory 2Gi --cpu 2 --timeout 120 --concurrency 8 --min-instances 0 --max-instances 2 \
  "${access[@]}"
gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format "value(status.url)"
