"""Independent integer/coordinate examples for the pure directional primitives."""
from copy import deepcopy
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.bvbrc_proteome_directional import parse_genome_comparison_directional_report
from gene_annotation_episode.bvbrc_proteome_directional_geometry import (
    DirectionalNumericalContractError, calculate_protein_block,
    inspect_protein_correspondence, union_position_intervals,
)


FIXTURES = Path(__file__).parent / "fixtures" / "bvbrc_proteome_directional"
ROOT = next(p for p in Path(__file__).resolve().parents if
            (p / "verification/tool_graders_bvbrc_proteome_directional_calculation_contract_2026-10-25_177").is_dir())
EXAMPLES = ROOT / "verification/tool_graders_bvbrc_proteome_directional_calculation_contract_2026-10-25_177/NUMERICAL_NATIVE_EXAMPLES_001.json"
DEFAULT_KEY = dict(report_ordinal=0, query_ordinal=0, subject_ordinal=0, hsp_ordinal=0, block_ordinal=0)


def cell(value=None, *, state=None, native_text=None):
    state = state or ("missing" if value is None else "present")
    if state == "missing":
        return dict(state=state, value=None, native_text=None, locations=[])
    text = str(value) if native_text is None else native_text
    return dict(state=state, value=value, native_text=text,
                locations=[dict(source_ref="synthetic", sha256="0" * 64,
                                span=dict(byte_start=0, byte_end=len(text)))])


def block(q="ACDE", s="ACDE", *, qs=1, ss=1, qe=None, se=None, ordinal=0):
    return dict(ordinal=ordinal, span=dict(byte_start=0, byte_end=1000), issues=[],
                query_start=cell(qs), query_end=cell(qs + len(q.replace("-", "")) - 1 if qe is None else qe),
                subject_start=cell(ss), subject_end=cell(ss + len(s.replace("-", "")) - 1 if se is None else se),
                query_symbols=cell(q), subject_symbols=cell(s), midline=cell())


def calc(native=None, *, key=None, ql=10, sl=10, alphabet="standard20", places=18):
    return calculate_protein_block(native or block(), key=key or DEFAULT_KEY,
        query_length=cell(ql), subject_length=cell(sl), amino_acid_alphabet=alphabet,
        ratio_decimal_places=places, rounding="half_even")


def hsp(blocks, *, key=None, contiguous="yes"):
    key = key or {k: v for k, v in blocks[0]["key"].items() if k != "block_ordinal"}
    included, excluded = [], []
    for b in blocks:
        good = all(b["coverage"][axis + "_trace_paired_union"]["count"]["state"] == "value" for axis in ("query", "subject"))
        (included if good else excluded).append(b["key"])
    absent = [key] if not blocks else []
    return dict(key=key, blocks=blocks, contiguous_blocks=contiguous,
                pair_geometry_support=dict(included_blocks=included, excluded_blocks=excluded,
                    hsps_without_traceback=absent, complete_for_displayed_blocks=not excluded and not absent))


def graph(rows, *, key=None):
    return inspect_protein_correspondence(rows, key=key or dict(report_ordinal=0, query_ordinal=0, subject_ordinal=0))


def value(row, name):
    return row["counts"][name]["value"]


def conflict(g, code):
    return next(c for c in g["conflicts"] if c["code"] == code)


