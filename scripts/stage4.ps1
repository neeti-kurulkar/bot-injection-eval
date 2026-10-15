# Stage 4: verify the frozen attack suite (counts only; held-out stays sealed) and run its tests.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\stage4.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Output "== Split manifest and file checksums, counts per goal / surface / language / split"
uv run python -m sahayak.cli attack-stats
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output "== Attack-suite tests (never unseal held-out)"
uv run pytest tests/unit/test_attacks.py -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Output "== Language review sheet (DEVELOPMENT items only): data\attacks\dev\review_sample.md"
