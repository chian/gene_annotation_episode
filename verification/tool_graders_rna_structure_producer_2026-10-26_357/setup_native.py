"""Isolated target installation; no shared project/upstream environment mutation."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import urllib.request

packet = Path(os.environ["RNA_PRODUCER_PACKET"])
target = packet / "native-site"
if target.exists():
    raise RuntimeError("isolated_target_already_exists")
command = [sys.executable, "-B", "-m", "pip", "install", "--no-deps", "--disable-pip-version-check",
    "--target", str(target), "ViennaRNA==2.7.0"]
print(json.dumps({"selected_setup_argv": command}), flush=True)
subprocess.run(command, check=True)
sources = {}
for relative in ("src/ViennaRNA/params/io.c", "src/ViennaRNA/params/io.h",
        "src/ViennaRNA/params/constants.h", "src/ViennaRNA/mfe/mfe.c",
        "src/ViennaRNA/eval/eval.c", "src/ViennaRNA/eval/structures.h",
        "interfaces/Python/RNA/__init__.py"):
    url = "https://raw.githubusercontent.com/ViennaRNA/ViennaRNA/v2.7.0/" + relative
    destination = packet / "primary-source" / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = urllib.request.urlopen(url).read()
        destination.write_bytes(data)
        sources[relative] = {"url": url, "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}
    except Exception as error:
        sources[relative] = {"url": url, "failure": repr(error)}
(packet / "primary-source" / "retrieval.json").write_text(json.dumps(sources, indent=2) + "\n")
print(json.dumps({"installed_target": str(target), "source_retrieval": sources}), flush=True)
