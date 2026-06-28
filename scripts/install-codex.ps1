param(
    [ValidateSet("deepseek", "kimi", "ollama", "custom")]
    [string]$Provider = "deepseek",
    [string]$BaseUrl = "",
    [string]$Model = "",
    [string]$ApiKey = "",
    [string]$VenvPath = ".venv",
    [switch]$SkipAgentRules,
    [switch]$SessionOnly,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
    $scriptDir = Split-Path -Parent $PSCommandPath
    return (Resolve-Path -LiteralPath (Join-Path $scriptDir "..")).Path
}

function Get-ProviderDefaults {
    param([string]$Name)

    switch ($Name) {
        "deepseek" {
            return @{
                BaseUrl = "https://api.deepseek.com/v1"
                Model = "deepseek-chat"
                ApiKeyLabel = "DeepSeek API key"
                ApiKeyDefault = ""
            }
        }
        "kimi" {
            return @{
                BaseUrl = "https://api.moonshot.ai/v1"
                Model = "kimi-k2.5"
                ApiKeyLabel = "Moonshot/Kimi API key"
                ApiKeyDefault = ""
            }
        }
        "ollama" {
            return @{
                BaseUrl = "http://localhost:11434/v1"
                Model = "qwen2.5-coder:14b"
                ApiKeyLabel = "Ollama API key placeholder"
                ApiKeyDefault = "local"
            }
        }
        default {
            return @{
                BaseUrl = ""
                Model = ""
                ApiKeyLabel = "Worker API key"
                ApiKeyDefault = ""
            }
        }
    }
}

function Read-SecretValue {
    param([string]$Prompt)

    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    }
    finally {
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
    }
}

function Get-ExistingWorkerApiKey {
    $processKey = [Environment]::GetEnvironmentVariable("WORKER_API_KEY", "Process")
    if (-not [string]::IsNullOrWhiteSpace($processKey)) {
        return $processKey
    }

    $userKey = [Environment]::GetEnvironmentVariable("WORKER_API_KEY", "User")
    if (-not [string]::IsNullOrWhiteSpace($userKey)) {
        return $userKey
    }

    return ""
}

function Set-WorkerEnv {
    param(
        [string]$Key,
        [string]$Url,
        [string]$ModelName,
        [bool]$ProcessOnly
    )

    [Environment]::SetEnvironmentVariable("WORKER_API_KEY", $Key, "Process")
    [Environment]::SetEnvironmentVariable("WORKER_BASE_URL", $Url, "Process")
    [Environment]::SetEnvironmentVariable("WORKER_MODEL", $ModelName, "Process")

    if (-not $ProcessOnly) {
        [Environment]::SetEnvironmentVariable("WORKER_API_KEY", $Key, "User")
        [Environment]::SetEnvironmentVariable("WORKER_BASE_URL", $Url, "User")
        [Environment]::SetEnvironmentVariable("WORKER_MODEL", $ModelName, "User")
    }
}

function Add-UserPath {
    param([string]$PathToAdd)

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @()
    if ($userPath) {
        $parts = $userPath -split ";" | Where-Object { $_ }
    }
    if ($parts -notcontains $PathToAdd) {
        [Environment]::SetEnvironmentVariable("Path", (($parts + $PathToAdd) -join ";"), "User")
    }
    if (($env:Path -split ";") -notcontains $PathToAdd) {
        $env:Path = "$env:Path;$PathToAdd"
    }
}

