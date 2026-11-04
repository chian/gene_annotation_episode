"""Engineering shape controls; no native data, producer or receipt is claimed."""
from copy import deepcopy
import hashlib
import sqlite3
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import protein_structure_contracts as science
from gene_annotation_episode import protein_structure_result_views as views
from gene_annotation_episode import protein_structure_action_records as actions
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.communication import validate_form, ReportBoundaryError
from gene_annotation_episode.runtime import _references_in


SOURCE = "source_" + "a" * 24


def file(raw, format):
    sha = hashlib.sha256(raw).hexdigest()
    return dict(artifact_ref="artifact_" + sha, sha256=sha, byte_length=len(raw), format=format)


def selection(role="single"):
    return dict(structure_role=role, file_identity=file(b"engineering structure", "pdb_3x_text"),
        data_block=None, model_key=dict(ordinal_0based=0, serial_state="implicit",
            native_serial_token=dict(lexeme=None, text=None, syntax="absent", lexical_state="absent", span=None)),
        chain_key=dict(namespace="pdb", chain_id="A", ter_segment_ordinal_0based=0),
        sequence_basis="observed_polymer", residue_variant_choices=[],
        symbol_policy=dict(unknown="reject", explicit_component_overrides=[]),
        ca_selection=dict(policy="unambiguous_only", choices=[]), zero_occupancy_policy="include",
        bfactor_semantics="unspecified", semantics_evidence=None)


def sequence():
    selected = selection()
    return dict(version="structure_sequence_descriptor_v2",
        custody=dict(version="protein_structure_action_custody_v1", source_ref=SOURCE),
        reference_ref="reference_" + "b" * 24, sequence_file=file(b"ACD", "ascii_protein_sequence_v1"),
        residue_map_file=file(b"engineering map", "protein_structure_sequence_v1"),
        structure_file=deepcopy(selected["file_identity"]), selection=selected, sequence_length=3,
        allowed_uses=["sequence_align", "structure_correspondence"])


def saved():
    return dict(version="protein_structure_saved_sheet_v2",
        custody=dict(version="protein_structure_action_custody_v1", source_ref=SOURCE),
        sheet_file=file(b"engineering sheet", "protein_structure_comparison_sheet_v1"),
        original_components_file=file(b"engineering components", "protein_structure_components_v1"),
        operation="compare_protein_structures", original_mode="fit_then_evaluate_ca",
        allowed_uses=["recalculate", "select_projection", "use_transform"])


def legacy_custody():
    key = dict(run_id="engineering", episode_id="result", operation_key="engineering:result:0")
    return dict(run_id=key["run_id"], result_episode_id=key["episode_id"], result_operation_key=key["operation_key"],
        result_receipt_key="protein_structure_result_receipt:" + digest(key), handoff_ref="source_" + "c" * 24,
        source_ref=SOURCE, bundle_artifact_ref=file(b"engineering bundle", "native_protein_structure_bundle_v1")["artifact_ref"],
        original_request_sha256="d" * 64)


def transform():
    return dict(version="protein_structure_transform_v1", direction="moving_to_fixed",
        convention="row_vector_y_R_plus_t", rotation=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        translation_A=[0.0, 0.0, 0.0], fixed_selection=selection("fixed"), moving_selection=selection("moving"),
        origin="received_fitted", received_from=dict(saved_sheet=saved(),
            components_file=file(b"engineering components", "protein_structure_components_v1"),
            calculation_id="engineering_calculation", calculation_custody=saved()["custody"]))


def rows(*, window=None, delivery="values"):
    descriptor = sequence()
    selected = dict(projection_id="selected_descriptor", family="extracted_sequence",
        members=dict(kind="extracted_sequence", residue_positions=dict(kind="all")),
        fields=["descriptor"], window=window, delivery_kind=delivery)
    return dict(version="protein_structure_projection_rows_v1", projection_id=selected["projection_id"],
        family=selected["family"], selection=selected, coordinate_set=None, requested_count=1,
        matched_count=1, returned_count=1, omitted_count=0, state="complete", issues=[], qualifications=[],
        calculation_id=None, rows=[dict(row_key="sequence_header",
            identity=dict(kind="sequence_header", reference_ref=descriptor["reference_ref"]),
            values=[dict(field="descriptor", value=descriptor, population=None)], issues=[], qualifications=[])])


