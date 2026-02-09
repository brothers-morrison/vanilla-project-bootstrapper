"""Main module for Hello World application."""


def hello_world() -> str:
    """Return a hello world greeting.
    
    Returns:
        str: A greeting message
    """
    return "Hello, World!"


def main() -> None:
    """Entry point for the hello world application."""
    print(hello_world())
