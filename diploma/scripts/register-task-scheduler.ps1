# Registers a daily scheduled task for autonomous diploma writing.
# Run ONCE from your normal user account (not admin - task runs in user context).
#
# What it does:
# - Daily trigger at 22:00
# - Action: launches claude CLI with diploma/scripts/wake-up-prompt.txt
# - Working dir: D:\model-forge
# - StartWhenAvailable: if PC slept at 22:00, runs at next wake
#
# To remove later:
#   Unregister-ScheduledTask -TaskName "Diploma Auto-Write" -Confirm:$false

param(
  [string]$RepoPath = "D:\model-forge",
  [string]$TaskName = "Diploma Auto-Write",
  [string]$Time     = "22:00",
  [string]$ClaudeExe = "D:\node-v24.14.0-win-x64\claude.cmd"
)

$WakeUpPrompt = Join-Path $RepoPath "diploma\scripts\wake-up-prompt.txt"

if (-not (Test-Path $WakeUpPrompt)) {
  Write-Error "Wake-up prompt not found: $WakeUpPrompt"
  exit 1
}

if (-not (Test-Path $ClaudeExe)) {
  Write-Warning "Claude CLI not found at $ClaudeExe - task will be created but may need fixing."
}

# PowerShell wrapper reads UTF-8 prompt file and pipes to claude CLI.
$PSCommand = "`$prompt = Get-Content -Raw -Encoding UTF8 '$WakeUpPrompt'; & '$ClaudeExe' --dangerously-skip-permissions -p `$prompt"

$Action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"$PSCommand`"" `
  -WorkingDirectory $RepoPath

# Daily at $Time, with "run on next available time if missed" semantics
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

$Settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -DontStopOnIdleEnd `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
  -RestartCount 1 `
  -RestartInterval (New-TimeSpan -Minutes 5)

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description "Autonomous diploma writing - one section per evening, atomic commit. See $RepoPath\diploma\CLAUDE.md" `
  -Force

Write-Host ""
Write-Host "Task '$TaskName' registered successfully."
Write-Host "Daily trigger at $Time."
Write-Host ""
Write-Host "To run NOW (manual test):"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "To check status:"
Write-Host "  Get-ScheduledTaskInfo -TaskName '$TaskName'"
Write-Host ""
Write-Host "To remove:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
