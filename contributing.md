# Contributing to SofaScraper

Thank you for your interest in contributing! Whether you're fixing a bug, adding a new feature, improving documentation, or suggesting an idea - all contributions are welcome.

Please take a moment to read this guide before opening an issue or pull request.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Branching Strategy](#branching-strategy)
- [Making Changes](#making-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

---

## Code of Conduct

Please be respectful and constructive in all interactions. We are committed to keeping this project a welcoming space for everyone.

---

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/kinghuba/sofascraper.git
   cd sofascraper
   ```
3. Add the upstream remote so you can keep your fork up to date:
   ```bash
   git remote add upstream https://github.com/kinghuba/sofascraper.git
   ```

---

## Development Setup

We recommend using [`uv`](https://github.com/astral-sh/uv) for dependency management and [`ruff`](https://github.com/astral-sh/ruff) for linting and formatting.

### Install dependencies with `uv`

```bash
pip install uv
uv sync
```

### Install Playwright browsers

```bash
playwright install chromium
```

### Lint and format with `ruff`

```bash
# Check for linting issues
ruff check .

# Auto-fix where possible
ruff check . --fix

# Format code
ruff format .
```

You can configure `ruff` in `pyproject.toml` under `[tool.ruff]`.

---

## Project Structure

```
sofascraper/
├── cli/           # Click CLI entry point and command definitions
├── core/          # Scraping logic, Playwright management, sport-specific scrapers
├── storage/       # Data persistence (JSON, DB)
└── utils/         # Helpers, enums, dataclasses, constants
```

---

## Branching Strategy

- **`main`** - stable, release-ready code.
- **`develop`** - integration branch for ongoing work. Branch from here.
- **Feature branches** - named `feature/<short-description>` (e.g. `feature/tennis-scraper`).
- **Bug fix branches** - named `fix/<short-description>` (e.g. `fix/popup-timeout`).

Always branch from `develop`, not `main`.

```bash
git checkout develop
git pull upstream develop
git checkout -b feature/my-new-feature
```

---

## Making Changes

- Keep each pull request focused on a single concern.
- Write clear, descriptive commit messages. Prefer the imperative mood: `Add tennis scraper` rather than `Added tennis scraper`.
- If your change touches a public-facing interface (CLI options, output format, data classes), update the relevant section of `README.md`.
- If you add a new dependency, add it via `uv`:
  ```bash
  uv add <package>
  ```

---

## Code Style

This project uses `ruff` for both linting and formatting. Before committing, always run:

```bash
ruff check . --fix
ruff format .
```

Additional conventions:

- Type annotations are required for all function signatures.
- Use dataclasses (from `utils/football_data_classes.py`) for structured data - avoid raw dicts in business logic.
- Use `logging` rather than `print` throughout.
- Follow the existing async/await patterns in `BaseScraper` and `FootballScraper`.

---

## Testing

Tests are not yet part of the alpha release, but contributions that add test coverage are especially welcome.

When tests are introduced, run them with:

```bash
pytest
```

For new scrapers or parsers, aim to cover at minimum:

- Happy-path parsing of a representative API response fixture.
- Edge cases: missing fields, null values, unexpected types.

---

## Submitting a Pull Request

1. Push your branch to your fork:
   ```bash
   git push origin feature/my-new-feature
   ```
2. Open a pull request against the **`develop`** branch of this repository.
3. Include:
   - A clear description of what the PR does and why.
   - Steps to reproduce the issue being fixed, if applicable.
   - Any known limitations or follow-up work.
4. A maintainer will review your PR. Please be responsive to review comments - address them and push updates to the same branch.
5. Once approved, your PR will be merged into `develop`.

---

## Reporting Bugs

Open a GitHub Issue and include:

- A clear, descriptive title.
- Steps to reproduce the bug.
- Expected behaviour vs. actual behaviour.
- Relevant log output (run with `--verbose` to get full debug logs).
- Your Python version and operating system.

---

## Feature Requests

Open a GitHub Issue with the label `enhancement`. Describe:

- The problem you're trying to solve.
- Your proposed solution or idea.
- Any alternatives you've considered.

Discussing an idea in an issue before opening a PR helps avoid wasted effort and makes it easier to get contributions merged.

---

## Questions?

Feel free to open an issue if you have a question or need clarification. I am happy to help.