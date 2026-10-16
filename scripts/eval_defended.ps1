# Stage 6: defended condition (B) and ablations on the attack + look-alike suite. Resumable.
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\eval_defended.ps1 -DevOnly     # B, B-nomark, B-noguard (~65 min)
#   powershell -ExecutionPolicy Bypass -File scripts\eval_defended.ps1 -HeldOut     # B only, ONLY after gate approval
param([switch]$DevOnly, [switch]$HeldOut)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not ($DevOnly -xor $HeldOut)) { Write-Output "Choose exactly one of -DevOnly or -HeldOut."; exit 1 }
if (-not (Test-Path data\world\sahayak.db)) { uv run python -m sahayak.cli build-db | Out-Null }
uv run pytest tests/model -q
if ($LASTEXITCODE -ne 0) { Write-Output "model tests failed; is Ollama running with the pinned model?"; exit 1 }
ollama ps

if ($DevOnly) {
    foreach ($v in @("B", "B-nomark", "B-noguard")) {
        $id = "stage6-$v-dev"
        Write-Output "== $id"
        uv run python -m sahayak.cli run-eval --suite dev --variant $v --run-id $id
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        uv run python -m sahayak.cli summarize-eval --run-id $id --publish "defended-$v-dev" | Out-Null
    }
} else {
    if ($env:SAHAYAK_HELDOUT_APPROVED -ne "stage5-heldout-gate-approved") {
        Write-Output "Held-out run refused: it needs explicit gate approval (spec rule 7)."
        exit 1
    }
    uv run python -m sahayak.cli run-eval --suite heldout --variant B --run-id stage6-B-heldout
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    uv run python -m sahayak.cli summarize-eval --run-id stage6-B-heldout --publish defended-B-heldout | Out-Null
}
ollama ps