@pytest.mark.parametrize("kind", ["sequence", "saved"])
def test_action_descriptor_explicit_v2_is_detached_and_keeps_declared_uses(kind):
    value = sequence() if kind == "sequence" else saved()
    validator = science.validate_structure_sequence_descriptor if kind == "sequence" else science.validate_saved_sheet_descriptor
    result = validator(value)
    assert result == value
    result["allowed_uses"].clear()
    assert value["allowed_uses"]
    bad = deepcopy(value)
    bad["version"] = "structure_sequence_descriptor_v1" if kind == "sequence" else "protein_structure_saved_sheet_v1"
    with pytest.raises(ValueError, match="invalid_schema"):
        validator(bad)


@pytest.mark.parametrize("case", ["sequence_missing", "sequence_empty", "sequence_duplicate", "sequence_format",
    "sequence_selection", "saved_missing", "saved_empty", "saved_format"])
def test_action_descriptor_rejects_missing_use_or_inconsistent_files(case):
    is_sequence = case.startswith("sequence")
    value = sequence() if is_sequence else saved()
    if case.endswith("missing"):
        value.pop("allowed_uses")
    elif case.endswith("empty"):
        value["allowed_uses"] = []
    elif case.endswith("duplicate"):
        value["allowed_uses"] *= 2
    elif case.endswith("selection"):
        value["structure_file"] = file(b"other structure", "pdb_3x_text")
    else:
        value["sequence_file" if is_sequence else "sheet_file"]["format"] = "text"
    validator = science.validate_structure_sequence_descriptor if is_sequence else science.validate_saved_sheet_descriptor
    with pytest.raises(ValueError):
        validator(value)


@pytest.mark.parametrize("case", ["v1_descriptor_action_custody", "v2_descriptor_legacy_custody"])
def test_received_transform_cannot_mix_descriptor_and_calculation_custody(case):
    value = transform()
    assert science.validate_declared_transform_record(value) == value
    if case == "v1_descriptor_action_custody":
        value["received_from"]["saved_sheet"].update(version="protein_structure_saved_sheet_v1", custody=legacy_custody())
    else:
        value["received_from"]["calculation_custody"] = legacy_custody()
    with pytest.raises(ValueError, match="invalid_schema"):
        science.validate_declared_transform_record(value)


@pytest.mark.parametrize("case", ["empty_use", "wrong_format", "wrong_selection"])
def test_selected_v2_descriptor_cells_apply_full_relationship_validation(case):
    value = rows()
    assert views.validate_protein_structure_projection_rows(value) == value
    descriptor = value["rows"][0]["values"][0]["value"]
    if case == "empty_use":
        descriptor["allowed_uses"] = []
    elif case == "wrong_format":
        descriptor["sequence_file"]["format"] = "text"
    else:
        descriptor["selection"]["chain_key"]["chain_id"] = "B"
        descriptor["structure_file"] = file(b"different structure", "pdb_3x_text")
    with pytest.raises(ValueError):
        views.validate_protein_structure_projection_rows(value)


def test_same_source_distinct_entire_selections_remain_separate_views():
    first = actions.action_view_from_projection_rows(rows(), source_ref=SOURCE, operation="extract_sequence")
    second = actions.action_view_from_projection_rows(rows(window=dict(offset_0based=0, limit=1)),
        source_ref=SOURCE, operation="extract_sequence")
    assert first["selection"]["projection_id"] == second["selection"]["projection_id"]
    assert actions.merge_protein_structure_action_facts([first], [second, deepcopy(first)],
        fact_source=actions.VIEW_SOURCE) == [first, second]
    conflicting = deepcopy(first)
    conflicting["outcome"]["rows"][0]["qualifications"] = ["observed_sequence_not_full_polymer"]
    with pytest.raises(ValueError):
        actions.merge_protein_structure_action_facts([first, conflicting], fact_source=actions.VIEW_SOURCE)


