"""Pure process facts preserve existing local quantities and typed boundaries."""
from copy import deepcopy
import json
from types import MappingProxyType, SimpleNamespace

import pytest

from gene_annotation_episode.communication import (ReportBoundaryError,
    validate_closed_schema, validate_form)
from gene_annotation_episode.domain import identity, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_reports import closing_yield, report_sources as yield_sources
from gene_annotation_episode.numerical import (NumericBand, SignedNumericBand,
    STATUS_INSUFFICIENT, STATUS_UNIDENTIFIABLE, YieldController, YieldEstimate)
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_records import scientific_invocation_ref
from gene_annotation_episode.scientific_process_reports import (build_process_result,
    credit_binding_ref, merge_process_results, project_process_result, report_sources, validate_process_result)
from test_scientific_process_library import independent_source, write


PATH = (("annotation", "root"), ("scientific_process", "child"))
METADATA = {"credit_kind": "scientific", "credit_binding": {
    "version": "fixture_existing_credit_v1", "projection": "original"}}


@pytest.fixture(scope="module")
def library(tmp_path_factory):
    directory = tmp_path_factory.mktemp("process-results")
    # Report contracts need an A reference, but no first-slot option is adopted
    # in the current publication. Use only invented engineering source material
    # here; the real P01-P19/source-row snapshot has its own persistence check.
    source = directory / "invented-source"
    bodies = independent_source(source)
    second = {**deepcopy(bodies[1]), "id": "P02", "name": "Second fixture contrast"}
    write(source / "entries/P02.json", second)
    index = json.loads((source / "index.json").read_text())
    index["entries"].append({**{key: second[key] for key in
        ("id", "slot", "name", "description")}, "detail_path": "entries/P02.json",
        "source_evidence_ids": ["E-P02-01"]})
    next(row for row in index["slots"] if row["slot"] == "thought_pattern")["count"] += 1
    write(source / "index.json", index)
    table = json.loads((source / "option_sources.json").read_text())
    table["rows"].append({"evidence_id": "E-P02-01", "option_id": "P02",
        **deepcopy(second["evidence"][0])})
    write(source / "option_sources.json", table)
    library = ScientificProcessLibrary.freeze(directory / "library", source=source)
    from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
    library.tool_library = ScientificToolLibrary.freeze(directory / "tools", catalog=[{
        "name": "fixture.inspect", "input_schema": obj({})}])
    return library


def selection(library, *, thought="P01", tools=("fixture.inspect",)):
    return {"version": "scientific_process_selection_v2",
        "annotation_ref": library.reference("A01"), "thought_ref": library.reference(thought),
        "tools": list(tools)}


def context(library, *, path=PATH, revision=False, thought="P01", tools=("fixture.inspect",)):
    assignment = {"selection": selection(library, thought=thought, tools=tools),
        "evidence_refs": [], "constraints": {}, "context": {}}
    if revision:
        assignment["revision_origin"] = {"version": "scientific_process_revision_origin_v1",
            "parent_invocation_ref": scientific_invocation_ref("fixture-run", path[:-1]),
            "preparation_operation_ref": "operation_" + "d" * 24}
    return BindingContext("fixture-run", "PRIVATE_AUDIT_EPISODE", path[-1][0], path,
        {"subject_refs": ["input_" + "a" * 24]}, assignment,
        {"goal": {"goal_id": "PRIVATE_AUDIT_GOAL"}, "message": {
            "scientific_invocation_ref": scientific_invocation_ref("fixture-run", path),
            "episode_assignment": deepcopy(assignment)}})


def snapshot(ctx, *, count=2, metadata=METADATA, episode_yield=None):
    return {"completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": count},
        "own_action_count": count, "initial_credit": 15.25, "credit": 14.5,
        "controller_credit": deepcopy(metadata), "episode_yield": deepcopy(episode_yield),
        "parent_invocation_ref": (scientific_invocation_ref(ctx.run_id, ctx.path[:-1])
                                  if len(ctx.path) > 1 else None)}


