# Регистрирует ежевечернюю задачу в Windows Task Scheduler для автономного написания ВКР.
# Запускать ОДИН РАЗ от обычного пользователя (не админ — задача будет в его контексте).
#
# Что делает:
# - Создаёт задачу с триггером 22:00 ежедневно
# - Action: запускает claude CLI с wake-up-prompt.txt из этого репо
# - Working dir: D:\model-forge
# - Если ноут спал в 22:00 — задача запустится при следующем включении (StartWhenAvailable)
#
# Как удалить задачу:
#   Unregister-ScheduledTask -TaskName "Diploma Auto-Write" -Confirm:$false

param(
  [string]$RepoPath = "D:\model-forge",
  [string]$TaskName = "Diploma Auto-Write",
  [string]$Time     = "22:00",
  [string]$ClaudeExe = "$env:LOCALAPPDATA\AnthropicClaude\Claude.exe"
  # ↑ актуальный путь к claude CLI на твоей машине. Уточни через `where claude` если другой.
)

$WakeUpPrompt = Join-Path $RepoPath "diploma\scripts\wake-up-prompt.txt"

if (-not (Test-Path $WakeUpPrompt)) {
  Write-Error "Не найден wake-up prompt: $WakeUpPrompt"
  exit 1
}

if (-not (Test-Path $ClaudeExe)) {
  Write-Warning "Claude CLI не найден по пути $ClaudeExe — задача будет создана, но возможно потребует правки Action.Path."
}

# Команда: cmd.exe запускает claude с promptом из файла, в нужной рабочей директории.
# Используем PowerShell-обёртку для надёжности кодировки UTF-8 prompt-файла на Windows.
$Action = New-ScheduledTaskAction `
  -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"`$prompt = Get-Content -Raw -Encoding UTF8 '$WakeUpPrompt'; & '$ClaudeExe' --dangerously-skip-permissions -p `$prompt`"" `
  -WorkingDirectory $RepoPath

# Триггер: ежедневно в 22:00, с включённым "запустить если пропустили"
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Trigger.StartBoundary = ([datetime]::Today.AddHours(22)).ToString("yyyy-MM-ddTHH:mm:ss")

# Settings: запускать если пропустили, не блокировать на network/idle, лимит 30 минут
$Settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -DontStopOnIdleEnd `
  -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
  -RestartCount 1 `
  -RestartInterval (New-TimeSpan -Minutes 5)

# Регистрация
Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description "Автономное написание ВКР: каждый вечер пишет одну секцию диплома и делает атомарный коммит. Подробности: $RepoPath\diploma\CLAUDE.md" `
  -Force

Write-Host ""
Write-Host "Задача '$TaskName' зарегистрирована."
Write-Host "Триггер: ежедневно в $Time."
Write-Host ""
Write-Host "Чтобы прогнать прямо сейчас (для проверки):"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Чтобы посмотреть статус:"
Write-Host "  Get-ScheduledTaskInfo -TaskName '$TaskName'"
Write-Host ""
Write-Host "Чтобы удалить:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
