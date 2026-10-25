"""Give README panel URLs a content-based cache key (stdlib only)."""
import hashlib
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote


def version_panels(root, ref=None):
    if ref is None:
        ref = os.environ.get("GITHUB_REF_NAME") or subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=root, text=True
        ).strip() or "master"
    ref = quote(ref, safe="/")
    readme = root / "README.md"
    original = readme.read_text()

    def replace(match):
        filename = match.group(1)
        digest = hashlib.sha256((root / "assets" / filename).read_bytes()).hexdigest()[:16]
        return f"https://raw.githubusercontent.com/yubinex/yubinex/{ref}/assets/{filename}?v={digest}"

    updated = re.sub(
        r'https://(?:github\.com/yubinex/yubinex/raw|raw\.githubusercontent\.com/yubinex/yubinex)'
        r'/[^"\s?#]+/assets/([\w-]+\.svg)(?:\?v=[\w-]+)?',
        replace,
        original,
    )
    if updated != original:
        readme.write_text(updated)
    return updated != original


if __name__ == "__main__":
    version_panels(Path(__file__).resolve().parents[2])
