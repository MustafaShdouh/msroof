"""One Node.js executable resolver for offline tools and verification."""
import os
from pathlib import Path
import shutil


def node_executable():
    configured = os.environ.get("MASROOF_NODE")
    if configured:
        path = Path(configured)
        if not path.is_file():
            raise FileNotFoundError("MASROOF_NODE must name an existing Node.js executable")
        return str(path.resolve())
    found = shutil.which("node")
    if found:
        return found
    standard = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs/node.exe"
    if standard.is_file():
        return str(standard)
    raise FileNotFoundError("Node.js 24+ is required; install it or set MASROOF_NODE")
