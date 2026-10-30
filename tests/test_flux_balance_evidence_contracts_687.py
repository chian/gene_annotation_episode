"""Root007 shared-record checks using explicitly synthetic records only.

The XML audit below describes normalized character data, not lexical XML bytes.
No XML/native model parser, scientific library or optimizer is run by this file.
The separately retained679 example is an old test normalization, not a producer.
"""
from copy import deepcopy
import json
import math
import os
from pathlib import Path

import pytest

from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.flux_balance_contracts import (
    flux_balance_schema, normalize_fba_solver_status, validate_flux_balance_record,
)
from gene_annotation_episode.flux_balance_sheet import validate_flux_balance_sheet
from test_flux_balance_core_679 import make_sheet, number


NEW_KINDS = (
    "FBAXmlName", "FBAXmlPathStep", "FBAXmlAttribute", "FBAXmlNamespace",
    "FBAXmlSourceElement", "FBASourceAudit", "FBASolverOptionApplication", "FBARequestApplication",
)
OPTION_NAMES = ("feasibility_tolerance", "optimality_tolerance", "integrality_tolerance")
SBML = "urn:synthetic687:sbml"
FBC = "urn:synthetic687:fbc"
FORMATS = dict(original_model="sbml", selected_request="flux_balance_selected_request_v1",
    effective_model="cobra_model_capture_v1", effective_problem="cobra_glpk_problem_capture_v1",
    solution="cobra_glpk_solution_capture_v1", flux_csv="biomni_fba_csv_v1", native_log="utf8_text")
FILES = {role: dict(artifact_ref="synthetic687:" + role, sha256=str(i) * 64,
                   size_bytes=i, format=format_name)
         for i, (role, format_name) in enumerate(FORMATS.items(), 1)}


def location(role, pointer):
    return dict(file=deepcopy(FILES[role]), pointer=pointer)


def name(local, namespace=None):
    return dict(namespace_uri=namespace, local_name=local)


def step(local, ordinal=0, namespace=SBML):
    return dict(name=name(local, namespace), sibling_ordinal=ordinal)


def attribute(local, value, namespace=None):
    return dict(name=name(local, namespace), value=value)


def element(index, path, parent, children, *, declarations=(), attributes=(), text=None, tail=None):
    return dict(source_record_index=index, path=deepcopy(path), parent_source_record_index=parent,
        child_source_record_indices=list(children), namespace_declarations=list(declarations),
        attributes=list(attributes), text=text, tail=tail)


def audit():
    root = [step("sbml")]
    model = root + [step("model")]
    parameters = model + [step("listOfParameters")]
    reaction = model + [step("reaction")]
    gpr = reaction + [step("geneProductAssociation", namespace=FBC)]
    conjunction = gpr + [step("and", namespace=FBC)]
    disjunction = conjunction + [step("or", namespace=FBC)]
    notes = root + [step("notes", namespace=None)]
    elements = [
        element(0, root, None, [1, 12], declarations=[dict(prefix="", uri=SBML), dict(prefix="fbc", uri=FBC)], text="\n "),
        element(1, model, 0, [2, 5], attributes=[attribute("id", "synthetic_687")]),
        element(2, parameters, 1, [3, 4]),
        element(3, parameters + [step("parameter")], 2, [],
            attributes=[attribute("id", "LB_IN"), attribute("value", "-10")], tail="\n  "),
        element(4, parameters + [step("parameter", 1)], 2, [],
            attributes=[attribute("id", "UB_IN"), attribute("value", "8")]),
        element(5, reaction, 1, [6], attributes=[attribute("id", "R_IN"),
            attribute("lowerFluxBound", "LB_IN", FBC), attribute("upperFluxBound", "UB_IN", FBC)]),
        element(6, gpr, 5, [7]),
        element(7, conjunction, 6, [8, 9]),
        element(8, conjunction + [step("geneProductRef", namespace=FBC)], 7, [],
            attributes=[attribute("geneProduct", "G_a", FBC)]),
        element(9, disjunction, 7, [10, 11]),
        element(10, disjunction + [step("geneProductRef", namespace=FBC)], 9, [],
            attributes=[attribute("geneProduct", "G_b", FBC)]),
        element(11, disjunction + [step("geneProductRef", 1, FBC)], 9, [],
            attributes=[attribute("geneProduct", "G_c", FBC)]),
        element(12, notes, 0, [13], declarations=[dict(prefix="", uri="")], text="", tail="\n"),
        element(13, notes + [step("item", namespace=None)], 12, [],
            attributes=[attribute("empty", ""), attribute("lang", "en", "http://www.w3.org/XML/1998/namespace")],
            text="A & B\nC", tail=None),
    ]
    return dict(version="cobra_fba_source_audit_v1", input_profile="sbml",
        original_model=location("original_model", ""), xml_elements=elements, issues=[])


