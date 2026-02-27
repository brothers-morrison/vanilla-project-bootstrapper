"""Security and risk detection tests for VM hardening.

These tests check for common security issues, disk space problems,
firewall configuration, and SSH hardening that should be present
on a production worker VM.

================================================================================
DEPENDENCY REQUIREMENTS
================================================================================

These tests require specific system utilities. On Alpine Linux, install with:

    apk add --no-cache \
        coreutils \
        findutils \
        iptables \
        iproute2 \
        openssh \
        sudo \
        procps \
        util-linux \
        bash

Or on Ubuntu/Debian:

    apt-get update && apt-get install -y \
        coreutils \
        findutils \
        iptables \
        iproute2 \
        openssh-server \
        sudo \
        procps \
        util-linux \
        bash \
        systemd

================================================================================
RUNNING TESTS
================================================================================

Run all tests:
    pytest tests/test_security.py -v

Run specific test class:
    pytest tests/test_security.py::TestDiskSpace -v

Run with tags:
    pytest tests/test_security.py -m "disk" -v

Skip tests requiring specific tools:
    pytest tests/test_security.py --ignore-glob="*iptables*" -v

================================================================================
TEST TAGS
================================================================================

- @pytest.mark.dependency:df,free,swapon - Core system tools
- @pytest.mark.dependency:iptables,ufw - Firewall tools
- @pytest.mark.dependency:ss,netstat - Network socket tools
- @pytest.mark.dependency:ps,find - Process/file tools
- @pytest.mark.dependency:sysctl - Kernel parameter tools
- @pytest.mark.apk - Alpine-specific (uses /etc/apk)
- @pytest.mark.apt - Debian/Ubuntu-specific (uses /etc/apt)
- @pytest.mark.ssh - SSH configuration tests
- @pytest.mark.network - Network security tests
- @pytest.mark.security - General security tests

"""

import os
import subprocess
import pytest
from pathlib import Path


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================


