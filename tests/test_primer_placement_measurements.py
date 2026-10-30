"""Independent supplied-output controls; genuine source execution is opt-in."""
from copy import deepcopy
import ast
import builtins
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import traceback

import pytest

from gene_annotation_episode.biopython_pairwise_grader import count_literal_alignment_columns
from gene_annotation_episode.primer_placement_measurements import (
    NATIVE_SCHEMA, build_primer_placement_sheet, calculate_primer_placement_components,
)
from gene_annotation_episode.sequence_mapping import VERSION


def mapping(length, reference, start=0, strand="+"):
    return {"version": VERSION, "units_per_symbol": 1, "symbol_length": length,
        "path": [{"subject_ref": reference, "start": start, "end": start + length, "unit": "nt", "strand": strand}]}


def operands(target="AAAACCCCAAAA", primers="AAAA"):
    occurrences = [primers] if type(primers) is str else primers
    return {"target_sequence": target, "primers": deepcopy(primers), "target_ref": "supplied:target",
        "primer_refs": ["supplied:primer:" + str(i) for i in range(len(occurrences))],
        "target_mapping": mapping(len(target), "source:target", 100),
        "primer_mappings": [mapping(len(p), "source:primer:" + str(i), 500) if type(p) is str and p else None for i, p in enumerate(occurrences)]}


def native_fixture(groups, outcome="completed"):
    return {"schema": NATIVE_SCHEMA, "outcome": outcome, "result": {
        "explanation": "labelled synthetic supplied-output control, not a native claim", "sequences": deepcopy(groups)},
        "failure": {"exception_type": "SyntheticControl", "message": "explicit failure control"} if outcome == "failed" else None,
        "source_identity": {"path": "labelled-synthetic-fixture", "callable": "align_sequences", "sha256": "0" * 64}}


HITS = [{"position": 0, "strand": "+", "mismatches": []},
        {"position": 1, "strand": "+", "mismatches": [[3, "A", "C"]]},
        {"position": 7, "strand": "+", "mismatches": [[0, "A", "C"]]},
        {"position": 8, "strand": "+", "mismatches": []}]
GROUP = {"sequence": "AAAA", "alignments": HITS}


def components(record=None, args=None):
    return calculate_primer_placement_components(build_primer_placement_sheet(
        native_fixture([GROUP]) if record is None else record, **(operands() if args is None else args)))


def codes(result):
    return {r["code"] for r in result["issues"]}


def test_shared_literal_column_authority_preserves_existing_gaps_and_ambiguity_arithmetic():
    assert count_literal_alignment_columns("ACD-EFG", "ACTVE-G") == {
        "alignment_columns": 7, "paired_positions": 5, "identical_positions": 4,
        "substituted_positions": 1, "query_gap_columns": 1, "reference_gap_columns": 1,
        "query_aligned_positions": 6, "reference_aligned_positions": 6}
    assert count_literal_alignment_columns("ANN", "ANA")["identical_positions"] == 2
    assert count_literal_alignment_columns("AAAA", "AAAC")["substituted_positions"] == 1


def test_independent_four_placements_exact_counts_denominators_and_full_input_retention():
    native, args = native_fixture([GROUP]), operands("aaaaccccaaaa", "aaaa")
    before = deepcopy((native, args))
    sheet = build_primer_placement_sheet(native, **args)
    result = calculate_primer_placement_components(sheet)
    assert (native, args) == before
    assert sheet["inputs"]["target_sequence"] == "aaaaccccaaaa"
    assert sheet["inputs"]["primers"] == "aaaa"
    assert result["status"] == "complete"
    assert result["summary"] == {"target_length_symbols": 12, "requested_primer_occurrence_count": 1,
        "native_group_count": 1, "known_native_hit_list_count": 1,
        "retained_native_hit_occurrence_count": 4, "usable_saved_hit_count": 4,
        "plus_hit_count": 4, "minus_hit_count": 0, "strand_known_hit_count": 4,
        "source_compatible_hit_count": 4, "mismatch_count_sum": 2, "mismatch_count_denominator_hits": 4}
    group = result["groups"][0]
    assert group["candidate_windows_per_orientation"] == 9
    assert group["candidate_oriented_windows"] == 18
    assert [h["target_interval"] for h in group["hits"]] == [[0, 4], [1, 5], [7, 11], [8, 12]]
    assert [h["mismatch_fraction"] for h in group["hits"]] == [
        {"numerator": 0, "denominator": 4, "value": 0}, {"numerator": 1, "denominator": 4, "value": .25},
        {"numerator": 1, "denominator": 4, "value": .25}, {"numerator": 0, "denominator": 4, "value": 0}]
    assert set(result["summary"]) <= set(result["definitions"])
    assert all("unit" in result["definitions"][field] and "missing_behavior" in result["definitions"][field] for field in result["summary"])
    assert not any(key in result for key in ("score", "confidence", "evalue"))


