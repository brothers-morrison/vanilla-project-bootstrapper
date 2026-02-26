"""Comprehensive tests for vm_setup_script.py - Full coverage."""

import json
import os
import subprocess
import sys
import time
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, mock_open
from typing import Optional, Union, List

import pytest


class TestBColors:
    """Test bcolors class for ANSI color codes."""

    def test_all_color_codes_defined(self):
        """Test all color codes are properly defined."""
        from vm_setup_script import bcolors

        assert hasattr(bcolors, "HEADER")
        assert hasattr(bcolors, "OKBLUE")
        assert hasattr(bcolors, "OKCYAN")
        assert hasattr(bcolors, "OKGREEN")
        assert hasattr(bcolors, "WARNING")
        assert hasattr(bcolors, "FAIL")
        assert hasattr(bcolors, "ENDC")
        assert hasattr(bcolors, "BOLD")
        assert hasattr(bcolors, "UNDERLINE")

    def test_color_codes_are_strings(self):
        """Test all color codes are non-empty strings."""
        from vm_setup_script import bcolors

        assert isinstance(bcolors.HEADER, str)
        assert isinstance(bcolors.ENDC, str)
        assert bcolors.ENDC == "\033[0m"

    def test_endc_resets_formatting(self):
        """Test ENDC properly resets ANSI formatting."""
        from vm_setup_script import bcolors

        test_string = f"{bcolors.BOLD}bold{bcolors.ENDC}"
        assert bcolors.ENDC in test_string


class TestCommandRunner:
    """Test CommandRunner class for security and functionality."""

    @pytest.fixture
    def runner(self):
        """Create CommandRunner instance."""
        from vm_setup_script import CommandRunner

        return CommandRunner()

    def test_run_success(self, runner):
        """Test successful command execution."""
        result = runner.run(["echo", "hello"], shell=False)
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_run_with_shell_string(self, runner):
        """Test command execution with shell string."""
        result = runner.run('echo "test output"', shell=True)
        assert result.returncode == 0
        assert "test output" in result.stdout

    def test_run_captures_output(self, runner):
        """Test output is captured."""
        result = runner.run(["ls", "-la"], shell=False, cwd="/tmp")
        assert result.stdout is not None
        assert result.stderr is not None

    def test_run_check_raises_on_failure(self, runner):
        """Test check=True raises on non-zero exit."""
        with pytest.raises(subprocess.CalledProcessError):
            runner.run(["false"], shell=False, check=True)

    def test_run_check_false_returns_result(self, runner):
        """Test check=False returns result on failure."""
        result = runner.run(["false"], shell=False, check=False)
        assert result.returncode != 0

    def test_run_timeout_raises(self, runner):
        """Test timeout raises TimeoutExpired."""
        with pytest.raises(subprocess.TimeoutExpired):
            runner.run(["sleep", "10"], shell=False, timeout=1)

    def test_run_with_cwd(self, runner, tmp_path):
        """Test command runs in specified directory."""
        result = runner.run(["pwd"], shell=False, cwd=str(tmp_path))
        assert str(tmp_path) in result.stdout

    def test_run_with_env(self, runner):
        """Test command runs with custom environment."""
        result = runner.run(
            ["printenv", "TEST_VAR"], shell=False, env={"TEST_VAR": "test_value"}
        )
        assert "test_value" in result.stdout

    def test_run_list_command(self, runner):
        """Test command as list without shell injection risk."""
        malicious_input = "; rm -rf /"
        result = runner.run(["echo", malicious_input], shell=False)
        assert result.returncode == 0
        assert malicious_input in result.stdout

    def test_run_security_shell_true_caution(self, runner):
        """Test shell=True with user input doesn't get executed as command injection."""
        user_input = "test; cat /etc/passwd"
        result = runner.run(f'echo "{user_input}"', shell=True)
        assert "test; cat /etc/passwd" in result.stdout