def test_literal_symbols_classes_and_both_gap_directions():
    # Explicit columns: a/A resolved identity; C/D substitution; X/X, B/Z,
    # U/U, O/O unresolved under20; */* stop; -/A and A/- separate gaps.
    got = calc(block("aCXBUO*-A", "ADXZUO*A-"))
    assert {k: c["value"] for k, c in got["counts"].items()} == {
        "alignment_columns": 9, "paired_columns": 7,
        "displayed_symbol_identical_pairs": 5, "displayed_symbol_nonidentical_pairs": 2,
        "resolved_amino_acid_pairs": 2, "resolved_amino_acid_identical_pairs": 1,
        "resolved_amino_acid_substituted_pairs": 1, "unresolved_symbol_pairs": 4,
        "stop_containing_pairs": 1, "query_gap_columns": 1, "subject_gap_columns": 1,
        "query_gap_runs": 1, "subject_gap_runs": 1,
        "query_non_gap_symbols": 8, "subject_non_gap_symbols": 8,
    }
    assert [c["kind"] for c in got["columns"]] == ["resolved_identical", "resolved_substituted",
        "unresolved_pair", "unresolved_pair", "unresolved_pair", "unresolved_pair", "stop_containing_pair",
        "query_gap", "subject_gap"]
    assert got["columns"][0]["query_symbol"] == "a"
    assert got["columns"][6]["displayed_symbol_equal"] is True
    assert got["columns"][7]["query_position"] == dict(state="gap", value=None)
    assert got["columns"][8]["query_position"] == dict(state="position", value=7)
    assert got["coverage"]["query_trace_paired_union"]["intervals"] == [[0, 7]]
    assert got["coverage"]["subject_trace_paired_union"]["intervals"] == [[0, 7]]
    assert got["fractions"]["trace_resolved_amino_acid_identity"]["value"] == dict(numerator=1, denominator=2, decimal="0.500000000000000000")
    changed = calc(block("aCXBUO*-A", "ADXZUO*A-"), alphabet="standard20_plus_uo", places=3)
    assert value(changed, "resolved_amino_acid_pairs") == 4
    assert value(changed, "resolved_amino_acid_identical_pairs") == 3
    assert value(changed, "unresolved_symbol_pairs") == 2
    assert changed["fractions"]["trace_resolved_amino_acid_identity"]["value"]["decimal"] == "0.750"
    assert changed["coverage"]["query_trace_paired_union"]["intervals"] == got["coverage"]["query_trace_paired_union"]["intervals"]