def application():
    return dict(version="cobra_fba_request_application_v1",
        selected_request=location("selected_request", "/requested_job"), constraint_changes=[],
        objective_request=dict(kind="model_default", reaction_id=None), objective_application="model_default",
        objective_requested_source=location("selected_request", "/requested_job/native_flux_balance/objective"),
        objective_effective_source=location("effective_problem", "/effective/objective"),
        solver_option_applications=[dict(name=key, application="not_requested",
            requested_source=location("selected_request", "/requested_job/native_flux_balance/solver_options/" + key),
            effective_source=None, issue_code=None) for key in OPTION_NAMES],
        request_realization="exact", issues=[])


def change(index, identifier, state, position=None, code=None):
    def bound(side, value):
        return dict(kind="finite", value=value, native_token=str(value), float_hex=None,
            source=location("selected_request", f"/requested_job/native_flux_balance/constraints/{index}/{side}"))
    return dict(reaction_id=identifier, requested_lower=bound("lower", -10), requested_upper=bound("upper", 8),
        effective_reaction_position=position, application=state, issue_code=code)


def issue(code):
    return dict(code=code, stage="apply", field=None, source_row_index=None, reaction_position=None,
        metabolite_position=None, variable_position=None, constraint_position=None, detail_file=None)


def manifest():
    return dict(version="flux_balance_native_manifest_v1", sealed=True,
        attempt={**{key: "synthetic687" for key in ("run_id", "episode_id", "resource_id", "execution_id", "attempt_id", "operation_key")},
                 "requested_job_sha256": "a" * 64, "assignment_sha256": "b" * 64},
        software_sha256="c" * 64, model_identity={key: FILES["original_model"][key] for key in ("sha256", "size_bytes")},
        actual_distributions=[], actual_solver=dict(interface=None, name=None, version=None, cobra_version=None,
            optlang_version=None, raw_status=None, status="unknown", feasibility_tolerance=number(),
            optimality_tolerance=number(), integrality_tolerance=number(), raw_parameters_file=None,
            diagnostic_file=None, alternate_optimum_claim="not_assessed", alternate_claim_source=None),
        source_function_sha256="d" * 64, effective_problem_sha256=FILES["effective_problem"]["sha256"],
        files=[dict(role=role, relative_path=role + ".fixture", format=file["format"], state="present",
                    identity={key: file[key] for key in ("sha256", "size_bytes")}) for role, file in FILES.items()],
        solve_call_count=1, execution_outcome="completed", request_realization="exact", issues=[])


def old_records():
    sheet = make_sheet()
    models = deepcopy(sheet["models"])
    models.update(input_profile="sbml", loader=dict(name="read_sbml_model", cobra_version="synthetic",
        number_type="float64", id_replacement="cobra_F_REPLACE"))
    model_payload = {key: deepcopy(value) for key, value in models.items() if key != "source"}
    model_payload["version"] = "cobra_model_capture_v1"
    return {"ModelSnapshot": (sheet["models"]["effective"], "native_capture_evidence"),
        "ProblemSnapshot": (sheet["problems"]["effective"], "native_capture_evidence"),
        "SolutionPayload": (sheet["native_solution"]["native"], "native_capture_evidence"),
        "EffectiveModelPayload": (model_payload, "source_audit"),
        "ParsedModelSnapshots": (models, "source_audit"),
        "FBANativeManifest": (manifest(), "request_application")}


