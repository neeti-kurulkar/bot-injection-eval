# Stage 3: run the 30 benign scenarios on the pinned local model, Condition A (resumable).
# Usage: powershell -ExecutionPolicy Bypass -File scripts\stage3_benign.ps1 -RunId stage3-benign-decision [-Repeat]
#   -Repeat  re-runs the first 5 scenarios into "<RunId>-repeat" and compares (GPU determinism check)
param([Parameter(Mandatory = $true)][string]$RunId, [string]$Notes = "", [switch]$Repeat)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path data\world\sahayak.db)) { uv run python -m sahayak.cli build-db | Out-Null }

Write-Output "== Model placement before the run (load + ollama ps)"
uv run pytest tests/model -q
if ($LASTEXITCODE -ne 0) { Write-Output "model tests failed; is Ollama running with the pinned model?"; exit 1 }
ollama ps

Write-Output "== Benign run $RunId (records in data\runs\$RunId)"
uv run python -m sahayak.cli run-benign --run-id $RunId --notes $Notes
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
ollama ps

if ($Repeat) {
    Write-Output "== Determinism check: first 5 scenarios again"
    uv run python -m sahayak.cli run-benign --run-id "$RunId-repeat" --limit 5 --notes "determinism repeat of $RunId" | Out-Null
    uv run python -m sahayak.cli compare-runs --a $RunId --b "$RunId-repeat"
}
