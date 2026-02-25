#!/usr/bin/env python3
"""
Juggle Daemon Manager - Cron Script
Runs every hour to manage juggle daemon agents:
- Checks for existing daemon runners
- Kills hung/frozen processes
- Starts new agents up to the agent limit
"""

import os
import sys
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

HOME = Path.home()
JUGGLE_BIN = HOME / ".local" / "bin" / "juggle"
JUGGLE_DIR = HOME / ".juggle"
MAX_AGENTS = int(os.environ.get("MAX_JUGGLE_AGENTS", "3"))
# tbd, how to make this more dynamic, more -yolo mode?
PROJECT_DIRS = [
    HOME / "Development",
    HOME / "vanilla-project-bootstrapper",
]


def run_command(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PATH"] = f"{HOME}/.local/bin:" + env.get("PATH", "")
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
    )


def get_session_dirs(project_dir: Path) -> list[Path]:
    sessions_dir = project_dir / ".juggle" / "sessions"
    if not sessions_dir.exists():
        return []
    return [d for d in sessions_dir.iterdir() if d.is_dir()]


def is_process_running(session_name: str) -> bool:
    result = subprocess.run(
        ["pgrep", "-f", f"juggle.*agent.*run.*{session_name}.*--daemon"],
        capture_output=True,
    )
    return result.returncode == 0


def is_agent_hung(session_dir: Path) -> bool:
    state_file = session_dir / "agent.state"
    if not state_file.exists():
        return True

    try:
        state = json.loads(state_file.read_text())
        last_updated = state.get("last_updated")
        if not last_updated:
            return True

        last_ts = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
        now = datetime.now(last_ts.tzinfo)
        diff_minutes = (now - last_ts).total_seconds() / 60

        return diff_minutes > 60
    except (json.JSONDecodeError, ValueError, OSError):
        return True


def agent_never_started(session_dir: Path) -> bool:
    state_file = session_dir / "agent.state"
    return not state_file.exists()


def get_unmarked_completed_balls(juggle_dir: Path) -> list[dict]:
    balls_file = juggle_dir / "balls.jsonl"
    if not balls_file.exists():
        return []

    balls_dir = juggle_dir / "balls"
    if not balls_dir.exists():
        return []

    unmarked = []
    try:
        ball_states = {}
        for line in balls_file.read_text().strip().split("\n"):
            if line:
                ball = json.loads(line)
                ball_states[ball["id"]] = ball

        for lock_file in balls_dir.glob("*.lock.info"):
            ball_id = lock_file.stem.replace(".lock.info", "")
            if ball_id in ball_states:
                ball = ball_states[ball_id]
                if ball.get("state") != "complete":
                    try:
                        lock_info = json.loads(lock_file.read_text())
                        started_at = lock_info.get("started_at")
                        if started_at:
                            started_ts = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                            now = datetime.now(started_ts.tzinfo)
                            diff_hours = (now - started_ts).total_seconds() / 3600
                            if diff_hours > 1:
                                unmarked.append(ball)
                    except (json.JSONDecodeError, ValueError, OSError):
                        pass
    except OSError:
        pass

    return unmarked


def kill_hung_agent(session_name: str) -> None:
    log.info(f"Killing hung agent for session: {session_name}")
    subprocess.run(
        ["pkill", "-f", f"juggle.*agent.*run.*{session_name}.*--daemon"],
        capture_output=True,
    )
    subprocess.run(
        ["pkill", "-9", "-f", f"juggle.*agent.*run.*{session_name}.*--daemon"],
        capture_output=True,
    )


def start_agent(session_name: str, project_dir: Path) -> None:
    log.info(f"Starting agent for session: {session_name} in {project_dir}")
    run_command(
        [str(JUGGLE_BIN), "agent", "run", session_name, "--daemon", "--provider", "opencode"],
        cwd=project_dir,
    )


def count_active_agents() -> int:
    result = subprocess.run(
        ["pgrep", "-f", "juggle.*agent.*run.*--daemon"],
        capture_output=True,
    )
    if result.returncode == 0:
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        return len(lines) if lines else 0
    return 0


def main() -> None:
    log.info("Starting juggle daemon manager")

    if not JUGGLE_BIN.exists():
        log.error(f"juggle not found at {JUGGLE_BIN}")
        sys.exit(1)

    active_count = count_active_agents()
    log.info(f"Currently running: {active_count} agents (max: {MAX_AGENTS})")

    for project_dir in PROJECT_DIRS:
        if not project_dir.exists():
            continue

        for session_dir in get_session_dirs(project_dir):
            session_name = session_dir.name

            if is_process_running(session_name):
                if is_agent_hung(session_dir):
                    kill_hung_agent(session_name)
                    active_count -= 1

    if active_count < MAX_AGENTS:
        to_start = MAX_AGENTS - active_count
        log.info(f"Starting {to_start} additional agent(s)")

        for project_dir in PROJECT_DIRS:
            if to_start <= 0:
                break

            if not project_dir.exists():
                continue

            for session_dir in get_session_dirs(project_dir):
                if to_start <= 0:
                    break

                session_name = session_dir.name

                if not is_process_running(session_name):
                    start_agent(session_name, project_dir)
                    to_start -= 1

    log.info("Juggle daemon manager completed")


if __name__ == "__main__":
    main()
