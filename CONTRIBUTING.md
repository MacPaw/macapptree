# Contributing to macapptree

Thank you for your interest in contributing! This document covers how to set up the project locally, the workflow for submitting changes, and our conventions.

---

## Prerequisites

- macOS (the package uses macOS-only APIs)
- Python 3.8 or later
- Your terminal must have **Accessibility** permission granted in System Settings → Privacy & Security → Accessibility

---

## Development setup

```bash
# 1. Clone the repo
git clone https://github.com/MacPaw/macapptree.git
cd macapptree

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install with dev dependencies
pip install -e ".[dev]"
```

---

## Running tests

```bash
pytest
```

Since the library relies on live macOS Accessibility APIs, most tests require a running macOS session with the appropriate permissions. Tests that depend on a specific application being open are skipped automatically when that app is not available.

---

## Submitting changes

1. Fork the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
2. Make your changes and commit with a clear message:
   ```
   feat: add support for AXSheet elements
   fix: handle missing kCGWindowBounds gracefully
   ```
3. Open a pull request against `main` and fill in the PR template.

---

## Code conventions

- Follow [PEP 8](https://peps.python.org/pep-0008/) style.
- Keep public functions typed where practical.
- No comments explaining *what* the code does — names should do that. Comments should only explain *why* (hidden constraints, workarounds, non-obvious invariants).
- Keep pull requests focused: one logical change per PR.

---

## Reporting bugs

Use [GitHub Issues](https://github.com/MacPaw/macapptree/issues). Include:

- macOS version and Python version
- Minimal reproducible example
- Expected vs. actual behavior

For security vulnerabilities, follow the process described in [SECURITY.md](SECURITY.md) instead.

---

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
