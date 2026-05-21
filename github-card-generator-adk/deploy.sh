#!/bin/bash
# deploy.sh — Deploy GitHub Dev Card Generator to Google Cloud Run
# Usage: ./deploy.sh [GCP_PROJECT_ID] [GEMINI_API_KEY]
# Or set env vars: GCP_PROJECT, GEMINI_API_KEY

set -euo pipefail

GCP_PROJECT="${1:-${GOOGLE_CLOUD_PROJECT:-}}"
GEMINI_KEY="${2:-${GEMINI_API_KEY:-}}"
REGION="us-central1"

if [[ -z "$GCP_PROJECT" ]]; then
  echo "❌ GCP project ID required. Pass as arg or set GOOGLE_CLOUD_PROJECT."
  exit 1
fi

if [[ -z "$GEMINI_KEY" ]]; then
  echo "❌ Gemini API key required. Pass as arg or set GEMINI_API_KEY."
  exit 1
fi

echo "🚀 Deploying GitHub Dev Card Generator"
echo "   Project: $GCP_PROJECT"
echo "   Region:  $REGION"
echo ""

# ── Step 1: Deploy backend ─────────────────────────────────────────────────
echo "📦 Deploying backend service..."
BACKEND_URL=$(gcloud run deploy github-card-backend \
  --source ./backend \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${GCP_PROJECT},GEMINI_API_KEY=${GEMINI_KEY}" \
  --project "$GCP_PROJECT" \
  --format "value(status.url)" \
  2>&1 | tail -1)

echo "✅ Backend deployed: $BACKEND_URL"

# ── Step 2: Verify backend health ─────────────────────────────────────────
echo ""
echo "🩺 Checking backend health..."
sleep 5
HEALTH=$(curl -sf "${BACKEND_URL}/health" || echo '{"status":"error"}')
echo "   Health response: $HEALTH"

# ── Step 3: Deploy frontend ────────────────────────────────────────────────
echo ""
echo "🎨 Deploying frontend service..."
FRONTEND_URL=$(gcloud run deploy github-card-frontend \
  --source ./frontend \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --port 80 \
  --memory 256Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars "BACKEND_URL=${BACKEND_URL}" \
  --project "$GCP_PROJECT" \
  --format "value(status.url)" \
  2>&1 | tail -1)

echo "✅ Frontend deployed: $FRONTEND_URL"

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
echo "🎉 Deployment complete!"
echo ""
echo "  Backend:  $BACKEND_URL"
echo "  Frontend: $FRONTEND_URL"
echo "  Docs:     ${BACKEND_URL}/docs"
echo "  Health:   ${BACKEND_URL}/health"
echo "════════════════════════════════════════"
