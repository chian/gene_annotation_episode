"""Pin unchanged, already retained synthetic N captures; no native execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode()


def retain(path, destination):
    raw = path.read_bytes()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert destination.read_bytes() == raw
    else:
        destination.write_bytes(raw)
    return dict(original_path=str(path.relative_to(ROOT)), retained_path=str(destination.relative_to(HERE)),
                sha256=sha(raw), size_bytes=len(raw))


sources = {
    "native6": ("tool_graders_native_blast_database_producer_2026-10-26_313/examples002/psiblast-sequence-complete/attempt", "313.synthetic"),
    "native6_shared": ("tool_graders_native_blast_database_producer_2026-10-26_313/check004/temporary/pytest/test_exact_shared_sidecar_iden0/attempt", "313.synthetic"),
    "standard_blastn": ("tool_graders_standard_blast_database_producer_2026-10-26_331/check003/temporary/pytest/test_one_synthetic_process_all0/attempt", "331.synthetic"),
    "standard_blastp": ("tool_graders_standard_blast_database_producer_2026-10-26_331/check003/temporary/pytest/test_one_synthetic_process_all1/attempt", "331.synthetic"),
}
index = {}
for name, (relative, execution_id) in sources.items():
    original = ROOT / "verification" / relative
    target = HERE / "fixtures" / name
    bundle = json.loads((original / "bundle.json").read_bytes())
    plan_name = "selected-plan.json" if name.startswith("native6") else "native-blast-standard-database-plan.json"
    plan = json.loads((original / plan_name).read_bytes())
    artifacts = []
    for row in bundle["artifacts"]:
        raw = (original / row["relative_path"]).read_bytes()
        assert sha(raw) == row["sha256"] and len(raw) == row["size_bytes"]
        record = retain(original / row["relative_path"], HERE / "fixtures" / "bytes" / row["sha256"])
        artifacts.append(dict(artifact_key=row["artifact_key"], **record))
    index[name] = dict(evidence="retained synthetic executable output; not scientific BLAST",
        bundle=retain(original / "bundle.json", target / "bundle.json"),
        plan=retain(original / plan_name, target / "plan.json"), artifacts=artifacts,
        attempt_identity=dict(identity={**plan["identity"], "execution_id": execution_id},
            attempt_directory=plan["attempt_directory"], plan_sha256=sha(canonical(plan))))

counterexample = ROOT / "verification/tool_graders_standard_blast_database_metadata_2026-10-26_332/check003/temporary/pytest/test_selected_database_sidecar0/sidecar_counterexample.json"
index["standard332"] = dict(evidence="retained hand-built synthetic N-valid counterexample; not native science",
    counterexample=retain(counterexample, HERE / "fixtures/standard332/sidecar_counterexample.json"))
(HERE / "fixtures/INDEX.json").write_text(json.dumps(index, indent=2) + "\n")
source = ROOT / "gene_annotation_episode/native_blast_database_metadata.py"
before = retain(source, HERE / "source_before/native_blast_database_metadata.py")
(HERE / "SOURCE_BEFORE.json").write_text(json.dumps(before, indent=2) + "\n")
print(json.dumps({"retained_cases": list(index), "source_before": before["sha256"]}))