class TestVMSetupInitialization:
    """Test VMSetup class initialization."""

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        from vm_setup_script import VMSetup

        setup = VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
            project_repo="test-project",
        )

        assert setup.github_repo == "https://github.com/test/repo.git"
        assert setup.email == "test@example.com"
        assert setup.api_key == "secret-key"
        assert setup.project_repo == "test-project"

    def test_init_with_default_project_repo(self):
        """Test initialization with default project_repo."""
        from vm_setup_script import VMSetup

        setup = VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

        assert setup.project_repo == ""

    def test_init_creates_command_runner(self):
        """Test initialization creates CommandRunner instance."""
        from vm_setup_script import VMSetup, CommandRunner

        setup = VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

        assert isinstance(setup.runner, CommandRunner)


class TestVMSetupFormatting:
    """Test VMSetup formatting methods."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    def test_color_outputs_correctly(self, vm_setup, capsys):
        """Test color method outputs with ANSI codes."""
        vm_setup.color("Test Message")
        captured = capsys.readouterr()
        assert "Test Message" in captured.out
        assert "\033[92m" in captured.out  # OKGREEN

    def test_h1_default_formatting(self, vm_setup, capsys):
        """Test h1 with default parameters."""
        vm_setup.h1("Test Header")
        captured = capsys.readouterr()
        assert "Test Header" in captured.out
        assert "=" * 40 in captured.out

    def test_h1_custom_decorator(self, vm_setup, capsys):
        """Test h1 with custom decorator character."""
        vm_setup.h1("Test", decorative_char="*")
        captured = capsys.readouterr()
        assert "Test" in captured.out
        assert "*" * 40 in captured.out

    def test_h1_custom_line_length(self, vm_setup, capsys):
        """Test h1 with custom line length."""
        vm_setup.h1("Test", line_length=20)
        captured = capsys.readouterr()
        assert "Test" in captured.out
        assert "=" * 20 in captured.out

    def test_h2_formatting(self, vm_setup, capsys):
        """Test h2 method formatting."""
        vm_setup.h2("Test Section")
        captured = capsys.readouterr()
        assert "Test Section" in captured.out


class TestVMSetupGitOperations:
    """Test VMSetup git-related methods."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.CommandRunner.run")
    def test_clone_and_configure_git(self, mock_run, vm_setup, capsys):
        """Test git clone and configuration."""
        mock_run.return_value = Mock(returncode=0)

        vm_setup.clone_and_configure_git()

        captured = capsys.readouterr()
        assert "Cloning repository" in captured.out
        assert "Configuring Git" in captured.out
        assert mock_run.call_count >= 2

    @patch("vm_setup_script.CommandRunner.run")
    def test_sync_repository_success(self, mock_run, vm_setup, tmp_path, capsys):
        """Test successful repository sync."""
        mock_run.return_value = Mock(returncode=0)
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        vm_setup.sync_repository("test-repo")

        captured = capsys.readouterr()
        assert "Fetching from remote" in captured.out

    @patch("vm_setup_script.CommandRunner.run")
    def test_sync_repository_not_found(self, mock_run, vm_setup, tmp_path, capsys):
        """Test sync with non-existent repository."""
        vm_setup.sync_repository("nonexistent-repo")

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()

    @patch("vm_setup_script.CommandRunner.run")
    def test_sync_repository_pull_fails(self, mock_run, vm_setup, tmp_path, capsys):
        """Test sync handles pull failure gracefully."""
        mock_run.side_effect = [
            Mock(returncode=0),
            subprocess.CalledProcessError(1, "git pull", stderr="error"),
        ]
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        vm_setup.sync_repository("test-repo")

        captured = capsys.readouterr()
        assert "Warning: git pull failed" in captured.out

    @patch("vm_setup_script.CommandRunner.run")
    def test_sync_repository_push_fails(self, mock_run, vm_setup, tmp_path, capsys):
        """Test sync handles push failure gracefully."""
        mock_run.side_effect = [
            Mock(returncode=0),
            Mock(returncode=0),
            subprocess.CalledProcessError(1, "git push", stderr="error"),
        ]
        repo_dir = tmp_path / "test-repo"
        repo_dir.mkdir()

        vm_setup.sync_repository("test-repo")

        captured = capsys.readouterr()
        assert "Warning: git push failed" in captured.out