def row(library, **kwargs):
    ctx = context(library, **kwargs)
    return build_process_result(ctx, snapshot(ctx))


def test_source_is_closed_with_actual_slot_enums_and_semantic_namespaces(library):
    source = report_sources(library, library.tool_library)["scientific_process_results"]
    schema = obj({"parent_chosen_name": source["report_schema"]})
    validate_closed_schema(schema)
    properties = source["report_schema"]["items"]["properties"]
    assert properties["version"]["const"] == "scientific_process_result_v2"
    assert properties["selection"]["properties"]["version"]["const"] == "scientific_process_selection_report_v1"
    for field, slot in (("evidence_axis", "annotation_distinction"),
                        ("thought_pattern", "thought_pattern")):
        option = properties["selection"]["properties"][field]["properties"]
        expected = sorted(header["option_ref"]["option_id"] for header in library.headers()
                          if header["option_ref"]["slot"] == slot)
        assert option["option_id"] == {"type": "string", "enum": expected}
        assert option["slot"] == {"type": "string", "enum": [slot]}
        assert option["library_id"]["format"] == "identifier"
        assert option["library_id"]["x-reference-namespace"] == "scientific_process_library"
        assert option["entry_sha256"]["x-reference-namespace"] == "scientific_option_digest"
    assert properties["preparation_operation_ref"]["x-reference-namespace"] == "scientific_preparation"
    assert properties["credit_binding_ref"]["x-reference-namespace"] == "scientific_credit_binding"
    expected_yield = yield_sources()["episode_yield"]["report_schema"]
    expected_yield.pop("x-source")
    assert properties["episode_yield"] == expected_yield
    assert '"pattern"' not in json.dumps(schema)
    value = project_process_result(row(library), library=library, tool_library=library.tool_library)
    seen = []
    validate_form({"parent_chosen_name": [value]}, schema,
                  lambda reference, namespace: not seen.append((reference, namespace)))
    assert (value["invocation_ref"], "scientific_invocation") in seen
    with pytest.raises(ReportBoundaryError, match="unavailable"):
        validate_form({"parent_chosen_name": [value]}, schema, lambda *_: False)
    source["report_schema"]["items"]["properties"].clear()
    assert report_sources(library, library.tool_library)["scientific_process_results"]["report_schema"]["items"]["properties"]


def test_builder_copies_existing_baseline_and_closing_scalar_without_new_scores(library):
    ctx = context(library)
    closed = snapshot(ctx)
    value = build_process_result(ctx, closed)
    assert value == {"version": "scientific_process_result_v1",
        "invocation_ref": scientific_invocation_ref(ctx.run_id, ctx.path),
        "parent_invocation_ref": scientific_invocation_ref(ctx.run_id, ctx.path[:-1]),
        "origin_kind": "ordinary_child", "preparation_operation_ref": None,
        "selection": selection(library), "initial_credit": 15.25, "credit": 14.5,
        "credit_kind": "scientific", "credit_binding_ref": identity("scientific_credit_binding", METADATA),
        "completed_actions": 2, "episode_yield": None}
    assert "PRIVATE_AUDIT" not in json.dumps(value)
    assert "delta" not in value and "score" not in value
    closed["credit"] = 999
    closed["controller_credit"]["credit_binding"]["projection"] = "changed"
    value["selection"]["tools"].append("fixture.unknown")
    assert list(ctx.assignment["selection"]["tools"]) == ["fixture.inspect"]
    assert build_process_result(ctx, snapshot(ctx))["credit"] == 14.5


def test_builder_requires_actual_completion_and_does_not_touch_context_before_closure():
    class UnavailableContext:
        def __getattr__(self, key):
            raise AssertionError("No closing context read is available")
    assert build_process_result(UnavailableContext(), {}) is None
    assert build_process_result(UnavailableContext(), {"completion": None,
        "own_action_count": None}) is None


