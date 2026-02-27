# vanilla-project-bootstrapper

Idea:
Help quickly set up Python projects with minimal (but decent) gitignore and set up project layout for success.
I shouldn't need to re-invent the wheel every time, remember to add /.venv/ and /pycache/ to .gitignore EVERY TIME, lets just build on the backs of giants.
At a high level for a greenfield project, we plan to: 
  1. Clone in the repo files
  2. Remove all git folders (clearing the git history and ties to this project),
  3. run the setup scripts (and make it as automated as humanly possible)

## Features
** Main feature are the /setup.sh and /vm_setup_script.py which take a vanilla ubuntu linux machine, and set up everything on them that needs to be configured for a fully working opencode/claude code autonomous ai agent.
** this project ALSO provides a complete Python "Hello World" console application,


- ✅ **Modular package structure** using `src/` layout
- ✅ **Runnable as module** with `__main__.py`
- ✅ **Test infrastructure** with pytest
- ✅ **Automated setup script** that handles environment configuration
- ✅ **Modern project configuration** using `pyproject.toml`
- ✅ **Command-line entry point** via `hello-world` command
- ✅ **Comprehensive `.gitignore`** for Python projects

## Project Structure
Also see: [https://medium.com/the-pythonworld/best-practices-for-structuring-a-python-project-like-a-pro-1265363836f9]

```
.
├── src/
│   └── hello_world/
│       ├── __init__.py      # Package initialization
│       ├── __main__.py      # Entry point for running as module
│       └── main.py          # Main application logic
├── tests/
│   ├── __init__.py          # Test package initialization
│   └── test_hello_world.py # Sample pytest test
├── pyproject.toml           # Project configuration and metadata
├── requirements.txt         # Project dependencies
├── setup.sh                 # Automated setup script
├── .gitignore              # Comprehensive Python gitignore
└── README.md               # This file
```

## Quick Start

### 1. Run the Setup Script

The `setup.sh` script automates the entire setup process:

```bash
bash setup.sh
```

This script will:
- ✅ Check for Python 3 and install Python 3.12 (LTS) if needed
- ✅ Verify the `venv` module is available
- ✅ Create a virtual environment in `.venv/`
- ✅ Activate the virtual environment
- ✅ Upgrade pip to the latest version
- ✅ Install dependencies from `requirements.txt`
- ✅ Install the package in editable mode

### 2. Activate the Virtual Environment

After running the setup script, the virtual environment will be active. In future sessions, activate it manually:

```bash
source .venv/bin/activate
```

### 3. Run the Hello World Application

You can run the application in multiple ways:

```bash
# As a Python module
python -m hello_world

# Or using the installed command
hello-world
```

Both methods will output:
```
Hello, World!
```

### 4. Run Tests

Execute the test suite using pytest:

```bash
pytest
```

Expected output:
```
================================================= test session starts ==================================================
platform linux -- Python 3.12.x, pytest-9.0.2, pluggy-1.6.0
rootdir: /path/to/vanilla-project-bootstrapper
configfile: pyproject.toml
testpaths: tests
collected 1 item

tests/test_hello_world.py::test_hello_world PASSED                                                               [100%]

================================================== 1 passed in 0.01s ===================================================
```

## Development

### Manual Setup (Alternative to setup.sh)

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install package in editable mode
pip install -e .
```

### Adding New Features

1. Add your code to `src/hello_world/`
2. Add tests to `tests/`
3. Run tests with `pytest`
4. Update dependencies in `requirements.txt` if needed

### Deactivating the Virtual Environment

When you're done working:

```bash
deactivate
```

## Requirements

- **Python**: 3.8 or higher (3.12 LTS recommended)
- **Operating System**: Linux, macOS, or WSL on Windows
- **Dependencies**: Listed in `requirements.txt`
  - pytest >= 8.0.0

## Best Practices Included

This project demonstrates several Python best practices:

1. **src/ Layout**: Package code is isolated in `src/` directory
2. **Proper Package Structure**: Includes `__init__.py` and `__main__.py`
3. **Testing**: Uses pytest with proper test structure
4. **Modern Configuration**: Uses `pyproject.toml` instead of `setup.py`
5. **Virtual Environment**: Isolates project dependencies
6. **Automated Setup**: Reduces manual configuration errors
7. **Comprehensive .gitignore**: Prevents committing unnecessary files
8. **Type Hints**: Functions include type annotations
9. **Documentation**: Includes docstrings following PEP 257

## License

MIT License - see LICENSE file for details
