import hashlib
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
    return hashlib.sha256(data).hexdigest()
