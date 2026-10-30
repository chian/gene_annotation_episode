"""Save actual tiny native results, labeled corruptions, sheets and exact replay."""
from contextlib import ExitStack
from copy import deepcopy
import builtins
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
from unittest.mock import patch

from Bio.Seq import Seq
from gene_annotation_episode import sequence_views
from gene_annotation_episode.sequence_extraction_grader import grade_extraction, calculate_extraction_scores
from gene_annotation_episode.sequence_mapping import VERSION, translation_mapping
from gene_annotation_episode.sequence_ops import translate

ROOT = Path(__file__).resolve().parents[2]


def part(start, end, subject="input:synthetic", unit="nt", strand="+"):
    return {"subject_ref": subject, "start": start, "end": end, "unit": unit, "strand": strand}


def parent(length, path=None, scale=1):
    return {"version": VERSION, "units_per_symbol": scale, "symbol_length": length,
            "path": path or [part(0, length * scale)]}


def reverse_keys(value):
    if isinstance(value, dict):
        return {key: reverse_keys(item) for key, item in reversed(list(value.items()))}
    if isinstance(value, list):
        return [reverse_keys(item) for item in value]
    return value


examples = []
segments = [{"start": 4, "end": 7}, {"start": 0, "end": 3},
            {"start": 4, "end": 7}, {"start": 2, "end": 5}]
for orientation in ("as_is", "reverse_complement"):
    examples.append(("ordered_" + orientation, "ACGTTGCAA", "dna", segments, orientation, parent(9), None))
for molecule in ("dna", "rna"):
    examples.append((molecule + "_ambiguity", "AcGtUrYsWkMbDhVn", molecule, None,
                     "reverse_complement", parent(16), None))
protein = translate("ATGAAAGGGTAA", code=11)
split = translation_mapping([part(20, 24, "contig:z"), part(50, 58, "contig:a", strand="-")],
    start=0, end=12, strand="+", protein_length=4)
examples.append(("protein_split_ancestry", protein["sequence"], "protein",
                 [{"start": 1, "end": 3}, {"start": 1, "end": 2}], "as_is", split, None))
for label in ("wrong_same_length", "truncated_output", "missing_mapping", "invalid_mapping"):
    examples.append((label, "aCGT", "dna", None, "as_is", parent(4), label))
expected_summaries = {
    "ordered_as_is": {"input_symbol_count": 9, "output_symbol_count": 12,
        "selected_symbol_occurrence_count": 12, "distinct_selected_input_symbol_count": 7,
        "repeated_selected_input_symbol_count": 5, "selected_input_fraction": 7 / 9,
        "compared_symbol_count": 12, "matching_symbol_count": 12, "mismatching_symbol_count": 0,
        "source_segment_count": 4, "unmapped_output_symbol_count": 0},
    "protein_split_ancestry": {"output_symbol_count": 3, "distinct_selected_input_symbol_count": 2,
        "repeated_selected_input_symbol_count": 1, "source_segment_count": 4,
        "mapped_output_symbol_count": 3, "unmapped_output_symbol_count": 0},
    "wrong_same_length": {"output_length_difference": 0, "compared_symbol_count": 4,
        "matching_symbol_count": 2, "mismatching_symbol_count": 2, "unmapped_output_symbol_count": 2},
    "truncated_output": {"output_length_difference": -2, "compared_symbol_count": 2,
        "matching_symbol_count": 2, "mismatching_symbol_count": 0, "unmapped_output_symbol_count": 0},
    "missing_mapping": {"matching_symbol_count": 4, "source_segment_count": None,
        "unmapped_output_symbol_count": 4},
    "invalid_mapping": {"matching_symbol_count": 4, "source_segment_count": None,
        "unmapped_output_symbol_count": 4},
}
expected_summaries["ordered_reverse_complement"] = expected_summaries["ordered_as_is"]
for molecule in ("dna", "rna"):
    expected_summaries[molecule + "_ambiguity"] = {
        "matching_symbol_count": 16, "mismatching_symbol_count": 0, "output_symbol_count": 16}
retained, report = [], []
for name, sequence, molecule, selected, orientation, mapping, corruption in examples:
    request = {"molecule": molecule, "segments": selected or [{"start": 0, "end": len(sequence)}],
               "orientation": orientation}
    native = sequence_views.view_sequence(sequence, **request)
    original = deepcopy(native)
    if corruption == "wrong_same_length":
        native["sequence"] = "ACGA"
    elif corruption == "truncated_output":
        native["sequence"], native["output_length"] = "aC", 2
    elif corruption == "missing_mapping":
        mapping = None
    elif corruption == "invalid_mapping":
        mapping["path"][0]["end"] = 3
    operands = {"input_sequence": sequence, "subject_ref": "product:synthetic_parent",
                "parent_mapping": mapping, "request": request}
    result = grade_extraction(native, **operands)
    for field, number in expected_summaries[name].items():
        assert result["scores"]["summary"][field] == number, (name, field)
    directory = Path(name)
    directory.mkdir()
    for filename, body in (("native_original.json", original), ("native_supplied.json", native),
                           ("inputs.json", operands), ("sheet.json", result["sheet"]),
                           ("scores.json", result["scores"]),
                           ("sheet_reversed_keys.json", reverse_keys(result["sheet"]))):
        (directory / filename).write_text(json.dumps(body, sort_keys=filename != "sheet_reversed_keys.json", indent=2) + "\n")
    canonical = json.loads((directory / "sheet.json").read_text())
    reversed_sheet = json.loads((directory / "sheet_reversed_keys.json").read_text())
    retained.append((canonical, reversed_sheet, result["scores"]))
    report.append({"name": name, "material": "synthetic_sequences",
        "native_execution": "actual_sequence_views.view_sequence",
        "supplied_corruption": corruption, "independent_expected_values": expected_summaries[name],
        "summary": result["scores"]["summary"], "source_coverage": result["scores"]["output_source_coverage"]})


def forbidden(*args, **kwargs):
    raise AssertionError("saved-sheet replay cannot call native work, I/O or network")


with ExitStack() as stack:
    for owner, name in ((builtins, "open"), (io, "open"), (Path, "open"), (Path, "read_text"),
                        (Path, "read_bytes"), (socket, "socket"), (subprocess, "Popen"),
                        (sequence_views, "view_sequence"), (Seq, "reverse_complement"),
                        (Seq, "reverse_complement_rna")):
        stack.enter_context(patch.object(owner, name, forbidden))
    for canonical, reversed_sheet, expected in retained:
        assert calculate_extraction_scores(canonical) == expected
        assert calculate_extraction_scores(reversed_sheet) == expected

paths = ["gene_annotation_episode/sequence_extraction_grader.py", "tests/test_sequence_extraction_grader.py",
         "gene_annotation_episode/sequence_views.py", "gene_annotation_episode/sequence_mapping.py",
         "gene_annotation_episode/knowledge/sequence-extraction.md",
         "verification/tool_graders_sequence_derivation_2026-10-26_279/CONTRACT_001.md"]
body = {"examples": report, "saved_recalculations": 2 * len(retained),
        "native_io_network_forbidden_during_recalculation": True,
        "source_hashes": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}}
Path("report.json").write_text(json.dumps(body, indent=2) + "\n")
print(json.dumps(body, indent=2))