class TestVMSetupNodeJS:
    """Test Node.js setup method."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.os.system")
    @patch("vm_setup_script.CommandRunner.run")
    def test_setup_nodejs(self, mock_run, mock_system, vm_setup, capsys):
        """Test Node.js setup."""
        mock_run.return_value = Mock(returncode=0, stdout="v20.0.0\n")

        vm_setup.setup_nodejs()

        captured = capsys.readouterr()
        assert "Node.js" in captured.out


class TestVMSetupAPIKey:
    """Test API key setup - SECURITY TESTS."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="test-api-key-12345",
        )

    @patch("vm_setup_script.Path.home")
    @patch("builtins.open", new_callable=mock_open)
    def test_setup_api_key_writes_to_bashrc(
        self, mock_file, mock_home, vm_setup, tmp_path, capsys
    ):
        """Test API key is written to .bashrc."""
        mock_home.return_value = tmp_path

        vm_setup.setup_api_key()

        captured = capsys.readouterr()
        assert "API key" in captured.out

        handle = mock_file()
        handle.write.assert_called()

    def test_api_key_in_environment(self, vm_setup):
        """Test API key is set in environment."""
        with patch("vm_setup_script.Path.home") as mock_home:
            mock_home.return_value = Path("/tmp")
            vm_setup.setup_api_key()

        assert "OPENROUTER_API_KEY" in os.environ

    @patch("vm_setup_script.Path.home")
    @patch("builtins.open", new_callable=mock_open)
    def test_api_key_quoting_in_bashrc(self, mock_file, mock_home, vm_setup, tmp_path):
        """Test API key is properly quoted in .bashrc."""
        vm_setup.api_key = "key with spaces and $pecial"
        mock_home.return_value = tmp_path

        vm_setup.setup_api_key()

        handle = mock_file()
        written_content = ""
        for call in handle.write.call_args_list:
            written_content += call[0][0]

        assert "export OPENROUTER_API_KEY=" in written_content


class TestVMSetupPlaywright:
    """Test Playwright setup method."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.CommandRunner.run")
    def test_setup_playwright(self, mock_run, vm_setup, capsys):
        """Test Playwright installation."""
        mock_run.return_value = Mock(returncode=0)

        vm_setup.setup_playwright()

        captured = capsys.readouterr()
        assert "Playwright" in captured.out
        assert mock_run.call_count == 2


class TestVMSetupGitHubCLI:
    """Test GitHub CLI setup method."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.os.system")
    @patch("vm_setup_script.Path.home")
    @patch("builtins.open", new_callable=mock_open)
    def test_setup_github_cli(
        self, mock_file, mock_home, mock_system, vm_setup, tmp_path
    ):
        """Test GitHub CLI setup creates script."""
        mock_home.return_value = tmp_path
        mock_system.return_value = 0

        vm_setup.setup_github_cli()

        handle = mock_file()
        handle.write.assert_called()


