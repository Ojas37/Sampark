$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Python dependency installation failed." }
if (-not (Test-Path "frontend\node_modules")) {
    Push-Location frontend
    npm install
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Frontend dependency installation failed." }
    Pop-Location
}
& .\.venv\Scripts\python.exe backend\scripts\seed.py
if ($LASTEXITCODE -ne 0) { throw "Synthetic demo seeding failed." }
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root'; .\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000"
Push-Location frontend
npm run dev -- --host 127.0.0.1
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "The frontend development server exited with an error." }
Pop-Location
