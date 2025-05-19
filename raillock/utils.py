import hashlib
import os
from typing import Optional


def calculate_tool_checksum(
    tool_name: str, description: str, server_name: Optional[str] = None
) -> str:
    """
    Calculate the checksum for a tool.
    If server_name is provided, include it in the hash (for SSE consistency).
    """
    if server_name:
        data = f"{server_name}:{tool_name}:{description}".encode("utf-8")
    else:
        data = f"{tool_name}:{description}".encode("utf-8")
    if os.environ.get("RAILLOCK_DEBUG", "false").lower() == "true":
        print(
            f"[DEBUG][checksum] tool_name={tool_name!r} description={description!r} server_name={server_name!r} data={data!r}"
        )
    return hashlib.sha256(data).hexdigest()


def debug_print(*args, **kwargs):
    if os.environ.get("RAILLOCK_DEBUG", "false").lower() == "true":
        print("[DEBUG][RailLock]", *args, **kwargs)