def test_target_mismatch_paths_preserve_split_reversed_original_ancestry():
    args = operands()
    args["target_mapping"]["path"] = [
        {"subject_ref": "source:a", "start": 100, "end": 104, "unit": "nt", "strand": "+"},
        {"subject_ref": "source:b", "start": 200, "end": 208, "unit": "nt", "strand": "-"}]
    result = components(args=args)
    hit = result["groups"][0]["hits"][1]
    assert hit["target_mapping"]["intervals"] == [
        {"subject_ref": "source:a", "start": 101, "end": 104, "unit": "nt", "strand": "+"},
        {"subject_ref": "source:b", "start": 207, "end": 208, "unit": "nt", "strand": "-"}]
    mismatch = hit["mismatches"][0]
    assert mismatch["target_position"] == 4
    assert mismatch["target_source_intervals"] == [
        {"subject_ref": "source:b", "start": 207, "end": 208, "unit": "nt", "strand": "-"}]
    assert result["groups"][0]["hits"][2]["mismatches"][0]["target_source_intervals"] == [
        {"subject_ref": "source:b", "start": 204, "end": 205, "unit": "nt", "strand": "-"}]


def test_reverse_native_mismatch_position_is_oriented_and_maps_to_original_primer():
    record = native_fixture([{"sequence": "CGTT", "alignments": [
        {"position": 1, "strand": "-", "mismatches": [[2, "C", "T"]]}]}])
    result = components(record, operands("AAATGGG", "CGTT"))
    hit = result["groups"][0]["hits"][0]
    assert result["status"] == "complete"
    assert hit["oriented_source_primer"] == "AACG"
    assert hit["target_window"] == "AATG"
    mismatch = hit["mismatches"][0]
    assert mismatch["oriented_primer_position"] == 2
    assert mismatch["original_primer_position"] == 1
    assert mismatch["target_position"] == 3
    assert mismatch["primer_source_intervals"] == [
        {"subject_ref": "source:primer:0", "start": 501, "end": 502, "unit": "nt", "strand": "-"}]
    assert hit["mismatch_fraction"]["value"] == .25


def test_palindromes_and_repeated_primer_occurrences_are_not_deduplicated():
    palindrome = {"sequence": "ATAT", "alignments": [
        {"position": p, "strand": strand, "mismatches": []} for strand in ("+", "-") for p in (0, 2)]}
    result = components(native_fixture([palindrome, palindrome]), operands("ATATAT", ["ATAT", "ATAT"]))
    assert result["status"] == "complete"
    assert result["summary"]["requested_primer_occurrence_count"] == 2
    assert result["summary"]["retained_native_hit_occurrence_count"] == 8
    assert result["summary"]["plus_hit_count"] == result["summary"]["minus_hit_count"] == 4
    assert [g["primer_occurrence_ordinal"] for g in result["groups"]] == [0, 1]
    assert [(h["strand"], h["target_interval"][0]) for h in result["groups"][0]["hits"]] == [("+", 0), ("+", 2), ("-", 0), ("-", 2)]


def test_native_duplicate_and_out_of_order_occurrences_are_retained_and_qualified():
    native = native_fixture([{"sequence": "AAAA", "alignments": [HITS[1], HITS[1], HITS[0]]}])
    result = components(native)
    assert result["summary"]["retained_native_hit_occurrence_count"] == 3
    assert result["summary"]["mismatch_count_sum"] == 2
    assert {"primer_repeated_native_hit_occurrence", "primer_native_source_order_conflict"} <= codes(result)
    assert [h["target_interval"][0] for h in result["groups"][0]["hits"]] == [1, 1, 0]