@pytest.mark.parametrize("kind", ["ModelSnapshot", "ProblemSnapshot", "SolutionPayload", "EffectiveModelPayload", "ParsedModelSnapshots", "FBANativeManifest"])
def test_six_additions_are_optional_nullable_and_preserve_every_old_required_key(kind):
    record, optional = old_records()[kind]
    before = deepcopy(record)
    checked = validate_flux_balance_record(kind, record)
    assert checked == before and digest(checked) == digest(before)
    assert optional not in checked
    schema = flux_balance_schema(kind)
    assert set(schema["required"]) == set(before)
    assert set(schema["properties"]) == set(before) | {optional}
    for key in before:
        incomplete = deepcopy(before)
        del incomplete[key]
        with pytest.raises(ValueError, match="schema_invalid"):
            validate_flux_balance_record(kind, incomplete)
    with pytest.raises(ValueError, match="schema_invalid"):
        validate_flux_balance_record(kind, {**before, "undeclared_evidence": None})
    nullable = {**record, optional: None}
    assert validate_flux_balance_record(kind, nullable) == nullable
    assert record == before


def test_new_public_shapes_are_closed_required_detached_and_exact():
    tree, applied = audit(), application()
    fixtures = dict(FBAXmlName=name("id"), FBAXmlPathStep=step("sbml"),
        FBAXmlAttribute=attribute("id", ""), FBAXmlNamespace=dict(prefix="", uri=SBML),
        FBAXmlSourceElement=tree["xml_elements"][0], FBASourceAudit=tree,
        FBASolverOptionApplication=applied["solver_option_applications"][0], FBARequestApplication=applied)
    assert tuple(fixtures) == NEW_KINDS
    for kind, record in fixtures.items():
        checked = validate_flux_balance_record(kind, record)
        assert checked == record and checked is not record
        schema = flux_balance_schema(kind)
        assert set(schema["required"]) == set(record) == set(schema["properties"])
        assert schema["additionalProperties"] is False
        for key in record:
            with pytest.raises(ValueError, match="schema_invalid"):
                validate_flux_balance_record(kind, {k: v for k, v in record.items() if k != key})
        with pytest.raises(ValueError, match="schema_invalid"):
            validate_flux_balance_record(kind, {**record, "not_declared": None})
        schema["properties"].clear()
        assert flux_balance_schema(kind)["properties"]


def test_xml_audit_preserves_normalized_character_data_gpr_and_source_references():
    original = audit()
    checked = validate_flux_balance_record("FBASourceAudit", original)
    nodes = checked["xml_elements"]
    assert len(nodes) == 14
    assert nodes[4]["path"][-1]["sibling_ordinal"] == 1
    assert nodes[5]["attributes"][1]["value"] == "LB_IN"
    assert nodes[3]["attributes"][1]["value"] == "-10"
    assert all(attribute["name"]["local_name"] != "units" for attribute in nodes[3]["attributes"])
    assert nodes[7]["child_source_record_indices"] == [8, 9]
    assert nodes[9]["child_source_record_indices"] == [10, 11]
    assert nodes[12]["text"] == "" and nodes[3]["text"] is None
    assert nodes[13]["text"] == "A & B\nC" and nodes[13]["tail"] is None
    assert nodes[13]["attributes"][0]["value"] == ""
    assert nodes[1]["attributes"][0]["name"]["namespace_uri"] is None
    nodes[5]["attributes"][1]["value"] = "changed"
    assert original["xml_elements"][5]["attributes"][1]["value"] == "LB_IN"


