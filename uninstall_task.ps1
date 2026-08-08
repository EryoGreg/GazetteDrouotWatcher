# Removes the "GazetteDrouotWatcher" scheduled task registered by install_task.ps1.
# Does not touch state/, logs/, or any project files — only the Task Scheduler entry.

$TaskName = "GazetteDrouotWatcher"

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $existing) {
    Write-Host "No '$TaskName' task is registered - nothing to do."
    exit 0
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
Write-Host "Removed task '$TaskName'. The watcher will no longer run automatically."
Write-Host "Re-run install_task.ps1 any time to set it up again."