def test_noncanonical_source_rc_remains_literal_and_is_never_repaired_to_iupac_science():
    native = native_fixture([{"sequence": "AR", "alignments": [
        {"position": 0, "strand": "+", "mismatches": []},
        {"position": 2, "strand": "+", "mismatches": [[1, "R", "C"]]},
        {"position": 1, "strand": "-", "mismatches": [[1, "T", "A"]]}]}])
    result = components(native, operands("ARAC", "AR"))
    hits = result["groups"][0]["hits"]
    assert hits[2]["oriented_source_primer"] == "RT"
    assert hits[2]["target_window"] == "RA"
    assert [h["native_mismatch_entry_count"] for h in hits] == [0, 1, 1]
    assert all(h["mismatch_count"] is None and h["source_acceptance"] == "unsupported" for h in hits)
    assert all(h["mismatch_list_matches_full_operands"] is True for h in hits)
    assert hits[2]["primer_mapping"]["intervals"] is None
    assert "primer_source_noncanonical_rc_is_not_iupac_science" in codes(result)


def test_empty_primer_pseudo_hits_keep_native_entries_without_zero_mismatch_science():
    hits = [{"position": p, "strand": strand, "mismatches": []} for strand in ("+", "-") for p in (0, 1, 2)]
    result = components(native_fixture([{"sequence": "", "alignments": hits}]), operands("AC", ""))
    group = result["groups"][0]
    assert group["reported_hit_count"] == 6 and group["candidate_oriented_windows"] is None
    assert result["summary"]["retained_native_hit_occurrence_count"] == 6
    assert result["summary"]["mismatch_count_denominator_hits"] == 0
    assert all(h["mismatch_fraction"] == {"numerator": None, "denominator": 0, "value": None} for h in group["hits"])
    assert all(h["target_interval"] is None and h["native_mismatch_entry_count"] == 0 for h in group["hits"])


def test_longer_primer_and_explicit_empty_occurrence_list_have_completed_empty_native_results():
    longer = components(native_fixture([{"sequence": "AAAA", "alignments": []}]), operands("AA", "AAAA"))
    assert longer["status"] == "complete"
    assert longer["groups"][0]["candidate_oriented_windows"] == 0
    assert longer["summary"]["retained_native_hit_occurrence_count"] == 0
    empty = components(native_fixture([]), operands("AA", []))
    assert empty["summary"]["requested_primer_occurrence_count"] == 0
    assert empty["summary"]["retained_native_hit_occurrence_count"] == 0


def test_missing_groups_and_native_failure_preserve_unknown_and_known_partial_populations():
    record = native_fixture([GROUP], outcome="truncated")
    result = components(record, operands(primers=["AAAA", "AAAA"]))
    assert result["native_outcome"] == "truncated"
    assert result["summary"]["retained_native_hit_occurrence_count"] == 4
    assert result["summary"]["known_native_hit_list_count"] == 1
    assert result["groups"][1]["reported_hit_count"] is None
    assert "primer_native_primer_population_conflict" in codes(result)
    record = native_fixture([], outcome="failed");record["result"] = None
    failed = components(record)
    assert failed["native_outcome"] == "failed"
    assert failed["summary"]["retained_native_hit_occurrence_count"] is None
    assert failed["summary"]["plus_hit_count"] is None
    assert failed["summary"]["mismatch_count_sum"] is None


def test_wrong_native_primer_sequence_is_not_rematched_by_name_or_ordinal_repaired():
    record = native_fixture([{"sequence": "CCCC", "alignments": HITS}])
    result = components(record)
    assert result["groups"][0]["native_group"]["sequence"] == "CCCC"
    assert result["summary"]["source_compatible_hit_count"] == 0
    assert result["groups"][0]["hits"][1]["mismatch_count"] == 1
    assert result["groups"][0]["hits"][1]["target_mapping"]["intervals"] is None


