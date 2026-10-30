"""Constructed source bytes/pixels for shared v3 stages; no paper/model run."""
from copy import deepcopy as cp
import errno
from pathlib import Path
import runpy

import pytest

from gene_annotation_episode import literature_controlled_response_inputs as shared
from gene_annotation_episode import literature_controlled_response_v2_inputs as legacy
from gene_annotation_episode import literature_controlled_response_v3_inputs as v3
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError


ROOT = Path(__file__).resolve().parents[1]
Fixture = runpy.run_path(str(ROOT / "tests/test_literature_controlled_response_v2_inputs.py"))["Fixture"]
ROLES = shared.PRIMITIVE_ORDER


def forbidden(*args, **kwargs):
    raise AssertionError("unexpected source/decode/count/model/population")


def fixture(index=0, *, companion=False, joint=True, local=True):
    f = Fixture(index)
    a = f.args
    a.update(version="controlled_response_source_selection_v3", companion_readings=[],
        joint_reading_assignments=[], joint_scopes=[], reading_reconciliations=[], local_pair_assignments=[])
    witness = f.witness("Only the intended factor differs.")
    scope = dict(value="same", witnesses=[cp(witness)])
    if companion:
        a["companion_readings"] = [dict(reading_key="same-A", primary_role=ROLES[0], reading=cp(a["arms"][ROLES[0]]))]
        a["reading_reconciliations"] = [dict(role=ROLES[0],
            relationship=dict(value="exact_duplicate", witnesses=[cp(witness)]),
            authority=dict(status="not_established", reading=None, witnesses=[]),
            **{name: cp(scope) for name in ("normalization", "calibration", "revision", "model_scope")})]
    if joint:
        assignment = dict.fromkeys(ROLES)
        if companion:
            assignment[ROLES[0]] = "same-A"
        a["joint_reading_assignments"] = [dict(assignment=assignment,
            admissibility=dict(value="compatible", witnesses=[cp(witness)]))]
        a["joint_scopes"] = [dict(assignment_index=0,
            **{name: cp(scope) for name in ("normalization", "calibration", "revision", "covariance_scope", "model_scope")},
            covariance_selection=cp(a["covariance"]), variance_status=cp(a["variance_status"]), model_kind=cp(a["model_kind"]))]
    if local:
        a["local_pair_assignments"] = [dict(pair_key="condition0", condition="condition0",
            protein=dict(role=ROLES[2], reading_key=None), control=dict(role=ROLES[3], reading_key=None),
            admissibility=dict(value="compatible", witnesses=[cp(witness)]), scope=cp(scope),
            covariance_selection=cp(a["covariance"]), variance_status=cp(a["variance_status"]))]
    return f


def read_arm(context, selector):
    entry = shared._reading_entry(context, selector)
    import json
    arm = json.loads(entry[0])
    if arm is None:
        return None
    science = shared.read_controlled_response_arm_science(context, arm, reading_selector=selector)
    selected = arm["measurement"]
    if selected is not None and selected["kind"] == "linear_bar":
        measurement = shared.read_controlled_response_graph_measurement(context, selector,
            endpoint=science["meanings"]["endpoint"])
    else:
        measurement = shared.read_controlled_response_text_measurement(context, selected,
            endpoint=science["meanings"]["endpoint"], reading_selector=selector)
    return shared.finish_controlled_response_arm(context, science, measurement=measurement, reading_selector=selector)


def stages(context):
    rows = {}
    for role, key in context._reading_registry:
        selector = dict(role=role, reading_key=key)
        rows[(role, key)] = read_arm(context, selector)
    scopes = []
    for kind, index in context._scope_registry:
        scope = dict(kind=kind, index=index)
        document = shared.read_controlled_response_covariance_document(context, scope)
        _, selectors = shared._scope_entry(context, scope)
        scopes.append(shared.bind_controlled_response_covariance_scope(context, scope, document,
            readings=[(s, rows[shared._selector_key(s)]) for s in selectors]))
    return rows, scopes


