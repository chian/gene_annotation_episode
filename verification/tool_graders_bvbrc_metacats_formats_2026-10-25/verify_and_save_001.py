"""Retained native-data verification and complete example writer (not a grader).

Run from the repository root with .venv/bin/python. This verification entrypoint
reads only the previously retained seven native cases and official legacy file.
The production parsers and validators receive supplied bytes/records only.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode import bvbrc_metacats_formats as f
from gene_annotation_episode import bvbrc_metacats_format_contracts as c


HERE = Path(__file__).resolve().parent
NATIVE = ROOT / "verification/tool_graders_bvbrc_metacats_native_execution_2026-10-25/cases"
BOUNDARY = ROOT / "verification/tool_graders_bvbrc_msa_metacats_boundaries_2026-10-25"
COUNTS = {
    "aa_two_groups": (12, 12, 1, 1, 3, 3),
    "aa_three_groups": (18, 18, 1, 3, 3, 9),
    "all_missing": (2, 2, 0, 0, 0, 0),
    "metadata_only_first_group": (13, 12, 1, 1, 3, 3),
    "native_pair_tail_underflow": (4000, 4000, 1, 0, 3, 3),
    "official_na": (14, 14, 143, 143, 765, 765),
    "twelve_groups": (48, 48, 1, 0, 3, 198),
}
VALIDATORS = {"metadata": c.validate_metacats_metadata, "adjusted_matrix": c.validate_metacats_adjusted_matrix,
              "chisq": c.validate_metacats_chisq_table, "pair": c.validate_metacats_pair_table,
              "raw_omnibus": c.validate_metacats_raw_r_table, "raw_pairwise": c.validate_metacats_raw_r_table}


def retained(path, kind, category, *, legacy=False):
    data = path.read_bytes()
    relative = str(path.relative_to(ROOT))
    artifact = {"raw_artifact_ref": relative, "source_ref": "retained-supplied-artifact:" + relative,
                "sha256": sha256(data).hexdigest()}
    kwargs = {"artifact": artifact, "encoding": "ascii"}
    if kind == "metadata":
        result = f.parse_metacats_metadata(data, **kwargs, delimiter="tab", header="present")
    elif kind == "adjusted_matrix":
        result = f.parse_metacats_adjusted_matrix(data, **kwargs, category_id=category)
    elif kind.startswith("raw_"):
        result = f.parse_metacats_raw_r_table(data, **kwargs, category_id=category,
            kind=kind[4:], layout="r_write_table_single_result_string")
    elif kind == "chisq":
        result = f.parse_metacats_chisq_table(data, **kwargs, category_id=category,
            layout="legacy_example_tsv" if legacy else "current_filtered_tsv")
    else:
        result = f.parse_metacats_pair_table(data, **kwargs, category_id=category, layout="current_filtered_tsv")
    assert result["value"] is not None
    saved = json.loads(json.dumps(result, allow_nan=False))
    assert VALIDATORS[kind](saved["value"]) == saved["value"]
    assert sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    return result, {"path": relative, "sha256": artifact["sha256"], "bytes": len(data)}


def main():
    examples, manifest = HERE / "saved_examples", []
    examples.mkdir(exist_ok=True)
    for case, expected in COUNTS.items():
        stem = "GROUP" if case == "official_na" else "comparison"
        paths = [("metadata", "metadata.tsv", "rows"),
                 ("adjusted_matrix", f"output/{stem}.txt", "rows"),
                 ("chisq", f"output/{stem}-chisqTable.tsv", "rows"),
                 ("pair", f"output/{stem}-mcTable.tsv", "rows"),
                 ("raw_omnibus", f"output/retained_raw/{stem}-chisqTable.txt", "omnibus_rows"),
                 ("raw_pairwise", f"output/retained_raw/{stem}-mcTable.txt", "pair_rows")]
        for (kind, path, collection), count in zip(paths, expected):
            result, source = retained(NATIVE / case / path, kind, "verification-category:" + case)
            assert result["status"] == "ok"
            assert len(result["value"][collection]) == count
            destination = examples / (case + "__" + kind + ".json")
            encoded = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()
            destination.write_bytes(encoded)
            manifest.append({"case": case, "kind": kind, "source": source, "status": result["status"],
                             "row_count": count, "example": str(destination.relative_to(ROOT)),
                             "example_sha256": sha256(encoded).hexdigest(), "example_bytes": len(encoded)})
    legacy_path = BOUNDARY / "additional_sources/bvbrc_metacats/docs/example_output.tsv"
    result, source = retained(legacy_path, "chisq", "verification-legacy-category", legacy=True)
    assert result["status"] == "partial"
    destination = examples / "official_legacy__chisq.json"
    encoded = (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()
    destination.write_bytes(encoded)
    manifest.append({"case": "official_legacy", "kind": "chisq", "source": source, "status": "partial",
        "row_count": len(result["value"]["rows"]), "example": str(destination.relative_to(ROOT)),
        "example_sha256": sha256(encoded).hexdigest(), "example_bytes": len(encoded)})
    sources = [ROOT / p for p in (
        "gene_annotation_episode/bvbrc_metacats_formats.py", "gene_annotation_episode/bvbrc_metacats_format_contracts.py",
        "tests/test_bvbrc_metacats_formats.py", "tests/test_bvbrc_metacats_format_contracts.py",
        "gene_annotation_episode/bvbrc_alignment_values.py")]
    sources += [BOUNDARY / "retained_sources/bvbrc_metacats" / p for p in (
        "scripts/Meta-CATS.R", "scripts/metadata_parser.pl", "service-scripts/App-MetaCATS.pl", "app_specs/MetaCATS.json")]
    report = {"verification_scope": "pure_parser_and_saved_document_validation",
        "new_native_execution": False, "appservice_execution": False, "episode_communication_verified": False,
        "all_original_input_bytes_unchanged": True, "examples": manifest,
        "implementation_and_inspected_producer_hashes": [
            {"path": str(path.relative_to(ROOT)), "sha256": sha256(path.read_bytes()).hexdigest()} for path in sources],
        "observed_examples": {
            "aa_two_groups_site2": {"chi_square": 8.33055648117294, "omnibus_p": 0.00389837142433717,
                "df": 1, "pair_p": 0.000533148220906465, "native_counts": [6, 6]},
            "aa_three_groups_pair_p": 0.0173810251352965,
            "native_pair_tail_underflow": {"raw_pair_p": 1, "filtered_pair_rows": 0, "native_omnibus_p": 0},
            "official_na": {"raw_sites": 765, "variable_sites": 312, "filtered_omnibus_rows": 143, "filtered_pair_rows": 143},
            "metadata_only_first_group": {"metadata_rows": 13, "matrix_rows": 12,
                "exported_headings": ["A", "B", "C"], "matrix_group_tokens": ["2", "3"], "exported_pair_token": "A,B"}},
        "remaining_work": ["original task/artifact/member/group association and provider assembly",
            "native-operation invocation and requested-return production binding",
            "complete episode-path integration verification", "live AppService resource verification",
            "raw R artifacts require explicit retention; deployed service does not promise their acquisition",
            "runtime R padded column identities are separate association evidence, not inferred by these parsers"]}
    (HERE / "VERIFICATION_001.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"retained_files": len(manifest), "cases": len(COUNTS),
                      "saved_example_bytes": sum(x["example_bytes"] for x in manifest),
                      "report": str((HERE / "VERIFICATION_001.json").relative_to(ROOT))}))


if __name__ == "__main__":
    main()
