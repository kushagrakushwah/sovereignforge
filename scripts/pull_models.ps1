# Pull all Ollama models needed by SovereignForge
# Run once after installing Ollama: .\scripts\pull_models.ps1

Write-Host "Pulling SovereignForge Ollama models (~20GB total)..." -ForegroundColor Cyan
Write-Host "This will take a while on first run." -ForegroundColor Yellow
Write-Host ""

$models = @(
    # Quantized versions for 6-8GB VRAM
    "qwen2.5:7b",                      # reasoning/document (Q4_K_M build)
    "qwen2.5-coder:7b",                # coding (Q4_K_M build)
    "qwen2.5vl:7b"                       # vision (multimodal)
)

foreach ($model in $models) {
    Write-Host "Pulling $model..." -ForegroundColor Yellow
    ollama pull $model
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $model pulled successfully" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Failed to pull $model" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "Model pull complete. Verify with: ollama list" -ForegroundColor Cyan
ollama list