def test_explicit_profile_original_registry_order_and_exact_legacy_primary_payloads():
    f = fixture(companion=True)
    original = Fixture().read()
    f.args["arms"] = dict(reversed(list(f.args["arms"].items())))
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        assert context.profile == "v3"
        assert list(context._reading_registry) == [(r, None) for r in ROLES] + [(ROLES[0], "same-A")]
        rows, scopes = stages(context)
        for role in ROLES:
            assert rows[(role, None)] == original["arms"][role]
        assert scopes[0]["whole_projection"] == original["covariance"]
        assert scopes[0]["document"] == scopes[1]["document"] == scopes[2]["document"]
        assert scopes[2]["whole_projection"] is None
        assert [r["reading"]["role"] for r in scopes[2]["bindings"]] == [ROLES[2], ROLES[3]]
        with pytest.raises(TypeError):
            context._reading_registry[(ROLES[0], "forged")] = None
        with pytest.raises(AttributeError):
            context.profile = "v1"
    assert f.calls == shared._reference_closure(f.args)
    assert not context._reading_registry and not context._scope_registry
    assert not context._stage_records and not context._document_records and not context._covariance_facts
    assert not context.cache and not context.visual.decoded and not context.native.cache


def test_full_document_is_parsed_once_but_each_scope_has_its_own_token(monkeypatch):
    f = fixture()
    parse = shared._covariance_document_facts
    calls = []
    def tracked(context, nomination):
        calls.append(nomination["source_ref"])
        return parse(context, nomination)
    monkeypatch.setattr(shared, "_covariance_document_facts", tracked)
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows, scopes = stages(context)
        assert calls == [f.cov_ref]
        base = shared.read_controlled_response_covariance_document(context, dict(kind="base", index=None))
        with pytest.raises(ExperimentalContractError, match="source_covariance_document_mismatch"):
            shared.bind_controlled_response_covariance_scope(context, dict(kind="joint", index=0), base,
                readings=[(dict(role=r, reading_key=None), rows[(r, None)]) for r in ROLES])
        assert calls == [f.cov_ref]


def test_selector_endpoint_finished_stage_and_context_tokens_are_exact():
    f, g = fixture(companion=True), fixture(companion=True)
    primary, companion = dict(role=ROLES[0], reading_key=None), dict(role=ROLES[0], reading_key="same-A")
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as a, shared.open_controlled_response_sources(g.args, read_source=g.source) as b:
        arm = a.arguments["arms"][ROLES[0]]
        science = shared.read_controlled_response_arm_science(a, arm, reading_selector=primary)
        second_science = shared.read_controlled_response_arm_science(a, arm, reading_selector=primary)
        measurement = shared.read_controlled_response_text_measurement(a, arm["measurement"],
            endpoint=science["meanings"]["endpoint"], reading_selector=primary)
        for selector in (None, companion):
            with pytest.raises(ExperimentalContractError):
                shared.finish_controlled_response_arm(a, science, measurement=measurement, reading_selector=selector)
        with pytest.raises(ExperimentalContractError, match="source_stage_endpoint_mismatch"):
            shared.finish_controlled_response_arm(a, second_science, measurement=measurement, reading_selector=primary)
        with pytest.raises(ExperimentalContractError, match="source_stage_context_mismatch"):
            shared.finish_controlled_response_arm(b, science, measurement=measurement, reading_selector=primary)
        with pytest.raises(ExperimentalContractError, match="source_stage_endpoint_mismatch"):
            shared.read_controlled_response_text_measurement(a, arm["measurement"],
                endpoint=science["meanings"]["endpoint"], reading_selector=companion)
        rows, scopes = stages(a)
        primary_arms = {r: rows[(r, None)] for r in ROLES}
        companions = [(companion, rows[(ROLES[0], "same-A")])]
        shared._validate_v3_finish_stages(a, primary_arms, companions, scopes)
        primary_arms[ROLES[0]] = science
        with pytest.raises(ExperimentalContractError, match="source_stage_selector_mismatch"):
            shared._validate_v3_finish_stages(a, primary_arms, companions, scopes)
        measurement["operand_projection"]["value"] = 999
        with pytest.raises(ExperimentalContractError, match="source_stage_selector_mismatch"):
            shared.finish_controlled_response_arm(a, science, measurement=measurement, reading_selector=primary)


