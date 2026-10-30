"""Export existing controlled-test facts and freeze source; no scientific run."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parents[1]
OUT = Path(sys.argv[1])


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def descriptor(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


positive, negative, saved = [], [], []
for tag in ("hosts_007", "remaining_hosts_010"):
    for folder in sorted((PACKET / tag / "temporary").iterdir()):
        if not folder.is_dir() or folder.is_symlink():
            continue
        body_path = folder / "actual-result.json"
        if body_path.exists() and (folder / "received-parent-facts.json").exists():
            body = read(body_path)
            rows = body["publication"]["rows_by_family"]
            requested = body["target"]["assignment"]["requested_job"]
            key = "native_blast_standard_database" if "native_blast_standard_database" in requested else "native_blast_database"
            job = requested[key]
            positive.append(dict(program=job["program"], query_kind=job["query"]["kind"],
                native_format=next(r["format"] for r in job["outputs"] if r["role"] == "primary_report"),
                complete=body["complete"], acquisition_complete=body["publication"]["acquisition_complete"],
                projection_complete=body["publication"]["projection_complete"],
                functions=rows["sequence_function"], population=rows["sequence_population"],
                inputs=[descriptor(folder / name) for name in ("actual-result.json", "requested-selector.json",
                    "selected-v3-payload.json", "original-parent-form.json", "original-parent-schema.json", "received-parent-facts.json")]))
        qualified = folder / "qualified-result.json"
        if qualified.exists():
            body = read(qualified)
            negative.append(dict(source=descriptor(qualified), complete=body["complete"],
                native_execution_successful=body["publication"]["native_execution_successful"],
                functions=body["publication"]["rows_by_family"]["sequence_function"], failures=body["failures"]))
for folder in sorted((PACKET / "final_custody_009" / "temporary").glob("test_actual_quality_return_and*")):
    if folder.is_symlink() or not (folder / "saved-calculation-T2.json").exists():
        continue
    request = read(folder / "saved-request.json")
    request_key = "native_blast_standard_database" if "native_blast_standard_database" in request["bundle"]["requested_job"] else "native_blast_database"
    manifest = read(folder / "saved-T2-manifest.json")
    saved.append(dict(program=request["bundle"]["requested_job"][request_key]["program"],
        model=request["sequence_model"], calculation=read(folder / "saved-calculation-T2.json"),
        input_identity=manifest["input_identity"], input_interpretation_id=manifest["input_interpretation_id"],
        calculation_id=manifest["calculation_id"], status=manifest["status"],
        sources=[descriptor(folder / name) for name in ("saved-calculation-T2.json", "saved-T2-manifest.json",
            "received-parent-facts.json", "original-parent-form.json", "saved-reuse.py")],
        rejected_erasure=descriptor(folder / "rejected-generation" / "worker-manifest.json"),
        rejected_origin=descriptor(folder / "rejected-origin-generation" / "worker-manifest.json")))
assert len(positive) == 14 and len(negative) == 13 and len(saved) == 3, (len(positive), len(negative), len(saved))
assert all(r["complete"] and r["projection_complete"] for r in positive)
write(OUT / "ACTUAL_TYPED_NUMERICAL_EXAMPLES_001.json", dict(
    evidence="Explicitly synthetic original reports and supplied numerical census/assertion records; actual selected child, capture, worker and original typed return; no database BLAST or remote job.",
    positive=positive, negative=negative, saved=saved))

checks = []
for folder in sorted(PACKET.iterdir()):
    if not folder.is_dir() or not (folder / "receipt.json").exists():
        continue
    receipt = read(folder / "receipt.json")
    stdout = (folder / "stdout.txt").read_text()
    summaries = [s for s in stdout.splitlines() if re.search(r"\d+ (?:passed|failed|deselected).+ in ", s) or re.search(r"\d+ passed in ", s)]
    before, after = folder / "before-source-pins.json", folder / "after-source-pins.json"
    checks.append(dict(run=folder.name, receipt=descriptor(folder / "receipt.json"),
        command=receipt["command"], cwd=receipt["cwd"], policy=receipt["policy"], returncode=receipt["returncode"],
        elapsed_seconds=receipt["metadata"].get("elapsed_seconds"), pytest_summary=summaries[-1:] or [],
        source_pins_unchanged=read(before) == read(after) if before.exists() and after.exists() else None))
write(PACKET / "CHECKS_001.json", checks)

owned = ["gene_annotation_episode/" + name + ".py" for name in (
    "blast_iteration_inputs", "blast_iteration_calculators", "native_blast_database_result_worker",
    "native_blast_standard_database_result_worker", "native_blast_database_result_publication")]
owned += ["tests/" + name + ".py" for name in (
    "test_native_blast_database_population_integration", "test_blast_population_association_recalculation",
    "blast_population_integration_fixtures", "test_blast_fasta_record_identity_integration")]
dependencies = ["gene_annotation_episode/" + name + ".py" for name in (
    "blast_database_population_associations", "blast_database_grader", "blast_sequence_database",
    "native_blast_database_population_metadata", "native_blast_database_metadata",
    "native_blast_standard_database_metadata", "native_blast_standard_database_contracts")]
frozen = PACKET / "final_sources_001"
frozen.mkdir(exist_ok=False)
for name in owned + dependencies:
    target = frozen / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
write(PACKET / "SOURCE_PINS_CURRENT_001.json", dict(owned=[descriptor(ROOT / n) for n in owned],
    dependencies=[descriptor(ROOT / n) for n in dependencies]))
diffs = []
for name in owned[:5]:
    old = PACKET / "before" / "source" / name
    diffs.extend(difflib.unified_diff(old.read_text().splitlines(True), (ROOT / name).read_text().splitlines(True),
        fromfile="before/" + name, tofile="after/" + name))
(PACKET / "PRODUCTION_DIFF_001.patch").write_text("".join(diffs))
print(json.dumps(dict(positive_cases=len(positive), negative_cases=len(negative), saved_cases=len(saved),
    frozen_source_files=len(owned + dependencies), existing_test_runs=len(checks))))
