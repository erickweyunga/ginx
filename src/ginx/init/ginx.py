from typing import Dict, Any

ginx_config: Dict[str, Any] = {
    "scripts": {
        "hello-ginx": {
            "command": "echo 'Hello, Ginx!'",
            "description": "A script to greet Ginx users",
        },
    },
    "plugins": {
        "enabled": ["version-sync"],
    },
    "settings": {
        "dangerous_commands": True,
    },
}