def test_request_mutation_after_authorization_is_not_a_new_custody_grant():
    f = fixture()
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        context.arguments["relationships"]["nonintended_conditions"]["value"] = "different"
        with pytest.raises(ExperimentalContractError, match="source_context_nomination_mismatch"):
            read_arm(context, dict(role=ROLES[0], reading_key=None))


def test_v3_original_cache_and_root_relationships_cannot_be_rebound():
    f = fixture()
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        key = (f.main_ref, "original")
        with pytest.raises(TypeError):
            context.cache[key] = dict(artifact_ref="replacement", content=b"replacement")
        with pytest.raises(TypeError):
            context.cache[key]["content"] = b"replacement"
        # A helper receives a copy of the interface, never a mutable cache entry.
        copy = context.source(*key)
        copy["content"] = b"replacement"
        assert context.source(*key)["content"] == f.data[f.main_ref]
        context.relationships["nonintended_conditions"]["effective_value"] = "different"
        with pytest.raises(ExperimentalContractError, match="source_context_science_mismatch"):
            read_arm(context, dict(role=ROLES[0], reading_key=None))


def test_complete_original_authorization_precedes_geometry_even_for_companion(monkeypatch):
    f = fixture(companion=True)
    ref = "source_" + "f" * 24
    f.data[ref] = b"Companion source context"
    f.args["companion_readings"][0]["reading"]["context"]["subject"] = dict(kind="text", source_ref=ref,
        representation="original", start=0, end=len(f.data[ref]), quote=f.data[ref].decode())
    closure = shared._reference_closure(f.args)
    calls = []
    def denied(reference, representation):
        calls.append((reference, representation))
        if (reference, representation) == closure[-1]:
            raise ContractError("source_out_of_scope")
        return f.source(reference, representation)
    monkeypatch.setattr(shared, "_Inputs", forbidden)
    with pytest.raises(ContractError, match="source_out_of_scope"):
        shared.open_controlled_response_sources(f.args, read_source=denied)
    assert calls == closure


@pytest.mark.parametrize("kind", ["base", "joint", "local"])
def test_documents_retain_full_original_invalid_unused_rows(kind):
    f = Fixture(1)
    f.doc["covariance"][3][3] = -1
    f.covariance()
    # Add v3 fields without changing the constructed source bytes or nominations.
    configured = fixture(1)
    for field in ("version", "companion_readings", "joint_reading_assignments", "joint_scopes", "reading_reconciliations", "local_pair_assignments"):
        f.args[field] = configured.args[field]
    for row in f.args["joint_scopes"] + f.args["local_pair_assignments"]:
        row["covariance_selection"] = cp(f.args["covariance"])
        row["variance_status"] = cp(f.args["variance_status"])
        if "model_kind" in row:
            row["model_kind"] = cp(f.args["model_kind"])
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows, scopes = stages(context)
        bound = next(row for row in scopes if row["scope"]["kind"] == kind)
        assert len(bound["document"]["variables"]) == 4
        assert bound["document"]["source_validation"] == "invalid"
        if kind != "local":
            assert bound["whole_projection"]["calculation_covariance"] is None
        assert rows[(ROLES[2], None)]["calculation_operand"]["value"] == 8


@pytest.mark.parametrize("version", ["controlled_response_source_selection_v1", "controlled_response_source_selection_v2"])
def test_legacy_selector_keyword_is_rejected_without_changing_legacy_calls(version):
    f = Fixture()
    if version.endswith("_v1"):
        # A v1-compatible all-text row is sufficient to test the added keyword.
        f.args["arms"][ROLES[3]]["measurement"] = cp(f.args["arms"][ROLES[1]]["measurement"])
    f.args["version"] = version
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        with pytest.raises(ExperimentalContractError, match="unsupported_stage_selector"):
            shared.read_controlled_response_arm_science(context, context.arguments["arms"][ROLES[0]],
                reading_selector=dict(role=ROLES[0], reading_key=None))


