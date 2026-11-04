"""Synthetic A108 retained-record validation; no acquired scientific evidence."""
from copy import deepcopy
import hashlib
import json
import math

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_context_inputs import (
    DATA_VERSION, LITERAL_FIELDS, NATIVE_UNITS, VERSION,
    context_population_schema, read_context_inputs,
)

SOURCE = "source_" + "1" * 24
DATA = "source_" + "2" * 24
OTHER = "source_" + "3" * 24
ARTIFACT = "artifact_" + "4" * 24
DATA_ARTIFACT = "artifact_" + "5" * 24
TEXT = "µ molecule M; organism O; condition C; reference compatibility."


def interval(lower=1, upper=2, lower_closed=True, upper_closed=True):
    return dict(lower=lower, upper=upper, lower_closed=lower_closed, upper_closed=upper_closed)


def observation(**changes):
    result = dict(requirement_key="exposure", measurement_key="measurement α", unit="ppbv_H2_gas",
        interval=interval(), relation="numeric", reported_sd=None, reported_sem=None,
        reported_plusminus=None, reported_count=None, count_relation="unknown", replicate_kind="unknown")
    result.update(changes)
    return result


def witness(quote="molecule M", *, source=SOURCE, representation="original"):
    start = TEXT.encode().index(quote.encode())
    return dict(source_ref=source, representation=representation,
                start=start, end=start + len(quote.encode()), quote=quote)


def fixture(*, populated=True):
    args = dict(source_ref=SOURCE, data_source_ref=DATA if populated else None,
        source_kind="synthetic_fixture", literals=dict.fromkeys(LITERAL_FIELDS),
        interpretation_witnesses=[])
    args["literals"]["molecule"] = witness()
    inputs = dict(question_kind="sample_context_coverage", origin="synthetic", scope_status="defined",
        frame_status="defined", pairing="paired", weight_basis="equal_units", sampling_design="census",
        alpha=None, permitted_remainder=None,
        requirements=[dict(key="exposure", unit="ppbv_H2_gas", supported=[interval(0, 10)], incompatible=[])],
        routes=[dict(key="route α", requirements=["exposure"], requirements_complete=True,
                     joint_support="unresolved")],
        contexts=[dict(key="context α", weight=1, cluster_key="cluster α", scope_match="matched",
                       observations=[observation()])], marginals=[])
    data = dict(version=DATA_VERSION, inputs=inputs)
    payloads = {SOURCE: dict(artifact_ref=ARTIFACT, content=TEXT.encode()),
                DATA: dict(artifact_ref=DATA_ARTIFACT, content=json.dumps(data).encode())}
    calls = []

    def read_source(reference, representation):
        calls.append((reference, representation))
        return payloads[reference]
    return args, payloads, data, calls, read_source


def read(fix):
    return read_context_inputs(fix[0], read_source=fix[4])


def save(fix):
    fix[1][DATA]["content"] = json.dumps(fix[2], ensure_ascii=False).encode()