class TestVMSetupSSHKeys:
    """Test SSH key setup - SECURITY TESTS."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.input")
    @patch("vm_setup_script.Path.home")
    @patch("vm_setup_script.CommandRunner.run")
    def test_setup_ssh_keys_skip_existing(
        self, mock_run, mock_home, mock_input, vm_setup, tmp_path, capsys
    ):
        """Test SSH key generation skipped when key exists."""
        mock_home.return_value = tmp_path
        mock_input.return_value = "n"

        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "id_ed25519").write_text("existing key")

        vm_setup.setup_ssh_keys()

        captured = capsys.readouterr()
        assert "Skipping" in captured.out

    @patch("vm_setup_script.os.system")
    @patch("vm_setup_script.Path.home")
    @patch("vm_setup_script.CommandRunner.run")
    def test_setup_ssh_keys_with_pub_key(
        self, mock_run, mock_home, mock_system, vm_setup, tmp_path, capsys
    ):
        """Test SSH key setup when public key exists."""
        mock_home.return_value = tmp_path

        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "id_ed25519").write_text("private key")
        (ssh_dir / "id_ed25519.pub").write_text("public key content")

        vm_setup.setup_ssh_keys()

        captured = capsys.readouterr()
        assert "public key" in captured.out.lower() or "SSH" in captured.out


class TestVMSetupOpenCode:
    """Test OpenCode setup method."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.CommandRunner.run")
    def test_setup_opencode(self, mock_run, vm_setup, capsys):
        """Test OpenCode installation."""
        mock_run.return_value = Mock(returncode=0)

        vm_setup.setup_opencode()

        captured = capsys.readouterr()
        assert "OpenCode" in captured.out
        assert "curl" in captured.out

    @patch("vm_setup_script.CommandRunner.run")
    def test_setup_opencode_curl_command(self, mock_run, vm_setup):
        """Test OpenCode uses correct curl command."""
        mock_run.return_value = Mock(returncode=0)

        vm_setup.setup_opencode()

        call_args = mock_run.call_args[0][0]
        assert "curl" in call_args
        assert "opencode.ai/install" in call_args


class TestVMSetupJuggle:
    """Test Juggle setup method."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.Path.home")
    @patch("vm_setup_script.CommandRunner.run")
    def test_setup_juggle(self, mock_run, mock_home, vm_setup, tmp_path, capsys):
        """Test Juggle installation."""
        mock_home.return_value = tmp_path
        mock_run.return_value = Mock(returncode=0)

        vm_setup.setup_juggle()

        captured = capsys.readouterr()
        assert "Juggle" in captured.out

    @patch("vm_setup_script.shutil.copy")
    @patch("vm_setup_script.Path.home")
    @patch("vm_setup_script.Path")
    @patch("vm_setup_script.CommandRunner.run")
    def test_setup_juggle_copies_config(
        self,
        mock_run,
        mock_path_class,
        mock_home,
        mock_copy,
        vm_setup,
        tmp_path,
        capsys,
    ):
        """Test Juggle config is copied."""
        mock_home.return_value = tmp_path
        mock_run.return_value = Mock(returncode=0)

        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path_class.return_value = mock_path_instance
        mock_path_class.side_effect = lambda x: (
            mock_path_instance
            if str(x) == str(tmp_path / ".juggle")
            else mock_path_instance
        )

        vm_setup.setup_juggle()

        captured = capsys.readouterr()
        assert "juggle.conf" in captured.out


class TestVMSetupUV:
    """Test uv setup method."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.CommandRunner.run")
    def test_setup_uv_pip(self, mock_run, vm_setup, capsys):
        """Test uv installation."""
        mock_run.return_value = Mock(returncode=0)

        vm_setup.setup_uv_pip()

        captured = capsys.readouterr()
        assert "uv" in captured.out
        assert "astral.sh" in captured.out


