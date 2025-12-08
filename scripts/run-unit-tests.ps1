#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run PersonaMate unit tests (fast, no services required)

.DESCRIPTION
    Execute unit tests directly in Docker without external services
#>

Write-Host "PersonaMate - Unit Tests" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Building test image..." -ForegroundColor Yellow
docker compose build pytest

Write-Host ""
Write-Host "Running unit tests (fast, no services needed)..." -ForegroundColor Green
Write-Host ""

docker compose run --rm pytest pytest `
    /app/test/python/test_embedding_pipeline.py `
    /app/test/python/test_tools.py `
    -v

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "[PASS] Unit tests passed!" -ForegroundColor Green
} else {
    Write-Host "[FAIL] Unit tests failed!" -ForegroundColor Red
}

Write-Host ""
exit $exitCode