def physical(kind, source, artifact, raw_id):
    owner = dict(source_ref=source, artifact_ref=artifact, raw_id=raw_id)
    raw = json.dumps(owner, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return "literature_" + kind + "_" + hashlib.sha256(raw).hexdigest()


def test_no_dataset_preserves_source_facts_and_unknown_question_without_fabrication():
    fix = fixture(populated=False)
    out = read(fix)
    assert set(out) == {"version", "arguments", "sources", "literals", "interpretations", "observations", "calculation_inputs"}
    assert out["version"] == VERSION
    assert out["observations"] is out["calculation_inputs"] is None
    assert out["literals"]["molecule"] == dict(value="molecule M", witness={**witness(), "artifact_ref": ARTIFACT})
    assert out["literals"]["sample_frame"] is None
    assert out["sources"] == [SOURCE] and fix[3] == [(SOURCE, "original")]


def test_retained_records_preserve_native_intervals_uncertainties_and_raw_physical_ids():
    fix = fixture()
    item = fix[2]["inputs"]["contexts"][0]["observations"][0]
    item.update(reported_sd=.1, reported_sem=.02, reported_plusminus=.3, reported_count=3,
                count_relation="at_least", replicate_kind="technical")
    save(fix)
    out = read(fix)
    assert out["observations"] == fix[2]
    assert out["arguments"] == fix[0] and out["sources"] == [SOURCE, DATA]
    context = out["calculation_inputs"]["contexts"][0]
    assert context["key"] == physical("context", DATA, DATA_ARTIFACT, "context α")
    assert context["cluster_key"] == physical("cluster", DATA, DATA_ARTIFACT, "cluster α")
    assert context["observations"][0] == {**item, "measurement_key": physical("measurement", DATA, DATA_ARTIFACT, "measurement α")}
    assert out["calculation_inputs"]["requirements"] == fix[2]["inputs"]["requirements"]
    assert out["calculation_inputs"]["routes"] == fix[2]["inputs"]["routes"]
    assert "cells" not in out and "counts" not in out
    out["calculation_inputs"]["contexts"][0]["observations"][0]["reported_count"] = 100
    assert out["observations"]["inputs"]["contexts"][0]["observations"][0]["reported_count"] == 3
    fix[0]["literals"]["molecule"]["quote"] = "changed"
    assert out["arguments"]["literals"]["molecule"]["quote"] == "molecule M"


def test_ids_depend_on_dataset_actual_artifact_and_raw_id_separately_per_physical_kind():
    fix = fixture()
    context = fix[2]["inputs"]["contexts"][0]
    context["key"] = context["cluster_key"] = context["observations"][0]["measurement_key"] = "same raw id µ"
    save(fix)
    original = read(fix)["calculation_inputs"]["contexts"][0]
    assert len({original["key"], original["cluster_key"], original["observations"][0]["measurement_key"]}) == 3
    fix[1][DATA]["artifact_ref"] = ARTIFACT
    altered = read(fix)["calculation_inputs"]["contexts"][0]
    assert original["key"] != altered["key"]
    assert original["cluster_key"] != altered["cluster_key"]
    assert original["observations"][0]["measurement_key"] != altered["observations"][0]["measurement_key"]
    fix[1][DATA]["artifact_ref"] = DATA_ARTIFACT
    fix[1][OTHER] = fix[1][DATA]
    fix[0]["data_source_ref"] = OTHER
    assert original["key"] != read(fix)["calculation_inputs"]["contexts"][0]["key"]


def test_exact_repeated_contexts_coalesce_only_in_calculation_inputs_and_equal_values_do_not():
    fix = fixture()
    contexts = fix[2]["inputs"]["contexts"]
    contexts.append(deepcopy(contexts[0]))
    independent = deepcopy(contexts[0])
    independent.update(key="different opportunity", cluster_key="different cluster")
    # Shared primitive remains a dependency; no invented independent measurement.
    contexts.append(independent)
    save(fix)
    out = read(fix)
    assert len(out["observations"]["inputs"]["contexts"]) == 3
    assert len(out["calculation_inputs"]["contexts"]) == 2
    first, second = out["calculation_inputs"]["contexts"]
    assert first["key"] != second["key"]
    assert first["observations"][0]["measurement_key"] == second["observations"][0]["measurement_key"]


@pytest.mark.parametrize("change", [dict(weight=None), dict(cluster_key=None), dict(scope_match="unresolved"), dict(observations=[])])
def test_same_context_id_conflicting_facts_reject_instead_of_adding_weight(change):
    fix = fixture()
    repeated = deepcopy(fix[2]["inputs"]["contexts"][0])
    repeated.update(change)
    fix[2]["inputs"]["contexts"].append(repeated)
    save(fix)
    with pytest.raises(ExperimentalContractError, match="duplicate_context_conflict"):
        read(fix)


@pytest.mark.parametrize("change", [dict(unit="ppmv_H2_gas"), dict(interval=None), dict(reported_sd=0),
    dict(reported_count=0), dict(replicate_kind="technical")])
def test_measurement_alias_conflicts_reject_across_different_contexts(change):
    fix = fixture()
    contexts = fix[2]["inputs"]["contexts"]
    second = deepcopy(contexts[0])
    second["key"] = "other"
    second["observations"][0].update(change)
    contexts.append(second)
    save(fix)
    with pytest.raises(ExperimentalContractError, match="shared_measurement_meaning_conflict"):
        read(fix)


@pytest.mark.parametrize("bounds", [interval(None, None, False, False), interval(None, 1, False, False),
    interval(1, None, False, False), interval(1, 1), interval(0, 2, False, True)])
def test_interval_unions_preserve_open_boundaries_gaps_and_infinite_ends(bounds):
    fix = fixture()
    fix[2]["inputs"]["requirements"][0]["supported"] = [bounds, interval(3, 5)]
    save(fix)
    assert read(fix)["calculation_inputs"]["requirements"][0]["supported"] == [bounds, interval(3, 5)]


def test_conflicting_domains_missing_values_and_native_unit_mismatch_are_preserved_for_calculator():
    fix = fixture()
    inputs = fix[2]["inputs"]
    inputs["requirements"][0]["incompatible"] = [interval(1, 3)]
    inputs["contexts"][0]["observations"][0].update(unit="uM_H2_solution", interval=None)
    inputs["contexts"][0].update(weight=None, cluster_key=None, scope_match="conflicting")
    inputs.update(scope_status="unreported", frame_status="unreported", routes=None)
    save(fix)
    assert read(fix)["calculation_inputs"]["requirements"] == inputs["requirements"]
    assert read(fix)["calculation_inputs"]["contexts"][0]["observations"][0]["interval"] is None


@pytest.mark.parametrize("relation", ["supported", "incompatible", "unresolved"])
def test_narrow_state_relations_are_explicit_and_have_no_numeric_domain(relation):
    fix = fixture()
    inputs = fix[2]["inputs"]
    inputs["requirements"][0].update(unit="state", supported=[], incompatible=[])
    inputs["contexts"][0]["observations"][0].update(unit="state", interval=None, relation=relation)
    save(fix)
    out = read(fix)["calculation_inputs"]["contexts"][0]["observations"][0]
    assert out["relation"] == relation and out["interval"] is None


@pytest.mark.parametrize("unit", NATIVE_UNITS[:-1])
def test_native_units_preserve_exact_basis_without_conversion(unit):
    fix = fixture()
    fix[2]["inputs"]["contexts"][0]["observations"][0]["unit"] = unit
    save(fix)
    assert read(fix)["calculation_inputs"]["contexts"][0]["observations"][0]["unit"] == unit


def test_unpaired_marginals_missing_requirements_and_unsupported_route_design_remain_explicit():
    fix = fixture()
    inputs = fix[2]["inputs"]
    inputs.update(pairing="unpaired_marginals", contexts=[], frame_status="unreported",
                  marginals=[dict(requirement_key="exposure", lower=.2, upper=.8)])
    inputs["routes"].append(dict(key="unexamined alternative", requirements=[], requirements_complete=False,
                                 joint_support="unresolved"))
    save(fix)
    assert read(fix)["calculation_inputs"] == inputs


@pytest.mark.parametrize("raw,error", [
    (b'{"version":"one","version":"two"}', "duplicate_json_key"),
    (b'{"nested":{"x":1,"x":2}}', "duplicate_json_key"),
    (b'{"x":NaN}', "finite_number_required"), (b'{"x":Infinity}', "finite_number_required"),
    (b'{"x":-Infinity}', "finite_number_required"), (b'{"x":1e999}', "finite_number_required"),
    (b'{"x":1e-999}', "numerical_model_range"), (b'{"x":-1e-999}', "numerical_model_range"),
    (b'{"x":' + b'1' * 400 + b'}', "finite_number_required"),
    (b'\xff', "malformed_context_measurements_source"),
    (b'{} trailing', "malformed_context_measurements_source"),
    (b'[' * 2000 + b']' * 2000, "malformed_context_measurements_source|closed_fields_required"),
])
def test_strict_json_rejects_duplicates_nonfinite_underflow_and_malformed_source(raw, error):
    fix = fixture()
    fix[1][DATA]["content"] = raw
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize("path,change,error", [
    ("root", {"version": "bad"}, "unsupported_context_measurements_version"),
    ("root", {"extra": 1}, "closed_fields_required"),
    ("input", {"extra": 1}, "closed_fields_required"),
    ("input", {"question_kind": "plausibility"}, "unsupported_question_kind"),
    ("input", {"origin": "inferred"}, "unsupported_origin"),
    ("input", {"scope_status": "assumed"}, "unsupported_scope_status"),
    ("input", {"frame_status": "assumed"}, "unsupported_frame_status"),
    ("input", {"pairing": "independent"}, "unsupported_pairing"),
    ("input", {"weight_basis": "confidence"}, "unsupported_weight_basis"),
    ("input", {"sampling_design": "technical"}, "unsupported_sampling_design"),
    ("input", {"alpha": 0}, "open_unit_interval_required"),
    ("input", {"alpha": 1}, "open_unit_interval_required"),
    ("input", {"permitted_remainder": 1}, "boolean_required"),
    ("input", {"routes": []}, "nonempty_array_required"),
    ("requirement", {"key": " "}, "nonempty_source_token_required"),
    ("requirement", {"unit": "ppm"}, "unsupported_unit"),
    ("requirement", {"unit": "state"}, "state_domain_regions_must_be_empty"),
    ("requirement", {"supported": None}, "array_required"),
    ("route", {"requirements": ["absent"]}, "unknown_requirement_reference"),
    ("route", {"requirements": ["exposure", "exposure"]}, "duplicate_physical_or_model_key"),
    ("route", {"requirements_complete": 1}, "boolean_required"),
    ("route", {"joint_support": "assumed"}, "unsupported_joint_support"),
    ("context", {"weight": 0}, "positive_value_required"),
    ("context", {"weight": 2}, "equal_units_weight_must_be_one"),
    ("context", {"cluster_key": " "}, "nonempty_source_token_required"),
    ("context", {"scope_match": "near"}, "unsupported_scope_match"),
    ("observation", {"requirement_key": "absent"}, "unknown_requirement_reference"),
    ("observation", {"measurement_key": " "}, "nonempty_source_token_required"),
    ("observation", {"unit": "state"}, "state_relation_requires_null_interval"),
    ("observation", {"relation": "supported"}, "numeric_unit_requires_numeric_relation"),
    ("observation", {"reported_sd": -.1}, "nonnegative_value_required"),
    ("observation", {"reported_sem": -.1}, "nonnegative_value_required"),
    ("observation", {"reported_plusminus": -.1}, "nonnegative_value_required"),
    ("observation", {"reported_count": -1}, "nonnegative_integer_count_required"),
    ("observation", {"reported_count": True}, "nonnegative_integer_count_required"),
    ("observation", {"reported_count": 1.0}, "nonnegative_integer_count_required"),
    ("observation", {"count_relation": "exact"}, "missing_count_requires_unknown_relation"),
    ("observation", {"replicate_kind": "independent"}, "unsupported_replicate_kind"),
    ("interval", {"lower_closed": 1}, "boolean_required"),
    ("interval", {"lower": None}, "unbounded_endpoint_must_be_open"),
    ("interval", {"upper": None}, "unbounded_endpoint_must_be_open"),
    ("interval", {"lower": 3}, "ordered_bounds_required"),
    ("interval", {"upper": 1, "upper_closed": False}, "nonempty_interval_required"),
])
def test_closed_design_and_meaningful_relationship_validation(path, change, error):
    fix = fixture()
    inputs = fix[2]["inputs"]
    targets = dict(root=fix[2], input=inputs, requirement=inputs["requirements"][0], route=inputs["routes"][0],
        context=inputs["contexts"][0], observation=inputs["contexts"][0]["observations"][0],
        interval=inputs["contexts"][0]["observations"][0]["interval"])
    targets[path].update(change)
    save(fix)
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize("where", ["requirement", "route", "observation", "marginal"])
def test_repeated_model_keys_and_observations_are_not_silently_removed(where):
    fix = fixture()
    inputs = fix[2]["inputs"]
    if where == "requirement": inputs["requirements"].append(deepcopy(inputs["requirements"][0]))
    elif where == "route": inputs["routes"].append(deepcopy(inputs["routes"][0]))
    elif where == "observation": inputs["contexts"][0]["observations"].append(observation())
    else:
        inputs.update(pairing="unpaired_marginals", contexts=[], marginals=[
            dict(requirement_key="exposure", lower=0, upper=1)] * 2)
    save(fix)
    with pytest.raises(ExperimentalContractError, match="duplicate_physical_or_model_key"):
        read(fix)


@pytest.mark.parametrize("value", [True, False, "1", math.inf, math.nan, 10**400])
@pytest.mark.parametrize("path", ["weight", "alpha", "lower", "reported_sd", "reported_sem", "reported_plusminus"])
def test_numeric_operands_never_accept_booleans_strings_or_nonfinite(value, path):
    fix = fixture()
    inputs = fix[2]["inputs"]
    context = inputs["contexts"][0]
    if path == "weight": context["weight"] = value
    elif path == "alpha": inputs["alpha"] = value
    elif path == "lower": context["observations"][0]["interval"]["lower"] = value
    else: context["observations"][0][path] = value
    save(fix)
    with pytest.raises(ExperimentalContractError, match="finite_number_required"):
        read(fix)


@pytest.mark.parametrize("marginal,error", [
    (dict(requirement_key="absent", lower=0, upper=1), "unknown_requirement_reference"),
    (dict(requirement_key="exposure", lower=True, upper=1), "finite_number_required"),
    (dict(requirement_key="exposure", lower=-.1, upper=1), "unit_interval_required"),
    (dict(requirement_key="exposure", lower=0, upper=1.1), "unit_interval_required"),
    (dict(requirement_key="exposure", lower=.8, upper=.2), "ordered_bounds_required"),
])
def test_marginal_bounds_and_references(marginal, error):
    fix = fixture()
    fix[2]["inputs"].update(pairing="unpaired_marginals", contexts=[], marginals=[marginal])
    save(fix)
    with pytest.raises(ExperimentalContractError, match=error):
        read(fix)


@pytest.mark.parametrize("pairing", ["paired", "unpaired_marginals"])
def test_pairing_cannot_silently_mix_paired_contexts_with_marginal_counts(pairing):
    fix = fixture()
    fix[2]["inputs"].update(pairing=pairing, marginals=[dict(requirement_key="exposure", lower=0, upper=1)])
    save(fix)
    with pytest.raises(ExperimentalContractError, match="paired_marginals_must_be_empty|unpaired_contexts_must_be_empty"):
        read(fix)


def test_declared_measured_weights_and_exact_zero_count_are_retained_without_derivation():
    fix = fixture()
    fix[2]["inputs"].update(weight_basis="measured_duration", alpha=.05)
    fix[2]["inputs"]["contexts"][0]["weight"] = 5e-324
    fix[2]["inputs"]["contexts"][0]["observations"][0].update(reported_count=0, count_relation="exact")
    save(fix)
    out = read(fix)["calculation_inputs"]
    assert out["contexts"][0]["weight"] == 5e-324
    assert out["contexts"][0]["observations"][0]["reported_count"] == 0


def test_source_order_is_root_fixed_literals_interpretations_dataset_with_callback_cache():
    fix = fixture()
    fix[1][OTHER] = dict(artifact_ref=ARTIFACT, content=TEXT.encode())
    fix[0]["literals"]["sample_frame"] = witness(source=OTHER, representation="text")
    fix[0]["interpretation_witnesses"] = [witness(source=OTHER, representation="text")]
    out = read(fix)
    assert out["sources"] == [SOURCE, OTHER, DATA]
    assert fix[3] == [(SOURCE, "original"), (OTHER, "text"), (DATA, "original")]
    assert out["interpretations"] == [{**witness(source=OTHER, representation="text"), "artifact_ref": ARTIFACT}]


@pytest.mark.parametrize("target", ["literal", "interpretation"])
@pytest.mark.parametrize("change", [dict(start=True), dict(start=-1), dict(end=10000),
    dict(start=0, end=1, quote="µ"), dict(quote="invented"), dict(representation="unsupported"), dict(extra=1)])
def test_witness_bytes_exact_quote_utf8_bounds_and_closed_fields(target, change):
    fix = fixture(populated=False)
    value = {**witness(), **change}
    if target == "literal": fix[0]["literals"]["endpoint"] = value
    else: fix[0]["interpretation_witnesses"] = [value]
    with pytest.raises(ExperimentalContractError):
        read(fix)


def test_schema_is_closed_detached_and_excludes_model_selected_numerical_operands():
    fix = fixture(populated=False)
    validate_schema(fix[0], context_population_schema())
    schema = context_population_schema()
    schema["properties"]["source_kind"]["enum"].append("bad")
    assert "bad" not in context_population_schema()["properties"]["source_kind"]["enum"]
    for extra in (dict(alpha=.05), dict(inputs=fix[2]["inputs"]), dict(score=1)):
        with pytest.raises(ContractError): validate_schema({**fix[0], **extra}, context_population_schema())
        with pytest.raises(ExperimentalContractError, match="closed_fields_required"):
            read_context_inputs({**fix[0], **extra}, read_source=fix[4])
    assert fix[3] == []


def test_authority_callback_failure_propagates_without_acquisition_or_fallback():
    fix = fixture()

    def denied(reference, representation):
        if reference == DATA: raise PermissionError("outside received scope")
        return fix[4](reference, representation)

    with pytest.raises(PermissionError, match="outside received scope"):
        read_context_inputs(fix[0], read_source=denied)
    assert fix[3] == [(SOURCE, "original")]


@pytest.mark.parametrize("value,error", [
    (dict(artifact_ref=ARTIFACT, content="not bytes"), "source_bytes_required"),
    (dict(artifact_ref="", content=b""), "nonempty_source_token_required"),
    (dict(artifact_ref=ARTIFACT, content=b"", extra=1), "closed_fields_required"),
])
def test_source_result_contract_remains_closed_and_exact(value, error):
    with pytest.raises(ExperimentalContractError, match=error):
        read_context_inputs(fixture()[0], read_source=lambda *_: value)


@pytest.mark.parametrize("field", ["reported_sd", "reported_sem", "reported_plusminus"])
@pytest.mark.parametrize("value", [0, .1])
def test_state_relations_do_not_have_numeric_error_magnitudes(field, value):
    fix = fixture()
    inputs = fix[2]["inputs"]
    inputs["requirements"][0].update(unit="state", supported=[], incompatible=[])
    item = inputs["contexts"][0]["observations"][0]
    item.update(unit="state", interval=None, relation="supported", reported_count=2,
                count_relation="exact", replicate_kind="biological")
    item[field] = value
    save(fix)
    with pytest.raises(ExperimentalContractError, match="state_uncertainty_requires_numeric_unit"):
        read(fix)
