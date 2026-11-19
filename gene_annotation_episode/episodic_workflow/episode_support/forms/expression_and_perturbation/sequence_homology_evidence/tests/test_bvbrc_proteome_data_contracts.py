"""Saved-data integrity, not native execution or source-custody verification."""
import hashlib

import pytest

from gene_annotation_episode.episodic_workflow.episode_support.forms.expression_and_perturbation.sequence_homology_evidence.bvbrc_proteome_data_contracts import ProteomeDataError, proteome_data_schema, validate_proteome_data


def field(pointer, ordinal=None, name=None):
    return {"source_ref": "supplied-test", "sha256": hashlib.sha256(b"synthetic supplied bytes").hexdigest(),
            "pointer": pointer, "row_ordinal": ordinal, "field_name": name}


def string(value, pointer, ordinal=0, name=None):
    return {"value": value, "presence": "omitted" if value is None else "blank" if value == "" else "value",
            "source_field": field(pointer, ordinal, name)}


def number(value, pointer, ordinal=0, name=None):
    return {"value": value, "presence": "omitted" if value is None else "value",
            "lexeme": None if value is None else str(value), "source_field": field(pointer, ordinal, name)}


def metadata(name, supplied):
    schema = proteome_data_schema(name)["$defs"][name]
    row = {"row_ordinal": 0, "source_field": field("/0", 0), "valid": True, "diagnostics": []}
    for key, shape in schema["properties"].items():
        if shape.get("$ref") == "#/$defs/NativeString":
            row[key] = string(supplied.get(key), "/0/" + key, name=key)
        elif shape.get("$ref") == "#/$defs/NativeNumber":
            row[key] = number(supplied.get(key), "/0/" + key, name=key)
    if name == "FeatureSequenceRecord":
        row["molecule"] = "aa"
        raw = supplied["sequence"].upper().encode()
        row.update(sequence_symbol_count=len(raw), computed_sha256=hashlib.sha256(raw).hexdigest(),
                   computed_md5=hashlib.md5(raw).hexdigest())
    return row


def snapshot(name, row, convention="unknown"):
    formats = {"FeatureSnapshot": "bvbrc_genome_feature_json_array_v1",
               "GenomeSnapshot": "bvbrc_genome_json_array_v1",
               "FeatureSequenceSnapshot": "bvbrc_feature_sequence_json_array_v1"}
    value = {"version": "bvbrc_proteome_metadata_proposal_v1", "snapshot_key": "supplied-metadata",
             "format": formats[name], "source": {"content": {"source_ref": "supplied-test",
                 "artifact_field": "artifact_ref", "artifact_ref": "synthetic-artifact",
                 "sha256": field("")["sha256"], "byte_count": 24},
                 "body_complete": True, "object_complete": "yes"},
             "population": {"origin": "supplied_snapshot", "query_source": None, "selected_fields": [],
                 "offset": None, "requested_limit": None, "reported_total_count": None,
                 "population_complete": "unknown", "completeness_evidence": []},
             "records": [row], "unsupported_field_paths": [], "diagnostics": []}
    if name == "FeatureSnapshot":
        value["coordinate_convention"] = {"value": convention,
            "source_fields": [] if convention == "unknown" else [field("/coordinate-declaration")]}
    return value


def input_index():
    schema = proteome_data_schema("SourceContract")["$defs"]["SourceContract"]["properties"]
    contract = {key: definition["const"] for key, definition in schema.items() if "const" in definition}
    contract.update(deployment_match="unobserved", deployment_evidence=[])
    parent = field("/submitted")
    value = {"version": "bvbrc_proteome_input_index_proposal_v1",
             "parameter_source": {"kind": "submitted", "source_field": parent},
             "reference_original_index": 3, "inputs": [], "source_contract": contract,
             "run_parameter_snapshots": [], "diagnostics": []}
    for index, (kind, pointer, text, track) in enumerate([
            ("genome_id", "/genome_ids/0", "G1", "comp_genome_1"),
            ("genome_id", "/genome_ids/1", "G2", "comp_genome_2"),
            ("user_genome", "/user_genomes/0", "/files/F1", "ref_genome"),
            ("user_feature_group", "/user_feature_groups/0", "/groups/FG1", "comp_genome_3")], 1):
        value["inputs"].append({"input_key": pointer, "parameter_pointer": pointer,
            "original_index": index, "kind": kind, "value": text, "expected_track_key": track,
            "source_field": field("/submitted" + pointer)})
    parameters = {"kind": "submitted", "source_field": parent}
    for key in ("min_ident", "min_seq_cov", "min_positives", "max_e_val"):
        parameters[key] = {"value": 0 if key == "min_ident" else None,
            "presence": "value" if key == "min_ident" else "omitted",
            "source_field": field("/submitted/" + key, name=key)}
    value["run_parameter_snapshots"] = [parameters]
    return value


def change(value, path, replacement):
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement


@pytest.mark.parametrize("supplied", [{"feature_id": "feature:1"}, {"patric_id": "fig|1.1.peg.1"},
                                      {"feature_id": "feature:1", "aa_length": 0, "start": -2}])
