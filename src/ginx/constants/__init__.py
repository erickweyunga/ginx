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
    "package-lock.json",
    "yarn.lock",
    "requirements.txt",
    "requirements-dev.txt",
    "dev-requirements.txt",
    "requirements/dev.txt",
    "requirements/development.txt",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".github",
    "LICENSE",
    "README.md",
    ".env",
    ".env.example",
    "CHANGELOG.md",
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


COMMON_SHELL_RESERVED_COMMANDS = [
    "rm",
    "echo",
    "ls",
    "cd",
    "sudo",
    "mkdir",
    "dir",
    "clear",
    "git",
    "python",
    "pip",
    "docker",
    "ginx",  # not including it in the dependecies
]


__all__ = [
    "DANGEROUS_PATTERNS",
    "COMMON_PROJECT_ROOT_MARKERS",
    "DEFAULT_REQUIREMENTS_FILES",
    "COMMON_DEV_PACKAGES",
    "COMMON_SHELL_RESERVED_COMMANDS",
]