@pytest.mark.parametrize("mutation", [
    lambda a: a["xml_elements"][0].update(parent_source_record_index=0),
    lambda a: a["xml_elements"][1].update(parent_source_record_index=None),
    lambda a: a["xml_elements"][2].update(source_record_index=9),
    lambda a: a["xml_elements"][2].update(child_source_record_indices=[4, 3]),
    lambda a: a["xml_elements"][2].update(child_source_record_indices=[3, 3, 4]),
    lambda a: a["xml_elements"][2].update(child_source_record_indices=[3, 99]),
    lambda a: a["xml_elements"][2].update(child_source_record_indices=[3]),
    lambda a: a["xml_elements"][3].update(parent_source_record_index=1),
    lambda a: a["xml_elements"][4]["path"][-1].update(sibling_ordinal=2),
    lambda a: a["xml_elements"][4]["path"][-1].update(sibling_ordinal=0),
    lambda a: a["xml_elements"][4]["path"][1]["name"].update(local_name="different_parent"),
    lambda a: a["xml_elements"][12].update(namespace_declarations=[]),
    lambda a: a["xml_elements"][5]["attributes"].append(attribute("lowerFluxBound", "duplicate", FBC)),
    lambda a: a["xml_elements"][0]["namespace_declarations"].append(dict(prefix="fbc", uri=FBC)),
    lambda a: a["xml_elements"][0].update(namespace_declarations=[dict(prefix="", uri=SBML)]),
    lambda a: a["xml_elements"][5]["attributes"][1]["name"].update(namespace_uri=SBML),
    lambda a: a.update(xml_elements=[]),
    lambda a: a.update(xml_elements=None),
])
def test_malformed_xml_tree_and_namespace_joins_reject(mutation):
    value = audit()
    mutation(value)
    with pytest.raises(ValueError, match="schema_invalid|model_identity_conflict"):
        validate_flux_balance_record("FBASourceAudit", value)


def test_bidirectional_but_nonpreorder_tree_is_rejected():
    value = audit()
    root = [step("sbml")]
    a, b = root + [step("a")], root + [step("b")]
    value["xml_elements"] = [
        element(0, root, None, [1, 2], declarations=[dict(prefix="", uri=SBML)]),
        element(1, a, 0, [3]), element(2, b, 0, []), element(3, a + [step("c")], 1, []),
    ]
    with pytest.raises(ValueError, match="model_identity_conflict:/xml_elements"):
        validate_flux_balance_record("FBASourceAudit", value)


@pytest.mark.parametrize("local", ["", "fbc:reaction", "9reaction", "bad name", "\x00", "a/b"])
def test_expanded_local_names_are_xml_names(local):
    with pytest.raises(ValueError, match="schema_invalid"):
        validate_flux_balance_record("FBAXmlName", name(local))


def test_xml_unicode_names_and_expanded_namespace_are_not_qname_spelling():
    assert validate_flux_balance_record("FBAXmlName", name("模型_α-1", SBML))["local_name"] == "模型_α-1"
    for namespace in ("", 1, True, []):
        with pytest.raises(ValueError, match="schema_invalid"):
            validate_flux_balance_record("FBAXmlName", name("model", namespace))
    for declaration in (dict(prefix="f:bc", uri=FBC), dict(prefix="xmlns", uri=FBC),
                        dict(prefix="xml", uri=FBC), dict(prefix="other", uri="http://www.w3.org/XML/1998/namespace")):
        with pytest.raises(ValueError, match="schema_invalid"):
            validate_flux_balance_record("FBAXmlNamespace", declaration)


