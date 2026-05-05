param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$PytestArgs,
    [string]$Project = "content_research_mvp"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ProjectPath = Join-Path $Root $Project
$CandidatePythons = @(
    (Join-Path $Root ".venv\Scripts\python.exe"),
    (Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"),
    "python"
)
$TempDir = Join-Path $Root ".tmp"
$CacheDir = Join-Path $Root ".pip-cache"

if (-not (Test-Path -LiteralPath $ProjectPath)) {
    throw "Project path not found: $ProjectPath"
}

New-Item -ItemType Directory -Force -Path $TempDir, $CacheDir | Out-Null
$env:TEMP = $TempDir
$env:TMP = $TempDir
$env:PIP_CACHE_DIR = $CacheDir
$env:PYTHONUTF8 = "1"

function Test-Pytest {
    param([string]$PythonExe)

    if ($PythonExe -ne "python" -and -not (Test-Path -LiteralPath $PythonExe)) {
        return $false
    }

    $PreviousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $PythonExe -m pytest --version *> $null
    $ExitCode = $LASTEXITCODE
    $ErrorActionPreference = $PreviousErrorActionPreference

    return $ExitCode -eq 0
}

function Initialize-ProjectVenv {
    $VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $VenvPython)) {
        throw "Project venv Python not found: $VenvPython"
    }

    Write-Host "pytest not found; bootstrapping project .venv with local temp/cache directories..."

    & $VenvPython -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) {
        throw "ensurepip failed for project .venv."
    }

    & $VenvPython -m pip install -e "$($ProjectPath)[dev]"
    if ($LASTEXITCODE -ne 0) {
        throw "Dev dependency install failed for project .venv."
    }

    return $VenvPython
}

$Python = $null
foreach ($Candidate in $CandidatePythons) {
    if (Test-Pytest $Candidate) {
        $Python = $Candidate
        break
    }
}

if ($null -eq $Python) {
    $Python = Initialize-ProjectVenv
}

if (-not (Test-Pytest $Python)) {
    throw "No Python with pytest is available after bootstrapping project .venv."
}

Push-Location $ProjectPath
try {
    & $Python -m pytest @PytestArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
