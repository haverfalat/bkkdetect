"""Package only the native integration and instructions, excluding credentials."""

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
version = json.loads((root / "custom_components/bkkdetect/manifest.json").read_text())["version"]
target = root / f"dist/bkkdetect-{version}.zip"
target.parent.mkdir(exist_ok=True)
with ZipFile(target, "w", ZIP_DEFLATED) as archive:
    for file in sorted((root / "custom_components/bkkdetect").rglob("*")):
        if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
            archive.write(file, file.relative_to(root))
    archive.write(root / "README.md", "BKKDETECT-INSTALL.md")
print(target)
