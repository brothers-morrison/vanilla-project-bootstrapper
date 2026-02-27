"""Tests for the hello_world module."""

from hello_world import __version__
from hello_world.main import hello_world, main


def test_hello_world():
    """Test that hello_world returns the expected greeting."""
    result = hello_world()
    assert result == "Hello, World!"
    assert isinstance(result, str)


def test_main(capsys):
    """Test that main prints the hello world greeting."""
    main()
    captured = capsys.readouterr()
    assert captured.out == "Hello, World!\n"


def test_version():
    """Test that __version__ is a valid semantic version string."""
    import re

    assert isinstance(__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+$", __version__)
