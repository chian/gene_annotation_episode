"""Pure engineering instructions; no adopted catalog or target findings."""
from copy import deepcopy

import pytest

from method_loop.durable import content_digest
from gene_annotation_episode.credit import CreditPolicy
from gene_annotation_episode.domain import (FINDING_QUALIFICATIONS,
    OBSERVATION_KINDS, PREDICATES, RECORD_SCHEMAS)
from gene_annotation_episode.scientific_credit import AnnotationSupportScore
from gene_annotation_episode.scientific_support_metadata import (
    annotation_policy_routes, support_observation_kinds, validate_support_entry)


def support_entry():
    """Invented body and provenance, independent of production A allocation."""
    return {"entry_version": "scientific_support_entry_v1", "id": "A01",
        "slot": "annotation_distinction", "name": "Synthetic support problem",
        "description": "Engineering instruction only.", "support": {
            "proposition": "Inspect actual correspondence for the assigned question.",
            "operands": [{"operand_id": "correspondence",
                "observation_kinds": ["alignment", "comparison"],
                "hypothesis_predicates": ["functional_family"],
                "assessment_relations": ["strengthens", "weakens"],
                "applicabilities": ["transfer", "incomparable"],
                "extent_bases": ["inferred_extent"],
                "finding_qualifications": ["different_source_subject"],
                "instruction": "Retain the actual source and bounded target attribution."}],
            "qualifications": ["This is synthetic instruction content."],
            "boundary": "No target evidence or score is supplied by this body."},
        "evidence": [{"case_group": "synthetic", "case_id": "synthetic_record",
            "source_url": "https://example.org/synthetic",
            "source_locator": "Engineering fixture",
            "observation": "Invented instruction provenance.",
            "limit": "No biological observation or adopted catalog entry."}]}


def runtime_binding(projector, *, fixed_case=False):
    definition = projector.as_record()
    if fixed_case:
        definition = {"policy_source_sha256": "a" * 64,
            "policy_parameters_sha256": "b" * 64, "definition": definition}
    return {"projector": "gene_annotation_episode.scientific_credit.AnnotationSupportScore",
        "versions": {"requirement": "same_caller_injected_executable"},
        "definition": definition, "scope_source": "context.scope",
        "meaning": "Annotation support, separately bound from investigation progress and numerical yield."}


def test_support_validation_detaches_all_content_and_returns_sorted_kind_union():
    original = support_entry()
    other = deepcopy(original["support"]["operands"][0])
    other.update(operand_id="second", observation_kinds=["source_content", "alignment"])
    original["support"]["operands"].append(other)
    result = validate_support_entry(original)
    assert result == original and result is not original
    result["support"]["operands"][0]["instruction"] = "Changed caller copy."
    result["evidence"][0]["limit"] = "Changed caller copy."
    assert result != original
    assert support_observation_kinds(original) == ["alignment", "comparison", "source_content"]


@pytest.mark.parametrize("field,values", [
    ("observation_kinds", OBSERVATION_KINDS),
    ("hypothesis_predicates", PREDICATES),
    ("assessment_relations", RECORD_SCHEMAS["assessment"]["properties"]["relation"]["enum"]),
    ("applicabilities", RECORD_SCHEMAS["assessment"]["properties"]["applicability"]["enum"]),
    ("extent_bases", RECORD_SCHEMAS["assessment"]["properties"]["extent_basis"]["enum"]),
    ("finding_qualifications", FINDING_QUALIFICATIONS),
])
def test_support_accepts_every_existing_enum_and_rejects_unknown_empty_duplicate(field, values):
    entry = support_entry()
    entry["support"]["operands"][0][field] = list(values)
    assert validate_support_entry(entry) == entry
    for invalid in ([], ["invented_value"], [values[0], values[0]], None, values[0], tuple(values)):
        entry["support"]["operands"][0][field] = invalid
        with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
            validate_support_entry(entry)


@pytest.mark.parametrize("path", [(), ("support",), ("support", "operands", 0), ("evidence", 0)])
def test_every_object_has_closed_required_fields(path):
    original = support_entry()
    obj = original
    for key in path:
        obj = obj[key]
    fields = list(obj)
    for field in fields + ["extra"]:
        entry, value = deepcopy(original), None
        value = entry
        for key in path:
            value = value[key]
        if field == "extra":
            value[field] = "undeclared"
        else:
            value.pop(field)
        with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
            validate_support_entry(entry)