@pytest.mark.parametrize("q,s,n,d,places,expected", [
    ("AAAA", "ACCC", 1, 4, 1, "0.2"), ("AAAA", "AAAC", 3, 4, 1, "0.8"),
    ("AAA", "ACC", 1, 3, 30, "0.333333333333333333333333333333"),
    ("AA", "AC", 1, 2, 0, "0"), ("AAA", "AAC", 2, 3, 0, "1"),
])
def test_exact_unreduced_fractions_and_half_even(q, s, n, d, places, expected):
    got = calc(block(q, s), places=places)["fractions"]["trace_symbol_identity_over_pairs"]
    assert got["value"] == dict(numerator=n, denominator=d, decimal=expected)
    with localcontext() as ctx:
        ctx.prec = 100
        independent = (Decimal(n) / Decimal(d)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
    assert Decimal(got["value"]["decimal"]) == independent


def test_empty_paired_population_differs_from_unresolved_population():
    gaps = calc(block("A-", "-A"))
    assert value(gaps, "paired_columns") == 0
    assert gaps["fractions"]["trace_symbol_identity_over_pairs"]["state"] == "undefined"
    assert gaps["fractions"]["trace_symbol_identity_over_pairs"]["reasons"] == ["zero_paired_population"]
    assert gaps["coverage"]["query_trace_paired_union"]["coverage"]["value"]["numerator"] == 0
    unresolved = calc(block("XX**", "XX**"))
    assert value(unresolved, "displayed_symbol_identical_pairs") == 4
    assert value(unresolved, "resolved_amino_acid_identical_pairs") == 0
    assert unresolved["fractions"]["trace_resolved_amino_acid_identity"]["reasons"] == ["zero_resolved_population"]
    assert graph([hsp([gaps])])["distinct_pair_count"]["value"] == 0


@pytest.mark.parametrize("side", ["query", "subject"])
def test_axis_failure_does_not_erase_other_axis_or_strings(side):
    native = block()
    native[side + "_end"] = cell(9)
    got = calc(native)
    other = "subject" if side == "query" else "query"
    assert value(got, "alignment_columns") == 4
    assert got["coverage"][side + "_reported_interval_union"]["count"]["value"] == 9
    assert got["coverage"][side + "_trace_paired_union"]["count"]["state"] == "conflict"
    assert got["coverage"][other + "_trace_paired_union"]["coverage"]["value"]["numerator"] == 4
    assert got["columns"][0][side + "_position"] == dict(state="unavailable_coordinate", value=None)
    assert graph([hsp([got])])["mapping_state"] == "incomplete_geometry"
    assert all(i["argument_pointer"] is None for i in got["diagnostics"])


@pytest.mark.parametrize("change,reason,state", [
    ({"query_start": cell()}, "missing_coordinate", "missing"),
    ({"query_start": cell(0)}, "invalid_coordinate", "invalid"),
    ({"query_start": cell(5)}, "reverse_protein_coordinates", "invalid"),
    ({"query_start": cell(9), "query_end": cell(12)}, "coordinate_outside_reported_length", "invalid"),
    ({"query_start": cell(None, state="invalid", native_text="bogus")}, "invalid_coordinate", "invalid"),
])
def test_coordinate_failure_categories(change, reason, state):
    native = block()
    native.update(change)
    got = calc(native)
    union = got["coverage"]["query_trace_occupied_union"]
    assert union["count"]["state"] == state
    assert reason in union["count"]["reasons"]
    assert got["coverage"]["subject_trace_occupied_union"]["count"]["value"] == 4


@pytest.mark.parametrize("length,state,reason", [(None, "missing", "missing_reported_length"), (0, "invalid", "invalid_reported_length")])
def test_length_only_prevents_normalization(length, state, reason):
    got = calc(ql=length)
    union = got["coverage"]["query_trace_paired_union"]
    assert union["intervals"] == [[0, 4]] and union["count"]["value"] == 4
    assert union["coverage"]["state"] == state and reason in union["coverage"]["reasons"]
    assert graph([hsp([got])])["mapping_state"] == "compatible_displayed_partial_map"


@pytest.mark.parametrize("q,s,reason", [("AC", "ACD", "traceback_width_conflict"),
    ("A?C", "ACC", "invalid_traceback_symbols"), ("A-C", "A-C", "double_gap_column"),
    ("éC", "AC", "invalid_traceback_symbols"), ("", "", "invalid_traceback_symbols")])
def test_invalid_string_population_keeps_native_interval(q, s, reason):
    got = calc(block(q, s, qe=4, se=4))
    assert got["columns"] == []
    assert got["counts"]["alignment_columns"]["state"] == "invalid"
    assert reason in got["counts"]["alignment_columns"]["reasons"]
    assert got["coverage"]["query_reported_interval_union"]["count"]["value"] == 4


def test_missing_string_and_mixed_invalid_missing_preserve_states():
    native = block()
    native["subject_symbols"] = cell()
    got = calc(native)
    assert got["counts"]["alignment_columns"]["state"] == "missing"
    native["query_symbols"] = cell("?")
    got = calc(native)
    assert got["counts"]["alignment_columns"]["state"] == "invalid"
    assert set(got["counts"]["alignment_columns"]["reasons"]) == {"missing_traceback_symbols", "invalid_traceback_symbols"}


def test_all_nonstandard_symbols_remain_distinct_from_stops_and_gaps():
    got = calc(block("BZJXUO*", "BZJXUO*"))
    assert value(got, "unresolved_symbol_pairs") == 6
    assert value(got, "stop_containing_pairs") == 1
    assert value(got, "displayed_symbol_identical_pairs") == 7
    assert value(got, "resolved_amino_acid_pairs") == 0
    changed = calc(block("BZJXUO*", "BZJXUO*"), alphabet="standard20_plus_uo")
    assert value(changed, "unresolved_symbol_pairs") == 4
    assert value(changed, "resolved_amino_acid_identical_pairs") == 2


def test_unconvertible_native_integer_keeps_invalid_state():
    native = block()
    native["query_start"] = cell(None, state="invalid", native_text="9" * 5000)
    got = calc(native)
    assert got["coverage"]["query_trace_paired_union"]["count"]["state"] == "invalid"
    assert value(got, "alignment_columns") == 4


def test_block_operands_are_exact_original_occurrence_fields_and_no_mutation():
    key = dict(report_ordinal=3, query_ordinal=2, subject_ordinal=4, hsp_ordinal=6, block_ordinal=1)
    native = block(ordinal=1)
    before = deepcopy(native)
    got = calc(native, key=key)
    base = "/queries/2/subjects/4/hsps/6/traceback_blocks/1/"
    sym = [dict(report_ordinal=3, pointer=base + name) for name in ("query_symbols", "subject_symbols")]
    assert got["counts"]["query_non_gap_symbols"]["inputs"] == sym
    interval = got["coverage"]["query_reported_interval_union"]
    assert interval["count"]["inputs"] == [dict(report_ordinal=3, pointer=base + name) for name in ("query_start", "query_end")] + [dict(report_ordinal=3, pointer="/queries/2/length")]
    assert got["coverage"]["query_trace_paired_union"]["count"]["inputs"] == sym + interval["count"]["inputs"]
    assert native == before
    got["coverage"]["query_trace_paired_union"]["reported_length"]["value"] = 99
    assert native == before


def test_union_set_math_boundary_and_no_input_mutation():
    intervals = [[4, 8], [0, 2], [1, 5], [8, 9], [15, 18], [16, 17], [4, 8]]
    before = deepcopy(intervals)
    assert union_position_intervals(intervals) == [[0, 9], [15, 18]]
    assert intervals == before
    assert union_position_intervals([]) == []


@pytest.mark.parametrize("bad", [None, [[1, 1]], [[-1, 2]], [[2, 1]], [[True, 2]], [(0, 2)], [[0, 2, 3]]])
def test_bad_intervals_are_argument_failures(bad):
    with pytest.raises(DirectionalNumericalContractError) as error:
        union_position_intervals(bad)
    assert error.value.code == "invalid_input_contract"
    assert error.value.pointer.startswith("/intervals")


@pytest.mark.parametrize("field,bad", [("ratio_decimal_places", True), ("ratio_decimal_places", -1),
    ("ratio_decimal_places", 31), ("rounding", "half_up"), ("amino_acid_alphabet", "auto")])
def test_explicit_parameter_failures(field, bad):
    args = dict(key=DEFAULT_KEY, query_length=cell(10), subject_length=cell(10),
                amino_acid_alphabet="standard20", ratio_decimal_places=18, rounding="half_even")
    args[field] = bad
    with pytest.raises(DirectionalNumericalContractError) as error:
        calculate_protein_block(block(), **args)
    assert (error.value.code, error.value.pointer) == ("invalid_parameters", "/" + field)


def test_repeated_occurrences_and_compatible_overlaps():
    rows = []
    for hi, native in enumerate([block(), block(), block("DEFG", "DEFG", qs=3, ss=3)]):
        rows.append(hsp([calc(native, key={**DEFAULT_KEY, "hsp_ordinal": hi})]))
    got = graph(rows)
    assert got["distinct_pair_count"]["value"] == 6
    assert got["repeated_pair_occurrence_count"]["value"] == 6
    assert [len(e["supports"]) for e in got["edges"]] == [2, 2, 3, 3, 1, 1]
    assert got["mapping_state"] == "compatible_displayed_partial_map"
    assert got["conflicts"] == []


def test_alternative_maps_and_literal_symbol_conflict_on_different_edges():
    rows = [hsp([calc()]), hsp([calc(block(ss=2), key={**DEFAULT_KEY, "hsp_ordinal": 1})])]
    got = graph(rows)
    assert got["distinct_pair_count"]["value"] == 8
    assert conflict(got, "alternative_query_mapping")["query_intervals"] == [[0, 4]]
    assert conflict(got, "alternative_subject_mapping")["subject_intervals"] == [[1, 4]]
    assert conflict(got, "subject_symbol_conflict")["subject_intervals"] == [[1, 4]]
    assert got["mapping_state"] == "observed_conflict"


def test_same_identity_booleans_do_not_hide_literal_symbol_conflicts():
    rows = [hsp([calc()]), hsp([calc(block("FGHI", "FGHI"), key={**DEFAULT_KEY, "hsp_ordinal": 1})])]
    got = graph(rows)
    assert all(e["symbol_state"] == "conflicting" for e in got["edges"])
    assert {c["code"] for c in got["conflicts"]} == {"query_symbol_conflict", "subject_symbol_conflict"}
    assert got["distinct_pair_count"]["value"] == 4
    assert got["repeated_pair_occurrence_count"]["value"] == 4


@pytest.mark.parametrize("side", ["query", "subject"])
def test_gap_versus_pair_conflict_is_independent_of_alternative_map(side):
    native = block("A-C", "ADC") if side == "subject" else block("ADC", "A-C")
    rows = [hsp([calc(native)]), hsp([calc(block("D", "D", qs=2, ss=2), key={**DEFAULT_KEY, "hsp_ordinal": 1})])]
    got = graph(rows)
    assert conflict(got, side + "_gap_versus_pair_conflict")[side + "_intervals"] == [[1, 2]]
    witnesses = conflict(got, side + "_gap_versus_pair_conflict")["columns"]
    assert {(c["hsp_ordinal"], c["column_ordinal"]) for c in witnesses} == {(0, 1), (1, 0)}


def test_known_symbol_and_gap_conflicts_survive_missing_opposite_axis():
    a = calc(block("AC", "A-", se=1))
    b_native = block("AD", "AD")
    b_native["subject_start"] = cell()
    b = calc(b_native, key={**DEFAULT_KEY, "hsp_ordinal": 1})
    got = graph([hsp([a]), hsp([b])])
    assert got["mapping_state"] == "observed_conflict"
    assert conflict(got, "query_symbol_conflict")["query_intervals"] == [[1, 2]]
    assert conflict(got, "query_gap_versus_pair_conflict")["query_intervals"] == [[1, 2]]
    assert got["pair_geometry_support"]["excluded_blocks"] == [b["key"]]
    assert got["distinct_pair_count"]["value"] == 1


def test_crossing_segments_without_span_overlap():
    first = calc(block("AC", "AC", qs=1, ss=5))
    second = calc(block("DE", "DE", qs=5, ss=1), key={**DEFAULT_KEY, "hsp_ordinal": 1})
    got = graph([hsp([first]), hsp([second])])
    assert {c["code"] for c in got["conflicts"]} == {"noncollinear_pair_order"}
    witness = got["conflicts"][0]
    assert witness["query_intervals"] == witness["subject_intervals"] == [[0, 2], [4, 6]]
    assert len(witness["columns"]) == 4


def test_noncontiguous_native_blocks_keep_separate_intervals_and_conflict():
    first = calc(block("AC", "AC"))
    second = calc(block("DE", "DE", qs=4, ss=3, ordinal=1), key={**DEFAULT_KEY, "block_ordinal": 1})
    got = graph([hsp([first, second], contiguous="no")])
    assert got["distinct_pair_count"]["value"] == 4
    assert got["mapping_state"] == "observed_conflict"
    assert conflict(got, "block_continuity_conflict")["query_intervals"] == [[1, 2], [3, 4]]


def test_partial_graph_and_empty_occurrences_retain_identity_without_zero():
    subject_key = dict(report_ordinal=7, query_ordinal=8, subject_ordinal=9)
    empty = graph([], key=subject_key)
    assert empty["key"] == subject_key and empty["edges"] == []
    assert empty["mapping_state"] == "incomplete_geometry"
    assert empty["distinct_pair_count"]["state"] == "missing"
    assert empty["distinct_pair_count"]["reasons"] == ["missing_traceback"]
    assert empty["pair_geometry_support"]["complete_for_displayed_blocks"] is True
    no_trace = hsp([], key={**subject_key, "hsp_ordinal": 0}, contiguous="unknown")
    got = graph([no_trace], key=subject_key)
    assert got["pair_geometry_support"]["hsps_without_traceback"] == [no_trace["key"]]
    assert got["pair_geometry_support"]["complete_for_displayed_blocks"] is False
    with pytest.raises(DirectionalNumericalContractError):
        graph([hsp([calc()])], key=subject_key)


def test_partial_graph_keeps_valid_subset_and_excluded_native_operands():
    first = calc()
    native = block(qs=5, ss=5, ordinal=1)
    native["subject_symbols"] = cell()
    second = calc(native, key={**DEFAULT_KEY, "block_ordinal": 1})
    got = graph([hsp([first, second], contiguous="unknown")])
    assert got["distinct_pair_count"]["value"] == 4
    assert got["repeated_pair_occurrence_count"]["value"] == 0
    assert got["mapping_state"] == "incomplete_geometry"
    assert got["pair_geometry_support"] == dict(included_blocks=[first["key"]], excluded_blocks=[second["key"]],
                                                hsps_without_traceback=[], complete_for_displayed_blocks=False)
    source_pointers = {r["pointer"] for r in got["distinct_pair_count"]["inputs"]}
    assert "/queries/0/subjects/0/hsps/0/traceback_blocks/1/subject_symbols" in source_pointers
    assert "/queries/0/subjects/0/hsps/0/traceback_blocks/1/query_end" in source_pointers


def test_native_endpoint_discontinuity_without_columns_is_not_a_graph_witness():
    native = block(qs=6, ss=6, ordinal=1)
    native["subject_symbols"] = cell()
    first = calc()
    second = calc(native, key={**DEFAULT_KEY, "block_ordinal": 1})
    got = graph([hsp([first, second], contiguous="unknown")])
    assert got["mapping_state"] == "incomplete_geometry"
    assert got["conflicts"] == []
    assert second["coverage"]["query_reported_interval_union"]["intervals"] == [[5, 9]]


def test_recalculation_and_graph_need_no_io_process_or_parser(monkeypatch):
    native = block("AC-X", "ACDX")

    def forbidden(*args, **kwargs):
        raise AssertionError("A pure geometry function attempted IO or parsing")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("gene_annotation_episode.bvbrc_proteome_directional.parse_genome_comparison_directional_report", forbidden)
    got = calc(native, places=4)
    changed = calc(native, places=9)
    assert got["fractions"]["trace_symbol_identity_over_columns"]["value"]["decimal"] == "0.7500"
    assert changed["fractions"]["trace_symbol_identity_over_columns"]["value"]["decimal"] == "0.750000000"
    assert graph([hsp([got])]) == graph([hsp([changed])])


def native_report(name):
    content = (FIXTURES / name).read_bytes()
    source = dict(content=dict(source_ref="retained_public_fixture", artifact_field="artifact_ref",
        artifact_ref="fixture", sha256=hashlib.sha256(content).hexdigest(), byte_count=len(content)),
        body_complete=True, object_complete="yes")
    return parse_genome_comparison_directional_report(content, source=source,
        declared_format="ncbi_blastall_blastp_pairwise_text_v1", report_key=name)


@pytest.mark.parametrize("release", ["2011", "2202", "2221"])
def test_all_retained_native_examples_against_independent_contract_arithmetic(release):
    expected = json.loads(EXAMPLES.read_text())[release]
    native = native_report(expected["fixture"])
    assert len(native["queries"]) == expected["query_count"]
    hsp_count = 0
    for qi, query in enumerate(native["queries"]):
        for si, subject in enumerate(query["subjects"]):
            rows = []
            for hi, observed in enumerate(subject["hsps"]):
                hsp_count += 1
                key = dict(report_ordinal=0, query_ordinal=qi, subject_ordinal=si, hsp_ordinal=hi)
                blocks = [calculate_protein_block(b, key={**key, "block_ordinal": bi},
                    query_length=query["length"], subject_length=subject["length"],
                    amino_acid_alphabet="standard20", ratio_decimal_places=18, rounding="half_even")
                    for bi, b in enumerate(observed["traceback_blocks"])]
                exp = expected["queries"][qi]["subjects"][si]["hsps"][hi]["counts"]
                for name in blocks[0]["counts"]:
                    total = sum(value(b, name) for b in blocks)
                    if name.endswith("_gap_runs"):
                        side = name.split("_")[0]
                        total -= sum(a[side + "_symbols"]["value"].endswith("-") and b[side + "_symbols"]["value"].startswith("-")
                                     for a, b in zip(observed["traceback_blocks"], observed["traceback_blocks"][1:]))
                    expected_name = {"query_non_gap_symbols": "occupied_query_positions", "subject_non_gap_symbols": "occupied_subject_positions"}.get(name, name)
                    assert total == exp[expected_name], (release, qi, si, hi, name)
                rows.append(hsp(blocks, key=key))
            subject_key = dict(report_ordinal=0, query_ordinal=qi, subject_ordinal=si)
            got = graph(rows, key=subject_key)
            exp = expected["queries"][qi]["subjects"][si]["union"]
            assert got["distinct_pair_count"]["value"] == exp["distinct_coordinate_pairs"]
            assert got["repeated_pair_occurrence_count"]["value"] == exp["repeated_coordinate_pair_occurrences"]
            assert (got["mapping_state"] == "compatible_displayed_partial_map") == exp["compatible_displayed_partial_correspondence"]
            for axis in ("query", "subject"):
                for kind in ("occupied", "paired"):
                    intervals = union_position_intervals([i for row in rows for b in row["blocks"]
                        for i in b["coverage"][axis + "_trace_" + kind + "_union"]["intervals"]])
                    assert sum(end - start for start, end in intervals) == exp[kind + "_" + axis + "_union_count"]
                for suffix, native_name in (("_mapping", "alternative_" + axis + "_mapping_positions"),
                                           ("_gap_versus_pair_conflict", axis + "_gap_vs_pair_conflict_positions"),
                                           ("_symbol_conflict", axis + "_symbol_conflict_positions")):
                    code = "alternative_" + axis + suffix if suffix == "_mapping" else axis + suffix
                    found = [c for c in got["conflicts"] if c["code"] == code]
                    intervals = found[0][axis + "_intervals"] if found else []
                    assert intervals == [[a - 1, b] for a, b in exp[native_name]], (release, qi, si, code)
    assert hsp_count == expected["hsp_count"]
    if release == "2011":
        assert native["queries"][0]["no_hits_marker"]["state"] == "present"
        assert native["queries"][0]["subjects"] == []


def test_actual_subject127_gap_conflict_has_both_native_column_witnesses():
    native = native_report("biopython_text_2202L_blastp_001.txt")
    query, rows = native["queries"][1], []
    subject = query["subjects"][0]
    for hi, observed in enumerate(subject["hsps"]):
        key = dict(report_ordinal=0, query_ordinal=1, subject_ordinal=0, hsp_ordinal=hi)
        blocks = [calculate_protein_block(b, key={**key, "block_ordinal": bi}, query_length=query["length"],
            subject_length=subject["length"], amino_acid_alphabet="standard20", ratio_decimal_places=18,
            rounding="half_even") for bi, b in enumerate(observed["traceback_blocks"])]
        rows.append(hsp(blocks, key=key))
    got = graph(rows, key=dict(report_ordinal=0, query_ordinal=1, subject_ordinal=0))
    gap = conflict(got, "subject_gap_versus_pair_conflict")
    assert gap["subject_intervals"] == [[126, 127]]
    witness = [rows[k["hsp_ordinal"]]["blocks"][k["block_ordinal"]]["columns"][k["column_ordinal"]] for k in gap["columns"]]
    assert len(witness) == 2
    assert {c["query_symbol"] for c in witness} == {"-", "S"}
    assert {c["subject_symbol"] for c in witness} == {"R"}
    assert {c["subject_position"]["value"] for c in witness} == {126}
    assert conflict(got, "alternative_subject_mapping")["subject_intervals"] == [[57, 126], [127, 162]]