def test_feature_identities_are_optional_alternatives_and_unknown_coordinates_preserved(supplied):
    row = metadata("FeatureRecord", supplied)
    assert validate_proteome_data("FeatureRecord", row) == row


@pytest.mark.parametrize("name,supplied", [
    ("FeatureRecord", {"product": "an assignment"}),
    ("FeatureRecord", {"feature_id": "   "}),
    ("FeatureRecord", {"feature_id": "x", "aa_length": -1}),
    ("FeatureRecord", {"feature_id": "x", "aa_sequence_md5": "not-a-digest"}),
    ("GenomeRecord", {"genome_id": "g", "taxon_id": 0}),
    ("GenomeRecord", {"genome_id": "g", "taxon_id": 562.5}),
])
def test_invalid_metadata_cannot_be_marked_valid(name, supplied):
    row = metadata(name, supplied)
    with pytest.raises(ProteomeDataError, match="metadata_validity_conflict"):
        validate_proteome_data(name, row)
    row["valid"] = False
    assert validate_proteome_data(name, row) == row


def test_feature_coordinates_have_explicit_convention_without_inferred_order():
    row = metadata("FeatureRecord", {"feature_id": "x", "start": 8, "end": 2})
    value = snapshot("FeatureSnapshot", row, "one_based_closed")
    assert validate_proteome_data("FeatureSnapshot", value) == value
    value["coordinate_convention"]["value"] = "zero_based_half_open"
    with pytest.raises(ProteomeDataError, match="metadata_validity_conflict"):
        validate_proteome_data("FeatureSnapshot", value)
    value["records"][0]["valid"] = False
    assert validate_proteome_data("FeatureSnapshot", value) == value


def test_metadata_source_locations_are_bound_to_actual_row_and_column():
    value = snapshot("GenomeSnapshot", metadata("GenomeRecord", {"genome_id": "g", "taxon_id": 562}))
    assert validate_proteome_data("GenomeSnapshot", value) == value
    value["records"][0]["taxon_id"]["source_field"]["pointer"] = "/1/taxon_id"
    with pytest.raises(ProteomeDataError, match="source_location_conflict"):
        validate_proteome_data("GenomeSnapshot", value)


def test_sequence_metadata_preserves_native_md5_case_and_checks_actual_string():
    digest = hashlib.md5(b"ACDE").hexdigest()
    row = metadata("FeatureSequenceRecord", {"md5": digest.upper(), "sequence": "acde"})
    assert validate_proteome_data("FeatureSequenceRecord", row) == row
    row["md5"]["value"] = "0" * 32
    with pytest.raises(ProteomeDataError, match="metadata_validity_conflict"):
        validate_proteome_data("FeatureSequenceRecord", row)
    row["valid"] = False
    assert validate_proteome_data("FeatureSequenceRecord", row)["computed_md5"] == digest


def test_native_lexeme_relationship_and_no_boolean_as_numeric():
    value = number(.875, "/score")
    value["lexeme"] = "8.750E-1"
    assert validate_proteome_data("NativeNumber", value) == value
    value["lexeme"] = ".9"
    with pytest.raises(ProteomeDataError, match="numeric_lexeme_conflict"):
        validate_proteome_data("NativeNumber", value)
    value["value"] = True
    with pytest.raises(ProteomeDataError, match="schema_invalid"):
        validate_proteome_data("NativeNumber", value)


@pytest.mark.parametrize("bad", [float("inf"), float("nan"), float("-inf")])
def test_nonfinite_parameters_rejected(bad):
    value = input_index()
    value["run_parameter_snapshots"][0]["min_ident"]["value"] = bad
    with pytest.raises(ProteomeDataError, match="nonfinite_number"):
        validate_proteome_data("InputIndex", value)


def test_original_input_order_reference_and_zero_parameter_snapshot():
    value = input_index()
    assert validate_proteome_data("InputIndex", value) == value
    assert value["run_parameter_snapshots"][0]["min_ident"]["value"] == 0
    value["inputs"][1]["expected_track_key"] = "comp_genome_1"
    with pytest.raises(ProteomeDataError, match="input_track_conflict"):
        validate_proteome_data("InputIndex", value)


@pytest.mark.parametrize("path,replacement", [
    (("reference_original_index",), 5), (("inputs", 0, "original_index"), 2),
    (("inputs", 1, "input_key"), "/genome_ids/0"),
    (("inputs", 2, "source_field", "pointer"), "/other/user_genomes/0"),
    (("run_parameter_snapshots",), []),
    (("run_parameter_snapshots", 0, "max_e_val", "source_field", "pointer"), "/submitted/min_ident"),
])
def test_original_input_relationship_mutations(path, replacement):
    value = input_index()
    change(value, path, replacement)
    with pytest.raises(ProteomeDataError):
        validate_proteome_data("InputIndex", value)


def test_excessive_nesting_has_a_fixed_contract_failure():
    value = {}
    for _ in range(1400):
        value = {"nested": value}
    with pytest.raises(ProteomeDataError, match="excessive_nesting"):
        validate_proteome_data("NativeSource", value)

