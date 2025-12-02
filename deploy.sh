#!/bin/bash
# PersonaMate Deployment Script for Linux/macOS
# Interactive deployment with options for full stack or MCP-only

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Functions
print_step() {
    echo -e "\n${CYAN}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_success "Docker found: $DOCKER_VERSION"
    else
        print_error "Docker is not installed"
        echo "Please install Docker from: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Check Docker Compose
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        print_success "Docker Compose found: $COMPOSE_VERSION"
    else
        print_error "Docker Compose is not available"
        exit 1
    fi

    # Check if Docker daemon is running
    if docker ps &> /dev/null; then
        print_success "Docker daemon is running"
    else
        print_error "Docker daemon is not running"
        echo "Please start Docker"
        exit 1
    fi

    # Check .env file
    if [ -f ".env" ]; then
        print_success ".env file found"
    else
        print_warning ".env file not found, will use defaults"
        echo "For production use, create a .env file with your configuration"
    fi
}

show_menu() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║         PersonaMate Deployment Configuration              ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Choose your deployment mode:"
    echo ""
    echo "  1) Full Stack (Recommended)"
    echo "     - MCP Server (FastMCP on port 8080)"
    echo "     - Neo4j Database (port 7687, browser on 7474)"
    echo "     - OpenWebUI Chat Interface (port 3000)"
    echo ""
    echo "  2) MCP Only"
    echo "     - MCP Server (FastMCP on port 8080)"
    echo "     - Neo4j Database (port 7687, browser on 7474)"
    echo "     - No web interface"
    echo ""
    echo "  3) Exit"
    echo ""
    read -p "Enter your choice (1-3): " choice

    case $choice in
        1) DEPLOY_MODE="full" ;;
        2) DEPLOY_MODE="mcp-only" ;;
        3) echo "Deployment cancelled"; exit 0 ;;
        *)
            print_error "Invalid choice. Please enter 1, 2, or 3"
            show_menu
            ;;
    esac
}

show_configuration() {
    print_step "Deployment Configuration"
    echo ""
    echo -n "Mode: "
    if [ "$DEPLOY_MODE" == "full" ]; then
        echo -e "${GREEN}Full Stack${NC}"
    else
        echo -e "${GREEN}MCP Only${NC}"
    fi
    echo ""
    echo "Services to deploy:"
    echo "  • MCP Server (http://localhost:8080/sse)"
    echo "  • Neo4j Database (bolt://localhost:7687)"
    echo "  • Neo4j Browser (http://localhost:7474)"
    if [ "$DEPLOY_MODE" == "full" ]; then
        echo "  • OpenWebUI (http://localhost:3000)"
    fi
    echo ""
}

deploy_services() {
    print_step "Stopping any existing services..."
    docker compose down 2>/dev/null || true

    print_step "Building images..."
    if docker compose build mcp; then
        print_success "MCP image built successfully"
    else
        print_error "Failed to build MCP image"
        exit 1
    fi

    print_step "Starting services..."

    if [ "$DEPLOY_MODE" == "full" ]; then
        docker compose up -d neo4j mcp openwebui
    else
        docker compose up -d neo4j mcp
    fi

    if [ $? -eq 0 ]; then
        print_success "Services started successfully"
    else
        print_error "Failed to start services"
        docker compose logs --tail 50
        exit 1
    fi
}

wait_for_services() {
    print_step "Waiting for services to be ready..."

    # Wait for Neo4j
    echo -n "  Waiting for Neo4j..."
    sleep 10

    MAX_ATTEMPTS=30
    ATTEMPT=0
    NEO4J_READY=false

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ] && [ "$NEO4J_READY" = false ]; do
        if docker exec personamate-neo4j cypher-shell -u neo4j -p personamate "RETURN 1" &>/dev/null; then
            NEO4J_READY=true
            echo -e " ${GREEN}Ready!${NC}"
        else
            sleep 2
            ATTEMPT=$((ATTEMPT + 1))
            echo -n "."
        fi
    done

    if [ "$NEO4J_READY" = false ]; then
        print_warning "\n  Neo4j might not be fully ready yet"
    fi

    # Wait for MCP
    echo -n "  Waiting for MCP Server..."
    sleep 5
    echo -e " ${GREEN}Ready!${NC}"

    if [ "$DEPLOY_MODE" == "full" ]; then
        echo -n "  Waiting for OpenWebUI..."
        sleep 10
        echo -e " ${GREEN}Ready!${NC}"
    fi
}

show_access_info() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║            Deployment Completed Successfully!             ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Access your services:"
    echo ""
    echo -e "${CYAN}  MCP Server:${NC}"
    echo "    • URL: http://localhost:8080/sse"
    echo "    • Transport: SSE (Server-Sent Events)"
    echo ""
    echo -e "${CYAN}  Neo4j Database:${NC}"
    echo "    • Bolt: bolt://localhost:7687"
    echo "    • Browser: http://localhost:7474"
    echo "    • Username: neo4j"
    echo "    • Password: personamate"
    echo ""

    if [ "$DEPLOY_MODE" == "full" ]; then
        echo -e "${CYAN}  OpenWebUI:${NC}"
        echo "    • URL: http://localhost:3000"
        echo "    • First time: Create an admin account"
        echo ""
    fi

    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "  • View logs:    docker compose logs -f"
    echo "  • Stop all:     docker compose down"
    echo "  • Restart:      docker compose restart"
    echo "  • View status:  docker compose ps"
    echo ""
}

show_next_steps() {
    echo -e "${CYAN}Next Steps:${NC}"
    echo ""

    if [ "$DEPLOY_MODE" == "full" ]; then
        echo "  1. Open OpenWebUI at http://localhost:3000"
        echo "  2. Create your admin account"
        echo "  3. Configure OpenWebUI to connect to MCP server"
        echo "  4. Start chatting with PersonaMate!"
    else
        echo "  1. Configure your MCP client to connect to:"
        echo "     http://localhost:8080/sse"
        echo "  2. Use the MCP protocol to interact with PersonaMate"
        echo "  3. Access Neo4j browser to view your knowledge graph"
    fi

    echo ""
    echo "For more information, see README.md"
    echo ""
}

# Main execution
clear

echo -e "${CYAN}"
cat << "EOF"

  ██████╗ ███████╗██████╗ ███████╗ ██████╗ ███╗   ██╗ █████╗ ███╗   ███╗ █████╗ ████████╗███████╗
  ██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗████╗  ██║██╔══██╗████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
  ██████╔╝█████╗  ██████╔╝███████╗██║   ██║██╔██╗ ██║███████║██╔████╔██║███████║   ██║   █████╗
  ██╔═══╝ ██╔══╝  ██╔══██╗╚════██║██║   ██║██║╚██╗██║██╔══██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝
  ██║     ███████╗██║  ██║███████║╚██████╔╝██║ ╚████║██║  ██║██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
  ╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝

EOF
echo -e "${NC}"

check_prerequisites

# Check for command line argument
if [ $# -eq 1 ]; then
    case $1 in
        full) DEPLOY_MODE="full" ;;
        mcp-only) DEPLOY_MODE="mcp-only" ;;
        *)
            print_error "Invalid argument. Use 'full' or 'mcp-only'"
            exit 1
            ;;
    esac
else
    show_menu
fi

show_configuration

echo ""
read -p "Continue with deployment? (Y/n): " confirm
if [ "$confirm" == "n" ] || [ "$confirm" == "N" ]; then
    echo "Deployment cancelled"
    exit 0
fi

deploy_services
wait_for_services
show_access_info
show_next_steps

echo -e "${GREEN}Deployment complete! 🚀${NC}"
echo ""
