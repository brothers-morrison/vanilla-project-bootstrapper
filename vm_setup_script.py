#!/usr/bin/env python3
"""
VM Setup Script for Ralph-Loop Project

Converts the original bash setup script to Python for better maintainability
and cross-platform compatibility.

TODO:
- Upgrade to use Terraform instead of manual setup
- Explore CI/CD options (GitHub Actions, etc.)
- Automate GitHub CLI authentication
- Fix SSH key addition via gh CLI
"""

import subprocess
import sys
import os
import threading
import time
from typing import Optional, Union, List
from pathlib import Path

os.environ["PATH"] = (
    os.environ.get("PATH", "") + ":" + str(Path.home() / ".local" / "bin")
)


"""
# Source - https://stackoverflow.com/a/287944
# Posted by joeld, modified by community. See post 'Timeline' for change history
# Retrieved 2026-01-21, License - CC BY-SA 4.0
"""


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Spinner:
    """A spinner class for visual feedback during long-running operations."""

    def __init__(self, message: str = "Working", mode: str = "spinner"):
        self.message = message
        self.mode = mode
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time: Optional[float] = None

    SPINNER_FRAMES = ["|", "/", "-", "\\"]
    WAIT_FRAMES = [".", "..", "..."]
    HANG_FRAMES = ["!", "!!", "!!!", "?"]

    def _spin(self):
        frame_idx = 0
        while not self._stop_event.is_set():
            if self.mode == "spinner":
                frames = self.SPINNER_FRAMES
            elif self.mode == "waiting":
                frames = self.WAIT_FRAMES
            else:
                frames = self.HANG_FRAMES

            frame = frames[frame_idx % len(frames)]
            elapsed = time.time() - self._start_time if self._start_time else 0

            if self.mode == "hanging":
                status = (
                    f" {bcolors.WARNING}HANGING?{bcolors.ENDC}" if elapsed > 30 else ""
                )
            else:
                status = ""

            sys.stdout.write(f"\r{self.message}{frame}{status}")
            sys.stdout.flush()
            frame_idx += 1
            time.sleep(0.25)

        sys.stdout.write("\r" + " " * (len(self.message) + 20))
        sys.stdout.write("\r")
        sys.stdout.flush()

    def start(self):
        """Start the spinner."""
        self._stop_event.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, final_message: str = ""):
        """Stop the spinner with an optional final message."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1)
        if final_message:
            print(final_message)

    @staticmethod
    def run_with_spinner(command, **kwargs):
        """Run a command with a spinner showing progress."""
        spinner = Spinner(message="Running: ", mode="spinner")
        spinner.start()
        try:
            result = subprocess.run(command, **kwargs)
            spinner.stop("Done!")
            return result
        except Exception as e:
            spinner.stop()
            raise


class CommandRunner:
    """Utility class for running shell commands."""

    DEFAULT_TIMEOUT = 300

    @staticmethod
    def run(
        command: Union[str, List[str]],
        shell: bool = True,
        capture: bool = True,
        check: bool = True,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None,
        show_spinner: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        Execute a shell command and return the result.

        Args:
            command: Command to execute (string if shell=True, list otherwise)
            shell: Whether to run command through shell
            capture: Whether to capture stdout/stderr
            check: Whether to raise exception on non-zero exit
            cwd: Working directory for command
            env: Environment variables
            timeout: Timeout in seconds (default 300)
            show_spinner: Show spinner while running

        Returns:
            CompletedProcess object with stdout, stderr, returncode
        """
        effective_timeout = (
            timeout if timeout is not None else CommandRunner.DEFAULT_TIMEOUT
        )

        def run_command():
            return subprocess.run(
                command,
                shell=shell,
                capture_output=capture,
                text=True,
                check=check,
                cwd=cwd,
                env=env,
                timeout=effective_timeout,
            )

        spinner = None
        if show_spinner:
            cmd_str = command if isinstance(command, str) else " ".join(command)
            spinner = Spinner(message=f"Running: {cmd_str[:30]}...", mode="spinner")
            spinner.start()

        try:
            result = run_command()
            if spinner:
                spinner.stop(f"{bcolors.OKGREEN}Done!{bcolors.ENDC}")
            return result
        except subprocess.CalledProcessError as e:
            if spinner:
                spinner.stop()
            print(f"Command failed with exit code {e.returncode}", file=sys.stderr)
            print(f"stdout: {e.stdout}", file=sys.stderr)
            print(f"stderr: {e.stderr}", file=sys.stderr)
            raise
        except subprocess.TimeoutExpired as e:
            if spinner:
                spinner.stop()
            print(
                f"Command timed out after {effective_timeout} seconds", file=sys.stderr
            )
            raise
        except Exception as e:
            if spinner:
                spinner.stop()
            print(f"Unexpected error: {e}", file=sys.stderr)
            raise