@pytest.mark.parametrize("bad", [
    {"position": True, "strand": "+", "mismatches": []},
    {"position": 99, "strand": "+", "mismatches": []},
    {"position": 1, "strand": "?", "mismatches": []},
    {"position": 1, "strand": "+", "mismatches": [[0, "A", "A"]]},
    {"position": 1, "strand": "+", "mismatches": [[True, "A", "C"]]},
    {"position": 1, "strand": "+", "mismatches": [[3, "A", "C"], [3, "A", "C"]]},
])
def test_malformed_native_hit_keeps_other_occurrences_and_actual_bad_entries(bad):
    result = components(native_fixture([{"sequence": "AAAA", "alignments": [bad, HITS[3]]}]))
    first, other = result["groups"][0]["hits"]
    assert first["native_hit"] == bad
    assert first["source_acceptance"] != "compatible"
    assert other["source_acceptance"] == "compatible"
    assert other["target_interval"] == [8, 12]


def test_real_two_mismatch_comparison_is_retained_but_not_accepted_as_a_source_hit():
    bad = {"position": 2, "strand": "+", "mismatches": [[2, "A", "C"], [3, "A", "C"]]}
    result = components(native_fixture([{"sequence": "AAAA", "alignments": [bad]}]))
    row = result["groups"][0]["hits"][0]
    assert row["mismatch_count"] == 2
    assert row["mismatch_fraction"]["value"] == .5
    assert row["source_acceptance"] == "incompatible"
    assert "primer_source_one_mismatch_acceptance_conflict" in codes(result)


def test_nonfinite_native_component_is_explicitly_rejected_without_erasing_other_hits():
    record = native_fixture([{"sequence": "AAAA", "alignments": [
        {"position": float("inf"), "strand": "+", "mismatches": []}, HITS[3]]}])
    sheet = build_primer_placement_sheet(record, **operands())
    assert sheet["rejected_values"] == [{"path": "/native_record/result/sequences/0/alignments/0/position",
        "value_type": "float", "nonfinite_token": "inf"}]
    result = calculate_primer_placement_components(json.loads(json.dumps(sheet, allow_nan=False)))
    assert result["groups"][0]["hits"][0]["target_interval"] is None
    assert result["groups"][0]["hits"][1]["source_acceptance"] == "compatible"


def test_saved_hit_corruption_is_unavailable_and_never_repaired_from_native_rows():
    sheet = build_primer_placement_sheet(native_fixture([GROUP]), **operands())
    sheet["groups"][0]["hits"][0]["mismatch_fraction"]["value"] = .9
    result = calculate_primer_placement_components(sheet)
    assert result["groups"][0]["hits"][0]["state"] == "incompatible"
    assert result["groups"][0]["hits"][0]["saved_hit"]["mismatch_fraction"]["value"] == .9
    assert result["summary"]["retained_native_hit_occurrence_count"] == 4
    assert result["summary"]["usable_saved_hit_count"] == 3
    assert result["summary"]["mismatch_count_sum"] == 2
    assert result["summary"]["mismatch_count_denominator_hits"] == 3


def test_missing_original_paths_preserve_literal_measurements_without_invented_mapping():
    args = operands();args["target_mapping"] = None;args["primer_mappings"] = [None]
    result = components(args=args)
    assert result["summary"]["mismatch_count_sum"] == 2
    assert result["groups"][0]["hits"][1]["target_mapping"]["state"] == "unavailable"
    assert result["groups"][0]["hits"][1]["mismatches"][0]["primer_source_intervals"] is None


def test_json_replay_requires_no_imports_native_io_or_network(monkeypatch):
    sheet = build_primer_placement_sheet(native_fixture([GROUP]), **operands())
    expected = calculate_primer_placement_components(sheet)
    saved = json.loads(json.dumps(sheet, sort_keys=True));before = deepcopy(saved)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved primer measurement attempted external work")
    guards = ((builtins, "open"), (io, "open"), (Path, "read_text"),
        (Path, "read_bytes"), (socket, "socket"), (subprocess, "Popen"), (builtins, "__import__"))
    originals = [(owner, name, getattr(owner, name)) for owner, name in guards]
    # setattr imports inspect, so install the import trap last. Restore every
    # guard before assertions or pytest's reporting/teardown can perform I/O.
    with monkeypatch.context() as guarded:
        for owner, name in guards:
            guarded.setattr(owner, name, forbidden)
        actual = calculate_primer_placement_components(saved)
    assert all(getattr(owner, name) is original for owner, name, original in originals)
    assert actual == expected
    assert saved == before


