# Contributing to AgentTrace

Thank you for your interest in contributing to AgentTrace! This guide will help you get started.

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/agenttrace/agenttrace.git
   cd agenttrace
   ```

2. Start the backend services:
   ```bash
   docker compose -f docker-compose.dev.yml up
   ```

3. Install the SDK in development mode:
   ```bash
   cd sdk
   pip install -e ".[dev]"
   ```

4. Run tests:
   ```bash
   pytest
   ```

## Code Standards

### Python
- Python 3.11+ required
- All async functions use `async def` and `await`
- Type hints on every function signature
- Docstrings on every public class and function
- Use `logging` module, never `print()`
- Lint with `ruff`, type-check with `mypy`

### TypeScript / React
- TypeScript strict mode enabled
- Functional components only
- React Query for server state
- Zustand for UI state only

### Git Commits

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat: add LangGraph integration`
- `fix: resolve span correlation bug`
- `docs: add CrewAI quickstart`
- `test: add drift detector unit tests`
- `chore: update pricing.json`

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Make your changes
4. Run linting: `ruff check .`
5. Run type checking: `mypy .`
6. Run tests: `pytest`
7. Commit with a conventional commit message
8. Push and open a PR against `main`

## Reporting Issues

Use the issue templates:
- **Bug Report** for bugs
- **Feature Request** for new features
- **Integration Request** for new framework integrations

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