@pytest.mark.parametrize("path,invalid", [
    (("id",), "A01\n"), (("id",), "P01"), (("id",), "A"),
    (("entry_version",), "scientific_support_entry_v2"),
    (("slot",), "thought_pattern"), (("name",), " \n\t"),
    (("support", "proposition"), ""), (("support", "qualifications"), []),
    (("support", "qualifications"), ["same", "same"]),
    (("support", "operands"), []), (("evidence",), []),
    (("support", "operands", 0, "operand_id"), "two labels"),
    (("support", "operands", 0, "operand_id"), "label\n"),
    (("support", "boundary"), float("nan")),
    (("support", "boundary"), float("inf")),
    (("support", "boundary"), object()),
    (("evidence", 0, "source_locator"), {1: "not JSON"}),
])
def test_malformed_support_has_specific_syntax_failure(path, invalid):
    entry = support_entry()
    value = entry
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = invalid
    with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
        validate_support_entry(entry)


def test_duplicate_operand_identity_and_duplicate_source_rows_are_invalid():
    entry = support_entry()
    second = deepcopy(entry["support"]["operands"][0])
    second["instruction"] = "Different instruction cannot duplicate an operand ID."
    entry["support"]["operands"].append(second)
    with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
        validate_support_entry(entry)
    entry = support_entry()
    entry["evidence"].append(deepcopy(entry["evidence"][0]))
    with pytest.raises(ValueError, match="scientific_support_entry_invalid"):
        validate_support_entry(entry)


@pytest.mark.parametrize("fixed_case", [False, True])
def test_actual_policy_overrides_omissions_complete_record_and_binding_hash(fixed_case):
    policy = CreditPolicy(observation_axes=(("alignment", "mechanistic"), ("context", "empirical")),
        epsilon=.1, scale=7., target_weights=(("synthetic_target", 2.),))
    projector = AnnotationSupportScore(policy)
    binding = runtime_binding(projector, fixed_case=fixed_case)
    snapshot = deepcopy(binding)
    result = annotation_policy_routes(projector, binding,
        observation_kinds=["source_content", "comparison", "context", "alignment"])
    assert result == {"version": "scientific_support_routes_v1", "status": "available",
        "reason": None, "annotation_binding_sha256": content_digest(binding),
        **{key: projector.as_record()[key] for key in
           ("projection_version", "formula_version", "integration_arithmetic")},
        "policy": policy.as_record(), "routes": [
            {"observation_kind": "alignment", "status": "mapped", "axis": "mechanistic"},
            {"observation_kind": "comparison", "status": "unmapped", "axis": None},
            {"observation_kind": "context", "status": "mapped", "axis": "empirical"},
            {"observation_kind": "source_content", "status": "unmapped", "axis": None}]}
    result["policy"]["observation_axes"][0][1] = "comparative"
    assert binding == snapshot and policy.observation_axes[0][1] == "mechanistic"


def test_equivalent_descriptive_meaning_changes_only_binding_identity():
    projector = AnnotationSupportScore(CreditPolicy())
    binding = runtime_binding(projector)
    first = annotation_policy_routes(projector, binding, observation_kinds=["alignment"])
    binding["meaning"] = "The caller's annotation support declaration."
    second = annotation_policy_routes(projector, binding, observation_kinds=["alignment"])
    assert first["annotation_binding_sha256"] != second["annotation_binding_sha256"]
    first.pop("annotation_binding_sha256")
    second.pop("annotation_binding_sha256")
    assert first == second and first["status"] == "available"


def assert_unavailable(result, reason):
    assert result["status"] == "unavailable" and result["reason"] == reason
    assert all(result[key] is None for key in ("annotation_binding_sha256", "policy",
        "projection_version", "formula_version", "integration_arithmetic"))
    assert result["routes"] == [{"observation_kind": "alignment", "status": "unavailable", "axis": None}]