def test_audit_whole_original_artifact_profile_and_load_failure_are_distinct():
    value = audit()
    for pointer, format_name in (("/model", "sbml"), ("", "cobra_json")):
        wrong = deepcopy(value)
        wrong["original_model"]["pointer"] = pointer
        wrong["original_model"]["file"]["format"] = format_name
        with pytest.raises(ValueError, match="model_identity_conflict"):
            validate_flux_balance_record("FBASourceAudit", wrong)
    for kind in ("EffectiveModelPayload", "ParsedModelSnapshots"):
        payload = old_records()[kind][0]
        payload.update(loaded_original=None, effective=None, source_audit=value)
        payload["issues"] = [issue("model_load_failed")]
        checked = validate_flux_balance_record(kind, payload)
        assert checked["effective"] is None and len(checked["source_audit"]["xml_elements"]) == 14
        payload.update(input_profile="cobra_json", loader=dict(name="load_json_model", cobra_version="synthetic",
            number_type="float64", id_replacement="none"))
        with pytest.raises(ValueError, match="model_identity_conflict"):
            validate_flux_balance_record(kind, payload)
    value.update(input_profile="cobra_json", xml_elements=None)
    value["original_model"]["file"]["format"] = "cobra_json"
    assert validate_flux_balance_record("FBASourceAudit", value)["xml_elements"] is None
    value["xml_elements"] = []
    with pytest.raises(ValueError, match="model_identity_conflict"):
        validate_flux_balance_record("FBASourceAudit", value)


def test_opaque_native_evidence_never_supplies_file_authority_but_audit_does():
    sheet = make_sheet()
    decoy = dict(artifact_ref="not-retained", sha256="f" * 64, size_bytes=1, format="fake")
    raw = dict(version="explicit-synthetic-observations", file_like=decoy,
        address_like=dict(role=[], pointer={}), raw_getters=dict(value=-0.0, native_token="-0.0"),
        native_passes=[dict(raw_getters=None, exception=dict(message="synthetic exception"))])
    for record in (sheet["models"]["effective"], sheet["problems"]["effective"], sheet["native_solution"]["native"]):
        record["native_capture_evidence"] = deepcopy(raw)
    checked = validate_flux_balance_sheet(sheet)
    assert checked == sheet
    assert math.copysign(1, checked["models"]["effective"]["native_capture_evidence"]["raw_getters"]["value"]) == -1
    checked["models"]["effective"]["native_capture_evidence"]["file_like"]["artifact_ref"] = "changed"
    assert sheet["models"]["effective"]["native_capture_evidence"]["file_like"] == decoy
    sheet["models"].update(input_profile="sbml", source_audit=audit())
    with pytest.raises(ValueError, match="artifact_identity_conflict"):
        validate_flux_balance_sheet(sheet)
    sheet["retained_files"].append(deepcopy(FILES["original_model"]))
    assert validate_flux_balance_sheet(sheet)["models"]["source_audit"] == audit()
    sheet["models"]["source_audit"]["original_model"]["file"]["sha256"] = "e" * 64
    with pytest.raises(ValueError, match="artifact_identity_conflict"):
        validate_flux_balance_sheet(sheet)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), b"bytes", {1: "non-string key"}])
def test_finite_json_still_covers_opaque_evidence(bad):
    for kind in ("ModelSnapshot", "ProblemSnapshot", "SolutionPayload"):
        value = old_records()[kind][0]
        value["native_capture_evidence"] = {"nested": [bad]}
        with pytest.raises(ValueError, match="schema_invalid"):
            validate_flux_balance_record(kind, value)


@pytest.mark.parametrize("bad", [True, -1, 1.0, "1", None])
def test_xml_counts_and_ordinals_do_not_coerce_scalars(bad):
    for field in ("source_record_index", "parent_source_record_index"):
        value = deepcopy(audit()["xml_elements"][1])
        value[field] = bad
        with pytest.raises(ValueError):
            validate_flux_balance_record("FBAXmlSourceElement", value)
    with pytest.raises(ValueError, match="schema_invalid"):
        validate_flux_balance_record("FBAXmlPathStep", {**step("model"), "sibling_ordinal": bad})


