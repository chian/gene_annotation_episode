"""Explicit current schema export/check; no mutations of production or history."""
from pathlib import Path
import hashlib
import json
import sys

PACKET = Path(sys.argv[1]).resolve()
REPO = PACKET.parents[1]
OUT = Path.cwd()


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "resolved_path": str(path.resolve()),
            "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


paths = sorted(path for package in ("gene_annotation_episode", "method_loop")
               for path in (REPO / package).glob("*.py"))
before = [pin(path) for path in paths]
write("export_source_pins_before.json", before)
static = json.loads((PACKET / "schema001/SCHEMA_REACHABILITY.json").read_text())
for expected in static["source_pins_after"]:
    assert pin(Path(expected["path"]))["sha256"] == expected["sha256"]
sys.path.insert(0, str(REPO))
from gene_annotation_episode.chromatin_interaction_return_views import chromatin_fact_sources

exports = chromatin_fact_sources()
assert len(exports) == 3
write("ACTUAL_EXPORTS.json", exports)
comparison = {}
for source, descriptor in exports.items():
    actual = descriptor["report_schema"]
    baseline = json.loads((PACKET / "schema001" / (source + ".static_schema.json")).read_text())
    write(source + ".actual_schema.json", actual)
    comparison[source] = {"exact_canonical_json_equal": canonical(actual) == canonical(baseline),
        "id": actual["$id"], "canonical_complete_schema_sha256":
            hashlib.sha256(canonical(actual).encode()).hexdigest()}
after = [pin(path) for path in paths]
write("export_source_pins_after.json", after)
loaded = sorted({str(Path(module.__file__).resolve()) for module in sys.modules.values()
    if hasattr(module, "__file__") and module.__file__
    and str(Path(module.__file__).resolve()).startswith(str(REPO) + "/")})
result = {"callable": "gene_annotation_episode.chromatin_interaction_return_views.chromatin_fact_sources",
    "interpreter": pin(Path(sys.executable)), "source_pins_unchanged": before == after,
    "imported_repository_files": [pin(Path(path)) for path in loaded],
    "comparisons": comparison, "changed_schema_regression_executed": False}
write("ACTUAL_EXPORT_CHECK.json", result)
assert before == after
assert all(row["exact_canonical_json_equal"] for row in comparison.values())
print(json.dumps({"source_pins_unchanged": before == after, "comparisons": comparison}))