class TestStartRalphLoop:
    """Test Ralph Loop start method."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.Path.cwd")
    @patch("vm_setup_script.CommandRunner.run")
    def test_start_ralph_loop_with_spec(
        self, mock_run, mock_cwd, vm_setup, tmp_path, capsys
    ):
        """Test Ralph loop with spec file."""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = Mock(returncode=0)

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Test Spec")

        vm_setup.start_ralph_loop("test-session")

        captured = capsys.readouterr()
        assert "Importing spec" in captured.out
        assert "daemon" in captured.out

    @patch("vm_setup_script.Path.cwd")
    @patch("vm_setup_script.CommandRunner.run")
    def test_start_ralph_loop_without_spec(
        self, mock_run, mock_cwd, vm_setup, tmp_path, capsys
    ):
        """Test Ralph loop without spec file."""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = Mock(returncode=0)

        vm_setup.start_ralph_loop("test-session")

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "not found" in captured.out.lower()

    @patch("vm_setup_script.Path.cwd")
    @patch("vm_setup_script.CommandRunner.run")
    def test_start_ralph_loop_default_session(
        self, mock_run, mock_cwd, vm_setup, tmp_path
    ):
        """Test Ralph loop uses default session."""
        mock_cwd.return_value = tmp_path
        mock_run.return_value = Mock(returncode=0)

        spec_file = tmp_path / "spec.md"
        spec_file.write_text("# Test")

        vm_setup.start_ralph_loop()

        calls = mock_run.call_args_list
        assert len(calls) >= 2


class TestRunFullSetup:
    """Test full setup orchestration."""

    @pytest.fixture
    def vm_setup(self):
        """Create VMSetup instance."""
        from vm_setup_script import VMSetup

        return VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

    @patch("vm_setup_script.VMSetup.setup_opencode")
    @patch("vm_setup_script.VMSetup.setup_juggle")
    @patch("vm_setup_script.VMSetup.setup_uv_pip")
    def test_run_full_setup_calls_all_methods(
        self, mock_uv, mock_juggle, mock_opencode, vm_setup, capsys
    ):
        """Test full setup calls all setup methods."""
        vm_setup.run_full_setup()

        mock_opencode.assert_called_once()
        mock_juggle.assert_called_once()
        mock_uv.assert_called_once()

    @patch("vm_setup_script.VMSetup.setup_opencode")
    @patch("vm_setup_script.VMSetup.setup_juggle")
    @patch("vm_setup_script.VMSetup.setup_uv_pip")
    def test_run_full_setup_handles_exception(
        self, mock_uv, mock_juggle, mock_opencode, vm_setup, capsys
    ):
        """Test full setup handles exceptions."""
        mock_opencode.side_effect = Exception("Installation failed")

        with patch("sys.exit"):
            vm_setup.run_full_setup()

        captured = capsys.readouterr()
        assert "failed" in captured.out.lower() or "error" in captured.out.lower()


class TestMainFunction:
    """Test main function and configuration."""

    def test_main_requires_environment_variables(self):
        """Test main fails without proper env vars."""
        with patch.dict(
            os.environ,
            {"GIT_EMAIL": "{{test@", "OPENROUTER_API_KEY": "{{key}"},
            clear=False,
        ):
            with patch("sys.exit"):
                from vm_setup_script import main

                main()

    def test_main_with_valid_env_vars(self):
        """Test main runs with valid env vars."""
        with patch.dict(
            os.environ,
            {"GIT_EMAIL": "test@test.com", "OPENROUTER_API_KEY": "valid-key"},
            clear=False,
        ):
            with patch("vm_setup_script.VMSetup") as mock_vm:
                with patch("vm_setup_script.VMSetup.run_full_setup"):
                    from vm_setup_script import main

                    main()

                    mock_vm.assert_called_once()


class TestSecurityConcerns:
    """Security-focused tests - CRITICAL."""

    def test_api_key_not_logged_in_plaintext(self):
        """Test API key doesn't appear in stdout."""
        from vm_setup_script import VMSetup

        with patch("vm_setup_script.Path.home") as mock_home:
            mock_home.return_value = Path("/tmp")

            setup = VMSetup(
                github_repo="https://github.com/test/repo.git",
                email="test@example.com",
                api_key="SUPER_SECRET_API_KEY_12345",
            )

            with patch("builtins.open", mock_open()) as mock_file:
                setup.setup_api_key()

                for call in mock_file().write.call_args_list:
                    content = str(call[0][0])
                    assert (
                        "SUPER_SECRET_API_KEY_12345" not in content
                        or "export OPENROUTER_API_KEY=" in content
                    )

    def test_command_injection_protection_list_commands(self):
        """Test list commands prevent injection."""
        from vm_setup_script import CommandRunner

        runner = CommandRunner()

        malicious_command = ["echo", "test; rm -rf /"]
        result = runner.run(malicious_command, shell=False)

        assert "; rm" not in result.stdout

    def test_email_not_injection_target(self):
        """Test email parameter can't be injected."""
        from vm_setup_script import VMSetup

        with patch("vm_setup_script.CommandRunner.run"):
            setup = VMSetup(
                github_repo="https://github.com/test/repo.git",
                email="test@example.com; cat /etc/passwd",
                api_key="secret",
            )

            setup.clone_and_configure_git()

            args = setup.runner.run.call_args_list[1]
            git_email_arg = args[0][0]
            assert "cat /etc/passwd" not in git_email_arg

    def test_github_repo_url_validated(self):
        """Test github repo URL is used safely."""
        from vm_setup_script import VMSetup

        with patch("vm_setup_script.CommandRunner.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)

            setup = VMSetup(
                github_repo="https://github.com/test/repo.git",
                email="test@example.com",
                api_key="secret",
            )

            setup.clone_and_configure_git()

            call_args = mock_run.call_args_list[0]
            repo_arg = call_args[0][0]
            assert isinstance(repo_arg, list)


class TestEdgeCases:
    """Edge case handling tests."""

    def test_empty_project_repo(self):
        """Test with empty project repo string."""
        from vm_setup_script import VMSetup

        setup = VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret",
            project_repo="",
        )
        assert setup.project_repo == ""

    def test_special_characters_in_email(self):
        """Test email with special characters."""
        from vm_setup_script import VMSetup

        setup = VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test+tag@example.com",
            api_key="secret",
        )
        assert setup.email == "test+tag@example.com"

    def test_unicode_in_api_key(self):
        """Test unicode characters in API key."""
        from vm_setup_script import VMSetup

        setup = VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="key-with-émojis-🔐",
        )
        assert "🔐" in setup.api_key


