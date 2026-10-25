"""Give README panel URLs a content-based cache key (stdlib only)."""
import hashlib
from pathlib import Path
import re


def version_panels(root):
    readme = root / "README.md"
    original = readme.read_text()

    def replace(match):
        url, filename = match.group(1), match.group(2)
        digest = hashlib.sha256((root / "assets" / filename).read_bytes()).hexdigest()[:16]
        return f"{url}?v={digest}"

    updated = re.sub(
        r'(https://github\.com/yubinex/yubinex/raw/master/assets/([\w-]+\.svg))(?:\?v=[\w-]+)?',
        replace,
        original,
    )
    if updated != original:
        readme.write_text(updated)
    return updated != original


if __name__ == "__main__":
    version_panels(Path(__file__).resolve().parents[2])