def test_absent_custom_and_missing_metadata_never_default_or_project(monkeypatch):
    projector = AnnotationSupportScore(CreditPolicy())
    binding = runtime_binding(projector)
    monkeypatch.setattr(AnnotationSupportScore, "__call__", lambda *a, **kw: pytest.fail("projection invoked"))
    monkeypatch.setattr(AnnotationSupportScore, "read_details", lambda *a, **kw: pytest.fail("details invoked"))
    # Any attempted default construction is a failure after the actual instance exists.
    monkeypatch.setattr(CreditPolicy, "__init__", lambda *a, **kw: pytest.fail("default policy constructed"))
    assert annotation_policy_routes(projector, binding, observation_kinds=[])["status"] == "available"
    for executable, metadata, reason in (
        (None, binding, "annotation_score_unbound"),
        (projector, None, "binding_definition_missing"),
        (lambda *a: pytest.fail("custom projector invoked"), binding, "unsupported_projector"),
        (projector, {}, "binding_definition_missing"),
        (projector, {**binding, "definition": None}, "binding_definition_missing"),
    ):
        assert_unavailable(annotation_policy_routes(executable, metadata,
            observation_kinds=["alignment"]), reason)
    class Pretend:
        @property
        def policy(self):
            pytest.fail("arbitrary policy attribute inspected")
    assert_unavailable(annotation_policy_routes(Pretend(), binding,
        observation_kinds=["alignment"]), "unsupported_projector")
    class Subclass(AnnotationSupportScore):
        pass
    assert_unavailable(annotation_policy_routes(Subclass(projector.policy), binding,
        observation_kinds=["alignment"]), "unsupported_projector")


@pytest.mark.parametrize("mutation", ["projector", "versions", "scope_source", "meaning",
    "extra_outer", "policy", "projection_version", "extra_definition", "recursive_wrapper",
    "extra_case", "bad_case_hash", "non_json", "boolean_number"])
def test_only_exact_known_envelopes_and_actual_complete_definition_are_available(mutation):
    projector = AnnotationSupportScore(CreditPolicy())
    binding = runtime_binding(projector)
    if mutation in {"projector", "scope_source", "meaning"}:
        binding[mutation] = " "
    elif mutation == "versions":
        binding["versions"]["requirement"] = "shape_only"
    elif mutation == "extra_outer":
        binding["extra"] = "unknown"
    elif mutation == "policy":
        binding["definition"]["policy"]["observation_axes"][0][1] = "comparative"
    elif mutation == "projection_version":
        binding["definition"]["projection_version"] = "unknown"
    elif mutation == "extra_definition":
        binding["definition"]["extra"] = "unknown"
    elif mutation == "recursive_wrapper":
        binding = runtime_binding(projector, fixed_case=True)
        binding["definition"]["definition"] = {"definition": projector.as_record()}
    elif mutation == "extra_case":
        binding = runtime_binding(projector, fixed_case=True)
        binding["definition"]["extra"] = "unknown"
    elif mutation == "bad_case_hash":
        binding = runtime_binding(projector, fixed_case=True)
        binding["definition"]["policy_source_sha256"] = "A" * 64
    elif mutation == "non_json":
        binding["definition"]["policy"]["scale"] = float("nan")
    elif mutation == "boolean_number":
        # True compares equal to 1.0 in Python; serialized meaning must still match exactly.
        binding["definition"]["policy"]["axis_weights"]["empirical"] = True
    assert_unavailable(annotation_policy_routes(projector, binding,
        observation_kinds=["alignment"]), "binding_definition_mismatch")


def test_direct_definition_is_not_a_runtime_envelope_and_all_kinds_keep_policy_mapping():
    projector = AnnotationSupportScore(CreditPolicy())
    assert_unavailable(annotation_policy_routes(projector, projector.as_record(),
        observation_kinds=["alignment"]), "binding_definition_missing")
    result = annotation_policy_routes(projector, runtime_binding(projector),
        observation_kinds=list(OBSERVATION_KINDS))
    assert [row["observation_kind"] for row in result["routes"]] == sorted(OBSERVATION_KINDS)
    actual = dict(projector.policy.observation_axes)
    assert all(row["axis"] == actual.get(row["observation_kind"]) for row in result["routes"])
    assert all(row["axis"] != "discrimination" for row in result["routes"])
    for kind in ("source_content", "source_annotation", "coordinate_mapping"):
        assert next(row for row in result["routes"] if row["observation_kind"] == kind)["status"] == "unmapped"


@pytest.mark.parametrize("invalid", [["unknown"], ["alignment", "alignment"], "alignment",
    ("alignment",), [None], {"alignment"}, None, [float("nan")]])
def test_route_requests_reject_undeclared_or_duplicate_kind_values(invalid):
    with pytest.raises(ValueError, match="scientific_support_observation_kinds_invalid"):
        annotation_policy_routes(None, None, observation_kinds=invalid)
