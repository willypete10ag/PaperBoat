"""Compare native asset conversion pixels with an independent PNG decoder.

Requires ImageMagick's convert, included in the reusable cloud setup.
Generated reports are optional; no ROM assets or screenshots are written.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from build_badge_assets import indexed_png

from fixture_support import required_env
source = Path(required_env("PAPERBOAT_SOURCE_DIR")) / "port/ttyd64"
checks = []
for name, width, height in (
    ("pityflower", 32, 32), ("jumpman", 32, 32), ("hammerman", 32, 32),
    ("fpdrain", 32, 32), ("fp_drain_label", 40, 16),
    ("courageshell", 32, 32), ("powerpunch", 32, 32), ("minimrmini", 32, 32), ("mrsoftener", 32, 32), ("slowshroom", 32, 32), ("gradualsyrup", 32, 32), ("couplescake", 32, 32), ("meteormeal", 32, 32)
):
    path = source / (name + ".png")
    raster, colors = indexed_png(path, width, height)
    pixels = bytes(channel for packed in raster for index in (packed >> 4, packed & 15)
                   for channel in colors[index])
    reference = subprocess.check_output(["convert", str(path), "RGBA:-"])
    assert pixels == reference, f"PNG decoder mismatch: {name}"
    checks.append({"asset": name, "width": width, "height": height,
                   "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "rgba_sha256": hashlib.sha256(pixels).hexdigest()})
report = {"checks_passed": len(checks), "independent_decoder": "ImageMagick RGBA", "checks": checks}
if required_env("BADGE_ASSETS_RESULT"):
    Path(required_env("BADGE_ASSETS_RESULT")).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
