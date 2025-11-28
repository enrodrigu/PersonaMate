# CI/CD Pipeline Documentation

## GitHub Actions Workflow

The project uses GitHub Actions for automated testing and deployment. The pipeline runs on every push and pull request to `main` and `dev` branches.

## Pipeline Jobs

### 1. Test Job
Runs all automated tests in Docker environment:
- **MCP Integration Tests**: Validates MCP server functionality
- **Tool Implementation Tests**: Tests all personalDataTool and linkingTool functions
- **Coverage Report**: Generates code coverage metrics

**Requirements:**
- Neo4j service must be running
- Environment variables must be set via GitHub Secrets

### 2. Lint Job
Code quality checks:
- **flake8**: Checks for syntax errors and code style issues
- **black**: Verifies Python code formatting (120 char line length)

### 3. Build Job
Only runs on `main` branch pushes after tests pass:
- Builds Docker images
- Performs smoke test of services
- Validates deployment readiness

## Required GitHub Secrets

Add these secrets in your repository settings (`Settings` → `Secrets and variables` → `Actions`):

- `OPENAI_API_KEY`: Your OpenAI API key for LLM functionality
- `LANGCHAIN_API_KEY`: (Optional) LangChain tracing API key

## Running Tests Locally

```bash
# Start Neo4j
docker compose up -d neo4j

# Wait for Neo4j to initialize
sleep 15

# Run MCP tests
docker compose run --rm pytest pytest /app/test/python/test_mcp_integration.py -v

# Run tool tests
docker compose run --rm pytest pytest /app/test/python/test_tools.py -v

# Run all tests with coverage
docker compose run --rm pytest pytest /app/test/python/ -v --cov=/app/src/python --cov-report=term

# Cleanup
docker compose down -v
```

## Coverage Reports

The pipeline uploads coverage reports to Codecov (optional). To enable:

1. Sign up at [codecov.io](https://codecov.io)
2. Connect your GitHub repository
3. Add the Codecov badge to your README

## Troubleshooting

### Neo4j Connection Issues
If tests fail with `ServiceUnavailable` errors:
- Increase the sleep time in the workflow (line 32)
- Check Neo4j logs: `docker compose logs neo4j --tail 50`

### Test Failures
- Review test output in GitHub Actions logs
- Run tests locally to reproduce issues
- Ensure .env file has all required variables

### Build Failures
- Verify Dockerfile syntax
- Check that all dependencies are in requirements.txt
- Test Docker build locally: `docker compose build mcp`

## Best Practices

1. **Never commit secrets**: Use GitHub Secrets for API keys
2. **Run tests locally first**: Validate changes before pushing
3. **Keep tests fast**: Use module-scoped fixtures to reduce setup time
4. **Monitor coverage**: Aim for >80% code coverage
5. **Fix lint issues**: Run `black` and `flake8` before committing