@pytest.mark.parametrize("scope", [dict(kind="base", index=0), dict(kind="joint", index=True),
    dict(kind="joint", index=7), dict(kind="local", index=-1), dict(kind="base", index=None, extra=1)])
def test_scope_keys_reject_nonoriginal_or_malformed_bindings(scope):
    f = fixture()
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        with pytest.raises(ExperimentalContractError):
            shared.read_controlled_response_covariance_document(context, scope)


@pytest.mark.parametrize("companion", [False, True])
def test_actual_finish_and_detached_reconstruction_without_source_or_scientific_work(companion, monkeypatch):
    f = fixture(companion=companion)
    result = v3.read_controlled_response_v3_inputs(f.args, read_source=f.source)
    assert f.calls == shared._reference_closure(f.args)
    assert result["projection_status"] == "ready"
    assert len(result["covariance_document_scopes"]) == 3
    assert len(result["alternative_inputs"]) == 1
    assert result["component_local_inputs"]["pairs"][0]["pair_key"] == "condition0"
    from gene_annotation_episode import literature_controlled_response_figure_inputs as graph
    from gene_annotation_episode import literature_controlled_response_owner_calculations as owner
    from gene_annotation_episode import literature_controlled_response_local_calculations as local
    for module, names in ((shared, ("_Context", "_Sources", "_Inputs", "_native_number", "_native_unit")),
            (graph, ("read_controlled_response_rate_figure", "_strict_decode", "_count_bar_runs")),
            (owner, ("populate_controlled_response_owner",)), (local, ("populate_controlled_response_local",))):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    assert v3.validate_controlled_response_v3_extraction(f.args, result) == result


@pytest.mark.parametrize("field", ["scope", "binding", "doc", "graph", "conditional", "reconciliation", "local"])
def test_saved_scope_science_and_source_projection_tampering_is_rejected(field):
    f = fixture(companion=True)
    result = v3.read_controlled_response_v3_inputs(f.args, read_source=f.source)
    if field == "scope":
        result["covariance_document_scopes"][1]["scope"]["index"] = 1
    elif field == "binding":
        result["component_local_inputs"]["pairs"][0]["protein_binding"]["source_variable_index"] = 0
    elif field == "doc":
        result["covariance_document_scopes"][2]["document"]["matrix_tokens"][0][0] = "999"
    elif field == "graph":
        result["arms"][ROLES[3]]["graph_details"]["measurement"]["pixel_result"]["pixel_edge"]["nominal"]["numerator"] = "999"
    elif field == "conditional":
        result["alternative_inputs"][0]["calculation_inputs"]["arms"][ROLES[0]]["value"] = 999
    elif field == "reconciliation":
        result["reconciliation_decisions"][0]["selected_reading"]["reading_key"] = "same-A"
    else:
        result["component_local_inputs"]["readings"][0]["arm"]["source_observation_id"] = "caller_authored_id"
    with pytest.raises(ExperimentalContractError):
        v3.validate_controlled_response_v3_extraction(f.args, result)


def test_local_scope_ignores_unrelated_binding_conflict_but_not_pair_owner_conflict():
    f = fixture()
    nomination = f.args["local_pair_assignments"][0]["covariance_selection"]
    unrelated = nomination["bindings"][ROLES[0]]["correspondence"]
    unrelated["value"] = "conflicting"
    unrelated["witnesses"].append(f.witness("Only the intended factor differs."))
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows, scopes = stages(context)
        local = scopes[-1]
        assert [b["binding"]["state"] for b in local["bindings"]] == ["known", "known"]
    nomination["bindings"][ROLES[3]]["variable_index"] = nomination["bindings"][ROLES[2]]["variable_index"]
    nomination["bindings"][ROLES[3]]["label_witness"] = cp(nomination["bindings"][ROLES[2]]["label_witness"])
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows, scopes = stages(context)
        local = scopes[-1]
        assert [b["binding"]["state"] for b in local["bindings"]] == ["conflicting", "conflicting"]
        assert all(b["binding"]["resolved_owner_id"] is None for b in local["bindings"])


