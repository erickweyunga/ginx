"""
Test data and sample configurations.
"""

from typing import Any, Dict

# Sample configurations for testing
MINIMAL_CONFIG: Dict[str, Any] = {"scripts": {"hello": "echo hello"}}

COMPLEX_CONFIG: Dict[str, Any] = {
    "scripts": {
        "commit": {
            "command": "git commit -m ${message:string}",
            "description": "Commit with message",
            "timeout": 30,
        },
        "serve": {
            "command": "python -m http.server ${port:number}",
            "description": "Start HTTP server",
            "timeout": 0,
            "background": True,
        },
        "test": {
            "command": "pytest tests/ -v",
            "description": "Run test suite",
            "env": {"PYTHONPATH": "src"},
        },
    },
    "plugins": {
        "enabled": ["version-sync", "docker"],
        "disabled": ["legacy-plugin"],
        "directories": ["./plugins", "~/.ginx/plugins"],
        "settings": {"version-sync": {"check_interval": 3600, "auto_update": False}},
    },
    "settings": {
        "dangerous_commands": True,
        "default_timeout": 300,
        "max_timeout": 3600,
        "auto_discover_plugins": True,
        "background_support": True,
    },
}

# Invalid configurations for error testing
INVALID_CONFIGS: Dict[str, Any] = {
    "missing_command": {"scripts": {"broken": {"description": "Missing command field"}}},
    "invalid_yaml": "invalid: yaml: content:",
    "wrong_type": {"scripts": "this should be a dict"},
}

# Variable parsing test cases
VARIABLE_TEST_CASES = [
    # (template, input, expected_output)
    ("echo ${msg:string}", "hello", 'echo "hello"'),
    ("git checkout ${branch:raw}", "main", "git checkout main"),
    ("sleep ${time:number}", "5", "sleep 5"),
    ("git add ${files:args}", "a.txt b.txt", "git add 'a.txt' 'b.txt'"),
    ("git tag ${ver:string} -m ${ver:string}", "v1.0", 'git tag "v1.0" -m "v1.0"'),
]

# Error test cases
ERROR_TEST_CASES = [
    # (template, input, expected_error_type)
    ("echo ${msg}", "hello", "missing_type"),
    ("echo ${msg:invalid}", "hello", "invalid_type"),
    ("sleep ${time:number}", "abc", "invalid_number"),
    ("echo ${msg:string}", "", "missing_input"),
]
