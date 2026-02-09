"""Tests for the hello_world module."""

from hello_world.main import hello_world


def test_hello_world():
    """Test that hello_world returns the expected greeting."""
    result = hello_world()
    assert result == "Hello, World!"
    assert isinstance(result, str)
