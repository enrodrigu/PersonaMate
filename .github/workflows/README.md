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
Code quality and auto-formatting:
- **flake8**: Checks for syntax errors and code style issues
- **black**: Auto-formats Python code (120 char line length)
- **Auto-commit**: Automatically commits formatting changes on push events

**Auto-formatting behavior:**
- On `push`: Formats code and commits changes automatically with `[skip ci]` tag
- On `pull_request`: Formats code but does not commit (shows what needs formatting)

### 3. Build Job
Only runs on `main` branch pushes after tests pass:
- Builds Docker images
- Performs smoke test of services
- Validates deployment readiness

## Code Formatting

### Automatic Formatting (CI/CD)
The pipeline automatically formats code using black when you push to the repository. Formatted code is committed back with the message: `style: auto-format code with black [skip ci]`

### Local Formatting (Pre-commit Hooks)

**Setup pre-commit hooks** (recommended for contributors):
```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Now hooks run automatically on git commit
```

**Manual formatting**:
```bash
# Format all Python files
black src/python test/python --line-length=120

# Check what would be formatted without changing files
black src/python test/python --line-length=120 --check

# Run all pre-commit hooks manually
pre-commit run --all-files
```

### Formatting Rules
- Line length: 120 characters
- Style: Black default (PEP 8 compliant)
- Import sorting: isort with black profile
- Trailing whitespace: Removed automatically
- End of file: Single newline enforced

## Required GitHub Secrets

Add these secrets in your repository settings (`Settings` → `Secrets and variables` → `Actions`):

- `OPENAI_API_KEY`: Your OpenAI API key for LLM functionality

## Running Tests Locally

```bash
# Start Neo4j
docker compose up -d neo4j

# Wait for Neo4j to initialize
sleep 15

# Start MCP server (required for MCP integration tests)
docker compose up -d mcp
sleep 5

# Run MCP integration tests
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
