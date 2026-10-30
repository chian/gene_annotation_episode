"""Capture code actually imported by the constructed v3 source/population path."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in (ROOT / "gene_annotation_episode").glob("*.py")}
from gene_annotation_episode import literature_controlled_response_v3_inputs as source
from gene_annotation_episode import literature_controlled_response_v3_population as population
ns = runpy.run_path(str(ROOT / "tests/test_literature_controlled_response_v3_stages.py"))
f = ns["fixture"](companion=True)
extraction = source.read_controlled_response_v3_inputs(f.args, read_source=f.source)
assert source.validate_controlled_response_v3_extraction(f.args, extraction) == extraction
sheet = population.populate_controlled_response_v3(extraction)
assert population.validate_controlled_response_v3_population(extraction, sheet) == sheet
paths = set()
imports = {}
for name, module in sorted(sys.modules.items()):
    if name != "gene_annotation_episode" and not name.startswith("gene_annotation_episode."):
        continue
    path = Path(module.__file__).resolve()
    relative = str(path.relative_to(ROOT))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if before.get(relative) != digest:
        raise AssertionError((name, "module changed during freeze", str(path)))
    imports[name] = {"path": str(path), "sha256": digest}
    paths.add(relative)
for name in ("test_literature_controlled_response_v2_inputs.py", "test_literature_controlled_response_v3_stages.py",
        "test_literature_controlled_response_v3_inputs.py", "test_literature_controlled_response_local_calculations.py",
        "test_literature_controlled_response_v3_population.py"):
    paths.add("tests/" + name)
fixture_dir = Path("verification/literature_reference_evidence_2026-10-25_001/a105_controlled_full_source_design_069")
for name in ("CONSTRUCTED_SOURCE_CASES_001.json", "CONSTRUCTED_SOURCE_ROSTER_001.json"):
    paths.add(str(fixture_dir / name))
for row in json.loads((ROOT / fixture_dir / "CONSTRUCTED_SOURCE_ROSTER_001.json").read_text()):
    if row["encoded_image_file"] is not None:
        paths.add(str(fixture_dir / row["encoded_image_file"]))
pin = HERE / "pin_002"
pin.mkdir()
files = {}
for relative in sorted(paths):
    raw = (ROOT / relative).read_bytes()
    destination = pin / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    files[relative] = hashlib.sha256(raw).hexdigest()
manifest = {"kind": "coherent_constructed_v3_code_and_fixture_snapshot", "files": files,
    "live_imports": imports, "initial_source_calls": f.calls,
    "scientific_status": "Constructed fixtures only; no primary paper/model/native episode execution"}
with (HERE / "PIN_MANIFEST_002.json").open("x") as out:
    json.dump(manifest, out, indent=2)
    out.write("\n")
print(json.dumps({"pinned_files": len(files), "live_project_imports": len(imports),
    "shared_sha256": files["gene_annotation_episode/literature_controlled_response_inputs.py"]}))
