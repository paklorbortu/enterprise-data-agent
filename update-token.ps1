#!/usr/bin/env pwsh
# update-token.ps1
# Run this whenever gdocs-mcp/token.json is refreshed locally, to push the
# updated token to Secret Manager so Cloud Run picks it up on next cold start.

$PROJECT_ID = "empyrean-verve-401907"

Write-Host "Updating gdocs-oauth-token in Secret Manager..." -ForegroundColor Cyan

gcloud secrets versions add gdocs-oauth-token `
    --data-file="gdocs-mcp\token.json" `
    --project $PROJECT_ID

Write-Host "Done. The new token version is now :latest." -ForegroundColor Green
Write-Host "Cloud Run will use it on the next cold start or instance restart." -ForegroundColor Yellow