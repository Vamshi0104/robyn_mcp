from __future__ import annotations

AUTHOR = "Vamshi Krishna Madhavan"
LICENSE_NAME = "Apache-2.0"
CREATED_ON = "Mar 22, 2026"

_BANNER_LINES = [
    "|----------------------------------------------------------|",
    "|  ____   ___  ____ __   __ _   _      __  __  ____ ____  |",
    "| |  _ \\ / _ \\| __ )\\ \\ / /| \\ | |    |  \\/  |/ ___|  _ \\ |",
    "| | |_) | | | |  _ \\ \\ V / |  \\| |____| |\\/| | |   | |_) ||",
    "| |  _ <| |_| | |_) | | |  | |\\  |____| |  | | |___|  __/ |",
    "| |_| \\_\\\\___/|____/  |_|  |_| \\_|    |_|  |_|\\____|_|    |",
    "|----------------------------------------------------------|",
    "ROBYN-MCP",
    f"Author : {AUTHOR}",
    f"License: {LICENSE_NAME}",
    f"Created: {CREATED_ON}",
]


def build_install_banner() -> str:
    return "\n".join(_BANNER_LINES)
