# Stage 1: generate the seeded synthetic world, verify it, and run the world tests.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\stage1.ps1 [-Samples]
param([switch]$Samples)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Output "== Generating world (seed from config, default 20261015)"
uv run python -m sahayak.cli generate-world
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output "== Verifying files against MANIFEST.sha256"
uv run python -m sahayak.cli verify-world
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output "== Determinism and invariant tests"
uv run pytest tests/unit/test_world.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Samples) {
    uv run python -m sahayak.cli show-samples
}