@pytest.mark.parametrize("dependency", ["root", "covariance", "image", "covariance_utf8"])
def test_v3_availability_and_unsupported_bytes_reconstruct_as_partials(dependency):
    f = fixture(7, companion=True)
    reference = {"root": f.main_ref, "covariance": f.cov_ref,
        "image": f.args["images"][0]["source_ref"], "covariance_utf8": f.cov_ref}[dependency]
    if dependency == "covariance_utf8":
        f.data[reference] = b"\xff\xfe unsupported source"
    def source(ref, representation):
        if ref == reference and dependency != "covariance_utf8":
            raise EOFError("retained source unavailable")
        return f.source(ref, representation)
    result = v3.read_controlled_response_v3_inputs(f.args, read_source=source)
    assert v3.validate_controlled_response_v3_extraction(f.args, result) == result
    if dependency == "covariance_utf8":
        assert result["covariance_document_scopes"][0]["document"]["document_state"] == "unsupported_format"
    elif dependency == "covariance":
        assert result["covariance_document_scopes"][0]["document"]["document_state"] == "unavailable"


def test_local_repeated_owner_validates_full_original_rows():
    f = fixture()
    # Two selected roles explicitly nominate the same source physical owner.
    f.args["arms"][ROLES[2]]["physical_observation"] = cp(f.args["arms"][ROLES[3]]["physical_observation"])
    for nomination in [f.args["covariance"], f.args["joint_scopes"][0]["covariance_selection"],
            f.args["local_pair_assignments"][0]["covariance_selection"]]:
        nomination["bindings"][ROLES[2]]["owner_witness"] = cp(f.args["arms"][ROLES[2]]["physical_observation"]["canonical_witness"])
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows, scopes = stages(context)
        assert scopes[-1]["document"]["source_validation"] == "valid"
        assert all(row["binding"]["state"] == "conflicting" for row in scopes[-1]["bindings"])
        assert all(any(d["code"] == "covariance_shared_rows_conflicting" for d in row["binding"]["diagnostics"])
            for row in scopes[-1]["bindings"])


def test_finish_requires_complete_original_order_stage_rosters():
    f = fixture(companion=True)
    with shared.open_controlled_response_sources(f.args, read_source=f.source) as context:
        rows, scopes = stages(context)
        arms = {r: rows[(r, None)] for r in ROLES}
        companion = (dict(role=ROLES[0], reading_key="same-A"), rows[(ROLES[0], "same-A")])
        for companions, covariance_scopes in (([], scopes), ([companion], scopes[:-1]),
                ([companion], list(reversed(scopes))), ([companion], [scopes[0], scopes[0], scopes[2]])):
            with pytest.raises(ExperimentalContractError):
                shared.finish_controlled_response_inputs(context, arms=arms,
                    companion_arms=companions, covariance_scopes=covariance_scopes)


def test_equal_companion_measurements_still_have_distinct_saved_selector_callbacks():
    f = fixture(companion=True)
    second = cp(f.args["companion_readings"][0])
    second["reading_key"] = "same-A-2"
    f.args["companion_readings"].append(second)
    result = v3.read_controlled_response_v3_inputs(f.args, read_source=f.source)
    seen = []
    def check(selector, selected, measurement, *, source_records, image_records):
        seen.append(cp(selector))
        if selected and selected["kind"] == "linear_bar":
            arm = result["arms"][selector["role"]]
            return legacy._validate_graph(selected, arm["graph_details"],
                sources={(s["source_ref"], s["representation"]): s for s in source_records}, images=image_records, request=f.args)
        return legacy._validate_measurement(selected, measurement, source_records=source_records, image_records=image_records)
    assert shared.validate_controlled_response_saved_science(f.args, result, measurement_checks=check) == result
    assert seen == [dict(role=r, reading_key=None) for r in ROLES] + [
        dict(role=ROLES[0], reading_key="same-A"), dict(role=ROLES[0], reading_key="same-A-2")]


