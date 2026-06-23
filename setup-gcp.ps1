#!/usr/bin/env pwsh
# setup-gcp.ps1
# Run this ONCE before your first deployment to configure GCP for Cloud Run.
# Prerequisites: gcloud CLI installed and authenticated as a project owner.

$PROJECT_ID = "empyrean-verve-401907"
$REGION = "us-central1"
$SERVICE_ACCOUNT = "enterprise-data-agent-sa"
$SA_EMAIL = "$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"

Write-Host "`n=== Step 1: Enable required APIs ===" -ForegroundColor Cyan
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    secretmanager.googleapis.com `
    bigquery.googleapis.com `
    containerregistry.googleapis.com `
    --project $PROJECT_ID

Write-Host "`n=== Step 2: Create service account ===" -ForegroundColor Cyan
gcloud iam service-accounts create $SERVICE_ACCOUNT `
    --display-name="Enterprise Data Agent" `
    --project $PROJECT_ID

Write-Host "`n=== Step 3: Grant BigQuery access ===" -ForegroundColor Cyan
gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SA_EMAIL" `
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SA_EMAIL" `
    --role="roles/bigquery.jobUser"

Write-Host "`n=== Step 4: Grant Vertex AI access (for Gemini) ===" -ForegroundColor Cyan
gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SA_EMAIL" `
    --role="roles/aiplatform.user"

Write-Host "`n=== Step 5: Grant Secret Manager access ===" -ForegroundColor Cyan
gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$SA_EMAIL" `
    --role="roles/secretmanager.secretAccessor"

Write-Host "`n=== Step 6: Store gdocs OAuth credentials in Secret Manager ===" -ForegroundColor Cyan
# Path to your local OAuth client secret JSON
$CREDENTIALS_PATH = "C:\Users\phili\OneDrive\Documents\client_secret_135378614576-50c51t22i6nrdmo9497b3rumkaqdj959.apps.googleusercontent.com.json"
# Path to your already-authenticated token.json inside gdocs-mcp
$TOKEN_PATH = "gdocs-mcp\token.json"

gcloud secrets create gdocs-oauth-credentials `
    --data-file=$CREDENTIALS_PATH `
    --project $PROJECT_ID

gcloud secrets create gdocs-oauth-token `
    --data-file=$TOKEN_PATH `
    --project $PROJECT_ID

Write-Host "`n=== Step 7: Grant Cloud Build permission to deploy to Cloud Run ===" -ForegroundColor Cyan
$BUILD_SA = "$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$BUILD_SA" `
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID `
    --member="serviceAccount:$BUILD_SA" `
    --role="roles/iam.serviceAccountUser"

Write-Host "`n=== Step 8: Configure Cloud Run to use the service account ===" -ForegroundColor Cyan
Write-Host "This is handled automatically by cloudbuild.yaml on first deploy." -ForegroundColor Yellow
Write-Host "After deploying, run this to attach the service account:" -ForegroundColor Yellow
Write-Host "  gcloud run services update enterprise-data-agent --service-account $SA_EMAIL --region $REGION" -ForegroundColor White

Write-Host "`n=== Setup complete. Now run: ===" -ForegroundColor Green
Write-Host "  gcloud builds submit --project $PROJECT_ID --config cloudbuild.yaml ." -ForegroundColor White