def test_artifact_action_view_keeps_exact_table_identity_without_numerical_rows():
    value = rows(delivery="artifact")
    value["qualifications"] = ["artifact_descriptor_not_numerical_delivery"]
    table = dict(version="protein_structure_projection_table_v1", rows=value["rows"])
    table_file = file(canonical(table).encode("utf-8"), "protein_structure_projection_table_v1")
    result = actions.action_view_from_projection_rows(value, source_ref=SOURCE, operation="extract_sequence", table_file=table_file)
    assert "rows" not in result["outcome"]
    assert result["outcome"]["delivery"] == dict(kind="artifact", table_file=table_file,
        row_count=1, allowed_use="read_exact_selected_table")
    with pytest.raises(ValueError, match="selected_field_unavailable"):
        actions.action_view_from_projection_rows(value, source_ref=SOURCE, operation="extract_sequence")


@pytest.mark.parametrize("fact_source", actions.FACT_SOURCES)
def test_each_action_fact_schema_is_owned_when_embedded_under_arbitrary_parent_field(fact_source):
    values = {actions.VIEW_SOURCE: [actions.action_view_from_projection_rows(rows(), source_ref=SOURCE, operation="extract_sequence")],
        actions.SEQUENCE_SOURCE: [sequence()], actions.SAVED_SOURCE: [saved()]}
    schema = actions.protein_structure_action_fact_sources()[fact_source]["report_schema"]
    parent = dict(type="object", properties=dict(chosen=schema), required=["chosen"], additionalProperties=False,
        **{"$defs": {"FileIdentity": {"type": "null"}}})
    Draft202012Validator.check_schema(parent)
    assert Draft202012Validator(parent).is_valid(dict(chosen=values[fact_source]))
    assert actions.requested_protein_structure_action_fields(parent, fact_source=fact_source) == ["chosen"]
    assert schema["x-source"] == fact_source and schema["$id"] != schema["allOf"][0]["$id"]
    resource = schema["allOf"][0]
    reachable, pending = set(), [resource["items"]]
    while pending:
        node = pending.pop()
        if type(node) is dict:
            if "$ref" in node:
                name = node["$ref"].removeprefix("#/$defs/")
                if name not in reachable:
                    reachable.add(name)
                    pending.append(resource["$defs"][name])
            pending.extend(node.values())
        elif type(node) is list:
            pending.extend(node)
    assert set(resource["$defs"]) == set(schema["$defs"]) == reachable
    assert resource["$defs"] == schema["$defs"]
    assert not {"ProteinStructureSheet", "ProteinStructureComponents", "ProjectionInput", "ProteinActionResult"} & reachable
    schema["allOf"][0]["$defs"]["FileIdentity"]["additionalProperties"] = True
    with pytest.raises(ValueError):
        actions.requested_protein_structure_action_fields(parent, fact_source=fact_source)


@pytest.mark.parametrize("case", ["absent_table", "empty_table", "unrelated_tool"])
def test_classifier_unmanaged_registry_needs_no_episode_authentication(case, monkeypatch):
    with sqlite3.connect(":memory:") as db:
        db.row_factory = sqlite3.Row
        if case != "absent_table":
            db.execute("CREATE TABLE tool_operations(name TEXT,result TEXT)")
            if case == "unrelated_tool":
                db.execute("INSERT INTO tool_operations VALUES(?,?)", ("sequence.inspect", canonical(dict(result=dict(version="other")))))
        records = actions.ProteinStructureActionRecords(SimpleNamespace(db=db), "engineering")
        def forbidden(*args, **kwargs):
            raise AssertionError("An unrelated registry reached protein authority")
        monkeypatch.setattr(records, "authenticate", forbidden)
        assert records.retained_reference_access(object(), SOURCE, "source") is None


