"""
Formatting and display utility functions.
"""

import typer


def format_duration(seconds: float) -> str:
    """
    Format duration in a human-readable way.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds:.2f}s"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def colorize_output(text: str, success: bool = True) -> str:
    """
    Add color codes to text based on success/failure.

    Args:
        text: Text to colorize
        success: Whether this represents success (green) or failure (red)

    Returns:
        Colorized text
    """
    if success:
        return typer.style(text, fg=typer.colors.GREEN)
    else:
        return typer.style(text, fg=typer.colors.RED)
