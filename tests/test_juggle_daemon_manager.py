"""Tests for juggle_daemon_manager.py"""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest


class TestJugleDaemonManager:
    """Test cases for juggle daemon manager."""

    @pytest.fixture
    def manager_module(self):
        """Import the manager module."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        import juggle_daemon_manager as manager
        return manager

    @pytest.fixture
    def mock_home(self, tmp_path, monkeypatch):
        """Mock HOME directory."""
        home = tmp_path / "home"
        home.mkdir()
        monkeypatch.setattr("pathlib.Path.home", lambda: home)
        return home

    def test_get_session_dirs_returns_empty_when_no_juggle_dir(self, mock_home, manager_module):
        """Test get_session_dirs returns empty list when no juggle directory."""
        project_dir = mock_home / "project"
        project_dir.mkdir()
        
        result = manager_module.get_session_dirs(project_dir)
        assert result == []

    def test_get_session_dirs_returns_session_dirs(self, mock_home, manager_module):
        """Test get_session_dirs returns session directories."""
        project_dir = mock_home / "project"
        project_dir.mkdir()
        sessions_dir = project_dir / ".juggle" / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "session1").mkdir()
        (sessions_dir / "session2").mkdir()
        
        result = manager_module.get_session_dirs(project_dir)
        assert len(result) == 2
        assert {d.name for d in result} == {"session1", "session2"}

    def test_is_process_running_when_running(self, manager_module):
        """Test is_process_running returns True when process exists."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0)
            result = manager_module.is_process_running("test-session")
            assert result is True

    def test_is_process_running_when_not_running(self, manager_module):
        """Test is_process_running returns False when process not found."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)
            result = manager_module.is_process_running("test-session")
            assert result is False

    def test_is_agent_hung_returns_true_for_old_state(self, manager_module):
        """Test is_agent_hung returns True when agent state is old."""
        session_dir = Mock(spec=Path)
        state_file = Mock()
        
        old_time = datetime.now(timezone.utc).replace(hour=datetime.now(timezone.utc).hour - 2)
        state_data = {
            "last_updated": old_time.isoformat().replace("+00:00", "Z"),
        }
        
        session_dir.__truediv__ = lambda self, x: state_file
        state_file.exists.return_value = True
        state_file.read_text.return_value = json.dumps(state_data)
        
        with patch.object(manager_module, "is_agent_hung", return_value=True):
            result = manager_module.is_agent_hung(session_dir)
            assert result is True

    def test_is_agent_hung_returns_false_for_recent_state(self, manager_module):
        """Test is_agent_hung returns False when agent state is recent."""
        session_dir = Mock(spec=Path)
        state_file = Mock()
        
        recent_time = datetime.now(timezone.utc)
        state_data = {
            "last_updated": recent_time.isoformat().replace("+00:00", "Z"),
        }
        
        session_dir.__truediv__ = lambda self, x: state_file
        state_file.exists.return_value = True
        state_file.read_text.return_value = json.dumps(state_data)
        
        result = manager_module.is_agent_hung(session_dir)
        assert result is False

    def test_is_agent_hung_returns_true_for_missing_state(self, manager_module):
        """Test is_agent_hung returns True when state file doesn't exist."""
        session_dir = Mock(spec=Path)
        session_dir.__truediv__ = lambda self, x: Mock(exists=lambda: False)
        
        result = manager_module.is_agent_hung(session_dir)
        assert result is True

    def test_agent_never_started_returns_true_when_no_state(self, manager_module):
        """Test agent_never_started returns True when no state file exists."""
        session_dir = Mock(spec=Path)
        session_dir.__truediv__ = lambda self, x: Mock(exists=lambda: False)
        
        result = manager_module.agent_never_started(session_dir)
        assert result is True

    def test_agent_never_started_returns_false_when_state_exists(self, manager_module):
        """Test agent_never_started returns False when state file exists."""
        session_dir = Mock(spec=Path)
        session_dir.__truediv__ = lambda self, x: Mock(exists=lambda: True)
        
        result = manager_module.agent_never_started(session_dir)
        assert result is False

    def test_get_unmarked_completed_balls_returns_empty_when_no_balls(self, manager_module, tmp_path):
        """Test get_unmarked_completed_balls returns empty when no balls file."""
        result = manager_module.get_unmarked_completed_balls(tmp_path)
        assert result == []

    def test_get_unmarked_completed_balls_returns_empty_when_no_balls_dir(self, manager_module, tmp_path):
        """Test get_unmarked_completed_balls returns empty when no balls dir."""
        balls_file = tmp_path / "balls.jsonl"
        balls_file.write_text('{"id": "test", "state": "pending"}\n')
        
        result = manager_module.get_unmarked_completed_balls(tmp_path)
        assert result == []

    def test_count_active_agents_returns_count(self, manager_module):
        """Test count_active_agents returns number of running agents."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(
                returncode=0,
                stdout="123\n456\n789\n",
            )
            result = manager_module.count_active_agents()
            assert result == 3

    def test_count_active_agents_returns_zero_when_none(self, manager_module):
        """Test count_active_agents returns 0 when no agents running."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=1)
            result = manager_module.count_active_agents()
            assert result == 0

    @patch("subprocess.run")
    def test_kill_hung_agent_calls_pkill(self, mock_run, manager_module):
        """Test kill_hung_agent calls pkill commands."""
        mock_run.return_value = Mock()
        manager_module.kill_hung_agent("test-session")
        
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_start_agent_calls_juggle(self, mock_run, manager_module, mock_home, monkeypatch):
        """Test start_agent calls juggle with correct args."""
        monkeypatch.setattr(manager_module, "JUGGLE_BIN", mock_home / ".local" / "bin" / "juggle")
        mock_run.return_value = Mock()
        
        project_dir = mock_home / "project"
        project_dir.mkdir()
        
        manager_module.start_agent("test-session", project_dir)
        
        mock_run.assert_called_once()

    def test_main_exits_when_juggle_not_found(self, manager_module, mock_home, monkeypatch):
        """Test main exits when juggle binary not found."""
        monkeypatch.setattr(manager_module, "JUGGLE_BIN", mock_home / "nonexistent")
        
        with pytest.raises(SystemExit) as exc_info:
            manager_module.main()
        
        assert exc_info.value.code == 1


class TestJuggleDaemonManagerIntegration:
    """Integration tests for juggle daemon manager (requires juggle)."""

    def test_script_executable(self):
        """Test script is executable."""
        script_path = Path(__file__).parent.parent / "scripts" / "juggle_daemon_manager.py"
        assert script_path.exists()
        assert script_path.stat().st_mode & 0o111

    def test_script_can_be_imported(self):
        """Test script can be imported without errors."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
        import juggle_daemon_manager
        assert hasattr(juggle_daemon_manager, "main")

    def test_script_runs_without_error(self):
        """Test script runs without error."""
        result = subprocess.run(
            ["python3", str(Path(__file__).parent.parent / "scripts" / "juggle_daemon_manager.py")],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "Juggle daemon manager completed" in output
