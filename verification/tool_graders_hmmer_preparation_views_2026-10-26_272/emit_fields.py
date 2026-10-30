"""Render the declared catalogue, with a bounded documentation build receipt."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode import hmmer_preparation_result_views as views
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


def render():
    groups = {}
    for program, modes in views.PROGRAM_MODES.items():
        for mode in modes:
            definitions, checks = views._definitions(program, mode)
            signature = json.dumps([definitions, sorted(checks)], sort_keys=True)
            entry = groups.setdefault(signature, {"operations": [], "definitions": definitions, "checks": sorted(checks)})
            entry["operations"].append(program + "/" + mode)
    lines = [
        "# Closed HMMER preparation projection fields — 272/V1", "",
        "This is the exact static path catalogue consumed by `preparation_projection_catalog(program, mode)`. "
        "It documents copied saved values; it is not an executable scoring language. Each operation below uses only its listed collections, row kinds, quantity paths and check names.", "",
        "## Selection and missing values", "",
        "A selector names one existing collection, an explicit row window or ordered record-key list, and the desired paths/check names. "
        "There is no default or fixed maximum result count. `calculations` means `calculations.rows`; the other collections are their exact `sheet` fields. "
        "A path declared for one row kind may be requested for another kind in the same collection; that inapplicable cell returns `value=null,state=missing,unit=null`. "
        "A declared but absent field uses its row-kind unit only when that mapping has one unit. "
        "A present saved component copies its exact value, state and unit, including nonzero incomplete/failed values. "
        "Explicit native scalar states are copied. No background, fit parameter, denominator, unit conversion or missing measurement is supplied by projection.", "",
        "Catalogue `unit` is one string or a sorted unique list of the actual declared units. "
        "The row-kind table below is the exact kind-to-unit mapping; alternatives within one row kind remain alternatives. "
        "Returned quantity `unit` is nullable and copies the saved cell when it exists. "
        "For F1 native `index_parameters.payload.value`, `bin_length` has `index_symbol_count` and `suffix array sample rate` has `suffix_array_sampling_interval`; "
        "`alphabet` and `input is asserted to be` are categorical rows and return null/missing/null for this numeric path.", "",
        "## Retained data and provenance", "",
        "Full saved D1 sheets remain retained. Native sequences, alignments, probability arrays, per-position/column tables, score vectors, tracebacks, XY series, calibration tables, "
        "FM packed arrays, interval/mismatch tables, dynamic E1 symbol-count tables, original tokens, inputs and arbitrary diagnostics do not cross this scalar projection. "
        "Their aggregate scalar components remain selectable below. The unit is the native or calculator's actual unit; generated scores and samples are never described as biological measurements or annotation confidence.", "",
        "Checks are copied by the exact saved row relationship. Every matching instance remains separate, including contradictory outcomes. "
        "A requested absent check is `unknown` with no occurrences. The check-name lists are closed family vocabularies; they do not assert that each name exists for every row. "
        "See [IDENTITY_HANDOFF_001.md](IDENTITY_HANDOFF_001.md) for E1 model/consensus, S1 scope and F1 null-key exceptions. "
        "Artifact references disclose only explicit selections or operands required by the selected row/cell/check. Aggregate rows have no fabricated single artifact. "
        "Original occurrence IDs, roles and ordinals distinguish identical bytes in different roles.", "",
        "## Exact catalogue", "",
    ]
    for ordinal, group in enumerate(groups.values(), 1):
        lines += [f"### Catalogue group {ordinal}", "", "Operations: " + ", ".join("`" + x + "`" for x in group["operations"]) + ".", "",
            "Checks allowed in the listed collections: " + ", ".join("`" + x + "`" for x in group["checks"]) + ".", "",
            "| Collection | Row kind | Exact quantity path | Exact unit(s) | Existing explicit state | Meaning and source |",
            "| --- | --- | --- | --- | --- | --- |"]
        for collection, kinds in group["definitions"].items():
            for kind, fields in sorted(kinds.items()):
                if not fields:
                    lines.append(f"| `{collection}` | `{kind}` | — | — | — | No declared scalar quantity; identity and matching requested checks only. |")
                for path, spec in sorted(fields.items()):
                    units = spec["unit"] if type(spec["unit"]) is list else [spec["unit"]]
                    unit = ", ".join("`" + u + "`" for u in sorted(set(units)))
                    state = "`" + path + ".state`" if spec["cell"] else "`" + spec["state"] + "`" if spec["state"] else "No separate state; null is missing"
                    source = ("calculations.rows" if collection == "calculations" else "sheet." + collection) + "/" + kind + "/" + path
                    meaning = spec["meaning"].replace("|", "\\|")
                    lines.append(f"| `{collection}` | `{kind}` | `{path}` | {unit} | {state} | {meaning} Source: `{source}`. |")
        lines.append("")
    lines += ["## Verification and source identity", "",
        "[VERIFICATION.md](VERIFICATION.md) distinguishes retained native results, synthetic custody/reference fixtures and intentionally malformed saved data. "
        "The catalogue build receipt records module and document hashes. Tests independently walk fixed dictionary component cells in every saved mode envelope, excluding retained arrays and dynamic symbol tables; "
        "this coverage check is test-only and is never runtime field discovery. Root publication and episode integration are separate checks.", ""]
    return "\n".join(lines)


def main():
    if sys.argv[1:] == ["--emit"]:
        document = render()
        target = HERE / "FIELDS.md"
        if target.exists() and target.read_text() != document:
            raise ValueError("existing catalogue differs; publish an additive correction")
        target.write_text(document)
        print(json.dumps({"file": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size, "operations": sum(map(len, views.PROGRAM_MODES.values()))}))
        return
    directory = HERE / sys.argv[1]
    directory.mkdir()
    policy = LocalJobPolicy(memory_bytes=20 * 1024**3, scratch_bytes=4 * 1024**3, wall_seconds=None)
    command = [str(ROOT / ".venv/bin/python"), str(Path(__file__).resolve()), "--emit"]
    result = run_local_job(command, cwd=directory, policy=policy,
        env={"PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(directory)})
    receipt = {"argv": command, "policy": asdict(policy), "returncode": result.returncode, "metadata": result.metadata,
        "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__).resolve(), ROOT / "gene_annotation_episode/hmmer_preparation_result_views.py")},
        "stdout_path": str(result.stdout_path), "stderr_path": str(result.stderr_path)}
    (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(result.stdout_path.read_text())


if __name__ == "__main__":
    main()