@pytest.mark.parametrize("band", [NumericBand.exact(0),
    SignedNumericBand(-3, -4, -2, uncertainty_code=0, alpha=0),
    NumericBand.coded(STATUS_INSUFFICIENT), NumericBand.coded(STATUS_UNIDENTIFIABLE)])
def test_builder_preserves_existing_signed_and_unavailable_closing_yields_without_refit(library, band):
    fits = []
    def estimate(history, parameters, contexts):
        fits.append(len(history))
        return YieldEstimate(len(history), band, parameters, {"private": "do not expose"})
    controller = YieldController("fixture", 15.25, 0, estimate_with_context=estimate)
    recorded = closing_yield(SimpleNamespace(controller_state=controller.state(), units_consumed=2))
    before = list(fits)
    ctx = context(library)
    value = build_process_result(ctx, snapshot(ctx, episode_yield=recorded))
    assert value["episode_yield"] == recorded
    assert fits == before
    assert value["episode_yield"]["expected_next_gain"] == band.as_record()
    assert "private" not in json.dumps(value)
    assert validate_process_result(value, library=library) == value


def test_explicit_origin_is_preserved_and_changed_options_alone_stay_ordinary(library):
    ordinary = row(library, thought="P02", tools=())
    revision = row(library, thought="P02", tools=(), revision=True)
    assert ordinary["selection"] == revision["selection"]
    assert ordinary["origin_kind"] == "ordinary_child"
    assert ordinary["preparation_operation_ref"] is None
    assert revision["origin_kind"] == "approach_revision"
    assert revision["preparation_operation_ref"] == "operation_" + "d" * 24


def test_root_and_unknown_actual_binding_keep_unknown_values(library):
    ctx = context(library, path=(("annotation", "root"),))
    value = build_process_result(ctx, snapshot(ctx, metadata=None))
    assert value["parent_invocation_ref"] is None
    assert value["credit_kind"] is None and value["credit_binding_ref"] is None
    assert value["episode_yield"] is None
    assert credit_binding_ref(None) is None


@pytest.mark.parametrize("kind", ["scientific", "monitoring", "operational"])
def test_binding_identity_uses_whole_actual_metadata_without_exporting_it(library, kind):
    ctx = context(library)
    metadata = {**deepcopy(METADATA), "credit_kind": kind}
    value = build_process_result(ctx, snapshot(ctx, metadata=metadata))
    assert value["credit_kind"] == kind
    assert value["credit_binding_ref"] == identity("scientific_credit_binding", metadata)
    assert credit_binding_ref(MappingProxyType(metadata)) == value["credit_binding_ref"]
    assert value["credit_binding_ref"] != identity("scientific_credit_binding", metadata["credit_binding"])
    assert "credit_binding" not in value


@pytest.mark.parametrize("change", ["invocation", "assignment", "origin", "parent", "count",
                                   "completion", "metadata"])
def test_builder_rejects_forged_original_relationships_and_closure_operands(library, change):
    ctx = context(library, revision=True)
    closed = snapshot(ctx)
    request = ctx.as_record()["request"]
    assignment = ctx.as_record()["assignment"]
    if change == "invocation":
        request["message"]["scientific_invocation_ref"] = "scientific_invocation_" + "f" * 24
    elif change == "assignment":
        assignment["selection"] = selection(library, thought="P02")
    elif change == "origin":
        assignment["revision_origin"]["parent_invocation_ref"] = "scientific_invocation_" + "f" * 24
        request["message"]["episode_assignment"] = assignment
    elif change == "parent":
        closed["parent_invocation_ref"] = "scientific_invocation_" + "f" * 24
    elif change == "count":
        closed["own_action_count"] = 3
    elif change == "completion":
        closed["completion"]["ended_by"] = "still_running"
    else:
        closed["controller_credit"] = {"credit_kind": "scientific", "credit_binding": {}}
    changed = BindingContext(ctx.run_id, ctx.episode_id, ctx.role, ctx.path, ctx.scope,
                             assignment, request)
    with pytest.raises(ValueError):
        build_process_result(changed, closed)


