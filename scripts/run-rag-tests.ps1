#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run PersonaMate RAG architecture integration tests

.DESCRIPTION
    Execute complete RAG tests across Neo4j, MongoDB, and Qdrant
#>

Write-Host "PersonaMate - RAG Architecture Tests" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Starting Neo4j, MongoDB, and Qdrant..." -ForegroundColor Yellow
docker compose up -d neo4j mongodb qdrant

Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Running RAG architecture integration tests..." -ForegroundColor Green
Write-Host ""

docker compose run --rm pytest pytest `
    /app/test/python/test_rag_architecture.py `
    -v -s

$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "[PASS] RAG architecture tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Cleaning up services..." -ForegroundColor Yellow
    docker compose down --remove-orphans
} else {
    Write-Host "[FAIL] RAG architecture tests failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Service logs:" -ForegroundColor Yellow
    docker compose logs --tail=50 neo4j mongodb qdrant
    Write-Host ""
    Write-Host "Cleaning up services..." -ForegroundColor Yellow
    docker compose down --remove-orphans
}

Write-Host ""
exit $exitCode