@pytest.mark.skipif(os.environ.get("HMMER_NATIVE_ORACLE_PRIMER") != "1", reason="explicit bounded genuine original-source oracle only")
def test_selected_pinned_original_primer_callable_retains_all_outputs_and_actual_errors():
    source_path = Path(os.environ.get("HMMER_NATIVE_ORACLE_PRIMER_SOURCE", str(Path(__file__).resolve().parents[1]
        / "reference/episode_tools/.venv/lib/python3.12/site-packages/biomni/tool/molecular_biology.py")))
    source = source_path.read_bytes();module = ast.parse(source, filename=str(source_path))
    selected = [n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "align_sequences"]
    assert len(selected) == 1
    target = selected[0]
    pin = hashlib.sha256(ast.get_source_segment(source.decode(), target).encode()).hexdigest()
    assert pin == "22db874a1776118c633103253ae0366f1e2d09df47b6bf41b031f423ff25d82e"
    namespace = {}
    exec(compile(ast.Module(body=[target], type_ignores=[]), str(source_path), "exec"), namespace)
    original = namespace["align_sequences"]
    cases = [("four_hits", "AAAACCCCAAAA", "AAAA"), ("reverse", "AAATGGG", "CGTT"),
        ("palindrome_and_duplicates", "ATATAT", ["ATAT", "ATAT"]),
        ("noncanonical", "ARAC", "AR"), ("empty", "AC", ""),
        ("longer", "AA", "AAAA"), ("error", "AA", [None])]
    capture = {"schema": "primer_original_source_oracle_v1", "selected_source_path": str(source_path),
        "source_sha256": hashlib.sha256(source).hexdigest(), "callable_sha256": pin,
        "python_version": sys.version, "cases": []}
    for name, dna, primers in cases:
        record = {"schema": NATIVE_SCHEMA, "outcome": "completed", "result": None, "failure": None,
            "source_identity": {"path": str(source_path), "callable": "align_sequences", "sha256": pin}}
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                record["result"] = json.loads(json.dumps(original(dna, primers)))
            except Exception as error:
                record.update(outcome="failed", failure={"exception_type": type(error).__name__,
                    "exception_module": type(error).__module__, "message": str(error), "traceback": traceback.format_exc()})
        args = operands(dna, primers)
        sheet = build_primer_placement_sheet(record, **args)
        capture["cases"].append({"case": name, "full_target": dna, "full_primers": primers,
            "native_record": record, "stdout": stdout.getvalue(), "stderr": stderr.getvalue(),
            "sheet": sheet, "components": calculate_primer_placement_components(sheet)})
    output = Path(os.environ["HMMER529_ATTEMPT"]) / "primer-original-source-oracle.json"
    output.write_text(json.dumps(capture, allow_nan=False, indent=2))
    by_name = {row["case"]: row for row in capture["cases"]}
    assert by_name["four_hits"]["native_record"]["result"]["sequences"] == [GROUP]
    assert by_name["four_hits"]["components"]["summary"]["mismatch_count_sum"] == 2
    reverse = by_name["reverse"]["native_record"]["result"]["sequences"][0]["alignments"]
    assert reverse == [{"position": 1, "strand": "-", "mismatches": [[2, "C", "T"]]}]
    assert by_name["palindrome_and_duplicates"]["components"]["summary"]["retained_native_hit_occurrence_count"] == 8
    assert by_name["noncanonical"]["components"]["groups"][0]["hits"][2]["oriented_source_primer"] == "RT"
    assert by_name["empty"]["components"]["groups"][0]["reported_hit_count"] == 6
    assert by_name["longer"]["components"]["summary"]["retained_native_hit_occurrence_count"] == 0
    assert by_name["error"]["native_record"]["failure"]["exception_type"] == "AttributeError"
    assert by_name["error"]["native_record"]["result"] is None
    assert by_name["error"]["components"]["summary"]["retained_native_hit_occurrence_count"] is None


