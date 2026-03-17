# Contributing

See the [CONTRIBUTING.md](https://github.com/agenttrace/agenttrace/blob/main/CONTRIBUTING.md) file in the repository root for detailed contribution guidelines.

## Quick Start

1. Fork and clone the repository
2. Set up the development environment:

    ```bash
    # SDK
    cd sdk && pip install -e ".[dev]"

    # Collector
    cd collector && pip install -e ".[dev]"

    # Dashboard
    cd dashboard && npm install
    ```

3. Run tests:

    ```bash
    # SDK tests
    cd sdk && pytest

    # Collector tests
    cd collector && pytest

    # Dashboard
    cd dashboard && npm run build
    ```

4. Create a branch, make changes, submit a PR.

## Areas for Contribution

- New framework integrations
- Dashboard improvements
- Documentation
- Bug fixes
- Performance optimizations

## Code Standards

- Python: type hints, async/await, Pydantic v2
- TypeScript: strict mode, React Query for data fetching
- All code must pass CI (lint + typecheck + tests)
