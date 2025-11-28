#!/usr/bin/env pwsh
<#
.SYNOPSIS
    PersonaMate Deployment Script
.DESCRIPTION
    Interactive deployment script that allows users to choose between:
    - Full stack (MCP + Neo4j + OpenWebUI)
    - MCP only (MCP + Neo4j)
.EXAMPLE
    .\deploy.ps1
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("full", "mcp-only", "interactive")]
    [string]$Mode = "interactive"
)

# Colors for output
$successColor = "Green"
$errorColor = "Red"
$infoColor = "Cyan"
$warningColor = "Yellow"

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Step($message) {
    Write-ColorOutput $infoColor "`n==> $message"
}

function Write-Success($message) {
    Write-ColorOutput $successColor "✓ $message"
}

function Write-Error-Message($message) {
    Write-ColorOutput $errorColor "✗ $message"
}

function Write-Warning-Message($message) {
    Write-ColorOutput $warningColor "! $message"
}

function Test-Prerequisites {
    Write-Step "Checking prerequisites..."
    
    # Check Docker
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            Write-Success "Docker found: $dockerVersion"
        } else {
            throw "Docker not found"
        }
    } catch {
        Write-Error-Message "Docker is not installed or not in PATH"
        Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
        exit 1
    }
    
    # Check Docker Compose
    try {
        $composeVersion = docker compose version 2>$null
        if ($composeVersion) {
            Write-Success "Docker Compose found: $composeVersion"
        } else {
            throw "Docker Compose not found"
        }
    } catch {
        Write-Error-Message "Docker Compose is not available"
        exit 1
    }
    
    # Check if Docker is running
    try {
        docker ps > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker daemon is running"
        } else {
            throw "Docker daemon not running"
        }
    } catch {
        Write-Error-Message "Docker daemon is not running"
        Write-Host "Please start Docker Desktop"
        exit 1
    }
    
    # Check .env file
    if (Test-Path ".env") {
        Write-Success ".env file found"
    } else {
        Write-Warning-Message ".env file not found, will use defaults"
        Write-Host "For production use, create a .env file with your configuration"
    }
}

function Get-DeploymentMode {
    Write-Host ""
    Write-ColorOutput $infoColor "╔════════════════════════════════════════════════════════════╗"
    Write-ColorOutput $infoColor "║         PersonaMate Deployment Configuration              ║"
    Write-ColorOutput $infoColor "╚════════════════════════════════════════════════════════════╝"
    Write-Host ""
    Write-Host "Choose your deployment mode:"
    Write-Host ""
    Write-Host "  1) Full Stack (Recommended)"
    Write-Host "     - MCP Server (FastMCP on port 8080)"
    Write-Host "     - Neo4j Database (port 7687, browser on 7474)"
    Write-Host "     - OpenWebUI Chat Interface (port 3000)"
    Write-Host ""
    Write-Host "  2) MCP Only"
    Write-Host "     - MCP Server (FastMCP on port 8080)"
    Write-Host "     - Neo4j Database (port 7687, browser on 7474)"
    Write-Host "     - No web interface"
    Write-Host ""
    Write-Host "  3) Exit"
    Write-Host ""
    
    $choice = Read-Host "Enter your choice (1-3)"
    
    switch ($choice) {
        "1" { return "full" }
        "2" { return "mcp-only" }
        "3" { 
            Write-Host "Deployment cancelled"
            exit 0 
        }
        default {
            Write-Error-Message "Invalid choice. Please enter 1, 2, or 3"
            return Get-DeploymentMode
        }
    }
}

function Show-Configuration($mode) {
    Write-Step "Deployment Configuration"
    Write-Host ""
    Write-Host "Mode: " -NoNewline
    Write-ColorOutput $successColor $(if ($mode -eq "full") { "Full Stack" } else { "MCP Only" })
    Write-Host ""
    Write-Host "Services to deploy:"
    Write-Host "  • MCP Server (http://localhost:8080/sse)"
    Write-Host "  • Neo4j Database (bolt://localhost:7687)"
    Write-Host "  • Neo4j Browser (http://localhost:7474)"
    if ($mode -eq "full") {
        Write-Host "  • OpenWebUI (http://localhost:3000)"
    }
    Write-Host ""
}

function Deploy-Services($mode) {
    Write-Step "Stopping any existing services..."
    docker compose down 2>$null
    
    Write-Step "Building images..."
    docker compose build mcp
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to build MCP image"
        exit 1
    }
    Write-Success "MCP image built successfully"
    
    Write-Step "Starting services..."
    
    if ($mode -eq "full") {
        docker compose up -d neo4j mcp openwebui
    } else {
        docker compose up -d neo4j mcp
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Message "Failed to start services"
        docker compose logs --tail 50
        exit 1
    }
    
    Write-Success "Services started successfully"
}

