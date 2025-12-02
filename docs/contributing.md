# Contributing to PersonaMate

Thank you for your interest in contributing to PersonaMate! This guide will help you get started.

## 🚀 Quick Start for Contributors

### 1. Fork and Clone
```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/PersonaMate.git
cd PersonaMate
git checkout -b feature/your-feature-name
```

### 2. Set Up Development Environment

**Option A: With Pre-commit Hooks (Recommended)**
```bash
# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Now formatting happens automatically on commit!
```

**Option B: Manual Formatting**
```bash
# Install dependencies
pip install -r requirements.txt

# Format manually before committing
black src/python test/python --line-length=120
```

### 3. Start Development Services
```bash
# Start Neo4j for testing
docker compose up -d neo4j

# Or use full deployment
./deploy.sh mcp-only
```

## 🧪 Testing Your Changes

### Run All Tests
```bash
# In Docker (recommended - matches CI environment)
docker compose up -d neo4j mcp
docker compose run --rm pytest pytest /app/test/python/ -v

# Locally (if you have environment set up)
pytest test/python/ -v
```

### Run Specific Tests
```bash
# MCP integration tests
docker compose run --rm pytest pytest /app/test/python/test_mcp_integration.py -v

# Tool implementation tests
docker compose run --rm pytest pytest /app/test/python/test_tools.py -v

# With coverage
docker compose run --rm pytest pytest /app/test/python/ -v --cov=/app/src/python --cov-report=term
```

### Test a Specific Function
```bash
docker compose run --rm pytest pytest /app/test/python/test_tools.py::TestPersonalDataTool::test_fetch_person_data_existing -v
```

## 💅 Code Style and Formatting

### Automatic Formatting
PersonaMate uses [black](https://github.com/psf/black) for consistent code formatting.

**Pre-commit hooks** (runs on `git commit`):
```bash
pre-commit install              # One-time setup
# Now formatting happens automatically!
```

**Manual formatting**:
```bash
# Format all Python code
black src/python test/python --line-length=120

# Check without modifying
black src/python test/python --line-length=120 --check

# Run all pre-commit checks
pre-commit run --all-files
```

**CI auto-format**: If you don't format locally, the CI pipeline will automatically format your code and commit it back when you push.

### Code Style Rules
- **Line length**: 120 characters
- **Style**: Black default (PEP 8 compliant)
- **Imports**: Sorted with isort (black profile)
- **Docstrings**: Google style preferred
- **Type hints**: Encouraged for new code

## 📝 Commit Message Guidelines

Use conventional commits format:

```
type(scope): subject

body (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(tools): add delete_person tool"
git commit -m "fix(mcp): handle empty person name in fetch"
git commit -m "docs: update deployment guide with new options"
git commit -m "test: add integration test for relationship cycles"
```

## 🏗️ Project Structure

```
PersonaMate/
├── src/python/
│   ├── mcp_server.py          # MCP server entry point
│   ├── tools/                 # Tool implementations
│   │   ├── personalDataTool.py
│   │   └── linkingTool.py
│   └── utils/                 # Utility modules
│       ├── neo4j_graph.py
│       └── helper.py
├── test/python/
│   ├── test_mcp_integration.py
│   └── test_tools.py
└── .github/workflows/
    └── ci.yml                 # CI/CD pipeline
```

## 🎯 What to Contribute

### Good First Issues
- Add new tool functions
- Improve error messages
- Add more test cases
- Update documentation
- Fix typos

### Feature Ideas
- Additional MCP tools (e.g., search, analytics)
- Enhanced Neo4j queries
- New relationship types
- Export/import functionality
- Advanced graph algorithms

### Testing
- Add edge case tests
- Improve test coverage
- Performance benchmarks
- Integration tests

## ✅ Pull Request Process

1. **Update your branch** with latest main:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Ensure all tests pass**:
   ```bash
   docker compose run --rm pytest pytest /app/test/python/ -v
   ```

3. **Update documentation** if needed:
   - Update README.md for user-facing changes
   - Add docstrings to new functions
   - Update DEPLOYMENT.md for deployment changes

4. **Create Pull Request**:
   - Provide clear description of changes
   - Link related issues
   - Add screenshots for UI changes
   - List any breaking changes

5. **Code Review**:
   - Address review comments
   - Keep discussion focused and professional
   - Be patient - maintainers are volunteers

## 🐛 Reporting Bugs

When reporting bugs, include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Minimal steps to recreate
3. **Expected vs Actual**: What should happen vs what happens
4. **Environment**:
   - OS (Windows/Linux/macOS)
   - Docker version
   - Python version (if relevant)
5. **Logs**: Relevant error messages or logs
   ```bash
   docker compose logs mcp --tail 50
   ```

## 💡 Suggesting Features

For feature requests:

1. **Use Case**: Describe the problem you're solving
2. **Proposed Solution**: Your suggested approach
3. **Alternatives**: Other solutions you considered
4. **Examples**: Similar features in other projects

## 🔍 Development Tips

### Debugging MCP Server
```bash
# View MCP server logs in real-time
docker compose logs mcp -f

# Check MCP server is responding
curl http://localhost:8080/sse

# Test MCP tools directly
docker compose run --rm pytest python -c "from tools.personalDataTool import fetch_person_data; print(fetch_person_data.invoke({'name': 'Test'}))"
```

### Debugging Neo4j
```bash
# Access Neo4j shell
docker exec -it personamate-neo4j cypher-shell -u neo4j -p personamate

# View all data
MATCH (n) RETURN n LIMIT 25;

# Clear test data
MATCH (n) WHERE n.name STARTS WITH 'Test' DETACH DELETE n;
```

### Quick Iterations
```bash
# Rebuild just MCP server
docker compose build mcp

# Restart without rebuilding
docker compose restart mcp

# Full reset
docker compose down -v && ./deploy.sh mcp-only
```

## 📚 Resources

- **FastMCP Documentation**: https://gofastmcp.com
- **Neo4j Documentation**: https://neo4j.com/docs
- **Black Documentation**: https://black.readthedocs.io
- **MCP Protocol**: https://modelcontextprotocol.io

## 📧 Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and ideas
- **Pull Request Comments**: For code review questions

## 📜 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

---

Thank you for contributing to PersonaMate! 🎉
