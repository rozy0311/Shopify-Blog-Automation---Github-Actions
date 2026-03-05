$ErrorActionPreference = "Stop"
$venvRoot = "D:\.venvs"
$venvPath = Join-Path $venvRoot "agent-training-pack"

Write-Host "[1/5] Create virtual environment"
New-Item -ItemType Directory -Force $venvRoot | Out-Null
python -m venv $venvPath

Write-Host "[2/5] Activate virtual environment"
& (Join-Path $venvPath "Scripts\Activate.ps1")

Write-Host "[3/5] Upgrade pip"
python -m pip install --upgrade pip

Write-Host "[4/5] Install core packages"
pip install pydantic python-dotenv rich openai langgraph streamlit

Write-Host "[5/5] Run memory cycle smoke test"
python .\scripts\run_memory_cycle.py

Write-Host "Training environment setup complete."
