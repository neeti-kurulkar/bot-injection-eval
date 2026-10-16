# Stage 7: one-command reproduction.
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend stub                     # no model needed
#   powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend ollama -Scope benign     # 30 benign, ~1.5 min
#   powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend ollama -Scope dev        # A, B, ablations, ~75 min
#   powershell -ExecutionPolicy Bypass -File scripts\reproduce.ps1 -Backend ollama -Scope heldout    # gate-approved only
# Runs are resumable: re-running continues an interrupted run with the same id.
param([ValidateSet("stub", "ollama")][string]$Backend = "stub",
      [ValidateSet("benign", "dev", "heldout")][string]$Scope = "benign")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
function Check($what) { if ($LASTEXITCODE -ne 0) { Write-Output "FAILED: $what"; exit 1 } }

Write-Output "== Environment"
uv sync | Out-Null; Check "uv sync"
uv run python -c "import sahayak, sys; print('sahayak', sahayak.__version__, 'python', sys.version.split()[0])"

Write-Output "== Synthetic world: regenerate into a temp folder and compare with the committed checksum"
$tmp = Join-Path $env:TEMP ("sahayak-world-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$regen = uv run python -m sahayak.cli generate-world --out $tmp | Select-String "world SHA-256"
$committed = uv run python -m sahayak.cli verify-world | Select-String "world SHA-256"
Remove-Item -Recurse -Force -Confirm:$false $tmp
Write-Output "  regenerated: $regen"
Write-Output "  committed:   $committed"
if ("$regen" -ne "$committed") { Write-Output "FAILED: world is not byte-identical to the committed one"; exit 1 }
uv run python -m sahayak.cli verify-world | Out-Null; Check "verify-world"
uv run python -m sahayak.cli attack-stats | Select-String "split manifest"; Check "attack split verification"

Write-Output "== Mock bank and full test suite"
uv run python -m sahayak.cli build-db | Out-Null; Check "build-db"
uv run pytest tests -q; Check "tests"

if ($Backend -eq "stub") {
    Write-Output "== Stub backend: every pipeline end to end (results are meaningless by design)"
    Get-ChildItem data\runs -Directory -Filter "repro-stub-*" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -Confirm:$false
    uv run python -m sahayak.cli run-benign --backend stub --run-id repro-stub-benign | Select-String "Benign pass"; Check "stub benign"
    foreach ($v in @("A", "B")) {
        uv run python -m sahayak.cli run-eval --backend stub --suite dev --variant $v --run-id "repro-stub-dev-$v" | Select-String "\*\*Any goal\*\* \| \*\*"; Check "stub dev $v"
    }
    uv run python -m sahayak.cli compare-variants --base repro-stub-dev-A --runs repro-stub-dev-B | Select-String "Any goal"; Check "stub compare"
    Write-Output "Stub reproduction complete."
    exit 0
}

Write-Output "== Local model checks (pinned digest, no thinking, tool round trip) and placement"
uv run pytest tests/model -q; Check "model tests (is Ollama running with the pinned model?)"
ollama ps

if ($Scope -eq "benign") {
    uv run python -m sahayak.cli run-benign --run-id repro-benign --notes "reproduction" | Select-String "Benign pass|Threshold|Scenarios with any|output tok/s"
    Check "benign run"
} elseif ($Scope -eq "dev") {
    foreach ($v in @("A", "B", "B-nomark", "B-noguard")) {
        Write-Output "== dev $v"
        uv run python -m sahayak.cli run-eval --suite dev --variant $v --run-id "repro-dev-$v" | Select-String "\*\*Any goal\*\* \| \*\*"
        Check "dev $v"
    }
    uv run python -m sahayak.cli compare-variants --base repro-dev-A --runs repro-dev-B repro-dev-B-nomark repro-dev-B-noguard | Select-String "^## |Any goal|false block"
} else {
    if ($env:SAHAYAK_HELDOUT_APPROVED -ne "stage5-heldout-gate-approved") {
        Write-Output "Held-out run refused: it needs an explicit gate decision (spec rule 7). See README."
        exit 1
    }
    foreach ($v in @("A", "B")) {
        uv run python -m sahayak.cli run-eval --suite heldout --variant $v --run-id "repro-heldout-$v" | Out-Null
        Check "held-out $v"
    }
    uv run python -m sahayak.cli compare-variants --base repro-heldout-A --runs repro-heldout-B --heldout | Select-String "Any goal|false block"
}
ollama ps
