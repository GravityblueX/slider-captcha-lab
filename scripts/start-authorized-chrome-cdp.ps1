param(
    [int]$Port = 9222,
    [string]$UserDataDir = "",
    [string]$Url = "about:blank"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $UserDataDir) {
    $UserDataDir = Join-Path $root ".liuhen\chrome-cdp-profile"
}

$candidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LocalAppData\Google\Chrome\Application\chrome.exe"
) | Where-Object { $_ -and (Test-Path $_) }

if (-not $candidates) {
    throw "Chrome executable not found. Please install Google Chrome or pass a custom command manually."
}

New-Item -ItemType Directory -Force -Path $UserDataDir | Out-Null
$chrome = $candidates[0]
$args = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$UserDataDir",
    "--no-first-run",
    "--no-default-browser-check",
    $Url
)

Write-Host "Starting authorized Chrome CDP session..."
Write-Host "Chrome: $chrome"
Write-Host "Endpoint: http://127.0.0.1:$Port"
Write-Host "User data: $UserDataDir"
Start-Process -FilePath $chrome -ArgumentList $args -WindowStyle Normal
