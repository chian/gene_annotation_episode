"""Emit labelled synthetic pure-reader/calculator examples; no episode claims."""
from pathlib import Path
import hashlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "synthetic_examples_001"
spec = importlib.util.spec_from_file_location("calibration_recovery_fixture_169", ROOT / "tests/test_literature_calibration_recovery_169.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)

manifest = {"synthetic_only": True, "original_source_example": False,
            "episode_or_model_execution": False, "examples": []}
for name, unit, control in (("reporter_standard", "nmol", "reporter_standard"),
                            ("enzyme_activity_spike", "nmol/min", "enzyme_activity_spike"),
                            ("unresolved_control", "nmol", "unknown")):
    source = fixture.Source(unit=unit, recovery="97.5")
    args = source.args(unit=unit, recovery="97.5")
    args["control_kind"] = source.interpretation(control, None if control == "unknown" else
        "enzyme activity spike" if control == "enzyme_activity_spike" else "Illustrative standard")
    extracted, sheet = fixture.run(source, args)
    directory = OUT / name
    files = {"synthetic_source.xml": source.content,
             "selected_arguments.json": (json.dumps(args, indent=2, ensure_ascii=False) + "\n").encode(),
             "extraction.json": (json.dumps(extracted, indent=2, ensure_ascii=False) + "\n").encode(),
             "numerical_components.json": (json.dumps(sheet, indent=2, ensure_ascii=False) + "\n").encode()}
    for filename, content in files.items():
        write(directory / filename, content)
    manifest["examples"].append({"name": name, "files": [
        {"path": str((directory / filename).relative_to(OUT)), "sha256": hashlib.sha256(content).hexdigest()}
        for filename, content in files.items()]})
write(OUT / "MANIFEST.json", (json.dumps(manifest, indent=2) + "\n").encode())
print(json.dumps({"synthetic_only": True, "examples_written": len(manifest["examples"]), "directory": str(OUT)}))
