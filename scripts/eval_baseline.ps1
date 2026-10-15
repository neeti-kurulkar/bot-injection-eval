# Stage 5: baseline (Condition A) evaluation on the attack + look-alike suite. Resumable.
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\eval_baseline.ps1 -DevOnly            # development families
#   powershell -ExecutionPolicy Bypass -File scripts\eval_baseline.ps1 -HeldOut            # ONLY after gate approval
param([switch]$DevOnly, [switch]$HeldOut, [string]$RunId = "")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not ($DevOnly -xor $HeldOut)) { Write-Output "Choose exactly one of -DevOnly or -HeldOut."; exit 1 }
if (-not (Test-Path data\world\sahayak.db)) { uv run python -m sahayak.cli build-db | Out-Null }

Write-Output "== Model checks and placement"
uv run pytest tests/model -q
if ($LASTEXITCODE -ne 0) { Write-Output "model tests failed; is Ollama running with the pinned model?"; exit 1 }
ollama ps

if ($DevOnly) {
    if (-not $RunId) { $RunId = "stage5-A-dev" }
    uv run python -m sahayak.cli run-eval --suite dev --condition A --run-id $RunId
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    uv run python -m sahayak.cli summarize-eval --run-id $RunId --publish baseline-dev | Out-Null
    uv run python -m sahayak.cli spotcheck-sheet --run-id $RunId
} else {
    if ($env:SAHAYAK_HELDOUT_APPROVED -ne "stage5-heldout-gate-approved") {
        Write-Output "Held-out run refused: it needs explicit gate approval (spec rule 7)."
        Write-Output "After approving at the Stage 5 gate, set: `$env:SAHAYAK_HELDOUT_APPROVED = 'stage5-heldout-gate-approved'"
        exit 1
    }
    if (-not $RunId) { $RunId = "stage5-A-heldout" }
    uv run python -m sahayak.cli run-eval --suite heldout --condition A --run-id $RunId
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    uv run python -m sahayak.cli summarize-eval --run-id $RunId --publish baseline-heldout | Out-Null
}
ollama ps
