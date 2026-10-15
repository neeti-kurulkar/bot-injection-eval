# Stage 2: build the mock bank DB, run the no-model test suites, and show a ToolLayer demo.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\stage2.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Output "== Building template DB from data/world"
uv run python -m sahayak.cli build-db
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output "== Unit and integration tests (no model)"
uv run pytest tests/unit tests/integration -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output "== ToolLayer demo, Condition A then B"
uv run python -m sahayak.cli demo-tools