@pytest.mark.skipif(os.environ.get("HMMER_NATIVE_ORACLE_WHOLE_MOLECULAR_BIOLOGY") != "1",
    reason="explicit bounded whole-module deployment verification only")
def test_selected_whole_molecular_biology_module_executes_orf_and_primer_measurements():
    import importlib.metadata as metadata
    import importlib.util
    import inspect

    from gene_annotation_episode.orf_measurements import (
        NATIVE_SCHEMA as ORF_NATIVE_SCHEMA, build_orf_sheet, calculate_orf_components,
    )

    attempt = Path(os.environ["HMMER529_ATTEMPT"])
    output = attempt / "molecular-biology-whole-module.json"
    capture = {"schema": "molecular_biology_whole_module_verification_v1",
        "qualification": "genuine selected whole-file deployment and explicit numerical controls; no public installed-operation or child-return claim",
        "selection": {"source": os.environ.get("HMMER_NATIVE_ORACLE_MOLECULAR_SOURCE"),
            "support_root": os.environ.get("HMMER_NATIVE_ORACLE_MOLECULAR_SUPPORT_ROOT")},
        "runtime": {"sys_executable": sys.executable, "sys_version": sys.version, "sys_prefix": sys.prefix},
        "support_payloads": [], "module_load": {"state": "not_started", "stdout": "", "stderr": "", "error": None},
        "verification_error": None, "libraries": [], "callables": {}, "cases": []}

    def file_pin(path):
        selected = Path(path).resolve(strict=True)
        data = selected.read_bytes()
        return {"path": str(selected), "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}

    def error_record(error):
        return {"exception_type": type(error).__name__, "exception_module": type(error).__module__,
            "message": str(error), "traceback": traceback.format_exc()}

    saved_path = list(sys.path)
    saved_bytecode = sys.dont_write_bytecode
    module_name = "_selected_whole_biomni_molecular_biology"
    previous_module = sys.modules.get(module_name)
    phase = "selection"
    load_out, load_err = io.StringIO(), io.StringIO()
    try:
        capture["runtime"]["executable_file"] = file_pin(sys.executable)
        source_path = Path(os.environ["HMMER_NATIVE_ORACLE_MOLECULAR_SOURCE"]).resolve(strict=True)
        support_root = Path(os.environ["HMMER_NATIVE_ORACLE_MOLECULAR_SUPPORT_ROOT"]).resolve(strict=True)
        capture["source_file"] = file_pin(source_path)
        assert capture["source_file"]["sha256"] == "de47e1dc0013cd6e8d2941d8945835d585f938e486a69bb2ba3333403a3efba4"
        payload_names = ("bs4", "beautifulsoup4-4.15.0.dist-info", "soupsieve", "soupsieve-2.8.4.dist-info")
        for name in payload_names:
            payload = support_root / name
            assert payload.is_dir(), str(payload)
            files = [file_pin(p) for p in sorted(payload.rglob("*")) if p.is_file()
                and "__pycache__" not in p.relative_to(payload).parts and p.suffix != ".pyc"]
            assert files
            capture["support_payloads"].append({"path": str(payload), "files": files})
        assert file_pin(support_root / "bs4/__init__.py")["sha256"] == "90e007f82a9fc5bcf22a8df3b395b7bc5245e54d65cd68fd51ca12a414718d4e"
        assert file_pin(support_root / "soupsieve/__init__.py")["sha256"] == "155e0e97615195dcbbac6f789d01cd1e82536487506d425d6641a15e4237b621"

        # The real whole module performs all its original imports itself. Only
        # the explicitly selected genuine dependency root is added to lookup.
        # No source AST, copied callable, injected dependency or import fallback.
        sys.path.insert(0, str(support_root))
        sys.dont_write_bytecode = True
        modules_before_load = set(sys.modules)
        phase = "module_load"
        capture["module_load"]["state"] = "loading"
        with contextlib.redirect_stdout(load_out), contextlib.redirect_stderr(load_err):
            spec = importlib.util.spec_from_file_location(module_name, source_path)
            assert spec is not None and spec.loader is not None
            whole = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = whole
            spec.loader.exec_module(whole)
        capture["module_load"].update(state="loaded", module_name=whole.__name__,
            executed_file=file_pin(whole.__file__), loader_type=type(spec.loader).__name__)

        phase = "loaded_identities"
        for module_key, distribution_name in (("pandas", "pandas"), ("requests", "requests"),
            ("Bio", "biopython"), ("bs4", "beautifulsoup4"), ("soupsieve", "soupsieve"),
            ("typing_extensions", "typing_extensions")):
            library = sys.modules.get(module_key)
            observed = {"module_name": module_key, "distribution_name": distribution_name,
                "distribution_version": metadata.version(distribution_name),
                "present_after_whole_module_load": library is not None,
                "already_present_before_load": module_key in modules_before_load,
                "module_version": getattr(library, "__version__", None),
                "module_file": file_pin(library.__file__) if library is not None else None}
            if module_key in ("pandas", "requests", "Bio", "bs4"):
                assert library is not None
            if module_key in ("bs4", "soupsieve") and library is not None:
                assert Path(observed["module_file"]["path"]).is_relative_to(support_root / module_key)
            capture["libraries"].append(observed)
        assert whole.pd is sys.modules["pandas"]
        assert whole.requests is sys.modules["requests"]
        assert whole.BeautifulSoup is sys.modules["bs4"].BeautifulSoup
        assert whole.Seq is sys.modules["Bio.Seq"].Seq
        for name, expected_pin in (
            ("annotate_open_reading_frames", "bc32fff2924e09ec940f6d9b8d74732a8ef86d0894761430a3ad57ea7148269b"),
            ("align_sequences", "22db874a1776118c633103253ae0366f1e2d09df47b6bf41b031f423ff25d82e")):
            function = getattr(whole, name)
            observed = {"name": function.__name__, "module": function.__module__,
                "code_filename": function.__code__.co_filename,
                "sha256": hashlib.sha256(inspect.getsource(function).rstrip("\n").encode()).hexdigest()}
            capture["callables"][name] = observed
            assert observed["module"] == whole.__name__
            assert Path(observed["code_filename"]).resolve() == source_path
            assert observed["sha256"] == expected_pin

        from Bio.Data import CodonTable
        native_bio_version = metadata.version("biopython")
        table = CodonTable.unambiguous_dna_by_id[1]
        frozen_table = {"code": 1, "names": list(table.names), "start_codons": list(table.start_codons),
            "stop_codons": list(table.stop_codons), "forward_table": dict(table.forward_table),
            "biopython_version": native_bio_version}
        capture["genetic_code_reference"] = {"source_file": file_pin(CodonTable.__file__), "snapshot": frozen_table}
        cases = [("orf_nested", "orf", "ATGAAAATGTAA", None),
            ("orf_ambiguity_stop", "orf", "ATGTARTAA", None),
            ("orf_actual_error", "orf", "ATG?AATAA", None),
            ("primer_four_hits", "primer", "AAAACCCCAAAA", "AAAA"),
            ("primer_reverse", "primer", "AAATGGG", "CGTT"),
            ("primer_actual_error", "primer", "AA", [None])]
        phase = "scientific_calls"
        for case_name, family, dna, primers in cases:
            callable_name = "annotate_open_reading_frames" if family == "orf" else "align_sequences"
            function = getattr(whole, callable_name)
            arguments = ({"sequence": dna, "min_length": 6, "search_reverse": False, "filter_subsets": False}
                if family == "orf" else {"long_seq": dna, "short_seqs": primers})
            record = {"schema": ORF_NATIVE_SCHEMA if family == "orf" else NATIVE_SCHEMA,
                "outcome": "completed", "result": None, "failure": None,
                "source_identity": {"path": str(source_path), "callable": function.__name__,
                    "sha256": capture["callables"][callable_name]["sha256"]}}
            if family == "orf":
                record.update(biopython_version=native_bio_version,
                    translation={"table": "Standard", "to_stop": True, "cds": False})
            case_out, case_err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(case_out), contextlib.redirect_stderr(case_err):
                try:
                    record["result"] = json.loads(json.dumps(function(**arguments), allow_nan=False))
                except Exception as error:
                    record.update(outcome="failed", failure=error_record(error))
            retained = {"case": case_name, "family": family, "input_origin": "explicit_numerical_control",
                "arguments": deepcopy(arguments), "native_record": record,
                "stdout": case_out.getvalue(), "stderr": case_err.getvalue(),
                "numerical_status": "not_started", "numerical_error": None, "sheet": None, "components": None}
            capture["cases"].append(retained)
            try:
                if family == "orf":
                    sheet = build_orf_sheet(record, input_sequence=dna, subject_ref="supplied:whole-orf-control",
                        parent_mapping=mapping(len(dna), "source:whole-orf-control"),
                        request={k: arguments[k] for k in ("min_length", "search_reverse", "filter_subsets")},
                        genetic_code=frozen_table)
                    calculated = calculate_orf_components(sheet)
                else:
                    sheet = build_primer_placement_sheet(record, **operands(dna, primers))
                    calculated = calculate_primer_placement_components(sheet)
                retained.update(numerical_status="calculated", sheet=sheet, components=calculated)
            except Exception as error:
                retained.update(numerical_status="failed", numerical_error=error_record(error))
    except Exception as error:
        if phase == "module_load":
            capture["module_load"].update(state="failed", error=error_record(error))
        else:
            capture["verification_error"] = {"phase": phase, **error_record(error)}
    finally:
        capture["module_load"].update(stdout=load_out.getvalue(), stderr=load_err.getvalue())
        sys.path[:] = saved_path
        sys.dont_write_bytecode = saved_bytecode
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
        output.write_text(json.dumps(capture, allow_nan=False, indent=2))

    assert capture["module_load"]["state"] == "loaded", capture["module_load"]
    assert capture["verification_error"] is None, capture["verification_error"]
    assert len(capture["cases"]) == 6
    assert all(row["numerical_status"] == "calculated" for row in capture["cases"]), capture["cases"]
    by_name = {row["case"]: row for row in capture["cases"]}
    assert by_name["orf_nested"]["native_record"]["result"]["orfs"] == [
        ["ATGAAAATGTAA", "MKM", 0, 12, "+", 1], ["ATGTAA", "M", 6, 12, "+", 1]]
    assert by_name["orf_nested"]["components"]["summary"]["retained_length_sum_nt"] == 18
    assert by_name["orf_nested"]["components"]["summary"]["retained_length_denominator_rows"] == 2
    assert by_name["orf_nested"]["components"]["summary"]["mean_retained_orf_length_nt"] == 9
    ambiguous = by_name["orf_ambiguity_stop"]
    assert ambiguous["native_record"]["result"]["orfs"] == [["ATGTARTAA", "M", 0, 9, "+", 1]]
    assert ambiguous["components"]["rows"][0]["translation"]["termination_codon"] == "TAR"
    assert ambiguous["components"]["rows"][0]["translation"]["untranslated_suffix_nt"] == 3
    assert by_name["primer_four_hits"]["native_record"]["result"]["sequences"] == [GROUP]
    assert by_name["primer_four_hits"]["components"]["summary"]["retained_native_hit_occurrence_count"] == 4
    assert [h["mismatch_fraction"]["value"] for h in by_name["primer_four_hits"]["components"]["groups"][0]["hits"]] == [0, .25, .25, 0]
    reverse = by_name["primer_reverse"]
    assert reverse["native_record"]["result"]["sequences"][0]["alignments"] == [
        {"position": 1, "strand": "-", "mismatches": [[2, "C", "T"]]}]
    assert reverse["components"]["groups"][0]["hits"][0]["mismatches"][0]["original_primer_position"] == 1
    for name, exception_type, count_field in (("orf_actual_error", "TranslationError", "reported_row_count"),
        ("primer_actual_error", "AttributeError", "retained_native_hit_occurrence_count")):
        failed = by_name[name]
        assert failed["native_record"]["outcome"] == "failed"
        assert failed["native_record"]["result"] is None
        assert failed["native_record"]["failure"]["exception_type"] == exception_type
        assert failed["components"]["summary"][count_field] is None
