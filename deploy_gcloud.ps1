# ☁️ Google Cloud Run & Cloud Scheduler Automated Deployment Script
param (
    [string]$ProjectName = "la-legal-job-hunter",
    [string]$Region = "us-central1",
    [string]$Passcode = "90038"
)

# Ensure gcloud is available in current session PATH
$GcloudBin = "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin"
if (Test-Path $GcloudBin) {
    $env:PATH = "$GcloudBin;$env:PATH"
}

Write-Host "🚀 Starting Google Cloud Run deployment for $ProjectName..." -ForegroundColor Cyan

# 1. Check authentication
$AuthAccount = (gcloud auth list --filter=status:ACTIVE --format="value(account)").Trim()
if (-not $AuthAccount) {
    Write-Host "🔑 Please login to your Google Cloud account in the browser..." -ForegroundColor Yellow
    gcloud auth login
}

# 2. Check or prompt for project
$CurrentProject = (gcloud config get-value project 2>$null).Trim()
if (-not $CurrentProject -or $CurrentProject -eq "(unset)") {
    Write-Host "⚠️ No Google Cloud project selected." -ForegroundColor Yellow
    Write-Host "👉 Please select a project or create one with: gcloud config set project YOUR_PROJECT_ID" -ForegroundColor Yellow
    gcloud projects list
    $SelectedProject = Read-Host "Enter your Google Cloud Project ID"
    if ($SelectedProject) {
        gcloud config set project $SelectedProject
    } else {
        Write-Host "❌ Deployment cancelled: Project ID required." -ForegroundColor Red
        exit 1
    }
}

# 3. Enable required Google Cloud APIs
Write-Host "🔧 Enabling Cloud Run & Cloud Scheduler APIs..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com cloudscheduler.googleapis.com storage.googleapis.com

# 4. Deploy application container to Google Cloud Run
Write-Host "📦 Building and deploying container to Google Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $ProjectName `
    --source . `
    --region $Region `
    --allow-unauthenticated `
    --set-env-vars "DASHBOARD_PASSCODE=$Passcode" `
    --memory 1Gi `
    --cpu 1

# 5. Retrieve deployed service URL
$ServiceUrl = (gcloud run services describe $ProjectName --region $Region --format "value(status.url)").Trim()
Write-Host "✅ Deployed successfully to: $ServiceUrl" -ForegroundColor Green

# 6. Create Cloud Scheduler Job (Runs twice daily at 8:00 AM & 5:00 PM PST)
Write-Host "⏰ Configuring Cloud Scheduler for 8:00 AM & 5:00 PM PST daily..." -ForegroundColor Yellow
gcloud scheduler jobs delete daily-legal-scrape --location=$Region --quiet 2>$null
gcloud scheduler jobs create http daily-legal-scrape `
    --schedule="0 8,17 * * *" `
    --time-zone="America/Los_Angeles" `
    --uri="$ServiceUrl/api/trigger-scrape" `
    --http-method=POST `
    --location=$Region `
    --description="Triggers twice-daily LA Legal & AI job scrape at 8:00 AM & 5:00 PM PST"

Write-Host "`n🎉 Google Cloud Deployment Complete!" -ForegroundColor Green
Write-Host "🌐 Live Google Cloud Website: $ServiceUrl" -ForegroundColor Cyan
Write-Host "🔒 Passcode: $Passcode" -ForegroundColor Magenta
Write-Host "⏰ Auto-Scrapes: 8:00 AM PST & 5:00 PM PST daily" -ForegroundColor Yellow
