"""Run only constructed v3 checks from the immutable coherent code snapshot."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PIN = HERE / "pin_001"
manifest = json.loads((HERE / "PIN_MANIFEST_001.json").read_text())
for relative, digest in manifest["files"].items():
    actual = hashlib.sha256((PIN / relative).read_bytes()).hexdigest()
    if actual != digest:
        raise AssertionError((relative, "pin bytes changed"))
sys.dont_write_bytecode = True
sys.path.insert(0, str(PIN))
import pytest
status = pytest.main(["-q", "-p", "no:cacheprovider", *[
    str(PIN / "tests" / name) for name in (
        "test_literature_controlled_response_v3_stages.py",
        "test_literature_controlled_response_v3_inputs.py",
        "test_literature_controlled_response_local_calculations.py",
        "test_literature_controlled_response_v3_population.py")]])
imports = {}
for name, module in sorted(sys.modules.items()):
    if name != "gene_annotation_episode" and not name.startswith("gene_annotation_episode."):
        continue
    filename = getattr(module, "__file__", None)
    if filename is None:
        continue
    path = Path(filename).resolve()
    relative = str(path.relative_to(PIN))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if manifest["files"].get(relative) != digest:
        raise AssertionError((name, "import was not pinned", str(path)))
    imports[name] = {"path": str(path), "sha256": digest}
for relative, digest in manifest["files"].items():
    if hashlib.sha256((PIN / relative).read_bytes()).hexdigest() != digest:
        raise AssertionError((relative, "pin changed during checks"))
(HERE / "PIN_IMPORTS_001.json").write_text(json.dumps(imports, indent=2) + "\n")
print(f"Actual imported project modules all pinned: {len(imports)}")
raise SystemExit(status)
