from typing import Any, Dict

ginx_config: Dict[str, Any] = {
    "scripts": {
        "upgrade-pip": {
            "command": "python -m pip install --upgrade pip",
            "description": "Upgrade pip to latest version",
        },
    },
    "plugins": {
        "enabled": ["version-sync"],
    },
    "settings": {
        "dangerous_commands": False,
    },
}
