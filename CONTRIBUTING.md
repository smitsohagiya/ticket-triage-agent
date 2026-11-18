# Contributing

## Setup

```bash
make setup   # installs dependencies with uv and the git hooks
```

## Before you push

```bash
make check   # lint, format check, type check, tests with coverage
```

## Commits and pull requests

- Use Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- One issue per change. Work on a branch named `feat/<short-name>` or `fix/<short-name>`.
- Open a pull request that says what changed, why, and how it was tested. CI must pass before merge.
