"""
Constants for Ginx CLI tool.
"""

DANGEROUS_PATTERNS = [
    "rm -rf",
    "dd if=",
    ":(){ :|:& };",  # Fork bomb
    "mkfs.",
    "format c:",
    "sudo rm -rf",  # Dangerous with sudo
    "sudo dd if=",
    "sudo mkfs.",
    "sudo format c:",
]

COMMON_PROJECT_ROOT_MARKERS = [
    ".git",
    ".gitignore",
    "pyproject.toml",
    "setup.py",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Makefile",
]

DEFAULT_REQUIREMENTS_FILES = [
    "requirements.txt",
    "requirements-dev.txt",
    "dev-requirements.txt",
    "requirements/dev.txt",
    "requirements/development.txt",
]

COMMON_DEV_PACKAGES = [
    "black",
    "isort",
    "flake8",
    "pytest",
    "mypy",
    "coverage",
    "bandit",
    "pylint",
    "autopep8",
    "pre-commit",
    "tox",
]


__all__ = [
    "DANGEROUS_PATTERNS",
    "COMMON_PROJECT_ROOT_MARKERS",
    "DEFAULT_REQUIREMENTS_FILES",
    "COMMON_DEV_PACKAGES",
]