@pytest.mark.parametrize("changes", [
    {"extra": "unrestricted finding"}, {"initial_credit": float("nan")},
    {"credit": float("inf")}, {"credit": True}, {"completed_actions": True},
    {"completed_actions": -1}, {"credit_kind": "invented"},
    {"credit_kind": None}, {"credit_binding_ref": None},
    {"credit_binding_ref": "episode_" + "a" * 64},
    {"invocation_ref": "episode_" + "a" * 64},
    {"parent_invocation_ref": "goal_" + "a" * 24},
    {"origin_kind": "approach_revision"},
    {"preparation_operation_ref": "operation_" + "a" * 24},
    {"episode_yield": {"unrestricted": "summary"}},
])
def test_result_validator_rejects_nonfinite_open_or_incoherent_rows(library, changes):
    with pytest.raises(ValueError):
        validate_process_result({**row(library), **changes}, library=library)


def test_result_validator_checks_selection_namespace_and_actual_pinned_body(library):
    for field, changes in (("thought_ref", {"option_id": "T01"}),
                           ("annotation_ref", {"library_id": "f" * 64})):
        value = row(library)
        value["selection"][field].update(changes)
        with pytest.raises(ValueError):
            validate_process_result(value, library=library)
    value = row(library)
    value["selection"]["tools"] = {"descriptor": "unrestricted tool instructions"}
    with pytest.raises(ValueError):
        validate_process_result(value)
    schema = obj({"results": report_sources(library, library.tool_library)["scientific_process_results"]["report_schema"]})
    value = project_process_result(row(library), library=library, tool_library=library.tool_library)
    value["selection"]["child_tool_info"] = [{"name": "fabricated.tool", "resources": None}]
    with pytest.raises(ReportBoundaryError):
        validate_form({"results": [value]}, schema, lambda *_: True)


def test_result_validator_checks_parent_origin_and_yield_count_relationships(library):
    value = row(library)
    value["parent_invocation_ref"] = value["invocation_ref"]
    with pytest.raises(ValueError, match="parent_invalid"):
        validate_process_result(value)
    value = row(library, revision=True)
    value["parent_invocation_ref"] = None
    with pytest.raises(ValueError, match="origin_invalid"):
        validate_process_result(value)
    ctx = context(library)
    recorded = {"completed_actions": 3, "expected_next_gain": NumericBand.exact(0).as_record(),
                "continuation_cost": 0, "stop_requested": True}
    with pytest.raises(ValueError, match="yield_count_mismatch"):
        build_process_result(ctx, snapshot(ctx, episode_yield=recorded))


@pytest.mark.parametrize("invalid", [{"value": float("nan")}, {1: "coerced"},
                                    {"value": {1, 2}}, {}, []])
def test_binding_reference_requires_finite_detached_metadata(invalid):
    with pytest.raises(ValueError):
        credit_binding_ref(invalid)


def test_stable_merge_keeps_own_first_and_deduplicates_only_identical_invocations(library):
    own = row(library)
    child = row(library, path=(*PATH, ("scientific_process", "grandchild")))
    other = row(library, path=(*PATH, ("scientific_process", "other")), tools=())
    received = [deepcopy(child), deepcopy(own), deepcopy(child), deepcopy(other)]
    merged = merge_process_results(own, received)
    assert merged == [own, child, other]
    assert merge_process_results(None, received) == [child, own, other]
    merged[1]["credit"] = 999
    assert received[0]["credit"] == 14.5
    with pytest.raises(ValueError, match="result_conflict"):
        merge_process_results(own, [{**deepcopy(own), "credit": 999}])
    with pytest.raises(ValueError, match="result_conflict"):
        merge_process_results(None, [own, {**deepcopy(own), "initial_credit": 0}])
    with pytest.raises(ValueError):
        merge_process_results(None, {"invocation_ref": own["invocation_ref"]})
