"""Create complete synthetic frozen338 sheets, never a native VDB execution."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent

if len(sys.argv) == 1:
    from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
    directory = PACKET / "fixtures_001"
    directory.mkdir(exist_ok=False)
    result = run_local_job([str(ROOT / ".venv/bin/python"), "-B", str(Path(__file__).resolve()), "--worker"],
        cwd=directory, policy=LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None),
        stdout_path=directory / "stdout.txt", stderr_path=directory / "stderr.txt",
        env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT) + ":" + str(ROOT / "tests")})
    (directory / "receipt.json").write_text(json.dumps(result.metadata, indent=2, sort_keys=True) + "\n")
    print(result.stdout_path.read_text())
    print(result.stderr_path.read_text())
    raise SystemExit(result.returncode)

assert sys.argv[1:] == ["--worker"]
from test_blast_vdb_function_inputs import whole_case, translated_case, populate, census_for
from gene_annotation_episode.blast_vdb_function_inputs import validate_blast_vdb_function_sheet

whole_values, assignments = whole_case()
whole = populate(whole_values, assignments)
whole = populate(whole_values, assignments, censuses=[census_for(whole)])
translated_values = translated_case()
translated = populate(translated_values)
translated = populate(translated_values, censuses=[census_for(translated, "feature", extra=False)])
siblings = populate(translated_case(siblings=True))
manifest = {"validation_kind": "synthetic_reports_and_explicit_synthetic_census; not_live_vdb", "files": []}
for name, sheet in (("whole_sequence.json", whole), ("translated_features.json", translated), ("translated_siblings.json", siblings)):
    payload = json.dumps(sheet, sort_keys=True, indent=2, allow_nan=False) + "\n"
    frozen = json.loads(payload)
    assert validate_blast_vdb_function_sheet(frozen) == frozen
    Path(name).write_text(payload)
    manifest["files"].append({"path": name, "bytes": len(payload.encode()), "sha256": hashlib.sha256(payload.encode()).hexdigest(),
        "entities": len(sheet["entities"]), "original_hsps": len(sheet["base_components"]["hsps"]), "observations": len(sheet["observations"]),
        "census_statuses": [row["status"] for row in sheet["link_results"] if row["record_kind"] == "census"]})
Path("manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
print(json.dumps(manifest, sort_keys=True))