def test_known_no_changes_unknown_application_and_applied_readback_remain_distinct():
    value = application()
    assert validate_flux_balance_record("FBARequestApplication", value)["constraint_changes"] == []
    value.update(constraint_changes=None, request_realization="unknown")
    assert validate_flux_balance_record("FBARequestApplication", value)["constraint_changes"] is None
    value["request_realization"] = "exact"
    with pytest.raises(ValueError, match="request_effective_mismatch"):
        validate_flux_balance_record("FBARequestApplication", value)
    value = application()
    value["constraint_changes"] = [change(0, "IN", "applied", 4), change(1, "OUT", "applied", 1)]
    value.update(objective_request=dict(kind="single_reaction", reaction_id="OUT"), objective_application="applied")
    option = value["solver_option_applications"][0]
    option.update(application="applied", effective_source=location("effective_problem", "/configuration_before_solve/feasibility_tolerance"))
    checked = validate_flux_balance_record("FBARequestApplication", value)
    assert [row["effective_reaction_position"] for row in checked["constraint_changes"]] == [4, 1]
    assert checked["request_realization"] == "exact"


@pytest.mark.parametrize("mutation", [
    lambda a: a["selected_request"].update(pointer=""),
    lambda a: a["objective_requested_source"].update(pointer="/requested_job/native_flux_balance/solver_options"),
    lambda a: a["objective_requested_source"]["file"].update(sha256="f" * 64),
    lambda a: a["objective_effective_source"].update(pointer="/loaded_original/objective"),
    lambda a: a.update(objective_effective_source=None),
    lambda a: a.update(objective_application="applied"),
    lambda a: a.update(objective_request=dict(kind="single_reaction", reaction_id="OUT")),
    lambda a: a["solver_option_applications"].reverse(),
    lambda a: a["solver_option_applications"].pop(),
    lambda a: a["solver_option_applications"].append(deepcopy(a["solver_option_applications"][0])),
    lambda a: a["solver_option_applications"][0].update(application="applied"),
    lambda a: a["solver_option_applications"][0].update(application="unknown"),
    lambda a: a["solver_option_applications"][0].update(application="not_attempted"),
    lambda a: a["solver_option_applications"][0]["requested_source"].update(pointer="/requested_job"),
    lambda a: a.update(request_realization="mismatch"),
])
def test_application_sources_order_and_exact_claim_require_local_evidence(mutation):
    value = application()
    mutation(value)
    with pytest.raises(ValueError, match="schema_invalid|artifact_identity_conflict|request_effective_mismatch"):
        validate_flux_balance_record("FBARequestApplication", value)


def test_rejected_unsupported_optimality_and_partial_setter_progress_are_retained():
    value = application()
    option = value["solver_option_applications"][1]
    option.update(application="rejected", issue_code="solver_option_unsupported")
    value["request_realization"] = "mismatch"
    assert validate_flux_balance_record("FBARequestApplication", value)["solver_option_applications"][1] == option
    value["request_realization"] = "unknown"
    with pytest.raises(ValueError, match="request_effective_mismatch"):
        validate_flux_balance_record("FBARequestApplication", value)
    option.update(application="applied", issue_code=None,
        effective_source=location("effective_problem", "/configuration_before_solve/optimality_tolerance"))
    with pytest.raises(ValueError):
        validate_flux_balance_record("FBASolverOptionApplication", option)
    value = application()
    value.update(constraint_changes=[change(0, "IN", "applied", 0),
        change(1, "BAD", "rejected", code="constraint_rejected"), change(2, "OUT", "not_attempted")],
        objective_application="not_attempted", objective_effective_source=None, request_realization="mismatch")
    checked = validate_flux_balance_record("FBARequestApplication", value)
    assert [row["application"] for row in checked["constraint_changes"]] == ["applied", "rejected", "not_attempted"]
    # Rejected invalid bounds remain source facts rather than an applied state.
    rejected = value["constraint_changes"][1]
    rejected["requested_lower"].update(value=20, native_token="20")
    assert validate_flux_balance_record("FBARequestApplication", value)["constraint_changes"][1]["requested_lower"]["value"] == 20