def test_empty_received_covariance_text_retains_original_empty_bytes_as_unsupported():
    f = fixture()
    f.data[f.cov_ref] = b""
    f.args["covariance"]["bindings"] = dict.fromkeys(ROLES)
    f.args["variance_status"] = dict(value="unknown", witnesses=[])
    f.args["model_kind"] = dict(value="none", witnesses=[])
    for row in f.args["joint_scopes"] + f.args["local_pair_assignments"]:
        row["covariance_selection"] = cp(f.args["covariance"])
        row["variance_status"] = cp(f.args["variance_status"])
        if "model_kind" in row:
            row["model_kind"] = cp(f.args["model_kind"])
    result = v3.read_controlled_response_v3_inputs(f.args, read_source=f.source)
    for row in result["covariance_document_scopes"]:
        document = row["document"]
        assert document["raw_text"] == ""
        assert document["document_state"] == "unsupported_format"
        assert document["source_validation"] == "unassessed"
        assert document["exact_matrix"] is None
    assert result["covariance"]["calculation_covariance"] is None
    assert result["calculation_inputs"]["covariance"] is None
    assert v3.validate_controlled_response_v3_extraction(f.args, result) == result


@pytest.mark.parametrize("mutation", [
    lambda r: r["arms"][ROLES[2]]["measurement"]["candidates"][0].update(native_value=True),
    lambda r: r["arms"][ROLES[2]]["calculation_operand"].update(approximate=0),
    lambda r: r["arms"][ROLES[0]]["reported_uncertainty"]["canonical"].update(count=True),
    lambda r: r["covariance_document_scopes"][0]["document"]["variables"][0].update(index=False),
    lambda r: r["images"][0].update(width=True),
])
def test_detached_source_schema_rejects_bool_number_substitution(mutation):
    f = fixture(7, companion=True)
    result = v3.read_controlled_response_v3_inputs(f.args, read_source=f.source)
    mutation(result)
    with pytest.raises(ExperimentalContractError, match="saved_extraction_schema_invalid"):
        v3.validate_controlled_response_v3_extraction(f.args, result)


def test_no_covariance_nomination_has_no_document_or_fabricated_projection(monkeypatch):
    f = fixture()
    f.args["covariance"] = None
    for row in f.args["joint_scopes"] + f.args["local_pair_assignments"]:
        row["covariance_selection"] = None
    monkeypatch.setattr(shared, "_covariance_document_facts", forbidden)
    result = v3.read_controlled_response_v3_inputs(f.args, read_source=f.source)
    assert all(row["document"] is None for row in result["covariance_document_scopes"])
    assert result["covariance"] is None
    assert result["calculation_inputs"]["covariance"] is None
    assert result["component_local_inputs"]["source_covariances"] == []
    assert result["component_local_inputs"]["pairs"][0]["protein_binding"] is None
    assert v3.validate_controlled_response_v3_extraction(f.args, result) == result


def test_saved_context_releases_stage_tokens_on_success_and_failure(monkeypatch):
    f = fixture(companion=True)
    result = v3.read_controlled_response_v3_inputs(f.args, read_source=f.source)
    closed = []
    original_close = shared._SavedV3SourceContext.close
    def check_close(context):
        original_close(context)
        assert context.closed
        assert not context._reading_registry and not context._scope_registry
        assert not context._stage_records and not context._document_records and not context._covariance_facts
        closed.append(True)
    monkeypatch.setattr(shared._SavedV3SourceContext, "close", check_close)
    assert v3.validate_controlled_response_v3_extraction(f.args, result) == result
    result["arms"][ROLES[2]]["calculation_operand"]["value"] = 999
    with pytest.raises(ExperimentalContractError, match="saved_operand_projection_mismatch"):
        v3.validate_controlled_response_v3_extraction(f.args, result)
    assert closed == [True, True]

