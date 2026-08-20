# Setup Windows Task Scheduler for LA Legal & AI Job Hunter (Runs at 8:00 AM and 5:00 PM daily)

$TaskName1 = "LALegalJobHunter_Morning"
$TaskName2 = "LALegalJobHunter_Evening"
$ScriptPath = "$PSScriptRoot\main.py"
$PythonPath = (Get-Command python).Source

Write-Host "Creating Task: $TaskName1 (8:00 AM PST)..." -ForegroundColor Cyan
$Action1 = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`" --daily" -WorkingDirectory $PSScriptRoot
$Trigger1 = New-ScheduledTaskTrigger -Daily -At "8:00AM"
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName1 -Action $Action1 -Trigger $Trigger1 -Principal $Principal -Settings $Settings -Force

Write-Host "Creating Task: $TaskName2 (5:00 PM PST)..." -ForegroundColor Cyan
$Action2 = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`" --daily" -WorkingDirectory $PSScriptRoot
$Trigger2 = New-ScheduledTaskTrigger -Daily -At "5:00PM"
Register-ScheduledTask -TaskName $TaskName2 -Action $Action2 -Trigger $Trigger2 -Principal $Principal -Settings $Settings -Force

Write-Host "Scheduled tasks successfully registered for 8:00 AM and 5:00 PM PST daily." -ForegroundColor Green
