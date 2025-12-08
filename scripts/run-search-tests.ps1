#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run PersonaMate search and embeddings tests

.DESCRIPTION
    Execute semantic search and embedding quality tests (requires Qdrant + MongoDB)
#>

Write-Host "PersonaMate - Search & Embeddings Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Starting Qdrant and MongoDB..." -ForegroundColor Yellow
docker compose up -d qdrant mongodb

Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 4

Write-Host ""
Write-Host "Running search & embeddings tests..." -ForegroundColor Green
Write-Host ""

docker compose run --rm pytest pytest `
    /app/test/python/test_search_embeddings.py `
    -v -s

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "[PASS] Search & embeddings tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Cleaning up services..." -ForegroundColor Yellow
    docker compose down --remove-orphans
} else {
    Write-Host "[FAIL] Search & embeddings tests failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Service logs:" -ForegroundColor Yellow
    docker compose logs --tail=50 qdrant mongodb
    Write-Host ""
    Write-Host "Cleaning up services..." -ForegroundColor Yellow
    docker compose down --remove-orphans
}

Write-Host ""
exit $exitCode
