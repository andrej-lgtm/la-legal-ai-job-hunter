# PowerShell script to register daily Windows Task Scheduler job for Legal & AI Job Hunter

$TaskName = "DailyLegalAIJobHunter"
$PythonPath = (Get-Command python).Source
$ScriptPath = "$PSScriptRoot\main.py"
$WorkingDir = "$PSScriptRoot"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Registering Daily Legal & AI Job Hunter Task    " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Check if Task already exists and remove if present
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Removing existing task '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Action: run python main.py --run-now in working directory
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument "main.py --run-now" -WorkingDirectory $WorkingDir

# Trigger: Run daily at 8:00 AM
$Trigger = New-ScheduledTaskTrigger -Daily -At "8:00 AM"

# Settings: Allow wake to run, run missed executions
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register the Scheduled Task
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Daily Legal & AI Job Finder for Los Angeles Metro"

Write-Host "`nTask successfully created!" -ForegroundColor Green
Write-Host "It will automatically run every day at 8:00 AM in the background." -ForegroundColor Green
Write-Host "You can test run it anytime with: python main.py --run-now" -ForegroundColor White