function Install-AgentRules {
    param([string]$RepoRoot)

    $codexHome = Join-Path $env:USERPROFILE ".codex"
    New-Item -ItemType Directory -Force -Path $codexHome | Out-Null
    $agentsPath = Join-Path $codexHome "AGENTS.md"

    $block = @"

<!-- codex-cheap-worker:start -->
## Cheap Worker Delegation

Use the Codex Cheap Worker tools when a task is mostly bulk reading, focused extraction, summarization, impact analysis, or boilerplate drafting.

Preferred commands:

ask-worker --paths <files...> --question "<focused question>"
draft-worker --context <reference-files...> --target <target-file> --spec "<draft spec>"

Delegate to ask-worker before reading raw files directly when:

- a task requires reading files over roughly 400 lines;
- a task requires scanning 3 or more files;
- the user asks for inventories, summaries, endpoint lists, exported API lists, documentation deltas, or cross-file mapping;
- entering an unfamiliar repository and the relevant files are unknown;
- a feature request may span multiple modules and Codex needs a project map first;
- estimating blast radius before changing an API, schema, function, route, or shared utility;
- finding call sites, references, routes, tests, config files, or documentation related to a change;
- comparing docs with source code to detect stale documentation;
- summarizing logs, generated reports, or long command outputs before deciding what to inspect;
- learning test style from existing tests before drafting new tests;
- preparing changelog, release notes, PR descriptions, or migration notes from multiple files or diffs;
- the worker can return a concise summary that Codex can verify.

Use draft-worker for boilerplate drafts such as tests, docs, config files, repetitive adapters, wrappers, changelog entries, release notes, PR descriptions, or migration notes. By default it writes drafts under .worker-drafts/; review the draft before applying it to source files.

Do not delegate architecture decisions, subtle debugging, security-sensitive code, files likely to contain secrets, small tasks under roughly 2,000 tokens, or exact line-by-line edits unless ask-worker --line-numbers is used first to narrow the area.

Treat worker output as a fast assistant, not source of truth. After receiving worker output, read the smallest relevant original files before editing. Do not edit code based only on worker summaries.
<!-- codex-cheap-worker:end -->
"@

    $existing = ""
    if (Test-Path -LiteralPath $agentsPath) {
        $existing = Get-Content -LiteralPath $agentsPath -Raw
    }

    $pattern = "(?s)<!-- codex-cheap-worker:start -->.*?<!-- codex-cheap-worker:end -->"
    if ($existing -match $pattern) {
        $updated = [regex]::Replace($existing, $pattern, $block.Trim())
    }
    elseif ([string]::IsNullOrWhiteSpace($existing)) {
        $updated = "# Global Codex Preferences`n$block"
    }
    else {
        $updated = $existing.TrimEnd() + "`n" + $block
    }

    Set-Content -LiteralPath $agentsPath -Value $updated -Encoding UTF8
    return $agentsPath
}

$repoRoot = Resolve-RepoRoot
Set-Location -LiteralPath $repoRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python was not found on PATH. Install Python 3.10+ first."
}

$defaults = Get-ProviderDefaults -Name $Provider
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = $defaults.BaseUrl
}
if ([string]::IsNullOrWhiteSpace($Model)) {
    $Model = $defaults.Model
}
if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = Read-Host -Prompt "OpenAI-compatible base URL"
}
if ([string]::IsNullOrWhiteSpace($Model)) {
    $Model = Read-Host -Prompt "Worker model"
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    if (-not [string]::IsNullOrWhiteSpace($defaults.ApiKeyDefault)) {
        $ApiKey = $defaults.ApiKeyDefault
    }
    elseif (-not [string]::IsNullOrWhiteSpace((Get-ExistingWorkerApiKey))) {
        $ApiKey = Get-ExistingWorkerApiKey
    }
    elseif ($NonInteractive) {
        throw "Missing WORKER_API_KEY. Set it first or pass -ApiKey before running install-codex.ps1 -NonInteractive."
    }
    else {
        $ApiKey = Read-SecretValue -Prompt "Enter $($defaults.ApiKeyLabel)"
    }
}
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    throw "API key cannot be empty for provider '$Provider'."
}

python -m venv $VenvPath
& "$VenvPath\Scripts\python.exe" -m pip install --upgrade pip
& "$VenvPath\Scripts\python.exe" -m pip install -e .

Set-WorkerEnv -Key $ApiKey -Url $BaseUrl -ModelName $Model -ProcessOnly $SessionOnly
Add-UserPath -PathToAdd (Join-Path $repoRoot "bin")

$agentsPath = $null
if (-not $SkipAgentRules) {
    $agentsPath = Install-AgentRules -RepoRoot $repoRoot
}

Write-Host ""
Write-Host "Codex Cheap Worker installed."
Write-Host "Provider: $Provider"
Write-Host "WORKER_BASE_URL=$BaseUrl"
Write-Host "WORKER_MODEL=$Model"
Write-Host "WORKER_API_KEY is set, but not printed."
Write-Host "Command shims were added to the user PATH."
if ($agentsPath) {
    Write-Host "Codex rules: $agentsPath"
}
Write-Host ""
Write-Host "Verify:"
Write-Host "  worker-health"
Write-Host '  ask-worker --paths README.md --question "Summarize this tool in one sentence" --dry-run'
Write-Host ""
Write-Host "Restart Codex so it reloads AGENTS.md and user environment variables."