@pytest.mark.parametrize("mutation", [
    lambda a: a["constraint_changes"][0].update(effective_reaction_position=None),
    lambda a: a["constraint_changes"][1].update(reaction_id="IN"),
    lambda a: a["constraint_changes"][1].update(effective_reaction_position=4),
    lambda a: a["constraint_changes"].reverse(),
    lambda a: a["constraint_changes"][0]["requested_lower"].update(source=None),
    lambda a: a["constraint_changes"][0]["requested_lower"].update(value=99, native_token="99"),
    lambda a: a["constraint_changes"][0]["requested_upper"].update(kind="missing", value=None, native_token=None),
])
def test_constraint_application_joins_preserve_original_order_and_known_values(mutation):
    value = application()
    value["constraint_changes"] = [change(0, "IN", "applied", 4), change(1, "OUT", "applied", 1)]
    mutation(value)
    with pytest.raises(ValueError):
        validate_flux_balance_record("FBARequestApplication", value)


def test_manifest_application_aggregate_counts_and_role_identities_are_local_relationships():
    value = manifest()
    value["request_application"] = application()
    assert validate_flux_balance_record("FBANativeManifest", value) == value
    value["request_realization"] = "unknown"
    with pytest.raises(ValueError, match="request_effective_mismatch"):
        validate_flux_balance_record("FBANativeManifest", value)
    value["request_realization"] = "exact"
    value["files"][1]["identity"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="artifact_identity_conflict"):
        validate_flux_balance_record("FBANativeManifest", value)
    value = manifest()
    applied = application()
    applied["solver_option_applications"][1].update(application="rejected", issue_code="solver_option_unsupported")
    applied["request_realization"] = "mismatch"
    value.update(request_application=applied, request_realization="mismatch", solve_call_count=0, execution_outcome="not_executed")
    assert validate_flux_balance_record("FBANativeManifest", value)["solve_call_count"] == 0
    value["solve_call_count"] = 1
    with pytest.raises(ValueError, match="request_effective_mismatch"):
        validate_flux_balance_record("FBANativeManifest", value)
    value.update(solve_call_count=0, request_realization="exact")
    with pytest.raises(ValueError, match="request_effective_mismatch"):
        validate_flux_balance_record("FBANativeManifest", value)


def test_unknown_application_and_observed_mismatch_do_not_invent_applied_state():
    value = application()
    value.update(constraint_changes=None, objective_application="unknown", objective_effective_source=None,
        request_realization="unknown")
    for row in value["solver_option_applications"]:
        row.update(application="unknown", effective_source=None)
    assert validate_flux_balance_record("FBARequestApplication", value) == value
    value["issues"] = [issue("request_effective_mismatch")]
    value["request_realization"] = "mismatch"
    assert validate_flux_balance_record("FBARequestApplication", value)["objective_application"] == "unknown"


