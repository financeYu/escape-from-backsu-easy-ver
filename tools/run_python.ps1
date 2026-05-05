param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$PythonArgs
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$TempDir = Join-Path $Root ".tmp"
$CacheDir = Join-Path $Root ".pip-cache"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    throw "Project venv Python not found: $VenvPython"
}

New-Item -ItemType Directory -Force -Path $TempDir, $CacheDir | Out-Null
$env:TEMP = $TempDir
$env:TMP = $TempDir
$env:PIP_CACHE_DIR = $CacheDir
$env:PYTHONUTF8 = "1"

& $VenvPython @PythonArgs
exit $LASTEXITCODE