function Wait-ForServices($mode) {
    Write-Step "Waiting for services to be ready..."
    
    # Wait for Neo4j
    Write-Host "  Waiting for Neo4j..." -NoNewline
    Start-Sleep -Seconds 10
    
    $maxAttempts = 30
    $attempt = 0
    $neo4jReady = $false
    
    while ($attempt -lt $maxAttempts -and -not $neo4jReady) {
        try {
            $result = docker exec personamate-neo4j cypher-shell -u neo4j -p personamate "RETURN 1" 2>$null
            if ($LASTEXITCODE -eq 0) {
                $neo4jReady = $true
                Write-ColorOutput $successColor " Ready!"
            }
        } catch {
            Start-Sleep -Seconds 2
            $attempt++
            Write-Host "." -NoNewline
        }
    }
    
    if (-not $neo4jReady) {
        Write-Warning-Message "`n  Neo4j might not be fully ready yet"
    }
    
    # Wait for MCP
    Write-Host "  Waiting for MCP Server..." -NoNewline
    Start-Sleep -Seconds 5
    Write-ColorOutput $successColor " Ready!"
    
    if ($mode -eq "full") {
        Write-Host "  Waiting for OpenWebUI..." -NoNewline
        Start-Sleep -Seconds 10
        Write-ColorOutput $successColor " Ready!"
    }
}

function Show-AccessInfo($mode) {
    Write-Host ""
    Write-ColorOutput $successColor "╔════════════════════════════════════════════════════════════╗"
    Write-ColorOutput $successColor "║            Deployment Completed Successfully!             ║"
    Write-ColorOutput $successColor "╚════════════════════════════════════════════════════════════╝"
    Write-Host ""
    Write-Host "Access your services:"
    Write-Host ""
    Write-ColorOutput $infoColor "  MCP Server:"
    Write-Host "    • URL: http://localhost:8080/sse"
    Write-Host "    • Transport: SSE (Server-Sent Events)"
    Write-Host ""
    Write-ColorOutput $infoColor "  Neo4j Database:"
    Write-Host "    • Bolt: bolt://localhost:7687"
    Write-Host "    • Browser: http://localhost:7474"
    Write-Host "    • Username: neo4j"
    Write-Host "    • Password: personamate"
    Write-Host ""
    
    if ($mode -eq "full") {
        Write-ColorOutput $infoColor "  OpenWebUI:"
        Write-Host "    • URL: http://localhost:3000"
        Write-Host "    • First time: Create an admin account"
        Write-Host ""
    }
    
    Write-ColorOutput $warningColor "Useful Commands:"
    Write-Host "  • View logs:    docker compose logs -f"
    Write-Host "  • Stop all:     docker compose down"
    Write-Host "  • Restart:      docker compose restart"
    Write-Host "  • View status:  docker compose ps"
    Write-Host ""
}

function Show-NextSteps($mode) {
    Write-ColorOutput $infoColor "Next Steps:"
    Write-Host ""
    
    if ($mode -eq "full") {
        Write-Host "  1. Open OpenWebUI at http://localhost:3000"
        Write-Host "  2. Create your admin account"
        Write-Host "  3. Configure OpenWebUI to connect to MCP server"
        Write-Host "  4. Start chatting with PersonaMate!"
    } else {
        Write-Host "  1. Configure your MCP client to connect to:"
        Write-Host "     http://localhost:8080/sse"
        Write-Host "  2. Use the MCP protocol to interact with PersonaMate"
        Write-Host "  3. Access Neo4j browser to view your knowledge graph"
    }
    
    Write-Host ""
    Write-Host "For more information, see README.md"
    Write-Host ""
}

# Main execution
Clear-Host

Write-ColorOutput $infoColor @"

  ██████╗ ███████╗██████╗ ███████╗ ██████╗ ███╗   ██╗ █████╗ ███╗   ███╗ █████╗ ████████╗███████╗
  ██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗████╗  ██║██╔══██╗████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
  ██████╔╝█████╗  ██████╔╝███████╗██║   ██║██╔██╗ ██║███████║██╔████╔██║███████║   ██║   █████╗  
  ██╔═══╝ ██╔══╝  ██╔══██╗╚════██║██║   ██║██║╚██╗██║██╔══██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝  
  ██║     ███████╗██║  ██║███████║╚██████╔╝██║ ╚████║██║  ██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
  ╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

"@

Test-Prerequisites

if ($Mode -eq "interactive") {
    $deployMode = Get-DeploymentMode
} else {
    $deployMode = $Mode
}

Show-Configuration $deployMode

Write-Host ""
$confirm = Read-Host "Continue with deployment? (Y/n)"
if ($confirm -eq "n" -or $confirm -eq "N") {
    Write-Host "Deployment cancelled"
    exit 0
}

Deploy-Services $deployMode
Wait-ForServices $deployMode
Show-AccessInfo $deployMode
Show-NextSteps $deployMode

Write-ColorOutput $successColor "Deployment complete! 🚀"
Write-Host ""