@pytest.mark.parametrize("fact_source", [actions.SEQUENCE_SOURCE, actions.SAVED_SOURCE])
def test_descriptor_only_production_reference_projection_excludes_file_identities(fact_source):
    value = sequence() if fact_source == actions.SEQUENCE_SOURCE else saved()
    schema = dict(type="object", properties=dict(chosen=actions.protein_structure_action_fact_sources()[fact_source]["report_schema"]),
        required=["chosen"], additionalProperties=False)
    form = dict(chosen=[value])
    expected = [SOURCE, value["reference_ref"]] if fact_source == actions.SEQUENCE_SOURCE else [SOURCE]
    records = {SOURCE: dict(id=SOURCE, record_type="source")}
    if fact_source == actions.SEQUENCE_SOURCE:
        records[value["reference_ref"]] = dict(id=value["reference_ref"], record_type="reference")
    # This is the actual generic extractor used by Workflow._receive_form.
    # Owned resources require the existing specialist projection alongside it.
    generic = _references_in({}, records.__getitem__, forms=[(form, schema)])
    assert generic == []
    projected = actions.protein_structure_action_form_references(form, schema)
    assert list(dict.fromkeys([*generic, *projected])) == expected
    assert all(not reference.startswith("artifact_") for reference in projected)
    assert actions.protein_structure_action_form_references(dict(chosen=[]), schema) == []
    bad = deepcopy(form)
    bad["chosen"][0]["allowed_uses"] = []
    with pytest.raises(ValueError):
        actions.protein_structure_action_form_references(bad, schema)


@pytest.mark.parametrize("case", ["sequence_source", "sequence_reference", "saved_source"])
def test_descriptor_source_and_reference_semantics_require_actual_resolver_permission(case):
    fact_source = actions.SEQUENCE_SOURCE if case.startswith("sequence") else actions.SAVED_SOURCE
    value = sequence() if fact_source == actions.SEQUENCE_SOURCE else saved()
    schema = dict(type="object", properties=dict(chosen=actions.protein_structure_action_fact_sources()[fact_source]["report_schema"]),
        required=["chosen"], additionalProperties=False)
    expected = {(SOURCE, "source")}
    if fact_source == actions.SEQUENCE_SOURCE:
        expected.add((value["reference_ref"], "reference"))
    seen = set()
    def resolver(reference, namespace):
        seen.add((reference, namespace))
        return (reference, namespace) in expected
    form = dict(chosen=[value])
    assert validate_form(form, schema, resolver) == form
    assert seen == expected
    denied = (value["reference_ref"], "reference") if case.endswith("reference") else (SOURCE, "source")
    with pytest.raises(ReportBoundaryError) as error:
        validate_form(form, schema, lambda reference, namespace: (reference, namespace) in expected - {denied})
    assert error.value.diagnostic["code"] == "unknown_reference"


def test_private_retained_control_json_read_uses_real_store_bytes_without_writes(tmp_path):
    from gene_annotation_episode.state import Store
    value = dict(version="engineering_private_control_v1",
        selected=dict(count=0, complete=False, unknown=None), values=[1, -2.5, "literal"])
    raw = canonical(value).encode("utf-8")
    with Store(tmp_path / "store") as store:
        reference = store.artifact(raw, "application/json")
        metadata = store.get(reference)
        changes = store.db.total_changes
        result = actions._json_artifact(store, reference)
        assert result == value and result is not value
        assert result["selected"]["count"] == 0 and result["selected"]["complete"] is False
        assert result["selected"]["unknown"] is None
        result["values"].clear()
        assert actions._json_artifact(store, reference) == value
        assert store.get_artifact(reference) == raw and store.get(reference) == metadata
        assert metadata["sha256"] == hashlib.sha256(raw).hexdigest() and metadata["size"] == len(raw)
        assert store.db.total_changes == changes
