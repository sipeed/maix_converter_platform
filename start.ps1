$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ListenHost = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$ListenPort = if ($env:PORT) { [int]$env:PORT } else { 8000 }

$venvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
$legacyVenvPython = Join-Path $RootDir "venv\Scripts\python.exe"
$PythonArgs = @()
if (Test-Path $venvPython) {
    $Python = $venvPython
} elseif (Test-Path $legacyVenvPython) {
    $Python = $legacyVenvPython
} else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $Python = $pythonCommand.Source
    } else {
        $pyCommand = Get-Command py -ErrorAction SilentlyContinue
        if (-not $pyCommand) {
            throw "Python was not found. Install Python 3.11 or activate a conda environment."
        }
        $Python = $pyCommand.Source
        $PythonArgs = @("-3")
    }
}

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$localHosts = @("127.0.0.1", "localhost", "::1")
if ($ListenHost -notin $localHosts -and [string]::IsNullOrWhiteSpace($env:MAIX_API_TOKEN)) {
    $env:MAIX_API_TOKEN = (& $Python @PythonArgs -c "import secrets; print(secrets.token_urlsafe(24))").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($env:MAIX_API_TOKEN)) {
        throw "Failed to generate MAIX_API_TOKEN."
    }
    Write-Host "Generated API token for remote access: $env:MAIX_API_TOKEN"
    Write-Host "Open the page with: http://<server-ip>:$ListenPort/?token=$env:MAIX_API_TOKEN"
}

Write-Host "Starting Maix Converter Platform..."
Write-Host "Root directory: $RootDir"
Write-Host "Host: $ListenHost  Port: $ListenPort"
Write-Host "Python: $Python $($PythonArgs -join ' ')"
Write-Host "Using plain static frontend in web/static (HTML/CSS/JS, no npm required)"

Push-Location $RootDir
try {
    & $Python @PythonArgs -m uvicorn web.app:app --host $ListenHost --port $ListenPort
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
