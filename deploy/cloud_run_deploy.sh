#!/bin/bash
# Cloud Run deployment for MatRes
# Run from project root: bash deploy/cloud_run_deploy.sh
set -e

PROJECT_ID="materials-resilience-agent"
REGION="us-central1"
SERVICE="matres"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE}"

# Only regenerate parquets if missing — avoids overwriting good data on bad network
PARQUETS=(data/usgs_mcs_2025.parquet data/materials_project_battery.parquet data/nhtsa_ev_recalls.parquet data/oec_flows.parquet)
MISSING=0
for f in "${PARQUETS[@]}"; do [[ ! -f "$f" ]] && MISSING=1 && break; done

if [[ $MISSING -eq 1 ]]; then
  echo "==> Regenerating missing data parquets..."
  venv/bin/python data/ingest_usgs.py
  venv/bin/python data/ingest_materials_project.py
  venv/bin/python data/ingest_nhtsa.py
  venv/bin/python data/ingest_oec.py
else
  echo "==> Data parquets already present — skipping ingest."
fi

echo "==> Building and pushing image..."
gcloud builds submit --config cloudbuild.yaml --project "${PROJECT_ID}"

echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300 \
  --set-env-vars "GEMINI_API_KEY=$(grep GEMINI_API_KEY .env | cut -d= -f2),MATERIALS_PROJECT_API_KEY=$(grep MATERIALS_PROJECT_API_KEY .env | cut -d= -f2),GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --project "${PROJECT_ID}"

echo "==> Done. Service URL:"
gcloud run services describe "${SERVICE}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format "value(status.url)"
