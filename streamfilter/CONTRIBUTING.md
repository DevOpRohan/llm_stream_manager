# Contributing to streamfilter

Thank you for your interest in contributing to **streamfilter**!  
We welcome all improvements, bug fixes, documentation enhancements, and new features.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork:
   ```bash
   git clone https://github.com/<your-username>/streamfilter.git
   cd streamfilter
   ```
3. Create a virtual environment and install dev dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```

## Branching & Workflow

- Create a new branch for each feature or fix:
  ```bash
  git checkout -b feature/my-new-feature
  ```
- Make your changes locally.
- Run tests and linters before committing (see below).
- Commit with clear messages. Follow the [Conventional Commits](https://www.conventionalcommits.org/) style:
  ```text
  feat(core): add CONTINUE_DROP and CONTINUE_PASS actions
  fix(decorator): correct token-mode flush logic
  docs: improve CONTRIBUTING.md
  ```

## Testing

We aim for **100% test coverage**.  

- Run the full test suite:
  ```bash
  pytest
  ```
  or via unittest:
  ```bash
  python3 -m unittest discover -v
  ```
- Add tests for any new behavior or bug fix in the `tests/` directory.

## Linting & Formatting

- Run `ruff` for linting:
  ```bash
  ruff .
  ```
- Type check with `mypy`:
  ```bash
  mypy streamfilter
  ```
- Optionally run pre-commit hooks if configured:
  ```bash
  pre-commit run --all-files
  ```

## Documentation

- Update `README.md` and `doc.md` with new features or changes.
- Keep examples in sync with code.

## Benchmarking

- For performance-sensitive changes, update or rerun `bench.py`.

## Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```
2. Open a Pull Request against the `main` branch of the upstream repository.
3. Ensure all CI checks pass: tests, coverage, linting, mypy.
4. Address review comments and iterate.

## Code of Conduct

All contributors agree to abide by the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

---
_We appreciate your contributions and feedback!_  🚀