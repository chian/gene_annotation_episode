"""Typed-record audit policy using labeled synthetic facts, not receipt proof.

The connected Workflow/retained real-form tests in410 supply real authority.
These tests isolate which internal paths may contain an audit identity and
verify that none receives a model-input exemption.
"""
from copy import deepcopy

import pytest

from method_loop.communication import ParentModelInputError, ParentReport
from method_loop.episode import _model_inputs
from gene_annotation_episode.communication import ReportBoundaryError, form_with_facts
from gene_annotation_episode.protein_structure_result_views import protein_structure_fact_sources
from gene_annotation_episode.runtime import TypedReportContract
from test_protein_structure_form_boundary import native_facts, form, object_form, FIELDS


def validator_for(expected):
    expected = deepcopy(expected)
    def validate(actual):
        if actual != expected:
            raise ReportBoundaryError("Changed recorded fixture", code="recorded_fact_mismatch")
    return validate


def custody_ids(payload):
    custody = payload["the_comparison"][0]["custody"]
    return tuple(custody[key] for key in ("run_id", "result_episode_id", "result_operation_key"))


def contract(schema, expected, *, semantic=True):
    return TypedReportContract("Return selected protein measurements", schema, None,
        validator_for(expected) if semantic else None)


def test_verified_internal_custody_roundtrips_without_mutating_form(native_facts):
    schema, payload = form(native_facts)
    original = deepcopy(payload)
    admitted = contract(schema, payload).admit(payload, audit_identifiers=custody_ids(payload))
    assert admitted.as_record() == original and payload == original
    admitted.exclude_audit_identifiers(custody_ids(payload))  # Redelivery uses this same method.
    assert admitted.as_record() == original
    with pytest.raises(ValueError):
        ParentReport.exclude_audit_identifiers(admitted, custody_ids(payload))


@pytest.mark.parametrize("source", list(FIELDS.values()))
def test_each_exact_registered_source_permits_only_its_internal_custody(native_facts, source):
    facts = deepcopy(native_facts)
    if source.endswith("failures"):
        facts[source][0]["custody"] = deepcopy(facts["execution_protein_structure_projections"][0]["custody"])
    node = {**protein_structure_fact_sources()[source]["report_schema"], "x-source": source}
    schema = object_form({"requested": node})
    payload = form_with_facts({}, schema, facts)
    audit = payload["requested"][0]["custody"]["result_episode_id"]
    assert contract(schema, payload).admit(payload, audit_identifiers=(audit,)).as_record() == payload


def test_shape_validation_alone_does_not_exempt_custody(native_facts):
    schema, payload = form(native_facts)
    with pytest.raises(ReportBoundaryError) as error:
        contract(schema, payload, semantic=False).admit(payload, audit_identifiers=custody_ids(payload))
    assert error.value.diagnostic["code"] == "audit_identity"


def test_semantic_rejection_precedes_internal_custody_admission(native_facts):
    schema, payload = form(native_facts)
    typed = contract(schema, payload)
    changed = deepcopy(payload)
    changed["reuse_later"][0]["allowed_uses"] = ["select_projection"]
    with pytest.raises(ReportBoundaryError) as error:
        typed.admit(changed, audit_identifiers=custody_ids(payload))
    assert error.value.diagnostic["code"] == "recorded_fact_mismatch"


@pytest.mark.parametrize("where", ["interpretation", "parent_field", "projection_name"])
def test_audit_id_outside_exact_custody_paths_remains_forbidden(native_facts, where):
    schema, payload = form(native_facts)
    audit = payload["the_comparison"][0]["custody"]["result_episode_id"]
    if where == "interpretation":
        schema["properties"]["interpretation"] = {"type": "string", "enum": [audit]}
        schema["required"].append("interpretation")
        payload["interpretation"] = audit
    elif where == "parent_field":
        schema["properties"][audit] = {"type": "boolean"}
        schema["required"].append(audit)
        payload[audit] = True
    else:
        payload["unavailable"][0]["projection_id"] = audit
    with pytest.raises(ReportBoundaryError) as error:
        contract(schema, payload).admit(payload, audit_identifiers=(audit,))
    assert error.value.diagnostic["code"] == "audit_identity"


@pytest.mark.parametrize("container", ["custody", "raw_report", "prose"])
def test_actual_model_inputs_cannot_contain_internal_custody(native_facts, container):
    schema, payload = form(native_facts)
    identifiers = custody_ids(payload)
    admitted = contract(schema, payload).admit(payload, audit_identifiers=identifiers)
    inputs = {"custody": payload["the_comparison"][0]["custody"]} if container == "custody" else (
        {"raw_report": payload} if container == "raw_report" else {"text": "tracked child " + identifiers[1]})
    with pytest.raises(ParentModelInputError):
        admitted.validate_model_inputs(inputs)
    with pytest.raises(ParentModelInputError):
        _model_inputs(inputs, (admitted,), (admitted,))
    scientific_text = {"text": "Requested RMSD: 2.0 angstrom; one evaluated residue pair."}
    admitted.validate_model_inputs(scientific_text)
    # Existing method_loop carries selected typed reports separately from
    # declared model inputs; the domain renderer must still select their text.
    intermediate = _model_inputs(scientific_text, (admitted,), (admitted,))
    assert intermediate["child_reports"] == [payload]


def test_redelivery_rechecks_other_fields_against_new_audit_identities(native_facts):
    schema, payload = form(native_facts)
    admitted = contract(schema, payload).admit(payload, audit_identifiers=custody_ids(payload))
    with pytest.raises(ValueError, match="child audit identity"):
        admitted.exclude_audit_identifiers((payload["unavailable"][0]["projection_id"],))


@pytest.mark.parametrize("semantic", [False, True])
def test_ordinary_reports_keep_generic_audit_boundary(semantic):
    schema = object_form({"value": {"type": "string", "enum": ["ordinary-child-id", "allowed"]}})
    expected = {"value": "ordinary-child-id"}
    with pytest.raises(ReportBoundaryError) as error:
        contract(schema, expected, semantic=semantic).admit(expected, audit_identifiers=("ordinary-child-id",))
    assert error.value.diagnostic["code"] == "audit_identity"
    expected = {"value": "allowed"}
    admitted = contract(schema, expected, semantic=semantic).admit(expected, audit_identifiers=("ordinary-child-id",))
    assert type(admitted) is ParentReport
