param(
    [switch]$SessionOnly,
    [string]$Model = "deepseek-chat"
)

$ErrorActionPreference = "Stop"

$baseUrl = "https://api.deepseek.com/v1"
$secureKey = Read-Host -Prompt "Enter DeepSeek API key" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)

try {
    $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
    if ([string]::IsNullOrWhiteSpace($apiKey)) {
        throw "API key cannot be empty."
    }

    [Environment]::SetEnvironmentVariable("WORKER_API_KEY", $apiKey, "Process")
    [Environment]::SetEnvironmentVariable("WORKER_BASE_URL", $baseUrl, "Process")
    [Environment]::SetEnvironmentVariable("WORKER_MODEL", $Model, "Process")

    if (-not $SessionOnly) {
        [Environment]::SetEnvironmentVariable("WORKER_API_KEY", $apiKey, "User")
        [Environment]::SetEnvironmentVariable("WORKER_BASE_URL", $baseUrl, "User")
        [Environment]::SetEnvironmentVariable("WORKER_MODEL", $Model, "User")
    }
}
finally {
    if ($bstr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

Write-Host ""
Write-Host "DeepSeek worker configuration saved."
Write-Host "Scope: $(if ($SessionOnly) { 'current PowerShell session only' } else { 'current session and Windows user environment' })"
Write-Host "WORKER_BASE_URL=$baseUrl"
Write-Host "WORKER_MODEL=$Model"
Write-Host "WORKER_API_KEY is set, but not printed."
Write-Host ""
Write-Host "If saved to the Windows user environment, restart Codex and new terminals to pick it up."

