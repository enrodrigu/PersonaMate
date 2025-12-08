#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run complete PersonaMate test suite with coverage

.DESCRIPTION
    Execute all tests and generate coverage report for codecov.io
#>

Write-Host "PersonaMate - Complete Test Suite" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Starting all services (Neo4j, MongoDB, Qdrant)..." -ForegroundColor Yellow
docker compose up -d neo4j mongodb qdrant

Write-Host "Waiting for all services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 6

Write-Host ""
Write-Host "Running complete test suite with coverage..." -ForegroundColor Green
Write-Host ""

docker compose run --rm pytest pytest `
    /app/test/python/ `
    -v `
    --cov=/app/src/python `
    --cov-report=xml:/app/output/coverage.xml `
    --cov-report=term

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "[PASS] All tests passed!" -ForegroundColor Green
    Write-Host ""
    if (Test-Path "coverage.xml") {
        Write-Host "Coverage report generated: coverage.xml (for codecov.io)" -ForegroundColor Cyan
    } else {
        Write-Host "Warning: coverage.xml not found" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Cleaning up services..." -ForegroundColor Yellow
    docker compose down --remove-orphans
} else {
    Write-Host "[FAIL] Some tests failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Service logs:" -ForegroundColor Yellow
    docker compose logs --tail=50 neo4j mongodb qdrant
    Write-Host ""
    Write-Host "Cleaning up services..." -ForegroundColor Yellow
    docker compose down --remove-orphans
}

Write-Host ""
exit $exitCode
