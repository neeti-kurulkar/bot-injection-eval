# Records the environment values pinned in docs/environment.md.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\record_env.ps1 [-Model qwen3:4b-instruct-2507-q4_K_M]
param([string]$Model = "qwen3:4b-instruct-2507-q4_K_M")

$ErrorActionPreference = "Stop"
Write-Output "== OS / hardware"
(Get-CimInstance Win32_OperatingSystem).Caption
"RAM_GB: {0}" -f [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

Write-Output "== Python / uv"
try { uv --version; "project venv: " + (uv run --no-sync python --version) } catch { Write-Output "uv: NOT INSTALLED" }
"system python (not used by the project): " + (python --version)

Write-Output "== Ollama"
ollama --version
$tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags"
$m = $tags.models | Where-Object { $_.name -eq $Model }
if (-not $m) { Write-Output "MODEL NOT FOUND: $Model (run: ollama pull $Model)"; exit 1 }
"model:        $($m.name)"
"digest:       $($m.digest)"
"quantization: $($m.details.quantization_level)"
"parameters:   $($m.details.parameter_size)"
ollama show $Model --modelfile | Select-String -Pattern "^PARAMETER"

Write-Output "== Thinking probe (one neutral prompt; expect content '5' and no thinking)"
$body = @{
  model = $Model; stream = $false; keep_alive = "5m"
  options = @{ num_ctx = 8192; seed = 1; temperature = 0 }
  messages = @(@{ role = "user"; content = "What is 2+3? Answer with one number. /no_think" })
} | ConvertTo-Json -Depth 5
$r = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -Body $body -ContentType "application/json"
"content:  '$($r.message.content)'"
"thinking: '$($r.message.thinking)'"
if ($r.message.thinking -or $r.message.content -match "</?think>") { Write-Output "PROTOCOL FAILURE: thinking text present" } else { Write-Output "thinking check: PASS" }

Write-Output "== GPU placement (num_ctx 8192)"
ollama ps
