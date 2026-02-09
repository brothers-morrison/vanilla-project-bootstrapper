"""Tests for the hello_world module."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from hello_world.main import hello_world


def test_hello_world():
    """Test that hello_world returns the expected greeting."""
    result = hello_world()
    assert result == "Hello, World!"
    assert isinstance(result, str)
