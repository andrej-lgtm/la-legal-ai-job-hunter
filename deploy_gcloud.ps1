# ☁️ Google Cloud Run & Cloud Scheduler Automated Deployment Script
param (
    [string]$ProjectName = "la-legal-job-hunter",
    [string]$Region = "us-central1",
    [string]$Passcode = "90038"
)

Write-Host "🚀 Starting Google Cloud Run deployment for $ProjectName..." -ForegroundColor Cyan

# 1. Enable required Google Cloud APIs
Write-Host "🔧 Enabling Cloud Run & Cloud Scheduler APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com cloudscheduler.googleapis.com storage.googleapis.com

# 2. Deploy application container to Google Cloud Run
Write-Host "📦 Building and deploying container to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ProjectName `
    --source . `
    --region $Region `
    --allow-unauthenticated `
    --set-env-vars "DASHBOARD_PASSCODE=$Passcode" `
    --memory 1Gi `
    --cpu 1

# 3. Retrieve deployed service URL
$ServiceUrl = (gcloud run services describe $ProjectName --region $Region --format "value(status.url)").Trim()
Write-Host "✅ Deployed successfully to: $ServiceUrl" -ForegroundColor Green

# 4. Create Cloud Scheduler Job (Runs twice daily at 8:00 AM & 5:00 PM PST)
Write-Host "⏰ Creating Cloud Scheduler job (8:00 AM & 5:00 PM PST)..." -ForegroundColor Yellow
gcloud scheduler jobs create http daily-legal-scrape `
    --schedule="0 8,17 * * *" `
    --time-zone="America/Los_Angeles" `
    --uri="$ServiceUrl/api/trigger-scrape" `
    --http-method=POST `
    --location=$Region `
    --description="Triggers daily LA Legal & AI job scrape at 8:00 AM & 5:00 PM PST"

Write-Host "`n🎉 Setup Complete!" -ForegroundColor Green
Write-Host "🌐 Live Website: $ServiceUrl" -ForegroundColor Cyan
Write-Host "🔒 Passcode: $Passcode" -ForegroundColor Magenta
Write-Host "⏰ Auto-Scrapes: 8:00 AM PST & 5:00 PM PST daily" -ForegroundColor Yellow
