$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.10+ is required."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js/npm is required."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

Push-Location dashboard
npm.cmd ci
Pop-Location

$code = Get-Command code -ErrorAction SilentlyContinue
if ($code) {
    $extensions = Get-Content ".vscode\extensions.json" | ConvertFrom-Json
    foreach ($extension in $extensions.recommendations) {
        & $code.Source --install-extension $extension --force
    }
} else {
    Write-Warning "VS Code CLI 'code' was not found; install the recommended extensions from .vscode/extensions.json."
}

Write-Host "Workspace dependencies are installed."
Write-Host "Open THE_MATREX.code-workspace in VS Code."
Write-Host "Open THE_MATREX.sln or import .vsconfig in Visual Studio."
