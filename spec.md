# Virtual Machine bootstrapper

The purpose of this script is to help set up Virtual Machines so that they are fully able to run autonomously.

## 1. Prerequisites : OS Level setup

bash setup.sh script checks OS level for [bash, python, venv]
After that, the rest of all setup is done by python.  
But these prerequisites insure that python can be run successfully.

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

After running the setup script, the virtual environment will be active. In future s>

```bash
source .venv/bin/activate
```

### 3. Run Python vm_setup_script.py

This script will check for and set up a number of things including:
0. OS Updates
1. OpenCode install & config
2. Juggle install & config
3. uv / Pip dependencies