class VMSetup:
    """Main setup class for configuring VM for Ralph-Loop."""

    def __init__(
        self, github_repo: str, email: str, api_key: str, project_repo: str = ""
    ):
        self.github_repo = github_repo
        self.project_repo = project_repo
        self.email = email
        self.api_key = api_key
        self.runner = CommandRunner()

    def color(self, message: str):
        print(f"\n{bcolors.OKGREEN}{message}{bcolors.ENDC}\n")

    def h1(self, message: str, decorative_char="=", line_length=40):
        """Print a formatted section header."""
        print(f"\n{bcolors.OKGREEN}{decorative_char * line_length}{bcolors.ENDC}")
        print(f"  {message}")
        print(f"{bcolors.OKGREEN}{decorative_char * line_length}{bcolors.ENDC}\n")

    def h2(self, message: str, decorative_char="=", line_length=40):
        print(
            f"\n{decorative_char * line_length}  {message}  {decorative_char * line_length}\n"
        )

    def clone_and_configure_git(self):
        """Clone repository and configure Git settings."""
        self.h1("Cloning Repository and Configuring Git")

        print(
            "NOTE: GitHub Personal Access Tokens (PAT) can only be used with HTTPS, not SSH"
        )
        print(
            "See: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens"
        )

        # Clone repository
        print(f"\nCloning repository: {self.github_repo}")
        self.runner.run(["git", "clone", self.github_repo])

        # Configure Git globally
        print("\nConfiguring Git user settings...")
        self.runner.run(["git", "config", "--global", "user.email", self.email])
        self.runner.run(["git", "config", "--global", "user.name", "Ralph Wiggum"])

        print("✓ Git configuration complete")

    def setup_nodejs(self):
        """Install Node.js and npm."""
        self.h1("Installing Node.js")

        # Install Node.js
        print("Installing Node.js 20.x...")
        self.runner.run(
            "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -",
            shell=True,
        )
        os.system("sudo apt install -y nodejs")

        # Verify installation
        result = self.runner.run(["node", "--version"])
        print(f"✓ Node.js installed: {result.stdout.strip()}")

        result = self.runner.run(["npm", "--version"])
        print(f"✓ npm installed: {result.stdout.strip()}")

    def setup_api_key(self):
        """Configure OpenRouter API key."""
        self.h1("Setting Up API Key")

        print("Setting OPENROUTER_API_KEY environment variable...")
        os.environ["OPENROUTER_API_KEY"] = self.api_key

        # Add to .bashrc for persistence
        bashrc_path = Path.home() / ".bashrc"
        export_line = f'export OPENROUTER_API_KEY="{self.api_key}"\n'

        with open(bashrc_path, "a") as f:
            f.write(f"\n# Added by VM setup script\n{export_line}")

        print("✓ API key configured and added to .bashrc")

    def setup_playwright(self):
        """Install Playwright and its dependencies."""
        self.h1("Installing Playwright")

        print("Installing Playwright dependencies...")
        self.runner.run(["npx", "playwright", "install-deps"])

        print("Installing Playwright browsers...")
        self.runner.run(["npx", "playwright", "install"])

        print("✓ Playwright installation complete")

    def setup_github_cli(self):
        """Install and configure GitHub CLI."""
        self.h1("Setting Up GitHub CLI")

        print(
            "# taken from https://gist.github.com/Manoj-Paramsetti/dc957bdd6a4430275d0fc28a0dc43ae9#official-sources"
        )

        print("WTF Github, why is this so complicated... ?")
        print(
            "https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian-ubuntu-linux-raspberry-pi-os-apt\n\n"
        )
        github_repo_setup_contents = """
        # https://github.com/cli/cli/blob/trunk/docs/install_linux.md#debian-ubuntu-linux-raspberry-pi-os-apt
(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
	&& sudo mkdir -p -m 755 /etc/apt/keyrings \
	&& out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
	&& cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
	&& sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
	&& sudo mkdir -p -m 755 /etc/apt/sources.list.d \
	&& echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
	&& sudo apt update \
	&& sudo apt install gh -y
        """
        github_repo_setup = Path.home() / "github_repo.sh"
        # Write out the github commands above, too painful to try to convert to python calls...
        with open(github_repo_setup, "w") as f:
            f.write(github_repo_setup_contents)

        os.system(f"sudo chmod +x {str(github_repo_setup)}")
        os.system(f"exec {str(github_repo_setup)}")

        print("Installing GitHub CLI...")
        os.system(f"sudo apt install -y gh")

        self.h1("  MANUAL STEP REQUIRED: GitHub CLI Authentication")
        print("\nPlease run the following command manually and follow the prompts:")
        self.color("  gh auth login")
        print("\nThis will authenticate you with GitHub interactively.")
        print("TODO: Explore automation options for this step\n")
        os.system("gh auth login")

    def setup_ssh_keys(self):
        """Generate SSH keys for GitHub."""
        self.h1("Setting Up SSH Keys")

        ssh_key_path = Path.home() / ".ssh" / "id_ed25519"

        do_generate_key = True
        if ssh_key_path.exists():
            print(f"SSH key already exists at {ssh_key_path}")
            response = input("Do you want to overwrite it? (y/N): ")
            if response.lower() != "y":
                print("Skipping SSH key generation")
                do_generate_key = False

        if do_generate_key:
            self.h1(f"Generating SSH key with email: {self.email}")
            self.h2("MANUAL STEP: You will be prompted for a passphrase")

            try:
                self.runner.run(
                    ["ssh-keygen", "-t", "ed25519", "-C", self.email],
                    capture=False,  # Let user see prompts
                )
            except subprocess.CalledProcessError:
                print("SSH key generation was cancelled or failed")
                return

        pub_key_path = Path(str(ssh_key_path) + ".pub")
        if pub_key_path.exists():
            with open(pub_key_path, "r") as f:
                pub_key = f.read().strip()

            self.h1("SSH Public Key Generated")
            print(f"\nYour public key:\n{bcolors.OKBLUE}{pub_key}{bcolors.ENDC}\n")
            print("Please add this key to your GitHub account:")
            print("  https://github.com/settings/keys\n\n")

            print("We'll wait while you now paste your SSH key into GitHub CLI...")
            os.system("sleep 3s")
            # print("\nNote: The 'gh ssh-key add' command currently fails with:")
            # print("  'HTTP 403: Resource not accessible by personal access token'")
            # print("TODO: adjust git remote to use SSH rather than HTTPS when performing git clone \n")
        else:
            print("SSH key file not found after generation")

    def sync_repository(self, repo_name: str):
        """Fetch, pull, and push repository changes."""
        self.h1("Syncing Repository")

        repo_path = Path(repo_name)
        if not repo_path.exists():
            print(f"Repository directory '{repo_name}' not found")
            return

        print(f"Working in repository: {repo_path}")

        # Fetch updates
        print("Fetching from remote...")
        self.runner.run(["git", "fetch"], cwd=str(repo_path))

        # Pull changes
        print("Pulling changes...")
        try:
            self.runner.run(["git", "pull"], cwd=str(repo_path))
        except subprocess.CalledProcessError as e:
            print(f"Warning: git pull failed: {e}")

        # Push changes
        print("Pushing to remote...")
        try:
            self.runner.run(
                ["git", "push", "--set-upstream", "origin", "main"], cwd=str(repo_path)
            )
        except subprocess.CalledProcessError as e:
            print(f"Warning: git push failed: {e}")
            print("You may need to authenticate or set up the remote properly")

    def setup_opencode(self):
        """Install OpenCode AI coding agent."""
        self.h1("Installing OpenCode")

        print("Installing OpenCode AI coding agent...")
        spinner = Spinner(message="Downloading OpenCode...", mode="spinner")
        spinner.start()
        try:
            self.runner.run(
                "curl -fsSL https://opencode.ai/install | bash",
                shell=True,
                timeout=120,
            )
            spinner.stop(f"{bcolors.OKGREEN}OpenCode installed!{bcolors.ENDC}")
        except subprocess.TimeoutExpired:
            spinner.stop()
            print(
                f"{bcolors.FAIL}OpenCode installation timed out after 120 seconds{bcolors.ENDC}"
            )
            raise

        print("✓ OpenCode installation complete")
        print("\nNext: Run 'opencode' to start, then use /connect to authenticate")

    def setup_juggle(self):
        """Install Juggle CLI for Ralph Loops."""
        self.h1("Installing Juggle")

        print("Installing Juggle CLI...")
        spinner = Spinner(message="Downloading Juggle...", mode="spinner")
        spinner.start()
        try:
            self.runner.run(
                "curl -sSL https://raw.githubusercontent.com/ohare93/juggle/main/install.sh | bash",
                shell=True,
                timeout=120,
            )
            spinner.stop(f"{bcolors.OKGREEN}Juggle installed!{bcolors.ENDC}")
        except subprocess.TimeoutExpired:
            spinner.stop()
            print(
                f"{bcolors.FAIL}Juggle installation timed out after 120 seconds{bcolors.ENDC}"
            )
            raise

        juggle_dir = Path.home() / ".juggle"
        juggle_dir.mkdir(exist_ok=True)

        config_source = Path(__file__).parent / "juggle.conf"
        config_dest = juggle_dir / "config.json"

        if config_source.exists():
            import shutil

            shutil.copy(config_source, config_dest)
            print(f"✓ Copied juggle.conf to {config_dest}")

        print("✓ Juggle installation complete")
        print(
            "\nRun 'juggle init' to configure, then 'juggle sessions create <name>' to start"
        )

    def configure_juggle(self):
        """Configure and start Juggle daemon with OpenCode provider."""
        self.h1("Configuring Juggle")

        juggle_bin = str(Path.home() / ".local" / "bin" / "juggle")

        if not Path(juggle_bin).exists():
            print("Juggle not installed. Running setup_juggle first...")
            self.setup_juggle()

        juggle_env = os.environ.copy()
        juggle_env["PATH"] = (
            str(Path.home() / ".local" / "bin") + ":" + juggle_env.get("PATH", "")
        )

        juggle_commands = [
            ("Initializing juggle project", [juggle_bin, "init"]),
            (
                "Setting opencode as default provider",
                [juggle_bin, "config", "provider", "set", "opencode"],
            ),
            (
                "Creating session 'ralph-loop'",
                [juggle_bin, "sessions", "create", "ralph-loop"],
            ),
            (
                "Creating initial ball",
                [juggle_bin, "start", "Initial Ralph Loop setup", "-s", "ralph-loop"],
            ),
            (
                "Starting juggle daemon",
                [
                    juggle_bin,
                    "agent",
                    "run",
                    "ralph-loop",
                    "--daemon",
                    "--provider",
                    "opencode",
                ],
            ),
        ]

        for i, (message, cmd) in enumerate(juggle_commands):
            spinner = Spinner(message=message + "...", mode="spinner")
            is_last = i == len(juggle_commands) - 1
            timeout = 30 if is_last else 60

            spinner.start()
            try:
                self.runner.run(
                    cmd,
                    cwd=str(Path.cwd()),
                    env=juggle_env,
                    check=False,
                    timeout=timeout,
                )
                spinner.stop(f"{bcolors.OKGREEN}{message} - done{bcolors.ENDC}")
            except subprocess.TimeoutExpired:
                spinner.stop()
                if not is_last:
                    print(
                        f"{bcolors.WARNING}Warning: {message} timed out after {timeout}s, continuing...{bcolors.ENDC}"
                    )
                else:
                    print(
                        f"{bcolors.FAIL}{message} timed out after {timeout}s{bcolors.ENDC}"
                    )
                    raise

        print("✓ Juggle daemon started successfully")
        print("\nUse 'juggle agent run --monitor ralph-loop' to monitor progress")

    def setup_uv_pip(self):
        """Install uv and pip dependencies."""
        self.h1("Setting uv / up Pip Dependencies")

        print("Installing uv package manager...")
        spinner = Spinner(message="Downloading uv...", mode="spinner")
        spinner.start()
        try:
            self.runner.run(
                "curl -LsSf https://astral.sh/uv/install.sh | sh",
                shell=True,
                timeout=120,
            )
            spinner.stop(f"{bcolors.OKGREEN}uv installed!{bcolors.ENDC}")
        except subprocess.TimeoutExpired:
            spinner.stop()
            print(
                f"{bcolors.FAIL}uv installation timed out after 120 seconds{bcolors.ENDC}"
            )
            raise

        print("✓ uv installation complete")

    def start_ralph_loop(self, session_name: str = "default"):
        """Start a Ralph Loop using Juggle with OpenCode as the agent.

        Args:
            session_name: Name of the juggle session to use
        """
        self.h1("Starting Ralph Loop")

        print(f"Importing spec to juggle session '{session_name}'...")
        spec_path = Path("spec.md")

        if spec_path.exists():
            self.runner.run(
                ["juggle", "import", "spec", str(spec_path)],
                cwd=str(Path.cwd()),
                check=False,
            )
        else:
            print(f"Warning: spec.md not found at {spec_path}")

        print(f"Starting juggle daemon with opencode agent...")
        self.runner.run(
            ["juggle", "--daemon", "agent", "run", session_name],
            cwd=str(Path.cwd()),
            check=False,
        )

        print("✓ Ralph Loop started")
        print("\nUse 'juggle' to view the TUI and monitor progress")

    def run_full_setup(self, max_duration: int = 300):
        """Execute the complete setup process.

        Args:
            max_duration: Maximum duration in seconds (default 300 = 5 minutes)
        """
        import signal

        print("\n" + "=" * 70)
        print("  Ralph-Loop VM Setup Script")
        print(f"  Max duration: {max_duration} seconds")
        print("=" * 70)

        start_time = time.time()

        def timeout_handler(signum, frame):
            elapsed = time.time() - start_time
            print(
                f"\n{bcolors.FAIL}Setup timed out after {elapsed:.1f} seconds!{bcolors.ENDC}",
                file=sys.stderr,
            )
            sys.exit(1)

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(max_duration)

        try:
            self.setup_opencode()
            elapsed = time.time() - start_time
            print(
                f"{bcolors.OKCYAN}[{elapsed:.1f}s] OpenCode setup complete{bcolors.ENDC}"
            )

            self.configure_juggle()
            elapsed = time.time() - start_time
            print(
                f"{bcolors.OKCYAN}[{elapsed:.1f}s] Juggle configuration complete{bcolors.ENDC}"
            )

            self.setup_uv_pip()
            elapsed = time.time() - start_time
            print(f"{bcolors.OKCYAN}[{elapsed:.1f}s] uv setup complete{bcolors.ENDC}")

            signal.alarm(0)

            total_time = time.time() - start_time
            self.h1("Setup Complete!")
            print(f"Total time: {total_time:.1f} seconds")
            print("Your VM is now configured for Ralph-Loop development.")
            print("\nNext steps:")
            print(
                "  1. Run 'opencode' to start OpenCode, then /connect to authenticate"
            )
            print("  2. Run 'juggle init' to configure Juggle")
            print("  3. Start developing!")

        except Exception as e:
            signal.alarm(0)
            elapsed = time.time() - start_time
            print(
                f"\n❌ Setup failed after {elapsed:.1f} seconds with error: {e}",
                file=sys.stderr,
            )
            sys.exit(1)


