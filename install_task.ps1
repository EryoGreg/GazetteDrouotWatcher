# Registers/updates the "GazetteDrouotWatcher" scheduled task.
#
# The poll interval is NOT hardcoded here — it's read live from
# gazette_watcher/config.py (POLL_INTERVAL_MINUTES) below, so that file
# stays the single place to control everything about how this app behaves.
# Re-run this script any time (e.g. after changing POLL_INTERVAL_MINUTES) to
# update the already-registered task with the new settings.

$TaskName = "GazetteDrouotWatcher"
$ProjectDir = $PSScriptRoot
$PythonExe = "C:\Python314\pythonw.exe"

if (-not (Test-Path $PythonExe)) {
    throw "pythonw.exe not found at $PythonExe. Edit install_task.ps1 with the correct path (must match the Python install that has playwright/win11toast)."
}

# Ask config.py itself for the interval, rather than duplicating the number
# here where it could drift out of sync with what the app is actually set to.
# Note: uses python.exe (not pythonw.exe) for this one read-only call —
# pythonw has no console attached, so PowerShell can't capture its output.
$PythonConsoleExe = $PythonExe -replace "pythonw\.exe$", "python.exe"
$IntervalMinutes = & $PythonConsoleExe -c "import sys; sys.path.insert(0, r'$ProjectDir'); from gazette_watcher import config; print(config.POLL_INTERVAL_MINUTES)"
if (-not $IntervalMinutes -or -not ($IntervalMinutes -as [int])) {
    throw "Couldn't read POLL_INTERVAL_MINUTES from gazette_watcher/config.py (got: '$IntervalMinutes')"
}
$IntervalMinutes = [int]$IntervalMinutes

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "-m gazette_watcher.watcher" `
    -WorkingDirectory $ProjectDir

# "Run once now, then repeat every $IntervalMinutes minutes, indefinitely"
# — RepetitionDuration can't be set to [TimeSpan]::MaxValue (Task Scheduler
# rejects that as an out-of-range duration), so 10 years stands in for
# "forever" instead.
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)).Repetition

$Settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Force -ErrorAction Stop

Write-Host "Registered task '$TaskName': runs every $IntervalMinutes min while logged on."
Write-Host "Working dir: $ProjectDir"
Write-Host "Python: $PythonExe"
Write-Host ""
Write-Host "To run it once immediately for testing:"
Write-Host "  Start-ScheduledTask -TaskName $TaskName"
Write-Host "To remove it later:"
Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
