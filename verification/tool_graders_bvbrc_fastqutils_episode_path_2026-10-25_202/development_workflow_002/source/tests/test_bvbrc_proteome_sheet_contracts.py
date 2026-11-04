"""Saved-data validation examples; none are retained live scientific outputs.

The historical filled contracts are independent examples, read unchanged.
Additional inputs/links below are manually constructed synthetic saved values.
Validation is never allowed to parse bytes or calculate scientific components.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode import bvbrc_proteome_sheet_contracts as contracts
from gene_annotation_episode.bvbrc_proteome_data_contracts import ProteomeDataError


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "verification/tool_graders_bvbrc_proteome_sheet_contract_2026-10-25_165"
IDENTITY = "native_first_hsp_alignment_identity_fraction"


def sheet():
    return json.loads((EXAMPLES / "FILLED_NATIVE_SHEET_001.json").read_text())["value"]


def components():
    return json.loads((EXAMPLES / "FILLED_NATIVE_COMPONENTS_001.json").read_text())["value"]


def cell(value=None, reason="exact_executed_input_missing", fields=()):
    return {"state": "missing_input" if value is None else "value", "value": value,
            "reason_codes": [reason] if value is None else [], "source_fields": list(fields)}


def source(key, content):
    return {"content": {"source_ref": key, "artifact_field": "artifact_ref", "artifact_ref": key,
                         "sha256": hashlib.sha256(content).hexdigest(), "byte_count": len(content)},
            "body_complete": True, "object_complete": "yes"}


def field(src, pointer, row=None, name=None):
    return {"source_ref": src["content"]["source_ref"], "sha256": src["content"]["sha256"],
            "pointer": pointer, "row_ordinal": row, "field_name": name}


def scope(**changes):
    return {name: changes.get(name) for name in ("track_key", "reference_row_ordinal", "association_key",
            "protein_key", "report_key", "query_ordinal", "hit_ordinal", "hsp_ordinal")}


def diagnostic(code, *, severity="qualification", **where):
    return {"code": code, "severity": severity, "path": "", "scope": scope(**where), "source_fields": []}


def inventory():
    content = b">refA\n" + b"A" * 100 + b"\n>refB\n" + b"C" * 40 + b"\n"
    src = source("synthetic-supplied-ref", content)
    result = {"version": "bvbrc_proteome_inventory_proposal_v1", "inventory_key": "ref-input",
              "format": "protein_fasta_utf8_v1", "source": src, "molecule": "aa",
              "normalization": "ascii_whitespace_removed_uppercase_no_symbol_substitution_v1",
              "records": [], "observed_header_count": 2, "complete_record_count": 2,
              "valid_complete_record_count": 2, "duplicate_identifier_groups": [], "sequence_groups": [],
              "diagnostics": []}
    for i, (name, sequence, start, end) in enumerate((("refA", "A" * 100, 0, 107), ("refB", "C" * 40, 107, 154))):
        digest = hashlib.sha256(sequence.encode()).hexdigest()
        result["records"].append({"record_ordinal": i, "byte_start": start, "byte_end_exclusive": end,
            "header": name, "identifier": name, "description": "", "sequence": sequence,
            "sequence_symbol_count": len(sequence), "sequence_sha256": digest,
            "sequence_md5": hashlib.md5(sequence.encode()).hexdigest(), "record_complete": True,
            "valid_sequence": True, "source_field": field(src, f"/records/{i}", i), "diagnostics": []})
        result["sequence_groups"].append({"molecule": "aa", "normalization": result["normalization"],
            "sequence_sha256": digest, "sequence_symbol_count": len(sequence),
            "members": [{"inventory_key": "ref-input", "record_ordinal": i}]})
    return result


def linked_sheet():
    saved = sheet()
    src = source("synthetic-original-parameters", b"supplied original parameters")
    parent = field(src, "/parameters")
    index = {"version": "bvbrc_proteome_input_index_proposal_v1", "parameter_source": {"kind": "submitted", "source_field": parent},
             "reference_original_index": 1, "inputs": [], "source_contract": deepcopy(saved["native_results"][0]["value"]["source_contract"]),
             "run_parameter_snapshots": [], "diagnostics": []}
    for i in range(5):
        pointer = f"/user_genomes/{i}"
        index["inputs"].append({"input_key": pointer, "parameter_pointer": pointer, "original_index": i+1,
            "kind": "user_genome", "value": f"supplied-{i}.faa", "expected_track_key": "ref_genome" if i == 0 else f"comp_genome_{i}",
            "source_field": field(src, "/parameters" + pointer, i, "user_genomes")})
    snapshot = {"kind": "submitted", "source_field": parent}
    for name in ("min_ident", "min_seq_cov", "min_positives", "max_e_val"):
        snapshot[name] = {"presence": "omitted", "value": None, "source_field": field(src, "/parameters/" + name, None, name)}
    index["run_parameter_snapshots"].append(snapshot)
    saved["input_index"] = index
    for track in saved["tracks"]:
        i = 0 if track["track_key"] == "ref_genome" else track["comparison_ordinal"]
        track["original_input_key"] = f"/user_genomes/{i}"
    for i in (1, 3):
        track = deepcopy(saved["tracks"][1])
        track.update(track_key=f"comp_genome_{i}", comparison_ordinal=i, original_input_key=f"/user_genomes/{i}",
                     native_materialization="not_in_projection", native_source_fields=[])
        saved["tracks"].append(track)
    inv = inventory()
    saved["inventories"] = [inv]
    saved["tracks"][0]["inventory_key"] = inv["inventory_key"]
    joins = {"version": "bvbrc_proteome_joins_proposal_v1", "primary_source_ref": saved["primary_source_ref"],
        "execution_links": [{"input_key": "/user_genomes/0", "inventory_key": "ref-input", "relation": "original_supplied_fasta",
                             "executed_fasta": None, "membership_complete": "unknown", "staged_path": None, "witness_source_fields": []}],
        "requested_native_links": [], "requested_metadata_links": [], "track_bindings": [],
        "reference_joins": [], "subject_joins": [], "metadata_joins": [],
        "sequence_groups": deepcopy(inv["sequence_groups"]), "diagnostics": []}
    for track in saved["tracks"]:
        joins["track_bindings"].append({"track_key": track["track_key"], "input_key": track["original_input_key"],
            "inventory_key": track["inventory_key"], "execution_relation": "original_supplied_fasta" if track["inventory_key"] else "unknown",
            "input_record_count": deepcopy(track["input_record_count"]), "membership_complete": "unknown", "identifier_collisions": [], "diagnostics": []})
    native = saved["native_results"][0]["value"]
    binding = native["source"]["content"]
    for i, row in enumerate(saved["reference_rows"]):
        ref = {"inventory_key": "ref-input", "record_ordinal": i}
        selector = {"source_ref": binding["source_ref"], "sha256": binding["sha256"], "kind": "reference",
                    "reference_row_ordinal": i, "track_key": "ref_genome", "association_key": None}
        joins["requested_native_links"].append({"native": deepcopy(selector), "protein": deepcopy(ref), "basis": "unique_exact_identifier",
              "native_identifier": inv["records"][i]["identifier"], "mapping_source_fields": []})
        joins["reference_joins"].append({"native": selector, "state": "joined", "protein": deepcopy(ref),
              "candidates": [deepcopy(ref)], "accepted_link_indices": [i], "diagnostics": []})
        row.update(protein=ref, join_state="joined", inventory_sequence_symbol_count=cell(inv["records"][i]["sequence_symbol_count"], fields=[inv["records"][i]["source_field"]]))
    for row in saved["association_rows"]:
        row["reference_protein"] = deepcopy(saved["reference_rows"][row["reference_row_ordinal"]]["protein"])
        row["reference_join_state"] = "joined"
        joins["subject_joins"].append({"native": {"source_ref": binding["source_ref"], "sha256": binding["sha256"], "kind": "association_subject",
              "reference_row_ordinal": row["reference_row_ordinal"], "track_key": row["track_key"], "association_key": row["association_key"]},
              "state": "not_supplied", "protein": None, "candidates": [], "accepted_link_indices": [], "diagnostics": []})
    saved["joins"] = joins
    return saved


def metadata_sheet():
    saved = linked_sheet()
    record = saved["inventories"][0]["records"][0]
    population = {"origin": "supplied_snapshot", "selected_fields": [], "query_source": None,
                  "offset": None, "requested_limit": None, "reported_total_count": None,
                  "population_complete": "unknown", "completeness_evidence": []}
    definitions = json.loads((EXAMPLES / "DATA_SHAPES_PROPOSAL_002.json").read_text())["$defs"]
    values = {
        "FeatureRecord": {"feature_id": "refA", "patric_id": "refA", "genome_id": "g1", "product": "source product", "aa_sequence_md5": record["sequence_md5"], "aa_length": 100},
        "GenomeRecord": {"genome_id": "g1", "taxon_id": 7},
        "FeatureSequenceRecord": {"md5": record["sequence_md5"], "sequence": record["sequence"]},
    }
    for name, dest, key, fmt in (("FeatureRecord", "feature_snapshots", "features", "bvbrc_genome_feature_json_array_v1"),
                                  ("GenomeRecord", "genome_snapshots", "genomes", "bvbrc_genome_json_array_v1"),
                                  ("FeatureSequenceRecord", "sequence_snapshots", "sequences", "bvbrc_feature_sequence_json_array_v1")):
        src = source("synthetic-" + key, json.dumps([values[name]]).encode())
        row = {"row_ordinal": 0, "source_field": field(src, "/0", 0), "valid": True, "diagnostics": []}
        for prop, shape in definitions[name]["properties"].items():
            if shape.get("$ref") not in {"#/$defs/NativeString", "#/$defs/NativeNumber"}:
                continue
            value = values[name].get(prop)
            row[prop] = {"presence": "omitted" if value is None else "value", "value": value,
                         "source_field": field(src, "/0/" + prop, 0, prop)}
            if shape["$ref"] == "#/$defs/NativeNumber":
                row[prop]["lexeme"] = None if value is None else str(value)
        snapshot = {"version": "bvbrc_proteome_metadata_proposal_v1", "snapshot_key": key, "format": fmt,
                    "source": src, "population": deepcopy(population), "records": [row], "unsupported_field_paths": [], "diagnostics": []}
        if name == "FeatureRecord":
            snapshot["coordinate_convention"] = {"value": "unknown", "source_fields": []}
        elif name == "FeatureSequenceRecord":
            row.update(molecule="aa", sequence_symbol_count=100, computed_md5=record["sequence_md5"], computed_sha256=record["sequence_sha256"])
        saved[dest] = [snapshot]
    protein = deepcopy(saved["reference_rows"][0]["protein"])
    refs = {"protein": protein, "feature": {"snapshot_key": "features", "row_ordinal": 0},
            "genome": {"snapshot_key": "genomes", "row_ordinal": 0}, "feature_sequence": {"snapshot_key": "sequences", "row_ordinal": 0}}
    saved["joins"]["requested_metadata_links"] = [{**deepcopy(refs), "basis": "exact_feature_identifier", "mapping_source_fields": []}]
    saved["joins"]["metadata_joins"] = [{**refs, "link_index": 0, "state": "joined", "diagnostics": []}]
    saved["reference_rows"][0]["metadata_links"] = [0]
    return saved


def validate(name, value):
    return contracts.validate_proteome_sheet_data(name, value)


def test_frozen_definitions_and_original_filled_examples_are_unchanged():
    asset = ROOT / "gene_annotation_episode/bvbrc_proteome_sheet_schemas.json"
    # Prospective request-content amendment; verify every historical schema byte
    # after removing only this explicitly permitted final enum alternative.
    original = json.loads(asset.read_text())
    enum = original["$defs"]["ContentBinding"]["properties"]["artifact_field"]["enum"]
    assert enum == ["artifact_ref", "text_ref", "stdout_ref", "stderr_ref", "request_ref"]
    assert enum.pop() == "request_ref"
    restored = (json.dumps(original, indent=2, ensure_ascii=False) + "\n").encode()
    assert hashlib.sha256(restored).hexdigest() == "739ee63e0e6eea56398c8482a1143dec8b7f7f073041de3edfa4a06af654d9ae"
    definitions = json.loads(asset.read_text())["$defs"]
    for name in ("bvbrc_proteome_data_schemas.json", "bvbrc_proteome_native_schemas.json"):
        prior = json.loads((asset.parent / name).read_text())["$defs"]
        assert all(definitions[key] == val for key, val in prior.items())
    saved = sheet()
    result = validate("NativeSheet", saved)
    expected = components()
    assert validate("NativeComponents", expected) == expected
    assert [r[IDENTITY]["value"] for r in result["association_rows"]] == [.875, 0, .875]
    assert expected["tracks"][1]["first_hsp_identity_summary"]["mean"]["value"] == .4375
    assert all(t["input_record_count"]["value"] is None for t in result["tracks"])


def test_detached_schema_values_and_result_envelopes():
    saved = sheet()
    envelope = {"status": "partial", "value": saved, "requirements": saved["requirements"], "diagnostics": saved["diagnostics"]}
    result = validate("NativeSheetResult", envelope)
    result["value"]["association_rows"][0][IDENTITY]["value"] = 12
    assert saved["association_rows"][0][IDENTITY]["value"] == .875
    schema = contracts.proteome_sheet_schema("NativeSheet")
    schema["$defs"]["NativeSheet"]["properties"].clear()
    assert contracts.proteome_sheet_schema("NativeSheet")["$defs"]["NativeSheet"]["properties"]
    expected = components()
    assert validate("NativeComponentsResult", {"status": "partial", "value": expected,
        "requirements": expected["requirements"], "diagnostics": expected["diagnostics"]})["value"] == expected


@pytest.mark.parametrize("mutate", [
    lambda s: s.update(primary_source_ref="wrong"),
    lambda s: s["native_results"].append(deepcopy(s["native_results"][0])),
    lambda s: s["tracks"].append(deepcopy(s["tracks"][1])),
    lambda s: s["reference_rows"][0].update(reference_row_key="ref_genome/row/1"),
    lambda s: s["association_rows"][0].update(association_key="comp_genome_4/row/0"),
    lambda s: s["association_rows"][0][IDENTITY].update(value=.9, lexeme=".9"),
    lambda s: s["association_rows"][0][IDENTITY]["source_field"].update(source_ref="wrong"),
    lambda s: s["association_rows"][0][IDENTITY]["source_field"].update(pointer="/wrong"),
    lambda s: s["association_rows"][0][IDENTITY]["source_field"].update(row_ordinal=9),
    lambda s: s["association_rows"][0][IDENTITY]["source_field"].update(sha256="0"*64),
    lambda s: s["association_rows"][0].update(native_subject_identifier_present=False),
    lambda s: s["tracks"][0]["input_record_count"].update(state="value", value=2),
    lambda s: s["tracks"][0].update(complete_reference_row_membership="yes"),
    lambda s: s["tracks"][1].update(complete_published_association_membership="yes"),
    lambda s: s["tracks"][1].update(comparison_ordinal=1),
    lambda s: s["tracks"][1]["native_source_fields"].clear(),
    lambda s: s["reference_rows"][0].update(join_state="joined", protein={"inventory_key": "missing", "record_ordinal": 0}),
    lambda s: s["reference_rows"][0].update(metadata_links=[0]),
    lambda s: s["association_rows"].pop(),
    lambda s: s["native_results"][0]["value"]["reference_rows"][0].update(reference_row_key="wrong"),
    lambda s: s["native_results"][0].update(status="invalid"),
])
def test_rejects_saved_native_copy_source_population_and_false_membership_claims(mutate):
    saved = sheet()
    mutate(saved)
    with pytest.raises(ProteomeDataError) as caught:
        validate("NativeSheet", saved)
    assert caught.value.code and type(caught.value.path) is str
    assert str(caught.value) == caught.value.code


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "0.2", -.1, 1.1])
def test_parameters_require_finite_plain_fractions(value):
    params = components()["parameters"]
    params["minimum_identity_fraction"] = value
    with pytest.raises(ProteomeDataError):
        validate("NativeCalculationParameters", params)


@pytest.mark.parametrize("mutate", [
    lambda p: p.update(track_keys=["ref_genome"]),
    lambda p: p.update(track_keys=["comp_genome_0"]),
    lambda p: p.update(track_keys=["comp_genome_2", "comp_genome_2"]),
    lambda p: p.update(allowed_hit_categories=["bi (<->)", "bi (<->)"]),
    lambda p: p.update(allowed_hit_categories=["orthology"]),
    lambda p: p.pop("minimum_identity_fraction"),
])
def test_parameter_selection_identities_are_explicit(mutate):
    params = components()["parameters"]
    mutate(params)
    with pytest.raises(ProteomeDataError):
        validate("NativeCalculationParameters", params)


def test_disabled_filters_empty_selection_and_true_zero_survive():
    params = components()["parameters"]
    params.update(track_keys=[], minimum_identity_fraction=0, minimum_subject_endpoint_difference_fraction=None, allowed_hit_categories=[])
    assert validate("NativeCalculationParameters", params) == params
    saved = sheet()
    assert validate("NativeSheet", saved)["association_rows"][1][IDENTITY]["value"] == 0


def test_original_supplied_occurrences_are_linked_without_execution_denominators():
    saved = linked_sheet()
    assert validate("NativeSheet", saved) == saved
    assert validate("NativeJoins", saved["joins"]) == saved["joins"]
    assert all(t["input_record_count"]["value"] is None for t in saved["tracks"])


@pytest.mark.parametrize("mutate", [
    lambda s: s["inventories"].append(deepcopy(s["inventories"][0])),
    lambda s: s["inventories"][0]["records"][0].update(record_ordinal=1),
    lambda s: s["inventories"][0]["records"][0].update(sequence_sha256="0"*64),
    lambda s: s["input_index"]["inputs"][2].update(expected_track_key="comp_genome_1"),
    lambda s: s["joins"]["reference_joins"][0]["protein"].update(record_ordinal=1),
    lambda s: s["joins"]["reference_joins"][0]["native"].update(sha256="0"*64),
    lambda s: s["joins"]["reference_joins"][0].update(accepted_link_indices=[1]),
    lambda s: s["joins"]["reference_joins"][0].update(state="unmatched"),
    lambda s: s["joins"]["requested_native_links"][0].update(native_identifier="refB"),
    lambda s: s["joins"]["requested_native_links"][0].update(basis="producer_occurrence_mapping"),
    lambda s: s["joins"]["track_bindings"][0].update(execution_relation="exact_executed_fasta"),
    lambda s: s["reference_rows"][0]["inventory_sequence_symbol_count"].update(value=99),
    lambda s: s["joins"]["sequence_groups"][0]["members"].append({"inventory_key": "ref-input", "record_ordinal": 1}),
])
def test_saved_declared_joins_cannot_change_source_identity_occurrence_or_sequence_group(mutate):
    saved = linked_sheet()
    mutate(saved)
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


def test_locator_only_execution_claim_is_preserved_unqualified():
    saved = linked_sheet()
    link = saved["joins"]["execution_links"][0]
    link.update(relation="exact_executed_fasta", executed_fasta=deepcopy(saved["inventories"][0]["source"]["content"]),
                membership_complete="yes", witness_source_fields=[saved["inventories"][0]["records"][0]["source_field"]])
    binding = saved["joins"]["track_bindings"][0]
    binding.update(execution_relation="unknown", membership_complete="unknown", input_record_count=cell(reason="execution_witness_interface_unavailable"))
    saved["tracks"][0]["input_record_count"] = deepcopy(binding["input_record_count"])
    result = validate("NativeSheet", saved)
    assert result["joins"]["execution_links"][0]["relation"] == "exact_executed_fasta"
    assert result["tracks"][0]["input_record_count"]["value"] is None
    binding["membership_complete"] = "yes"
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


@pytest.mark.parametrize("name", ["NativeSheet", "NativeJoins"])
def test_supplied_inventory_cannot_claim_complete_executed_membership(name):
    saved = linked_sheet()
    saved["joins"]["track_bindings"][0]["membership_complete"] = "yes"
    with pytest.raises(ProteomeDataError) as error:
        validate(name, saved if name == "NativeSheet" else saved["joins"])
    assert error.value.code == "proteome_sheet_execution_membership_unavailable"


@pytest.mark.parametrize("text", ["AA-?1", ""])
def test_invalid_complete_sequence_keeps_identity_and_actual_symbol_count(text):
    saved = linked_sheet()
    inv = saved["inventories"][0]
    row = inv["records"][0]
    row.update(sequence=text, sequence_symbol_count=len(text), sequence_sha256=hashlib.sha256(text.encode()).hexdigest(),
               sequence_md5=hashlib.md5(text.encode()).hexdigest(), valid_sequence=False)
    inv["valid_complete_record_count"] = 1
    inv["sequence_groups"] = inv["sequence_groups"][1:]
    saved["joins"]["sequence_groups"] = deepcopy(inv["sequence_groups"])
    saved["reference_rows"][0]["inventory_sequence_symbol_count"] = cell(len(text), fields=[row["source_field"]])
    result = validate("NativeSheet", saved)
    assert result["reference_rows"][0]["join_state"] == "joined"
    assert result["reference_rows"][0]["inventory_sequence_symbol_count"]["value"] == len(text)
    assert result["reference_rows"][0]["native_aa_length"]["value"] == 100


def test_incomplete_sequence_retains_identity_with_missing_full_count():
    saved = linked_sheet()
    inv = saved["inventories"][0]
    row = inv["records"][1]
    inv["source"]["object_complete"] = "unknown"
    row.update(record_complete=False, valid_sequence=False, sequence=None, sequence_symbol_count=None, sequence_sha256=None, sequence_md5=None)
    inv.update(complete_record_count=1, valid_complete_record_count=1)
    inv["sequence_groups"] = inv["sequence_groups"][:1]
    saved["joins"]["sequence_groups"] = deepcopy(inv["sequence_groups"])
    saved["reference_rows"][1]["inventory_sequence_symbol_count"] = cell(reason="fasta_record_incomplete")
    assert validate("NativeSheet", saved)["reference_rows"][1]["join_state"] == "joined"
    saved["reference_rows"][1]["inventory_sequence_symbol_count"] = cell(40)
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


def test_supplied_metadata_relationships_and_unrelated_invalid_cell_are_local():
    saved = metadata_sheet()
    assert validate("NativeSheet", saved) == saved
    row = saved["feature_snapshots"][0]["records"][0]
    row["aa_length"].update(presence="invalid", value=None, lexeme="unusable")
    row["valid"] = False
    row["diagnostics"].append(diagnostic("native_invalid_cell", severity="error"))
    assert validate("NativeSheet", saved)["joins"]["metadata_joins"][0]["state"] == "joined"


def test_invalid_sequence_md5_cannot_support_joined_metadata_without_sequence_row():
    saved = metadata_sheet()
    for item in (saved["joins"]["requested_metadata_links"][0], saved["joins"]["metadata_joins"][0]):
        item["feature_sequence"] = None
    validate("NativeSheet", saved)
    row = saved["feature_snapshots"][0]["records"][0]
    row["aa_sequence_md5"].update(presence="invalid", value=None)
    row["valid"] = False
    row["diagnostics"].append(diagnostic("native_invalid_cell", severity="error"))
    # The snapshot retains valid other fields; the rejected relation is the
    # relevant claim, not the entire metadata record or native measurement.
    contracts.validate_proteome_data("FeatureSnapshot", saved["feature_snapshots"][0])
    with pytest.raises(ProteomeDataError) as error:
        validate("NativeSheet", saved)
    assert error.value.code == "proteome_sheet_metadata_sequence_conflict"
    saved["joins"]["metadata_joins"][0].update(state="conflicting", feature=None, genome=None)
    saved["reference_rows"][0]["metadata_links"] = []
    assert validate("NativeSheet", saved)["association_rows"][0][IDENTITY]["value"] == .875


def genomic_metadata_sheet():
    saved = metadata_sheet()
    # Independently supply the original genome-ID selection and its links;
    # drawing coordinates from a user-FASTA selection remain a different case.
    keys = {}
    for i, entry in enumerate(saved["input_index"]["inputs"]):
        old, new = entry["input_key"], f"/genome_ids/{i}"
        keys[old] = new
        entry.update(input_key=new, parameter_pointer=new, kind="genome_id")
        entry["source_field"].update(pointer="/parameters" + new, field_name="genome_ids")
    for row in saved["tracks"]:
        row["original_input_key"] = keys[row["original_input_key"]]
    for row in saved["joins"]["track_bindings"] + saved["joins"]["execution_links"]:
        row["input_key"] = keys[row["input_key"]]
    snapshot = saved["feature_snapshots"][0]
    feature = snapshot["records"][0]
    native = saved["native_results"][0]["value"]["reference_rows"][0]
    for name in ("start", "end", "strand"):
        feature[name].update({key: deepcopy(value) for key, value in native[name].items() if key != "source_field"})
    snapshot["coordinate_convention"] = {"value": "one_based_closed", "source_fields": [deepcopy(feature["source_field"])]}
    saved["reference_rows"][0]["coordinate_kind"] = "genomic_metadata"
    return saved


def test_known_agreeing_metadata_coordinates_keep_declared_origin():
    saved = genomic_metadata_sheet()
    assert validate("NativeSheet", saved) == saved
    saved["reference_rows"][0]["coordinate_kind"] = "unknown"
    assert validate("NativeSheet", saved)["reference_rows"][0]["native_end"]["value"] == 303


@pytest.mark.parametrize("change", ["unknown_convention", "different_start", "missing_end", "different_strand"])
def test_genomic_origin_cannot_overstate_metadata_correspondence(change):
    saved = genomic_metadata_sheet()
    snapshot = saved["feature_snapshots"][0]
    feature = snapshot["records"][0]
    if change == "unknown_convention":
        snapshot["coordinate_convention"] = {"value": "unknown", "source_fields": []}
    elif change == "different_start":
        feature["start"].update(value=2, lexeme="2")
    elif change == "missing_end":
        feature["end"].update(presence="omitted", value=None, lexeme=None)
    else:
        feature["strand"]["value"] = "-"
    contracts.validate_proteome_data("FeatureSnapshot", snapshot)
    with pytest.raises(ProteomeDataError) as error:
        validate("NativeSheet", saved)
    assert error.value.code in {"proteome_sheet_coordinate_origin_unbound", "proteome_sheet_coordinate_origin_conflict"}
    saved["reference_rows"][0]["coordinate_kind"] = "unknown"
    assert validate("NativeSheet", saved)["reference_rows"][0]["native_end"]["value"] == 303


@pytest.mark.parametrize("mutate", [
    lambda s: s["reference_rows"][0].update(metadata_links=[1]),
    lambda s: s["reference_rows"][1].update(metadata_links=[0]),
    lambda s: s["reference_rows"][0].update(metadata_links=[]),
    lambda s: s["feature_snapshots"][0]["records"][0]["feature_id"].update(value="not-refA"),
    lambda s: s["genome_snapshots"][0]["records"][0]["genome_id"].update(value="not-g1"),
    lambda s: s["feature_snapshots"][0]["records"][0]["aa_sequence_md5"].update(value="0"*32),
    lambda s: s["joins"]["requested_metadata_links"][0].update(basis="producer_occurrence_mapping"),
    lambda s: s["joins"]["metadata_joins"][0].update(state="unmatched"),
    lambda s: s["sequence_snapshots"][0]["records"][0].update(computed_sha256="0"*64),
])
def test_metadata_links_retain_exact_records_and_do_not_transfer_assignments(mutate):
    saved = metadata_sheet()
    validate("NativeSheet", saved)
    mutate(saved)
    if saved["feature_snapshots"][0]["records"][0]["feature_id"]["value"] == "not-refA":
        saved["feature_snapshots"][0]["records"][0]["patric_id"]["value"] = "not-refA"
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


@pytest.mark.parametrize("presence,lexeme", [("explicit_null", None), ("omitted", None), ("blank", ""), ("invalid", "bad")])
def test_missing_and_invalid_native_cells_are_retained_without_becoming_zero(presence, lexeme):
    saved = sheet()
    native = saved["native_results"][0]["value"]["associations"][0]
    native["percent_identity"].update(presence=presence, value=None, lexeme=lexeme)
    if presence == "invalid":
        native["valid"] = False
        native["diagnostics"].append(diagnostic("native_number_invalid", severity="error", track_key="comp_genome_2", reference_row_ordinal=0, association_key="comp_genome_2/row/0"))
        saved["native_results"][0]["status"] = "partial"
    saved["association_rows"][0][IDENTITY] = deepcopy(native["percent_identity"])
    result = validate("NativeSheet", saved)
    assert result["association_rows"][0][IDENTITY]["presence"] == presence
    assert result["association_rows"][0]["native_subject_endpoint_difference_fraction"]["value"] == .99


def test_unknown_scientific_attachment_is_preserved_and_claimed_report_is_rejected():
    saved = sheet()
    assert validate("NativeSheet", saved)["directional_attachment"]["state"] == "unavailable"
    saved["directional_attachment"]["state"] = "complete_emitted_reports"
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)
    saved["directional_attachment"] = None
    assert validate("NativeSheet", saved)["directional_attachment"] is None


def test_invalid_nonprimary_projection_is_retained_but_not_selected():
    saved = sheet()
    failed = {"status": "invalid", "value": None, "requirements": [], "diagnostics": []}
    saved["native_results"].append(failed)
    assert validate("NativeSheet", saved)["native_results"][-1] == failed
    saved["native_results"][0] = deepcopy(failed)
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


def test_unavailable_occurrence_witness_does_not_erase_native_measurements():
    saved = linked_sheet()
    join = saved["joins"]["reference_joins"][0]
    saved["joins"]["requested_native_links"][0]["basis"] = "producer_occurrence_mapping"
    join.update(state="unmatched", protein=None, accepted_link_indices=[],
                diagnostics=[diagnostic("occurrence_witness_interface_unavailable")])
    saved["reference_rows"][0].update(join_state="unmatched", protein=None,
                                    inventory_sequence_symbol_count=cell(reason="occurrence_witness_interface_unavailable"))
    for row in saved["association_rows"]:
        if row["reference_row_ordinal"] == 0:
            row.update(reference_join_state="unmatched", reference_protein=None)
    result = validate("NativeSheet", saved)
    assert result["association_rows"][0][IDENTITY]["value"] == .875
    assert result["reference_rows"][0]["protein"] is None


def rejected_native_link_sheet():
    saved = linked_sheet()
    link = saved["joins"]["requested_native_links"][0]
    link["native"]["sha256"] = "0" * 64
    link["mapping_source_fields"] = [{**saved["reference_rows"][0]["native_aa_length"]["source_field"], "sha256": "0" * 64}]
    join = saved["joins"]["reference_joins"][0]
    join.update(state="conflicting", protein=None, accepted_link_indices=[], diagnostics=[diagnostic("identifier_mapping_conflict")])
    saved["reference_rows"][0].update(join_state="conflicting", protein=None,
        inventory_sequence_symbol_count=cell(reason="row_join_conflict"))
    for row in saved["association_rows"]:
        if row["reference_row_ordinal"] == 0:
            row.update(reference_join_state="conflicting", reference_protein=None)
    return saved


def test_wrong_digest_requested_link_survives_as_local_rejection():
    saved = rejected_native_link_sheet()
    result = validate("NativeSheet", saved)
    assert result["joins"]["requested_native_links"][0]["native"]["sha256"] == "0" * 64
    assert result["joins"]["reference_joins"][0]["protein"] is None
    assert result["association_rows"][0][IDENTITY]["value"] == .875
    assert result["reference_rows"][1]["join_state"] == "joined"
    assert validate("NativeJoins", saved["joins"]) == saved["joins"]


def test_raw_claim_pointer_still_must_obey_contract():
    saved = rejected_native_link_sheet()
    saved["joins"]["requested_native_links"][0]["mapping_source_fields"][0]["pointer"] = "/bad~escape"
    with pytest.raises(ProteomeDataError) as error:
        validate("NativeSheet", saved)
    assert error.value.code == "proteome_sheet_source_pointer_invalid"


def test_diagnostic_fields_are_actual_sources_not_rejected_digest_assertions():
    saved = rejected_native_link_sheet()
    saved["joins"]["reference_joins"][0]["diagnostics"][0]["source_fields"] = deepcopy(
        saved["joins"]["requested_native_links"][0]["mapping_source_fields"])
    with pytest.raises(ProteomeDataError) as error:
        validate("NativeSheet", saved)
    assert error.value.code == "proteome_sheet_source_digest_conflict"


def test_rejected_metadata_claim_can_retain_wrong_source_locator():
    saved = metadata_sheet()
    link = saved["joins"]["requested_metadata_links"][0]
    link["feature"]["row_ordinal"] = 999
    link["mapping_source_fields"] = [{**saved["reference_rows"][0]["native_aa_length"]["source_field"], "sha256": "0" * 64}]
    saved["joins"]["metadata_joins"][0].update(state="unmatched", feature=None, genome=None, feature_sequence=None,
        diagnostics=[diagnostic("metadata_join_missing")])
    saved["reference_rows"][0]["metadata_links"] = []
    result = validate("NativeSheet", saved)
    assert result["joins"]["requested_metadata_links"][0]["feature"]["row_ordinal"] == 999
    assert result["reference_rows"][0]["join_state"] == "joined"


def test_rejected_execution_claim_can_retain_wrong_source_locator():
    saved = linked_sheet()
    link = saved["joins"]["execution_links"][0]
    link.update(relation="exact_executed_fasta", executed_fasta={**saved["inventories"][0]["source"]["content"], "sha256": "0" * 64},
                witness_source_fields=[{**saved["inventories"][0]["records"][0]["source_field"], "sha256": "0" * 64}])
    saved["joins"]["track_bindings"][0].update(inventory_key=None, execution_relation="unknown", membership_complete="unknown",
        input_record_count=cell(reason="input_binding_conflict"))
    saved["tracks"][0]["inventory_key"] = None
    saved["tracks"][0]["input_record_count"] = deepcopy(saved["joins"]["track_bindings"][0]["input_record_count"])
    for join in saved["joins"]["reference_joins"]:
        join.update(state="not_supplied", protein=None, candidates=[], accepted_link_indices=[])
    for row in saved["reference_rows"]:
        row.update(join_state="not_supplied", protein=None,
                   inventory_sequence_symbol_count=cell(reason="row_join_missing"))
    for row in saved["association_rows"]:
        row.update(reference_join_state="not_supplied", reference_protein=None)
    result = validate("NativeSheet", saved)
    assert result["joins"]["execution_links"][0]["executed_fasta"]["sha256"] == "0" * 64
    assert result["tracks"][0]["inventory_key"] is None
    assert result["tracks"][0]["input_record_count"]["value"] is None
    assert result["association_rows"][0][IDENTITY]["value"] == .875


@pytest.mark.parametrize("relation", ["original_supplied_fasta", "exact_executed_fasta"])
@pytest.mark.parametrize("field,value", [("sha256", "0" * 64), ("byte_count", 999)])
def test_admitted_inventory_cannot_contradict_supplied_content_binding(relation, field, value):
    saved = linked_sheet()
    link = saved["joins"]["execution_links"][0]
    link.update(relation=relation, executed_fasta=deepcopy(saved["inventories"][0]["source"]["content"]))
    if relation == "exact_executed_fasta":
        binding = saved["joins"]["track_bindings"][0]
        binding.update(execution_relation="unknown", input_record_count=cell(reason="execution_witness_interface_unavailable"))
        saved["tracks"][0]["input_record_count"] = deepcopy(binding["input_record_count"])
    validate("NativeSheet", saved)
    link["executed_fasta"][field] = value
    with pytest.raises(ProteomeDataError) as error:
        validate("NativeSheet", saved)
    assert error.value.code == "proteome_sheet_execution_content_conflict"


def test_duplicate_identifiers_cannot_be_resolved_by_picking_first_record():
    saved = linked_sheet()
    inv = saved["inventories"][0]
    inv["records"][1].update(header="refA", identifier="refA")
    inv["duplicate_identifier_groups"] = [{"identifier": "refA", "record_ordinals": [0, 1]}]
    with pytest.raises(ProteomeDataError) as error:
        validate("NativeSheet", saved)
    assert error.value.code == "proteome_sheet_identifier_occurrence_ambiguous"


def test_cross_input_identifier_collisions_cannot_be_hidden():
    saved = linked_sheet()
    binding = saved["joins"]["track_bindings"][1]
    binding.update(inventory_key="ref-input", execution_relation="original_supplied_fasta")
    link = deepcopy(saved["joins"]["execution_links"][0])
    link["input_key"] = binding["input_key"]
    saved["joins"]["execution_links"].append(link)
    saved["tracks"][1]["inventory_key"] = "ref-input"
    with pytest.raises(ProteomeDataError) as error:
        validate("NativeSheet", saved)
    assert error.value.code == "proteome_sheet_identifier_collision_population_conflict"
    for b in (saved["joins"]["track_bindings"][0], binding):
        b["identifier_collisions"] = ["refA", "refB"]
    with pytest.raises(ProteomeDataError) as error:
        validate("NativeSheet", saved)
    assert error.value.code == "proteome_sheet_identifier_occurrence_ambiguous"


def tsv_sheet():
    saved = sheet()
    original = ROOT / "verification/tool_graders_bvbrc_proteome_native_2026-10-25/SYNTHETIC_PROJECTIONS_001.json"
    result = json.loads(original.read_text())[1]["result"]
    primary = result["value"]
    saved["native_results"] = [result]
    saved["primary_source_ref"] = primary["source"]["content"]["source_ref"]
    tracks = {row["track_key"]: row for row in primary["tracks"]}
    for row in saved["tracks"]:
        row["native_source_fields"] = deepcopy(tracks[row["track_key"]]["source_fields"])
        row["native_materialization"] = tracks[row["track_key"]]["materialization"]
    for row, native in zip(saved["reference_rows"], primary["reference_rows"]):
        for dest, src in (("native_aa_length", "aa_length"), ("native_start", "start"), ("native_end", "end"), ("native_strand", "strand")):
            row[dest] = deepcopy(native[src])
    for row, native in zip(saved["association_rows"], primary["associations"]):
        for dest, src in ((IDENTITY, "percent_identity"), ("native_subject_endpoint_difference_fraction", "seq_coverage"),
                          ("native_hit_category", "hit"), ("native_subject_length_aa", "aa_length")):
            row[dest] = deepcopy(native[src])
    return saved


def test_wrong_width_table_cells_survive_only_with_uncertain_positional_meaning():
    saved = tsv_sheet()
    validate("NativeSheet", saved)
    ref = saved["native_results"][0]["value"]["reference_rows"][0]
    ref["valid"] = False
    ref["diagnostics"].append(diagnostic("native_table_width_invalid", severity="error", track_key="ref_genome", reference_row_ordinal=0))
    saved["native_results"][0]["status"] = "partial"
    with pytest.raises(ProteomeDataError) as error:
        validate("NativeSheet", saved)
    assert error.value.code == "proteome_sheet_table_layout_claim_conflict"
    for row in saved["association_rows"]:
        if row["reference_row_ordinal"] == 0:
            row["layout_state"] = "uncertain_table_layout"
    assert validate("NativeSheet", saved)["association_rows"][0][IDENTITY]["value"] == .875


def represented_sheet():
    saved = sheet()
    alternate = tsv_sheet()["native_results"][0]
    saved["native_results"].append(alternate)
    saved["representation_comparisons"] = [{"link": {
        "left_source_ref": saved["primary_source_ref"], "right_source_ref": alternate["value"]["source"]["content"]["source_ref"],
        "relation": "alternate_full_projection", "reference_pairs": [{"left_row_ordinal": i, "right_row_ordinal": i} for i in range(2)],
        "association_pairs": [{"left_association_key": row["association_key"], "right_association_key": row["association_key"]} for row in saved["association_rows"]],
        "source_fields": []}, "state": "equal_observed_cells", "conflict_source_fields": [], "diagnostics": []}]
    return saved


def test_alternate_representations_validate_declared_pairs_and_conflicts_only():
    saved = represented_sheet()
    assert validate("NativeSheet", saved) == saved
    other = saved["native_results"][1]["value"]["associations"][0]["percent_identity"]
    other.update(value=.9, lexeme=".900")
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)
    comparison = saved["representation_comparisons"][0]
    comparison.update(state="conflicting", conflict_source_fields=[saved["association_rows"][0][IDENTITY]["source_field"], other["source_field"]])
    assert validate("NativeSheet", saved)["association_rows"][0][IDENTITY]["value"] == .875
    comparison["link"]["association_pairs"][0]["right_association_key"] = "comp_genome_4/row/0"
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


def test_incomplete_explicit_representation_map_cannot_claim_full_equality():
    saved = represented_sheet()
    comparison = saved["representation_comparisons"][0]
    comparison["link"]["association_pairs"].pop()
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)
    comparison["state"] = "incomplete_comparison"
    assert validate("NativeSheet", saved)["representation_comparisons"][0]["state"] == "incomplete_comparison"


@pytest.mark.parametrize("kind", ["reference", "association", "track", "source"])
def test_wrong_representation_target_is_local_unbound_claim(kind):
    saved = represented_sheet()
    comparison = saved["representation_comparisons"][0]
    link = comparison["link"]
    if kind == "reference":
        link["reference_pairs"][0]["right_row_ordinal"] = 999
    elif kind == "association":
        link["association_pairs"][0]["right_association_key"] = "comp_genome_2/row/999"
    elif kind == "track":
        link["association_pairs"] = [{"left_association_key": "comp_genome_2/row/0", "right_association_key": "comp_genome_4/row/0"}]
    else:
        link["right_source_ref"] = "missing-supplied-source"
    comparison.update(state="unbound", diagnostics=[diagnostic("representation_correspondence_missing")])
    result = validate("NativeSheet", saved)
    assert result["association_rows"][0][IDENTITY]["value"] == .875
    assert result["representation_comparisons"][0]["link"] == link
    comparison["diagnostics"] = []
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


def test_valid_observed_conflict_remains_visible_beside_bad_representation_target():
    saved = represented_sheet()
    comparison = saved["representation_comparisons"][0]
    # The first reference mapping is unusable. The independent second row's
    # explicit association mapping still contains an observed disagreement.
    comparison["link"]["reference_pairs"][0]["right_row_ordinal"] = 999
    changed = saved["native_results"][1]["value"]["associations"][2]["percent_identity"]
    changed.update(value=.9, lexeme=".900")
    comparison.update(state="conflicting", diagnostics=[diagnostic("representation_correspondence_missing")],
        conflict_source_fields=[deepcopy(saved["association_rows"][2][IDENTITY]["source_field"]), deepcopy(changed["source_field"])])
    result = validate("NativeSheet", saved)
    assert result["representation_comparisons"][0]["state"] == "conflicting"
    assert result["association_rows"][2][IDENTITY]["value"] == .875
    comparison.update(state="unbound", conflict_source_fields=[])
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


def test_duplicate_representation_maps_remain_invalid_even_for_missing_sources():
    saved = represented_sheet()
    comparison = saved["representation_comparisons"][0]
    comparison["link"]["right_source_ref"] = "missing"
    comparison["link"]["reference_pairs"].append(deepcopy(comparison["link"]["reference_pairs"][0]))
    comparison.update(state="unbound", diagnostics=[diagnostic("representation_correspondence_missing")])
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


def test_empty_source_only_representation_link_does_not_establish_equality():
    saved = sheet()
    primary = saved["native_results"][0]["value"]
    primary.update(reference_rows=[], associations=[], physical_record_count=0)
    saved.update(reference_rows=[], association_rows=[])
    for track, copied in zip(primary["tracks"], saved["tracks"]):
        track["source_fields"] = track["source_fields"][:1]
        if track["track_key"] != "ref_genome":
            track["materialization"] = "unknown"
        copied["native_source_fields"] = deepcopy(track["source_fields"])
        copied["native_materialization"] = track["materialization"]
    alternate = deepcopy(saved["native_results"][0])
    alternate["value"]["source"]["content"].update(source_ref="synthetic-empty-alternate", sha256="1"*64)
    for track in alternate["value"]["tracks"]:
        for item in track["source_fields"]:
            item.update(source_ref="synthetic-empty-alternate", sha256="1"*64)
    saved["native_results"].append(alternate)
    comparison = {"link": {"left_source_ref": saved["primary_source_ref"], "right_source_ref": "synthetic-empty-alternate",
        "relation": "alternate_full_projection", "reference_pairs": [], "association_pairs": [], "source_fields": []},
        "state": "incomplete_comparison", "conflict_source_fields": [], "diagnostics": []}
    saved["representation_comparisons"] = [comparison]
    result = validate("NativeSheet", saved)
    assert result["native_results"][0]["value"]["physical_record_count"] == 0
    assert result["representation_comparisons"][0]["state"] == "incomplete_comparison"
    comparison["state"] = "equal_observed_cells"
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)


def test_standalone_joins_validate_only_present_relationships_and_detach():
    joins = linked_sheet()["joins"]
    value = validate("NativeJoinsResult", {"status": "partial", "value": joins, "requirements": [], "diagnostics": joins["diagnostics"]})
    value["value"]["requested_native_links"][0]["native_identifier"] = "changed"
    assert joins["requested_native_links"][0]["native_identifier"] == "refA"
    # There is no inventory in standalone NativeJoins. The contextual sheet
    # check establishes the bounds; standalone validation cannot claim it did.
    joins["reference_joins"][0]["accepted_link_indices"] = [999]
    with pytest.raises(ProteomeDataError):
        validate("NativeJoins", joins)


@pytest.mark.parametrize("mutate", [
    lambda c: c["tracks"].append(deepcopy(c["tracks"][0])),
    lambda c: c["associations"].append(deepcopy(c["associations"][0])),
    lambda c: c["associations"][0].update(track_key="comp_genome_4"),
    lambda c: c["associations"][0]["first_hsp_alignment_identity_percent"]["source_fields"][0].update(field_name="wrong"),
    lambda c: c["associations"][0]["first_hsp_alignment_identity_percent"].update(value=None),
    lambda c: c["associations"][0].update(selection="fail"),
    lambda c: c["tracks"][0]["source_association_record_count"].update(value=2),
    lambda c: c["tracks"][0]["selection_counts"]["pass"].update(value=2),
    lambda c: c["tracks"][0]["native_bi_count"].update(value=2),
    lambda c: c["tracks"][0]["first_hsp_identity_summary"]["used_association_keys"].append("comp_genome_4/row/0"),
    lambda c: c["tracks"][0]["first_hsp_identity_summary"]["value_count"].update(value=2),
    lambda c: c["tracks"][0]["first_hsp_identity_summary"]["sum"]["source_fields"].clear(),
    lambda c: c["tracks"][0]["first_hsp_identity_summary"]["mean"].update(state="missing_input", value=None, reason_codes=["no_eligible_values"]),
    lambda c: c["tracks"][0]["reference_input_record_count"].update(state="value", value=3),
    lambda c: c["tracks"][0]["observed_reference_fraction"]["fraction"].update(state="value", value=0),
    lambda c: c.update(sheet_sha256="wrong"),
])
def test_component_saved_population_source_and_state_invariants(mutate):
    saved = components()
    mutate(saved)
    with pytest.raises(ProteomeDataError):
        validate("NativeComponents", saved)


def test_validation_does_not_recalculate_saved_means_or_claim_absent_sheet_digest_verification():
    saved = components()
    saved["tracks"][0]["first_hsp_identity_summary"]["mean"]["value"] = .123
    saved["sheet_sha256"] = "1" * 64
    assert validate("NativeComponents", saved) == saved
    # Formula correctness and actual input-sheet digest are B4's responsibilities.


def test_each_retained_part_is_validated_once_without_parser_calculator_or_io(monkeypatch):
    from gene_annotation_episode import bvbrc_proteome_native, bvbrc_proteome_inputs, bvbrc_proteome_calculators
    saved = metadata_sheet()
    expected = components()
    validate("NativeSheet", saved)  # Warm static packaged schema caches.
    calls = []
    native_validator, input_validator = contracts.validate_native_projection, contracts.validate_proteome_data

    def native_spy(value):
        calls.append("NativeProjection")
        return native_validator(value)

    def input_spy(name, value):
        calls.append(name)
        return input_validator(name, value)

    def forbidden(*args, **kwargs):
        raise AssertionError("saved-data validation performed acquisition or scientific work")

    with monkeypatch.context() as guard:
        guard.setattr(contracts, "validate_native_projection", native_spy)
        guard.setattr(contracts, "validate_proteome_data", input_spy)
        guard.setattr(Path, "read_bytes", forbidden)
        guard.setattr(Path, "read_text", forbidden)
        guard.setattr("builtins.open", forbidden)
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(subprocess, "run", forbidden)
        guard.setattr(subprocess, "Popen", forbidden)
        guard.setattr(bvbrc_proteome_native, "parse_genome_comparison", forbidden)
        guard.setattr(bvbrc_proteome_calculators, "calculate_native_components", forbidden)
        for name in bvbrc_proteome_inputs.__all__:
            guard.setattr(bvbrc_proteome_inputs, name, forbidden)
        assert validate("NativeSheet", saved) == saved
        assert validate("NativeComponents", expected) == expected
    assert calls == ["NativeProjection", "InputIndex", "ProteinInventory", "FeatureSnapshot", "GenomeSnapshot", "FeatureSequenceSnapshot"]


@pytest.mark.parametrize("kind", ["cycle", "unicode", "tuple", "nonstring_key", "boolean_count"])
def test_malformed_plain_data_uses_fixed_error_boundary(kind):
    saved = sheet()
    if kind == "cycle":
        saved["diagnostics"].append(saved)
    elif kind == "unicode":
        saved["primary_source_ref"] = "\ud800"
    elif kind == "tuple":
        saved["inventories"] = ()
    elif kind == "nonstring_key":
        saved[1] = "bad"
    else:
        saved["tracks"][0]["input_record_count"] = cell(True)
    with pytest.raises(ProteomeDataError):
        validate("NativeSheet", saved)