def test_original_selected_null_and_empty_constraints_keep_distinct_digests():
    pin = dict(path="/synthetic687/model.sbml", sha256=FILES["original_model"]["sha256"],
        size_bytes=FILES["original_model"]["size_bytes"])
    software = dict(version="fba_software_v1", python={**pin, "path": "/synthetic687/bin/python"},
        python_version="synthetic", python_home="/synthetic687", module_root="/synthetic687/modules",
        dependency_roots=[], implementation_files=[], runtime_files=[], distributions=[],
        solver_interface="optlang.glpk_interface", solver_runtime_files=[])
    job = dict(version="native_flux_balance_job_v1", operation="perform_flux_balance_analysis",
        mode="steady_state_linear_fba", source_alias="biomni.tool.systems_biology.perform_flux_balance_analysis",
        model_input=dict(file=pin, artifact_ref=None, format="sbml", original_loader_selection="sbml_file",
            repository_identifier=None, acquisition_receipt_file=None), constraints=None,
        objective=dict(kind="model_default", reaction_id=None), solver_options=dict.fromkeys(OPTION_NAMES),
        software=software, output_prefix="synthetic687", flux_output_name="flux.csv", source_function_sha256="d" * 64)
    selected = dict(version="flux_balance_selected_request_v1", attempt=manifest()["attempt"],
        requested_job=dict(argv=["/synthetic687/bin/python"], environment={}, native_flux_balance=job))
    unknown_spelling = validate_flux_balance_record("SelectedRequestPayload", selected)
    selected["requested_job"]["native_flux_balance"]["constraints"] = []
    empty_spelling = validate_flux_balance_record("SelectedRequestPayload", selected)
    assert unknown_spelling["requested_job"]["native_flux_balance"]["constraints"] is None
    assert empty_spelling["requested_job"]["native_flux_balance"]["constraints"] == []
    assert digest(unknown_spelling) != digest(empty_spelling)
    # Both known no-change selections have an empty application population.
    # Comparing either raw selection to the application is the later parser's job.
    assert validate_flux_balance_record("FBARequestApplication", application())["constraint_changes"] == []


def test_retained_old_sheet_digest_and_new_examples_are_saved_as_verification_only():
    path = Path(__file__).parents[1] / "verification/tool_graders_flux_balance_core_2026-10-29_679/VERIFIED_NUMERICAL_EXAMPLE_001.json"
    old = json.loads(path.read_text())
    sheet = validate_flux_balance_sheet(old["sheet"])
    assert sheet == old["sheet"]
    assert digest(sheet) == old["calculations"]["sheet_sha256"]
    assert "source_audit" not in sheet["models"]
    assert "native_capture_evidence" not in sheet["models"]["effective"]
    assert "native_capture_evidence" not in sheet["problems"]["effective"]
    assert "native_capture_evidence" not in sheet["native_solution"]["native"]
    value = manifest()
    value["request_application"] = application()
    examples = dict(fixture_identity="Explicit synthetic687 shared records; no native parser or solve",
        new_public_kinds=list(NEW_KINDS), source_audit=validate_flux_balance_record("FBASourceAudit", audit()),
        request_application=validate_flux_balance_record("FBARequestApplication", application()),
        native_manifest=validate_flux_balance_record("FBANativeManifest", value),
        old_fixture_identity=old["fixture_identity"], old_sheet_sha256=digest(sheet),
        old_record_unchanged=True, old_optional_members_absent=True)
    if os.environ.get("HMMER529_ATTEMPT"):
        Path(os.environ["HMMER529_ATTEMPT"], "contracts687_examples.json").write_text(json.dumps(examples, indent=2, allow_nan=False) + "\n")


@pytest.mark.parametrize("raw, expected", [
    ("optimal", "optimal"), ("feasible", "feasible"), ("infeasible", "infeasible"), ("unbounded", "unbounded"),
    ("infeasible_or_unbounded", "infeasible_or_unbounded"), ("time_limit", "time_limit"),
    ("iteration_limit", "iteration_limit"), ("numeric", "numerical_failure"),
    (None, "unknown"), ("", "unknown"), ("Optimal", "unknown"), (" optimal ", "unknown"),
    ("error", "unknown"), ("numerical_failure", "unknown"), ("not-a-native-status", "unknown"),
])
def test_shared_status_mapping_preserves_exact_old_spelling(raw, expected):
    assert normalize_fba_solver_status(raw) == expected


@pytest.mark.parametrize("raw", [True, 1, 1.0, [], {}, b"optimal", ("optimal",)])
def test_shared_status_mapping_rejects_non_string_scalars_and_containers(raw):
    with pytest.raises(ValueError, match="^schema_invalid:/raw_status$"):
        normalize_fba_solver_status(raw)