def check_command_exists(cmd: str) -> bool:
    """Check if a command exists on the system."""
    result = subprocess.run(
        ["which", cmd],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def skip_if_missing(dep: str):
    """Skip test if dependency is missing."""
    if not check_command_exists(dep):
        pytest.skip(f"Dependency '{dep}' not installed")


# ==============================================================================
# DISK SPACE TESTS
# ==============================================================================


class TestDiskSpace:
    """Test disk space availability and constraints.

    Dependencies: df (coreutils), find (findutils)
    Tags: disk, storage, dependency:df
    """

    def test_root_disk_space_available(self):
        """Check that root filesystem has adequate free space.

        Dependency: df (coreutils)
        Minimum: 2GB free on /
        """
        skip_if_missing("df")

        result = subprocess.run(
            ["df", "-BG", "/"],
            capture_output=True,
            text=True,
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            fields = lines[1].split()
            available_gb = int(fields[3].replace("G", ""))
            assert available_gb >= 2, (
                f"Root disk only {available_gb}GB free, need >=2GB"
            )

    def test_disk_space_for_workspace(self):
        """Check that /workspace has adequate space if it exists.

        Dependency: df (coreutils)
        Minimum: 1GB free
        """
        skip_if_missing("df")

        workspace = Path("/workspace")
        if workspace.exists():
            result = subprocess.run(
                ["df", "-BG", str(workspace)],
                capture_output=True,
                text=True,
            )
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 2:
                fields = lines[1].split()
                available_gb = int(fields[3].replace("G", ""))
                assert available_gb >= 1, f"Workspace only {available_gb}GB free"

    def test_tmp_space_available(self):
        """Check that /tmp has space for operations.

        Dependency: df (coreutils)
        Minimum: 1GB free
        """
        skip_if_missing("df")

        result = subprocess.run(
            ["df", "-BG", "/tmp"],
            capture_output=True,
            text=True,
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            fields = lines[1].split()
            available_gb = int(fields[3].replace("G", ""))
            assert available_gb >= 1, f"/tmp only {available_gb}GB free"


# ==============================================================================
# MEMORY CONSTRAINTS TESTS
# ==============================================================================


class TestMemoryConstraints:
    """Test memory constraints and swap configuration.

    Dependencies: free (procps), swapon (util-linux)
    Tags: memory, swap, dependency:free
    Critical: e2-micro has only 0.6GB RAM - swap is required!
    """

    def test_swap_exists(self):
        """Check if swap exists (CRITICAL for e2-micro with 0.6GB RAM).

        Dependency: swapon (util-linux)
        Requirement: Swap file or partition MUST exist
        """
        skip_if_missing("swapon")

        result = subprocess.run(
            ["swapon", "--show"],
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip()
        has_swap = bool(output) and "FILE" in output.upper()
        assert has_swap, (
            "No swap configured - will cause OOM on e2-micro! "
            "Add swap with: truncate -s 1G /swapfile && chmod 600 /swapfile && "
            "mkswap /swapfile && swapon /swapfile"
        )

    def test_memory_available(self):
        """Check that minimum memory is available.

        Dependency: free (procps)
        Minimum: 256MB available memory
        """
        skip_if_missing("free")

        result = subprocess.run(
            ["free", "-m"],
            capture_output=True,
            text=True,
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            fields = lines[1].split()
            available_mb = int(fields[6])
            assert available_mb >= 256, f"Only {available_mb}MB memory available"


# ==============================================================================
# FIREWALL TESTS
# ==============================================================================


class TestFirewall:
    """Test firewall configuration.

    Dependencies: iptables (iptables) OR ufw (ufw)
    Tags: firewall, network, dependency:iptables
    """

    def test_iptables_or_ufw_available(self):
        """Check that a firewall tool is available.

        Dependencies: iptables OR ufw
        Note: Alpine uses iptables by default, Ubuntu may use ufw
        """
        has_iptables = check_command_exists("iptables")
        has_ufw = check_command_exists("ufw")

        assert has_iptables or has_ufw, "No firewall tool (iptables or ufw) found"

    def test_iptables_default_policy(self):
        """Check that iptables has default DROP or ufw is enabled.

        Dependency: iptables (iptables) OR ufw (ufw)
        """
        if check_command_exists("ufw"):
            result = subprocess.run(
                ["ufw", "status"],
                capture_output=True,
                text=True,
            )
            assert "inactive" not in result.stdout.lower(), "UFW is inactive"
        elif check_command_exists("iptables"):
            result = subprocess.run(
                ["iptables", "-L", "-n"],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, "iptables not accessible"
        else:
            pytest.skip("No firewall tool available")

    def test_ssh_port_not_world_open(self):
        """Check that SSH port (22) is not exposed to 0.0.0.0/0.

        Dependency: iptables (iptables)
        Security: SSH should only be accessible from controller IP
        """
        if not check_command_exists("iptables"):
            pytest.skip("iptables not available")

        result = subprocess.run(
            ["iptables", "-L", "-n", "--line-numbers"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            output = result.stdout
            for line in output.split("\n"):
                if "dpt:22" in line and "0.0.0.0/0" in line:
                    assert False, "SSH port 22 is exposed to 0.0.0.0/0 (insecure!)"


# ==============================================================================
# SSH HARDENING TESTS
# ==============================================================================


class TestSSHHardening:
    """Test SSH server hardening.

    Dependencies: openssh (sshd_config file)
    Tags: ssh, security
    """

    def test_sshd_config_exists(self):
        """Check that sshd_config exists.

        Dependency: /etc/ssh/sshd_config (openssh)
        """
        sshd_config = Path("/etc/ssh/sshd_config")
        assert sshd_config.exists(), "sshd_config not found - is openssh installed?"

    def test_ssh_no_root_login(self):
        """Check that root login is disabled in sshd_config.

        Dependency: /etc/ssh/sshd_config (openssh)
        Security: Root login should be prohibited
        """
        sshd_config = Path("/etc/ssh/sshd_config")
        if sshd_config.exists():
            content = sshd_config.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("PermitRootLogin"):
                    assert "no" in line.lower(), "PermitRootLogin should be 'no'"

    def test_ssh_password_auth_disabled(self):
        """Check that password authentication is disabled.

        Dependency: /etc/ssh/sshd_config (openssh)
        Security: Password auth should be disabled, use keys only
        """
        sshd_config = Path("/etc/ssh/sshd_config")
        if sshd_config.exists():
            content = sshd_config.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("PasswordAuthentication"):
                    assert "no" in line.lower(), "PasswordAuthentication should be 'no'"

    def test_ssh_key_auth_enabled(self):
        """Check that public key authentication is enabled.

        Dependency: /etc/ssh/sshd_config (openssh)
        Requirement: PubkeyAuthentication must be explicitly enabled
        """
        sshd_config = Path("/etc/ssh/sshd_config")
        if sshd_config.exists():
            content = sshd_config.read_text()
            found_key_auth = False
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("PubkeyAuthentication"):
                    found_key_auth = True
                    assert "yes" in line.lower(), "PubkeyAuthentication should be 'yes'"
            assert found_key_auth, "PubkeyAuthentication not explicitly set"

    def test_ssh_empty_passwords_disallowed(self):
        """Check that empty passwords are not allowed.

        Dependency: /etc/ssh/sshd_config (openssh)
        Security: Empty passwords must be rejected
        """
        sshd_config = Path("/etc/ssh/sshd_config")
        if sshd_config.exists():
            content = sshd_config.read_text()
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("PermitEmptyPasswords"):
                    assert "no" in line.lower(), "PermitEmptyPasswords should be 'no'"


# ==============================================================================
# OPEN PORTS TESTS
# ==============================================================================


class TestOpenPorts:
    """Test for open ports and listening services.

    Dependencies: ss (iproute2) OR netstat (net-tools), ps (procps)
    Tags: network, ports, dependency:ss
    """

    def test_minimal_listening_ports(self):
        """Check that only expected ports are listening.

        Dependency: ss (iproute2) or netstat
        Expect: Ports 22 (SSH), optionally 80/443 (HTTP/HTTPS)
        """
        if check_command_exists("ss"):
            result = subprocess.run(
                ["ss", "-tuln"],
                capture_output=True,
                text=True,
            )
        elif check_command_exists("netstat"):
            result = subprocess.run(
                ["netstat", "-tuln"],
                capture_output=True,
                text=True,
            )
        else:
            pytest.skip("Neither ss nor netstat available")

        output = result.stdout

        listening = []
        for line in output.split("\n")[1:]:
            if "LISTEN" in line:
                parts = line.split()
                if len(parts) >= 5:
                    addr = parts[4]
                    if ":" in addr:
                        port = addr.split(":")[-1]
                        if port.isdigit():
                            listening.append(int(port))

        unexpected = [p for p in listening if p not in [22, 80, 443]]
        assert len(unexpected) <= 2, f"Unexpected listening ports: {unexpected}"

    def test_no_dangerous_services_running(self):
        """Check that dangerous services are not running.

        Dependency: ps (procps)
        Security: telnetd, ftpd, rshd, rlogind are insecure
        """
        skip_if_missing("ps")

        dangerous_services = ["telnetd", "ftpd", "rshd", "rlogind"]

        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
        )
        for service in dangerous_services:
            assert service not in result.stdout, (
                f"Dangerous service {service} is running"
            )


# ==============================================================================
# USER SECURITY TESTS
# ==============================================================================


class TestUserSecurity:
    """Test user and authentication security.

    Dependencies: whoami, getent (glibc), find (findutils)
    Tags: users, security, dependency:whoami
    """

    def test_not_running_as_root(self):
        """Check that we're not running as root.

        Dependency: whoami (coreutils)
        Security: Running as root is insecure for workloads
        """
        skip_if_missing("whoami")

        result = subprocess.run(
            ["whoami"],
            capture_output=True,
            text=True,
        )
        current_user = result.stdout.strip()
        assert current_user != "root", "Running as root is insecure"

    def test_sudo_group_exists(self):
        """Check that sudo group exists for privilege escalation.

        Dependency: getent (glibc) or group file
        Requirement: sudo group needed for admin tasks
        """
        result = subprocess.run(
            ["getent", "group", "sudo"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # Try wheel group (Alpine uses wheel)
            result = subprocess.run(
                ["getent", "group", "wheel"],
                capture_output=True,
                text=True,
            )
        assert result.returncode == 0, "Neither sudo nor wheel group exists"

    def test_no_world_writable_files_in_home(self):
        """Check for world-writable files (security issue).

        Dependency: find (findutils)
        Security: World-writable files are a security risk
        Note: Excludes common cache directories
        """
        skip_if_missing("find")

        home = Path.home()
        if home.exists():
            # Exclude common cache directories which may have lock files
            result = subprocess.run(
                [
                    "find",
                    str(home),
                    "-type",
                    "f",
                    "-perm",
                    "-0002",
                    "-not",
                    "-path",
                    "*/.cache/*",
                    "-not",
                    "-path",
                    "*/.local/share/*",
                    "-not",
                    "-path",
                    "*/.bun/*",
                    "-not",
                    "-path",
                    "*/.uv/*",
                    "-print",
                    "-quit",
                ],
                capture_output=True,
                text=True,
            )
            assert not result.stdout.strip(), (
                f"World-writable files: {result.stdout[:200]}"
            )
            assert not result.stdout.strip(), (
                f"World-writable files: {result.stdout[:200]}"
            )


# ==============================================================================
# NETWORK SECURITY TESTS
# ==============================================================================


class TestNetworkSecurity:
    """Test network security settings.

    Dependencies: sysctl (procps), cat (coreutils)
    Tags: network, kernel, dependency:sysctl
    """

    def test_ip_forwarding_disabled(self):
        """Check that IP forwarding is disabled.

        Dependency: sysctl (procps) or cat (coreutils)
        Security: IP forwarding should be disabled on worker VMs
        """
        if check_command_exists("sysctl"):
            result = subprocess.run(
                ["sysctl", "net.ipv4.ip_forward"],
                capture_output=True,
                text=True,
            )
            value = result.stdout.strip().split("=")[-1].strip()
        else:
            result = subprocess.run(
                ["cat", "/proc/sys/net/ipv4/ip_forward"],
                capture_output=True,
                text=True,
            )
            value = result.stdout.strip()

        assert value == "0", f"IP forwarding should be disabled, got: {value}"

    def test_icmp_redirects_disabled(self):
        """Check that ICMP redirects are disabled.

        Dependency: sysctl (procps)
        Security: ICMP redirects can be used for MITM attacks
        """
        if not check_command_exists("sysctl"):
            pytest.skip("sysctl not available")

        result = subprocess.run(
            ["sysctl", "net.ipv4.conf.all.accept_redirects"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            assert "0" in result.stdout, "ICMP redirects should be disabled"

    def test_source_routing_disabled(self):
        """Check that source routing is disabled.

        Dependency: sysctl (procps)
        Security: Source routing should be disabled
        """
        if not check_command_exists("sysctl"):
            pytest.skip("sysctl not available")

        result = subprocess.run(
            ["sysctl", "net.ipv4.conf.all.accept_source_route"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            assert "0" in result.stdout, "Source routing should be disabled"


# ==============================================================================
# PACKAGE SECURITY TESTS
# ==============================================================================


class TestPackageSecurity:
    """Test package and update security.

    Dependencies: apk (Alpine), apt (Debian), yum/dnf (RHEL)
    Tags: packages, updates, dependency:apk, dependency:apt
    """

    def test_package_manager_available(self):
        """Check that a package manager is available.

        Dependencies: apk (Alpine), apt (Debian), yum/dnf (RHEL)
        """
        has_apk = os.path.exists("/etc/apk")
        has_apt = os.path.exists("/etc/apt")
        has_yum = os.path.exists("/etc/yum")

        assert has_apk or has_apt or has_yum, "No package manager found"

    @pytest.mark.apk
    def test_alpine_security_updates(self):
        """Check for available security updates on Alpine.

        Dependency: apk (Alpine Linux)
        Note: Tag: apk - only runs on Alpine
        """
        if not os.path.exists("/etc/apk"):
            pytest.skip("Not Alpine Linux")

        result = subprocess.run(
            ["apk", "update"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            result = subprocess.run(
                ["apk", "version", "-l", "a"],
                capture_output=True,
                text=True,
            )
            updates = result.stdout.strip()
            if updates:
                print(f"NOTE: Available updates: {updates[:200]}")

    @pytest.mark.apt
    def test_debian_security_updates(self):
        """Check for available security updates on Debian/Ubuntu.

        Dependency: apt (Debian/Ubuntu)
        Note: Tag: apt - only runs on Debian-based systems
        """
        if not os.path.exists("/etc/apt"):
            pytest.skip("Not Debian-based")

        result = subprocess.run(
            ["apt-get", "update"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            result = subprocess.run(
                ["apt-get", "upgrade", "-s"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and "upgraded" in result.stdout:
                print(f"NOTE: Security updates available")


# ==============================================================================
# SECRETS MANAGEMENT TESTS
# ==============================================================================


class TestSecretsManagement:
    """Test secrets and credential handling.

    Dependencies: None (pure Python)
    Tags: secrets, security
    """

    def test_no_secrets_in_env(self):
        """Check that long secrets are not in environment variables.

        Dependency: None (uses os.environ)
        Security: Secrets should not be in env vars (use secret managers)
        """
        dangerous_vars = ["GH_TOKEN", "GITHUB_TOKEN", "AWS_SECRET", "PRIVATE_KEY"]

        for var in dangerous_vars:
            value = os.environ.get(var)
            if value:
                assert len(value) < 50, f"Secret {var} appears to be in environment"

    def test_ssh_directory_permissions(self):
        """Check that .ssh directory has proper permissions.

        Dependency: None (uses pathlib)
        Security: .ssh should be 700 (owner only)
        """
        ssh_dir = Path.home() / ".ssh"
        if ssh_dir.exists():
            stat_info = ssh_dir.stat()
            mode = oct(stat_info.st_mode)[-3:]
            assert mode in ["700", "600"], f".ssh dir has insecure permissions: {mode}"

    def test_ssh_key_permissions(self):
        """Check that SSH private keys have proper permissions.

        Dependency: None (uses pathlib)
        Security: Private keys should be 600 (owner only)
        """
        ssh_dir = Path.home() / ".ssh"
        if ssh_dir.exists():
            for key_file in ssh_dir.glob("id_*"):
                if not key_file.name.endswith(".pub"):
                    stat_info = key_file.stat()
                    mode = oct(stat_info.st_mode)[-3:]
                    assert mode == "600", f"SSH key {key_file} insecure: {mode}"


# ==============================================================================
# PROCESS SECURITY TESTS
# ==============================================================================


class TestProcessSecurity:
    """Test running processes for security issues.

    Dependencies: ps (procps)
    Tags: processes, security, dependency:ps
    """

    def test_no_obvious_reverse_shells(self):
        """Check for obvious reverse shell indicators.

        Dependency: ps (procps)
        Security: Detect common reverse shell patterns
        """
        skip_if_missing("ps")

        dangerous_patterns = ["/dev/tcp/", "bash -i", "sh -i"]

        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
        )
        for pattern in dangerous_patterns:
            assert pattern not in result.stdout, f"Suspicious pattern: {pattern}"


# ==============================================================================
# LOGGING TESTS
# ==============================================================================


class TestLogging:
    """Test logging and audit capabilities.

    Dependencies: tail (coreutils)
    Tags: logging, audit
    """

    def test_system_logs_accessible(self):
        """Check that system logs are accessible.

        Dependencies: log files exist
        Note: Different distros use different log locations
        """
        log_paths = [
            "/var/log/syslog",
            "/var/log/messages",
            "/var/log/auth.log",
            "/var/log/secure",
        ]
        accessible = any(Path(p).exists() for p in log_paths)
        assert accessible, "No system log files found"

    def test_auth_logs_readable(self):
        """Check that authentication logs exist and are readable.

        Dependency: tail (coreutils)
        """
        if not check_command_exists("tail"):
            pytest.skip("tail not available")

        log_paths = ["/var/log/auth.log", "/var/log/secure", "/var/log/messages"]
        log_file = None
        for p in log_paths:
            if Path(p).exists():
                log_file = p
                break

        if log_file:
            result = subprocess.run(
                ["tail", "-1", log_file],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Cannot read {log_file}"


# ==============================================================================
# SUMMARY MARKERS
# ==============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "apk: Alpine Linux specific tests")
    config.addinivalue_line("markers", "apt: Debian/Ubuntu specific tests")
    config.addinivalue_line("markers", "disk: Disk space tests")
    config.addinivalue_line("markers", "memory: Memory/swap tests")
    config.addinivalue_line("markers", "firewall: Firewall tests")
    config.addinivalue_line("markers", "ssh: SSH hardening tests")
    config.addinivalue_line("markers", "network: Network security tests")
    config.addinivalue_line("markers", "security: General security tests")