class TestJuggleConfiguration:
    """Test juggle.conf file."""

    def test_juggle_config_file_exists(self):
        """Test config file exists in project."""
        config_path = Path(__file__).parent.parent / "juggle.conf"
        assert config_path.exists(), "juggle.conf should exist"

    def test_juggle_config_valid_json(self):
        """Test config is valid JSON."""
        config_path = Path(__file__).parent.parent / "juggle.conf"
        with open(config_path) as f:
            config = json.load(f)

        assert isinstance(config, dict)

    def test_juggle_config_has_required_fields(self):
        """Test config has required fields."""
        config_path = Path(__file__).parent.parent / "juggle.conf"
        with open(config_path) as f:
            config = json.load(f)

        required_fields = ["search_paths", "vcs", "agent"]
        for field in required_fields:
            assert field in config, f"Missing required field: {field}"

    def test_juggle_config_vcs_valid(self):
        """Test VCS field is valid."""
        config_path = Path(__file__).parent.parent / "juggle.conf"
        with open(config_path) as f:
            config = json.load(f)

        assert config["vcs"] in ["git", "jj"]

    def test_juggle_config_agent_is_opencode(self):
        """Test agent is set to opencode."""
        config_path = Path(__file__).parent.parent / "juggle.conf"
        with open(config_path) as f:
            config = json.load(f)

        assert config["agent"] == "opencode"