def main():
    """Main entry point for the setup script."""

    # Configuration - IMPORTANT: Do not hardcode sensitive values!
    # These should be passed as environment variables or command-line arguments
    GITHUB_REPO = os.getenv(
        "GITHUB_REPO", "https://github.com/sandstream/Ralph-Loop.git"
    )
    EMAIL = os.getenv(
        "GIT_EMAIL", "{{your-masked-github-email-here@users.noreply.github.com}}"
    )
    API_KEY = os.getenv(
        "OPENROUTER_API_KEY", "{{inject-your-key-here-do-not-hardcode}}"
    )
    PROJECT_REPO = os.getenv("PROJECT_REPO", "")

    # Validate configuration
    if "{{" in EMAIL or "{{" in API_KEY:
        print(
            "\n❌ ERROR: Please configure environment variables before running!",
            file=sys.stderr,
        )
        print("\nRequired environment variables:")
        print("  export GIT_EMAIL='your-email@users.noreply.github.com'")
        print("  export OPENROUTER_API_KEY='your-api-key-here'")
        print(
            "  export GITHUB_REPO='https://github.com/your-username/your-repo.git'  # optional"
        )
        sys.exit(1)

    # Run setup
    setup = VMSetup(
        github_repo=GITHUB_REPO, email=EMAIL, api_key=API_KEY, project_repo=PROJECT_REPO
    )

    setup.run_full_setup()


if __name__ == "__main__":
    main()
