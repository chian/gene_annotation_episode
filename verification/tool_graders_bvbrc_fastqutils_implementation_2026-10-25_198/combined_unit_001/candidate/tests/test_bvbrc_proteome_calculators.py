"""Synthetic saved-sheet arithmetic, not native execution or service custody.

The historical filled examples remain unchanged. Variants below are synthetic
contract values; no test asserts an executed-input witness or calls a parser.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

from gene_annotation_episode import bvbrc_proteome_calculators as calculators
from gene_annotation_episode.bvbrc_proteome_sheet_contracts import validate_proteome_sheet_data


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "verification/tool_graders_bvbrc_proteome_sheet_contract_2026-10-25_165"
IDENTITY = "native_first_hsp_alignment_identity_fraction"
ENDPOINT = "native_subject_endpoint_difference_fraction"


def saved_sheet():
    return json.loads((EXAMPLES / "FILLED_NATIVE_SHEET_001.json").read_text())["value"]


def saved_components():
    return json.loads((EXAMPLES / "FILLED_NATIVE_COMPONENTS_001.json").read_text())["value"]


def parameters(**changes):
    return {"version": "bvbrc_proteome_native_parameters_proposal_v1",
            "track_keys": ["comp_genome_2", "comp_genome_4"],
            "minimum_identity_fraction": .6,
            "minimum_subject_endpoint_difference_fraction": .7,
            "allowed_hit_categories": None, **changes}


def calculate(sheet=None, **changes):
    value = saved_sheet() if sheet is None else sheet
    result = calculators.calculate_native_components(value, parameters=parameters(**changes))
    assert result["status"] in {"ok", "partial"}, result["diagnostics"]
    assert validate_proteome_sheet_data("NativeComponentsResult", result) == result
    return result["value"]


def track(result, key="comp_genome_4"):
    return next(row for row in result["tracks"] if row["track_key"] == key)


def association(sheet, key="comp_genome_4/row/0"):
    return next(row for row in sheet["association_rows"] if row["association_key"] == key)


def native_association(sheet, key="comp_genome_4/row/0"):
    return next(row for row in sheet["native_results"][0]["value"]["associations"]
                if row["association_key"] == key)


def scope(**changes):
    return {key: changes.get(key) for key in ("track_key", "reference_row_ordinal", "association_key",
             "protein_key", "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal")}


def native_error(sheet, row, code, field):
    row["valid"] = False
    row["diagnostics"].append({"code": code, "severity": "error", "path": row[field]["source_field"]["pointer"],
        "scope": scope(track_key=row.get("track_key", "ref_genome"),
                       reference_row_ordinal=row.get("reference_row_ordinal", row.get("row_ordinal")),
                       association_key=row.get("association_key")),
        "source_fields": [deepcopy(row[field]["source_field"])]})
    sheet["native_results"][0]["status"] = "partial"


def replace_fraction(sheet, name, value, *, presence="value", lexeme=None, key="comp_genome_4/row/0"):
    row = association(sheet, key)
    native = native_association(sheet, key)
    native_name = {IDENTITY: "percent_identity", ENDPOINT: "seq_coverage"}[name]
    cell = deepcopy(row[name])
    cell.update(value=value, presence=presence,
                lexeme=(str(value) if presence == "value" and lexeme is None else lexeme))
    row[name] = cell
    native[native_name] = deepcopy(cell)
    if presence == "invalid":
        native_error(sheet, native, "native_number_invalid", native_name)


def with_saved_tsv_projection():
    """Copy declared cells from a pre-existing synthetic A projection; no parser."""
    path = ROOT / "verification/tool_graders_bvbrc_proteome_native_2026-10-25/SYNTHETIC_PROJECTIONS_001.json"
    result = json.loads(path.read_text())[1]["result"]
    sheet = saved_sheet()
    primary = result["value"]
    sheet["native_results"] = [result]
    sheet["primary_source_ref"] = primary["source"]["content"]["source_ref"]
    native_tracks = {row["track_key"]: row for row in primary["tracks"]}
    for row in sheet["tracks"]:
        native = native_tracks[row["track_key"]]
        row["native_materialization"] = native["materialization"]
        row["native_source_fields"] = deepcopy(native["source_fields"])
    for row in sheet["reference_rows"]:
        native = primary["reference_rows"][row["reference_row_ordinal"]]
        for target, source in (("native_aa_length", "aa_length"), ("native_start", "start"),
                               ("native_end", "end"), ("native_strand", "strand")):
            row[target] = deepcopy(native[source])
    for row in sheet["association_rows"]:
        native = native_association(sheet, row["association_key"])
        for target, source in ((IDENTITY, "percent_identity"), (ENDPOINT, "seq_coverage"),
                               ("native_hit_category", "hit"), ("native_subject_length_aa", "aa_length")):
            row[target] = deepcopy(native[source])
    return sheet


def original_index(sheet):
    """Explicit synthetic original slots; these never establish execution."""
    raw = b'{"synthetic_original_parameter_slots":5}'
    parent = {"source_ref": "synthetic-parameter-record", "sha256": hashlib.sha256(raw).hexdigest(),
              "pointer": "/submitted", "row_ordinal": None, "field_name": None}
    index = {"version": "bvbrc_proteome_input_index_proposal_v1",
        "parameter_source": {"kind": "submitted", "source_field": parent},
        "reference_original_index": 1, "inputs": [],
        "source_contract": deepcopy(sheet["native_results"][0]["value"]["source_contract"]),
        "run_parameter_snapshots": [], "diagnostics": []}
    for ordinal in range(5):
        key = f"/user_genomes/{ordinal}"
        index["inputs"].append({"input_key": key, "parameter_pointer": key, "original_index": ordinal + 1,
            "kind": "user_genome", "value": f"/synthetic/input-{ordinal}.faa",
            "expected_track_key": "ref_genome" if ordinal == 0 else f"comp_genome_{ordinal}",
            "source_field": {**parent, "pointer": parent["pointer"] + key}})
    snapshot = {"kind": "submitted", "source_field": parent}
    for name in ("min_ident", "min_seq_cov", "min_positives", "max_e_val"):
        snapshot[name] = {"value": None, "presence": "omitted",
                          "source_field": {**parent, "pointer": "/submitted/" + name, "field_name": name}}
    index["run_parameter_snapshots"] = [snapshot]
    return index


def with_expected_tracks():
    sheet = saved_sheet()
    sheet["input_index"] = original_index(sheet)
    original = {row["expected_track_key"]: row for row in sheet["input_index"]["inputs"]}
    for row in sheet["tracks"]:
        row["original_input_key"] = original[row["track_key"]]["input_key"]
    for ordinal in (1, 3):
        row = deepcopy(sheet["tracks"][1])
        row.update(track_key=f"comp_genome_{ordinal}", comparison_ordinal=ordinal,
                   original_input_key=f"/user_genomes/{ordinal}",
                   native_materialization="not_in_projection", native_source_fields=[])
        sheet["tracks"].append(row)
    return sheet


def inventory(key, named_sequences):
    # Constructed supplied sequences and their actual bytes. These are neither
    # GenomeComparison output nor evidence that a service executed the inputs.
    chunks = [f">{name}\n{sequence}\n".encode() for name, sequence in named_sequences]
    raw = b"".join(chunks)
    source = {"content": {"source_ref": key, "artifact_field": "artifact_ref", "artifact_ref": key + ".faa",
               "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)},
              "body_complete": True, "object_complete": "yes"}
    result = {"version": "bvbrc_proteome_inventory_proposal_v1", "inventory_key": key,
        "format": "protein_fasta_utf8_v1", "source": source, "molecule": "aa",
        "normalization": "ascii_whitespace_removed_uppercase_no_symbol_substitution_v1", "records": [],
        "observed_header_count": len(chunks), "complete_record_count": len(chunks),
        "valid_complete_record_count": len(chunks), "duplicate_identifier_groups": [],
        "sequence_groups": [], "diagnostics": []}
    start, groups = 0, {}
    for ordinal, ((name, sequence), chunk) in enumerate(zip(named_sequences, chunks)):
        protein = {"inventory_key": key, "record_ordinal": ordinal}
        field = {"source_ref": key, "sha256": source["content"]["sha256"], "pointer": f"/records/{ordinal}",
                 "row_ordinal": ordinal, "field_name": None}
        digest = hashlib.sha256(sequence.encode()).hexdigest()
        result["records"].append({"record_ordinal": ordinal, "source_field": field, "byte_start": start,
            "byte_end_exclusive": start + len(chunk), "header": name, "identifier": name, "description": "",
            "sequence": sequence, "sequence_symbol_count": len(sequence), "sequence_sha256": digest,
            "sequence_md5": hashlib.md5(sequence.encode()).hexdigest(), "record_complete": True,
            "valid_sequence": True, "diagnostics": []})
        groups.setdefault(sequence, {"molecule": "aa", "normalization": result["normalization"],
            "sequence_sha256": digest, "sequence_symbol_count": len(sequence), "members": []})["members"].append(protein)
        start += len(chunk)
    result["sequence_groups"] = list(groups.values())
    return result


def with_supplied_occurrence_joins(*, same_subject=False, duplicate_pair=False):
    sheet = with_expected_tracks()
    primary = sheet["native_results"][0]["value"]
    # Avoid a cross-input identifier collision; equality of full sequences is
    # supplied separately and never selects an occurrence by identifier.
    native_association(sheet, "comp_genome_2/row/0")["patric_id"]["value"] = "subjectC"
    # Bind comp4's two distinct subjects to equal full supplied sequences.
    native_association(sheet)["aa_length"].update(value=100, lexeme="100")
    association(sheet)["native_subject_length_aa"] = deepcopy(native_association(sheet)["aa_length"])
    if same_subject or duplicate_pair:
        native_association(sheet)["patric_id"]["value"] = "subjectA"
    if duplicate_pair:
        primary["reference_rows"][1]["patric_id"]["value"] = "refA"
        primary["reference_rows"][1]["aa_length"].update(value=100, lexeme="100")
        sheet["reference_rows"][1]["native_aa_length"] = deepcopy(primary["reference_rows"][1]["aa_length"])
        fields = [deepcopy(row["patric_id"]["source_field"]) for row in primary["reference_rows"]]
        for row in primary["reference_rows"]:
            row["diagnostics"].append({"code": "native_duplicate_reference_id", "severity": "qualification",
                "path": row["native_pointer"], "scope": scope(track_key="ref_genome", reference_row_ordinal=row["row_ordinal"]),
                "source_fields": fields})
    sheet["inventories"] = [inventory("synthetic-ref", [("refA", "A" * 100), ("refB", "C" * 40)]),
                            inventory("synthetic-comp2", [("subjectC", "A" * 100)]),
                            inventory("synthetic-comp4", [("subjectA", "A" * 100), ("subjectB", "A" * 100)])]
    by_track = {"ref_genome": sheet["inventories"][0], "comp_genome_2": sheet["inventories"][1],
                "comp_genome_4": sheet["inventories"][2]}
    joins = {"version": "bvbrc_proteome_joins_proposal_v1", "primary_source_ref": sheet["primary_source_ref"],
        "execution_links": [], "requested_native_links": [], "requested_metadata_links": [], "track_bindings": [],
        "reference_joins": [], "subject_joins": [], "metadata_joins": [], "sequence_groups": [], "diagnostics": []}
    for row in sheet["tracks"]:
        inv = by_track.get(row["track_key"])
        row["inventory_key"] = inv["inventory_key"] if inv else None
        joins["track_bindings"].append({"track_key": row["track_key"], "input_key": row["original_input_key"],
            "inventory_key": row["inventory_key"], "execution_relation": "original_supplied_fasta" if inv else "unknown",
            "input_record_count": deepcopy(row["input_record_count"]), "membership_complete": "unknown",
            "identifier_collisions": [], "diagnostics": []})
        if inv:
            joins["execution_links"].append({"input_key": row["original_input_key"], "inventory_key": row["inventory_key"],
                "relation": "original_supplied_fasta", "executed_fasta": None, "membership_complete": "unknown",
                "staged_path": None, "witness_source_fields": []})
    all_groups = {}
    for inv in sheet["inventories"]:
        for group in inv["sequence_groups"]:
            key = group["sequence_sha256"]
            all_groups.setdefault(key, {**deepcopy(group), "members": []})["members"].extend(deepcopy(group["members"]))
    joins["sequence_groups"] = list(all_groups.values())
    binding = primary["source"]["content"]

    def joined(native, kind, key, native_key=None):
        inv = by_track[key]
        identifier = native["patric_id"]["value"]
        ordinal = next(i for i, r in enumerate(inv["records"]) if r["identifier"] == identifier)
        protein = {"inventory_key": inv["inventory_key"], "record_ordinal": ordinal}
        selector = {"source_ref": binding["source_ref"], "sha256": binding["sha256"], "kind": kind,
            "reference_row_ordinal": native.get("reference_row_ordinal", native.get("row_ordinal")),
            "track_key": key, "association_key": native_key}
        index = len(joins["requested_native_links"])
        joins["requested_native_links"].append({"native": selector, "protein": protein,
            "basis": "unique_exact_identifier", "native_identifier": identifier, "mapping_source_fields": []})
        value = {"native": selector, "state": "joined", "protein": protein, "candidates": [protein],
                 "accepted_link_indices": [index], "diagnostics": []}
        return value, inv["records"][ordinal]

    for row in sheet["reference_rows"]:
        value, record = joined(primary["reference_rows"][row["reference_row_ordinal"]], "reference", "ref_genome")
        joins["reference_joins"].append(value)
        row.update(protein=deepcopy(value["protein"]), join_state="joined",
                   inventory_sequence_symbol_count=calculators._cell(record["sequence_symbol_count"], fields=[record["source_field"]]))
    for row in sheet["association_rows"]:
        value, record = joined(native_association(sheet, row["association_key"]), "association_subject",
                               row["track_key"], row["association_key"])
        joins["subject_joins"].append(value)
        row.update(reference_protein=deepcopy(sheet["reference_rows"][row["reference_row_ordinal"]]["protein"]),
            reference_join_state="joined", subject_protein=deepcopy(value["protein"]), subject_join_state="joined",
            inventory_subject_sequence_symbol_count=calculators._cell(record["sequence_symbol_count"], fields=[record["source_field"]]))
    sheet["joins"] = joins
    return sheet


def test_original_filled_component_values_are_independently_checked():
    sheet, expected = saved_sheet(), saved_components()
    result = calculate(sheet)
    canonical = json.dumps(sheet, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    assert result["sheet_sha256"] == expected["sheet_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert [row["first_hsp_alignment_identity_percent"]["value"] for row in result["associations"]] == [87.5, 0, 87.5]
    assert [row["subject_endpoint_difference_percent"]["value"] for row in result["associations"]] == [99, 50, 99]
    assert [row["selection"] for row in result["associations"]] == ["pass", "fail", "pass"]
    for actual in result["tracks"]:
        prior = track(expected, actual["track_key"])
        for field in ("source_association_record_count", "published_association_record_count", "native_bi_count",
                      "native_uni_count", "unresolved_reference_association_count", "unresolved_subject_association_count"):
            assert actual[field]["value"] == prior[field]["value"]
        for field in ("first_hsp_identity_summary", "subject_endpoint_difference_summary"):
            assert actual[field]["used_association_keys"] == prior[field]["used_association_keys"]
            for summary in ("sum", "mean", "minimum", "maximum", "value_count"):
                assert actual[field][summary]["value"] == prior[field][summary]["value"]
    four = track(result)
    assert four["first_hsp_identity_summary"]["mean"]["value"] == float(Fraction(7, 8) / 2)
    assert four["subject_endpoint_difference_summary"]["mean"]["value"] == float((Fraction(1, 2) + Fraction(99, 100)) / 2)
    for name in ("reference_input_record_count", "comparison_input_record_count", "no_published_reference_count"):
        assert four[name]["state"] == "missing_input" and four[name]["value"] is None
    for name in ("observed_reference_fraction", "complete_published_reference_fraction",
                 "observed_selected_reference_fraction", "complete_selected_reference_fraction"):
        assert four[name]["fraction"]["value"] is None
        assert four[name]["denominator"]["value"] is None


def test_explicit_recalculation_detaches_parameters_and_preserves_every_native_lexeme():
    sheet, options = saved_sheet(), parameters()
    before = deepcopy(sheet)
    first = calculators.calculate_native_components(sheet, parameters=options)
    first_before = deepcopy(first)
    options["minimum_identity_fraction"] = .9
    second = calculators.calculate_native_components(sheet, parameters=options)
    assert sheet == before and first == first_before
    assert first["value"]["parameters"]["minimum_identity_fraction"] == .6
    assert second["value"]["parameters"]["minimum_identity_fraction"] == .9
    assert first["value"]["sheet_sha256"] == second["value"]["sheet_sha256"]
    assert [r["selection"] for r in second["value"]["associations"]] == ["fail"] * 3
    assert track(second["value"])["selection_counts"]["pass"]["value"] == 0
    assert association(sheet)[IDENTITY]["lexeme"] == "0.000"
    first["value"]["associations"][0]["first_hsp_alignment_identity_percent"]["source_fields"][0]["pointer"] = "/mutated"
    assert sheet == before


@pytest.mark.parametrize("lexeme,threshold,expected", [
    ("8.750E-1", .875, "pass"), ("+0.875000", .875, "pass"),
    ("0.874999999999999999999999999999999999", .875, "fail"),
    ("0.875000000000000000000000000000000001", .875, "pass"),
    ("0.000", 0, "pass"), ("1.000", 1, "pass"),
])
def test_inclusive_decimal_comparison_uses_native_lexeme(lexeme, threshold, expected):
    sheet = saved_sheet()
    replace_fraction(sheet, IDENTITY, float(lexeme), lexeme=lexeme)
    result = calculate(sheet, minimum_identity_fraction=threshold,
                       minimum_subject_endpoint_difference_fraction=None)
    actual = next(r for r in result["associations"] if r["association_key"] == "comp_genome_4/row/0")
    assert actual["selection"] == expected
    assert association(sheet)[IDENTITY]["lexeme"] == lexeme


@pytest.mark.parametrize("presence,lexeme,partition,state", [
    ("explicit_null", None, "null_count", "missing_input"),
    ("omitted", None, "omitted_count", "missing_input"),
    ("blank", "", "blank_count", "missing_input"),
    ("invalid", "not a fraction", "invalid_count", "invalid"),
])
def test_missing_invalid_and_true_zero_have_separate_summary_partitions(presence, lexeme, partition, state):
    sheet = saved_sheet()
    replace_fraction(sheet, IDENTITY, None, presence=presence, lexeme=lexeme)
    result = calculate(sheet, minimum_subject_endpoint_difference_fraction=.5)
    cell = result["associations"][1]
    summary = track(result)["first_hsp_identity_summary"]
    assert cell["first_hsp_alignment_identity_percent"]["state"] == state
    assert cell["first_hsp_alignment_identity_percent"]["value"] is None
    assert cell["selection"] == "unknown" and cell["unknown_conditions"] == ["identity"]
    assert summary[partition]["value"] == 1 and summary["value_count"]["value"] == 1
    assert summary["mean"]["value"] == .875
    assert summary["used_association_keys"] == ["comp_genome_4/row/1"]
    assert track(result)["published_association_record_count"]["value"] == 2
    assert track(calculate())["first_hsp_identity_summary"]["minimum"]["value"] == 0


def test_known_failure_dominates_but_does_not_erase_unknown_condition():
    sheet = saved_sheet()
    replace_fraction(sheet, IDENTITY, None, presence="explicit_null")
    result = calculate(sheet)
    row = result["associations"][1]
    assert row["selection"] == "fail"
    assert row["failed_conditions"] == ["subject_endpoint_difference"]
    assert row["unknown_conditions"] == ["identity"]
    assert track(result)["selection_counts"]["unknown"]["value"] == 0
    assert association(sheet)[IDENTITY]["presence"] == "explicit_null"


def test_invalid_unrelated_native_length_preserves_fraction_and_published_record():
    sheet = saved_sheet()
    row = native_association(sheet)
    row["aa_length"].update(value=None, presence="invalid", lexeme="wrong")
    association(sheet)["native_subject_length_aa"] = deepcopy(row["aa_length"])
    native_error(sheet, row, "native_number_invalid", "aa_length")
    result = calculate(sheet)
    assert track(result)["published_association_record_count"]["value"] == 2
    assert track(result)["first_hsp_identity_summary"]["value_count"]["value"] == 2
    assert result["associations"][1]["first_hsp_alignment_identity_percent"]["value"] == 0


def test_disabled_filters_differ_from_empty_category_list():
    disabled = calculate(minimum_identity_fraction=None, minimum_subject_endpoint_difference_fraction=None)
    empty = calculate(minimum_identity_fraction=None, minimum_subject_endpoint_difference_fraction=None,
                      allowed_hit_categories=[])
    assert [r["selection"] for r in disabled["associations"]] == ["pass"] * 3
    assert [r["selection"] for r in empty["associations"]] == ["fail"] * 3
    assert all(r["failed_conditions"] == ["category"] for r in empty["associations"])
    sheet = saved_sheet()
    row = native_association(sheet)
    row["hit"].update(value=None, presence="explicit_null")
    association(sheet)["native_hit_category"] = deepcopy(row["hit"])
    missing = calculate(sheet, minimum_identity_fraction=None, minimum_subject_endpoint_difference_fraction=None,
                        allowed_hit_categories=[])
    assert missing["associations"][1]["selection"] == "unknown"


def test_categories_are_exact_native_classifications_not_confidence():
    sheet = saved_sheet()
    native = native_association(sheet)
    native["hit"]["value"] = "other published category"
    association(sheet)["native_hit_category"] = deepcopy(native["hit"])
    native_error(sheet, native, "native_hit_category_invalid", "hit")
    result = calculate(sheet, minimum_identity_fraction=None, minimum_subject_endpoint_difference_fraction=None,
                       allowed_hit_categories=["bi (<->)"])
    assert track(result)["native_other_category_count"]["value"] == 1
    assert track(result)["native_bi_count"]["value"] == 1
    assert track(result)["native_missing_category_count"]["value"] == 0
    assert result["associations"][1]["failed_conditions"] == ["category"]


def test_source_scope_stays_partial_without_reinterpreting_visible_records():
    sheet = saved_sheet()
    primary = sheet["native_results"][0]
    primary["status"] = "partial"
    primary["value"]["source"]["object_complete"] = "unknown"
    primary["value"]["projection_completeness"] = "partial_or_unknown_artifact"
    result = calculate(sheet)
    four = track(result)
    assert four["source_scope"] == "partial_or_unknown_artifact"
    assert four["source_association_record_count"]["value"] == 2
    assert four["first_hsp_identity_summary"]["mean"]["value"] == .4375
    assert four["reference_input_record_count"]["value"] is None
    assert "projection_incomplete" in four["qualifications"]


def test_name_only_track_has_empty_summary_but_no_population_absence():
    sheet = saved_sheet()
    primary = sheet["native_results"][0]["value"]
    primary["associations"] = [r for r in primary["associations"] if r["track_key"] != "comp_genome_2"]
    sheet["association_rows"] = [r for r in sheet["association_rows"] if r["track_key"] != "comp_genome_2"]
    for row in primary["tracks"]:
        if row["track_key"] == "comp_genome_2":
            row["materialization"] = "unknown"
            row["source_fields"] = row["source_fields"][:1]
    for row in sheet["tracks"]:
        if row["track_key"] == "comp_genome_2":
            row["native_materialization"] = "unknown"
            row["native_source_fields"] = row["native_source_fields"][:1]
    result = track(calculate(sheet), "comp_genome_2")
    assert result["source_association_record_count"]["value"] == 0
    assert result["first_hsp_identity_summary"]["sum"]["value"] == 0
    for field in ("mean", "minimum", "maximum"):
        assert result["first_hsp_identity_summary"][field]["state"] == "not_applicable"
        assert result["first_hsp_identity_summary"][field]["value"] is None
    assert result["observed_reference_fraction"]["numerator"]["value"] == 0
    assert result["observed_reference_fraction"]["fraction"]["value"] is None
    assert "track_materialization_unknown" in result["no_published_reference_count"]["reason_codes"]


def test_uncertain_table_layout_excludes_every_fraction_and_makes_enabled_filters_unknown():
    sheet = with_saved_tsv_projection()
    primary = sheet["native_results"][0]["value"]
    native_error(sheet, primary["reference_rows"][0], "native_table_width_invalid", "patric_id")
    for native in primary["associations"]:
        if native["reference_row_ordinal"] == 0:
            native_error(sheet, native, "native_table_width_invalid", "patric_id")
    for row in sheet["association_rows"]:
        if row["reference_row_ordinal"] == 0:
            row["layout_state"] = "uncertain_table_layout"
    result = calculate(sheet, allowed_hit_categories=[])
    four = track(result)
    assert four["source_association_record_count"]["value"] == 2
    assert four["published_association_record_count"]["value"] == 1
    # Unresolved joins use published rows, not all source records.
    assert four["unresolved_reference_association_count"]["value"] == 1
    assert four["unresolved_subject_association_count"]["value"] == 1
    assert four["first_hsp_identity_summary"]["layout_uncertain_count"]["value"] == 1
    assert four["first_hsp_identity_summary"]["mean"]["value"] == .875
    row = result["associations"][1]
    assert row["selection"] == "unknown" and row["failed_conditions"] == []
    assert row["unknown_conditions"] == ["identity", "subject_endpoint_difference", "category"]
    assert row["first_hsp_alignment_identity_percent"]["state"] == "ambiguous"
    assert four["native_missing_category_count"]["value"] == 1


def test_explicit_missing_track_can_be_selected_without_compressing_native_ordinals():
    sheet = with_expected_tracks()
    result = calculate(sheet, track_keys=["comp_genome_3", "comp_genome_4"])
    assert [row["track_key"] for row in result["tracks"]] == ["comp_genome_3", "comp_genome_4"]
    missing = track(result, "comp_genome_3")
    assert missing["materialization"] == "not_in_projection"
    assert missing["source_association_record_count"]["value"] == 0
    assert "track_missing_from_projection" in missing["observed_reference_fraction"]["fraction"]["reason_codes"]
    assert track(result)["source_association_record_count"]["value"] == 2


def test_complete_materialized_blank_track_is_zero_published_not_known_input_absence():
    sheet = with_saved_tsv_projection()
    primary = sheet["native_results"][0]["value"]
    primary["associations"] = [r for r in primary["associations"] if r["track_key"] != "comp_genome_2"]
    sheet["association_rows"] = [r for r in sheet["association_rows"] if r["track_key"] != "comp_genome_2"]
    result = track(calculate(sheet), "comp_genome_2")
    assert result["materialization"] == "table_field_block"
    assert result["published_association_record_count"]["value"] == 0
    assert result["observed_reference_fraction"]["denominator"]["value"] is None
    assert result["no_published_reference_count"]["value"] is None


def test_bound_occurrences_and_demonstrated_sequence_groups_have_different_populations():
    sheet = with_supplied_occurrence_joins()
    first = track(calculate(sheet))
    assert first["observed_bound_reference_count"]["value"] == 2
    assert first["observed_bound_subject_count"]["value"] == 2
    assert first["observed_selected_reference_count"]["value"] == 1
    assert first["demonstrated_subject_sequence_group_count"]["value"] == 1
    assert first["unresolved_subject_sequence_count"]["value"] == 0
    assert first["reference_input_record_count"]["value"] is None
    second = track(calculate(sheet, minimum_identity_fraction=.9))
    assert second["observed_selected_reference_count"]["value"] == 0
    # Groups describe all bound subjects in the selected track before filtering.
    assert second["demonstrated_subject_sequence_group_count"]["value"] == 1
    assert second["observed_bound_subject_count"]["value"] == 2


def test_multiple_reference_subject_and_duplicate_pair_counts_do_not_inflate_support():
    two_pairs = track(calculate(with_supplied_occurrence_joins(same_subject=True)))
    assert two_pairs["observed_bound_reference_count"]["value"] == 2
    assert two_pairs["observed_bound_subject_count"]["value"] == 1
    assert two_pairs["multiple_reference_subject_count"]["value"] == 1
    assert two_pairs["excess_bound_pair_count"]["value"] == 1
    repeated = track(calculate(with_supplied_occurrence_joins(duplicate_pair=True)))
    assert repeated["source_association_record_count"]["value"] == 2
    assert repeated["observed_bound_reference_count"]["value"] == 1
    assert repeated["observed_bound_subject_count"]["value"] == 1
    assert repeated["multiple_reference_subject_count"]["value"] == 0
    assert repeated["excess_bound_pair_count"]["value"] == 0


@pytest.mark.parametrize("keep_one_subject", [False, True])
def test_absent_demonstrated_sequence_membership_stays_an_unresolved_bound_subject(keep_one_subject):
    sheet = with_supplied_occurrence_joins()
    groups = sheet["joins"]["sequence_groups"]
    if keep_one_subject:
        for group in groups:
            group["members"] = [member for member in group["members"]
                                if member != {"inventory_key": "synthetic-comp4", "record_ordinal": 1}]
    else:
        sheet["joins"]["sequence_groups"] = []
    result = track(calculate(sheet))
    assert result["observed_bound_subject_count"]["value"] == 2
    assert result["demonstrated_subject_sequence_group_count"]["value"] == (1 if keep_one_subject else 0)
    assert result["unresolved_subject_sequence_count"]["value"] == (1 if keep_one_subject else 2)
    # The calculator cannot infer a new equality group from retained strings.
    assert result["unresolved_subject_association_count"]["value"] == 0


@pytest.mark.parametrize("conflicting", [False, True])
def test_alternate_projection_is_never_added_to_primary_measurement_population(conflicting):
    sheet = saved_sheet()
    alternate = with_saved_tsv_projection()["native_results"][0]
    primary = sheet["native_results"][0]["value"]
    sheet["native_results"].append(alternate)
    alt = alternate["value"]
    conflicts = []
    if conflicting:
        cell = alt["associations"][0]["percent_identity"]
        cell.update(value=.9, lexeme="0.900")
        conflicts = [primary["associations"][0]["percent_identity"]["source_field"], cell["source_field"]]
    sheet["representation_comparisons"] = [{
        "link": {"left_source_ref": sheet["primary_source_ref"],
            "right_source_ref": alt["source"]["content"]["source_ref"],
            "relation": "alternate_full_projection",
            "reference_pairs": [{"left_row_ordinal": i, "right_row_ordinal": i} for i in range(2)],
            "association_pairs": [{"left_association_key": row["association_key"],
                                    "right_association_key": row["association_key"]} for row in primary["associations"]],
            "source_fields": []},
        "state": "conflicting" if conflicting else "equal_observed_cells",
        "conflict_source_fields": conflicts, "diagnostics": []}]
    result = calculate(sheet)
    assert len(result["associations"]) == 3
    assert track(result)["source_association_record_count"]["value"] == 2
    assert track(result)["first_hsp_identity_summary"]["mean"]["value"] == .4375
    assert track(result, "comp_genome_2")["first_hsp_identity_summary"]["mean"]["value"] == .875
    if conflicting:
        assert "representation_conflict" in track(result)["complete_published_reference_fraction"]["fraction"]["reason_codes"]


@pytest.mark.parametrize("changes", [
    {"track_keys": ["ref_genome"]}, {"track_keys": ["comp_genome_1"]},
    {"track_keys": ["comp_genome_2", "comp_genome_2"]}, {"track_keys": [False]},
    {"minimum_identity_fraction": True}, {"minimum_identity_fraction": "0.6"},
    {"minimum_identity_fraction": -0.01}, {"minimum_identity_fraction": 1.01},
    {"minimum_identity_fraction": float("nan")}, {"minimum_identity_fraction": float("inf")},
    {"minimum_subject_endpoint_difference_fraction": float("-inf")},
    {"allowed_hit_categories": ["ortholog"]}, {"formula": "return 1"}, {"version": "different"},
])
def test_invalid_parameters_return_closed_failure(changes):
    result = calculators.calculate_native_components(saved_sheet(), parameters=parameters(**changes))
    assert result["status"] == "invalid" and result["value"] is None
    assert result["diagnostics"][0]["code"] == "calculation_parameters_invalid"
    assert result["requirements"][0]["required_input"] == "valid_parameters"
    validate_proteome_sheet_data("NativeComponentsResult", result)


def test_absent_parameter_is_not_silently_disabled_and_empty_track_selection_is_explicit():
    options = parameters()
    del options["minimum_identity_fraction"]
    missing = calculators.calculate_native_components(saved_sheet(), parameters=options)
    assert missing["status"] == "invalid"
    empty = calculate(track_keys=[])
    assert empty["parameters"]["track_keys"] == []
    assert empty["associations"] == [] and empty["tracks"] == []


@pytest.mark.parametrize("mutation", [
    lambda s: s.update(scientific_mode="database_identification"),
    lambda s: s.update(unexpected=True),
    lambda s: s.update(primary_source_ref="wrong"),
    lambda s: association(s).__setitem__("association_key", "comp_genome_4/row/999"),
    lambda s: association(s)[IDENTITY]["source_field"].__setitem__("sha256", "0" * 64),
    lambda s: association(s)[IDENTITY].__setitem__("value", .9),
    lambda s: association(s)[IDENTITY].__setitem__("value", True),
    lambda s: association(s)[IDENTITY].__setitem__("lexeme", "NaN"),
    lambda s: s["tracks"][0]["input_record_count"].update(state="value", value=2),
])
def test_malformed_or_unwitnessed_saved_sheet_is_not_calculated(mutation):
    sheet = saved_sheet()
    mutation(sheet)
    result = calculators.calculate_native_components(sheet, parameters=parameters())
    assert result["status"] == "invalid" and result["value"] is None
    assert result["diagnostics"][0]["code"] == "sheet_relationship_invalid"


def test_selected_track_order_is_explicit_and_other_tracks_are_not_aggregated():
    result = calculate(track_keys=["comp_genome_4"])
    assert [r["track_key"] for r in result["tracks"]] == ["comp_genome_4"]
    assert len(result["associations"]) == 2
    assert track(result)["source_association_record_count"]["value"] == 2
    assert result["used_component_families"] == saved_components()["used_component_families"]
    assert result["retained_unused_component_families"] == saved_components()["retained_unused_component_families"]


def test_conditional_future_ratio_arithmetic_does_not_forge_an_execution_witness():
    # No production NativeSheet can presently admit these exact denominators.
    # This tests the ordinary arithmetic primitive with literal counts only.
    cases = json.loads((EXAMPLES / "NUMERICAL_EXAMPLES_001.json").read_text())["cases"]
    case = next(row for row in cases if row["case"] == "four_record_reference")
    values = [Fraction(str(row["identity"])) for row in case["rows"]]
    assert sum(values) / len(values) == Fraction(1, 2)
    endpoint = [Fraction(str(row["subject_endpoint_difference"])) for row in case["rows"]]
    assert sum(endpoint) / len(endpoint) == Fraction(56, 75)
    for numerator, denominator, expected in [(3, 4, .75), (2, 4, .5), (0, 4, 0)]:
        ratio = calculators._ratio(calculators._cell(numerator), calculators._cell(denominator))
        assert ratio["fraction"]["value"] == expected
    zero = calculators._ratio(calculators._cell(0), calculators._cell(0))
    assert zero == next(row for row in cases if row["case"] == "empty_exact_input")["ratio"]


def test_saved_sheet_recalculation_has_no_io_parsing_scientific_execution_or_store(monkeypatch):
    import socket
    import subprocess
    from gene_annotation_episode import bvbrc_proteome_native, bvbrc_proteome_inputs
    from gene_annotation_episode import blast_pairwise_grader
    sheet, options = saved_sheet(), parameters()
    initial = calculators.calculate_native_components(sheet, parameters=options)

    def forbidden(*args, **kwargs):
        raise AssertionError("calculator attempted acquisition, parsing or scientific work")

    with monkeypatch.context() as guard:
        guard.setattr(Path, "read_bytes", forbidden)
        guard.setattr(Path, "read_text", forbidden)
        guard.setattr("builtins.open", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(bvbrc_proteome_native, "parse_genome_comparison", forbidden)
        for name in ("read_protein_fasta", "read_feature_metadata", "read_genome_metadata", "read_feature_sequences"):
            guard.setattr(bvbrc_proteome_inputs, name, forbidden)
        guard.setattr(blast_pairwise_grader, "alignment_components", forbidden)
        guard.setattr(blast_pairwise_grader, "build_pairwise_sheet", forbidden)
        assert calculators.calculate_native_components(sheet, parameters=options) == initial
        options["minimum_identity_fraction"] = .9
        changed = calculators.calculate_native_components(sheet, parameters=options)
    assert track(changed["value"])["selection_counts"]["pass"]["value"] == 0