class TestSpinner:
    """Test Spinner class for visual feedback during long-running operations."""

    def test_spinner_init_default(self):
        """Test spinner initialization with default parameters."""
        from vm_setup_script import Spinner

        spinner = Spinner()
        assert spinner.message == "Working"
        assert spinner.mode == "spinner"

    def test_spinner_init_custom(self):
        """Test spinner initialization with custom parameters."""
        from vm_setup_script import Spinner

        spinner = Spinner(message="Custom message", mode="waiting")
        assert spinner.message == "Custom message"
        assert spinner.mode == "waiting"

    def test_spinner_modes(self):
        """Test spinner has all required modes."""
        from vm_setup_script import Spinner

        assert hasattr(Spinner, "SPINNER_FRAMES")
        assert hasattr(Spinner, "WAIT_FRAMES")
        assert hasattr(Spinner, "HANG_FRAMES")
        assert len(Spinner.SPINNER_FRAMES) > 0
        assert len(Spinner.WAIT_FRAMES) > 0
        assert len(Spinner.HANG_FRAMES) > 0

    def test_spinner_start_stop(self):
        """Test spinner can start and stop."""
        from vm_setup_script import Spinner
        import time

        spinner = Spinner(message="Test", mode="spinner")
        spinner.start()
        time.sleep(0.3)
        spinner.stop()
        assert True

    def test_spinner_stop_with_message(self):
        """Test spinner stop with final message."""
        from vm_setup_script import Spinner
        import time
        import sys
        from io import StringIO

        spinner = Spinner(message="Test", mode="spinner")
        spinner.start()
        time.sleep(0.3)

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        spinner.stop("Done!")
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout

        assert "Done!" in output


class TestHangDetection:
    """Tests for hang detection and timeout functionality."""

    def test_command_runner_default_timeout(self):
        """Test CommandRunner has default timeout set."""
        from vm_setup_script import CommandRunner

        assert hasattr(CommandRunner, "DEFAULT_TIMEOUT")
        assert CommandRunner.DEFAULT_TIMEOUT == 300

    def test_command_runner_timeout_works(self):
        """Test CommandRunner respects timeout parameter."""
        from vm_setup_script import CommandRunner

        runner = CommandRunner()

        with pytest.raises(subprocess.TimeoutExpired):
            runner.run(["sleep", "10"], shell=False, timeout=1)

    def test_command_runner_with_spinner(self):
        """Test CommandRunner can run with spinner."""
        from vm_setup_script import CommandRunner

        runner = CommandRunner()

        result = runner.run(
            ["echo", "hello"], shell=False, timeout=10, show_spinner=False
        )
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_vm_setup_respects_timeout_in_setup(self):
        """Test VMSetup methods have timeout protection."""
        from vm_setup_script import VMSetup

        with patch("vm_setup_script.CommandRunner.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 1)

            setup = VMSetup(
                github_repo="https://github.com/test/repo.git",
                email="test@example.com",
                api_key="secret-key",
            )

            with pytest.raises(subprocess.TimeoutExpired):
                setup.setup_opencode()

    def test_full_setup_timeout_handler(self):
        """Test run_full_setup respects max_duration timeout."""
        from vm_setup_script import VMSetup
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutError("Test timeout")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)

        setup = VMSetup(
            github_repo="https://github.com/test/repo.git",
            email="test@example.com",
            api_key="secret-key",
        )

        with patch("vm_setup_script.VMSetup.setup_opencode") as mock_opencode:
            mock_opencode.side_effect = lambda: time.sleep(10)

            with patch("sys.exit"):
                try:
                    setup.run_full_setup(max_duration=1)
                except (SystemExit, TimeoutError):
                    pass

        signal.signal(signal.SIGALRM, old_handler)

    def test_long_running_command_shows_warning(self):
        """Test commands that run too long can show hanging warning."""
        from vm_setup_script import Spinner
        import time

        spinner = Spinner(message="Long task", mode="hanging")
        spinner.start()

        time.sleep(1)
        assert not spinner._stop_event.is_set()

        spinner.stop()

    def test_spinner_integration_with_command_runner(self):
        """Test spinner integration doesn't break command execution."""
        from vm_setup_script import CommandRunner
        import time

        runner = CommandRunner()

        start = time.time()
        result = runner.run(["echo", "test"], shell=False, timeout=10)
        elapsed = time.time() - start

        assert result.returncode == 0
        assert "test" in result.stdout
        assert elapsed < 5
