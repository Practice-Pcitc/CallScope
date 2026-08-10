param(
    [string]$PythonPath = "",
    [string]$CodexHomePath = "$env:USERPROFILE\.codex"
)

$ErrorActionPreference = "Stop"
$HookRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $HookRoot
$HookScript = Join-Path $HookRoot "prompt_hook.py"
$WindowsLauncher = Join-Path $HookRoot "run_prompt_hook.cmd"

if (-not $PythonPath) {
    $Candidate = Join-Path $ProjectRoot "backend\.venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $Candidate) {
        $PythonPath = $Candidate
    } else {
        $PythonPath = (Get-Command python -ErrorAction Stop).Source
    }
}

$HooksPath = Join-Path $CodexHomePath "hooks.json"
New-Item -ItemType Directory -Force -Path $CodexHomePath | Out-Null

$Handler = [ordered]@{
    type = "command"
    command = "python `"$HookScript`""
    commandWindows = "cmd.exe /d /s /c $WindowsLauncher"
    timeout = 3
}
$Group = [ordered]@{ hooks = @($Handler) }

if (Test-Path -LiteralPath $HooksPath) {
    Copy-Item -LiteralPath $HooksPath -Destination "$HooksPath.bak" -Force
    $ExistingJson = [System.IO.File]::ReadAllText($HooksPath, [System.Text.Encoding]::UTF8)
    $Document = $ExistingJson | ConvertFrom-Json
} else {
    $Document = [pscustomobject][ordered]@{
        description = "Local Codex lifecycle hooks"
        hooks = [pscustomobject]@{}
    }
}

if (-not $Document.hooks) {
    $Document | Add-Member -NotePropertyName hooks -NotePropertyValue ([pscustomobject]@{})
}
@("SessionStart", "UserPromptSubmit", "PostToolUse", "SessionEnd") | ForEach-Object {
    $Document.hooks | Add-Member -NotePropertyName $_ -NotePropertyValue @($Group) -Force
}
$Json = $Document | ConvertTo-Json -Depth 12
$Utf8WithoutBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($HooksPath, $Json, $Utf8WithoutBom)

Write-Output "Installed CallScope lifecycle hooks: $HooksPath"
Write-Output "Events: SessionStart, UserPromptSubmit, PostToolUse, SessionEnd"
Write-Output "Previous configuration backup: $HooksPath.bak"
Write-Output "Open /hooks in Codex and trust the new hook definition before testing."
