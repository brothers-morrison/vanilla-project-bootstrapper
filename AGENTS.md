# Agent Guidelines for vanilla-project-bootstrapper

## Overview

Simple Python "Hello World" console application using `src/` layout with pytest for testing.

## Commands

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### Running the Application

```bash
python -m hello_world
hello-world
```

### Testing

```bash
pytest                           # Run all tests
pytest tests/test_hello_world.py # Run single test file
pytest tests/test_hello_world.py::test_hello_world  # Run single test
pytest -k "hello"                # Run tests matching pattern
pytest -v                        # Verbose output
pytest -v --tb=long              # Detailed failure info
```

### Linting/Formatting

Project has no linting configured. If adding:
```bash
pip install ruff
ruff check .     # Lint
ruff format .    # Format
```

## Code Style Guidelines

### General

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide
- Follow [PEP 257](https://peps.python.org/pep-0257/) for docstrings
- Use 4 spaces for indentation, no tabs
- Maximum line length: 88 characters
- Use trailing commas in multi-line structures

### Naming Conventions

- **Modules**: `snake_case` (e.g., `hello_world.py`)
- **Classes**: `PascalCase` (e.g., `MyClass`)
- **Functions**: `snake_case` (e.g., `def hello_world()`)
- **Variables**: `snake_case` (e.g., `my_variable`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_SIZE`)
- **Private items**: Prefix with underscore (e.g., `_private_func()`)

### Type Hints

- Always use type hints for function signatures
- Use built-in types directly (e.g., `str`, `int`, not `typing.Str`)
- Use `Optional[X]` instead of `X | None`

```python
def greet(name: str, times: int = 1) -> list[str]:
    """Return a greeting message."""
    return [f"Hello, {name}!"] * times
```

### Imports

- Standard library first, then third-party, then local
- Group imports: standard library, third-party, local
- Use absolute imports
- Sort imports alphabetically within groups

```python
import os
from pathlib import Path

import pytest

from hello_world.main import hello_world
```

### Docstrings

- Use triple quotes `"""`
- First line: imperative mood summary
- Args, Returns, Raises sections for functions

```python
def function(param: str) -> int:
    """Short summary.
    
    Args:
        param: Description
        
    Returns:
        Description
        
    Raises:
        ValueError: When invalid
    """
```

### Error Handling

- Use specific exceptions
- Include context in error messages
- Don't catch broad `Exception` without reason

```python
def read_config(path: Path) -> dict:
    """Read configuration from file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e
```

### Testing

- Test files: `tests/test_<module>.py`
- Test classes: `Test<Feature>`
- Test functions: `test_<description>`
- One assertion per test when practical

```python
def test_hello_world_returns_greeting():
    """Test that hello_world returns expected greeting."""
    result = hello_world()
    assert result == "Hello, World!"
    assert isinstance(result, str)
```

### Project Structure

```
src/
└── hello_world/
    ├── __init__.py      # Package init, version
    ├── __main__.py      # Module entry point
    └── main.py          # Main logic
tests/
├── __init__.py
└── test_hello_world.py
pyproject.toml           # Project config
requirements.txt         # Dependencies
```

### Configuration (pyproject.toml)

- Use `pyproject.toml` for project metadata
- Configure pytest under `[tool.pytest.ini_options]`
- Use `src/` layout with `[tool.setuptools.packages.find]`

## Key Files

- `src/hello_world/main.py`: Main application logic
- `src/hello_world/__main__.py`: Module entry point (`python -m hello_world`)
- `tests/test_hello_world.py`: Test suite
- `pyproject.toml`: Project configuration

## Ralph Loop (Autonomous Agent)

### Running Continuous Agent Loops

To continually run juggle sessions and pick up all incomplete balls:

```bash
# Run agent against ALL balls in repo (recommended for Ralph Loop)
juggle agent run all

# Run with specific number of iterations (default: 10)
juggle agent run all --iterations 50

# Run as background daemon (persists when TUI exits)
juggle agent run all --daemon

# Run with delay between iterations (in minutes)
juggle agent run all --delay 5
```

The `all` session special ID runs the agent against ALL balls in the repo that are not complete, without requiring a session file.

### How Balls Get Marked Complete

The juggle agent loop automatically handles marking balls as complete:

1. **Agent instructions** (from `juggle export --session all --format agent`) include:
   - Select one ball per iteration
   - Complete all acceptance criteria
   - Update ball state using: `juggle update <ball-id> --state complete`

2. **Completion signals** the agent outputs:
   - `<promise>CONTINUE</promise>` - Ball complete, more remain
   - `<promise>COMPLETE</promise>` - All balls complete

3. **Manual completion** (via TUI or CLI):
   - TUI: Select ball, press `c` to complete
   - CLI: `juggle <ball-id> complete`

### Configuration

```bash
# Set provider to opencode (already configured globally)
juggle config provider set opencode

# Set iteration delay (global)
juggle config delay set 5
```
