"""Mother-binding checks with the fixed library/resolver/service contracts.

These are engineering fixtures, not model-driven biological investigations.
"""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_scientific_process_library import synthetic_support_entry
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, identity, obj
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_records import (scientific_digest,
    scientific_invocation_ref, validate_invocation_ref, validate_revision,
    validate_revision_origin)


CATALOG = (Path(__file__).resolve().parents[1] / "research/slotted_process_library"
           / "publications/2026-10-21-001")
EVIDENCE = "observation_" + "a" * 24
SUBJECT = "input_" + "b" * 24
SCOPE = {"subject_refs": [SUBJECT]}
SCHEMA = obj({"status": {"type": "string", "enum": ["unresolved", "qualified"]},
    "basis": {"type": "array", "items": {"type": "string", "format": "reference",
        "x-reference-namespace": "observation"}}})
INVOCATION = {"objective": "Resolve the assigned molecular uncertainty",
    "purpose": "Return status and its actual observation basis",
    "report_schema": SCHEMA, "initial_report": {"status": "unresolved", "basis": []}}
PRIMITIVE = {"name": "fixture.inspect", "description": "Selected evidence inspection",
    "input_schema": obj({"value": {"type": "integer", "minimum": 0, "maximum": 10}})}


class ContractLibrary:
    """Exact SL1 refs/bodies without depending on its persistence implementation."""

    def __init__(self):
        # Production has no adopted first-slot option pending the support/scoring
        # review. This explicitly invented A body exercises the binding contract;
        # it is neither a recovered biological claim nor production availability.
        self.entries = {
            "A01": synthetic_support_entry([{
                "case_group": "synthetic_fixture", "case_id": "synthetic_record",
                "source_url": "https://example.org/synthetic-fixture", "source_locator": "fixture",
                "observation": "Synthetic instruction relationship.",
                "limit": "Engineering metadata only; no biological evidence."}]),
            "P01": json.loads((CATALOG / "entries/P01.json").read_text())}
        other = deepcopy(self.entries["P01"])
        other.update(id="P99", name="New data-defined thought pattern",
            live_alternatives=["The upstream operation explains the observed endpoint.",
                               "A downstream contributor explains it."],
            decision_guidance=["Keep competing ownership explanations live."], evidence=[])
        self.entries["P99"] = other
        self.library_id = scientific_digest(self.entries)

    def as_record(self):
        return {"version": "scientific_process_library_v1", "library_id": self.library_id,
                "manifest_sha256": scientific_digest({"entries": self.entries})}

    def reference(self, option_id):
        entry = self.entries[option_id]
        return {"version": "scientific_process_option_ref_v1", "library_id": self.library_id,
            "slot": entry["slot"], "option_id": option_id,
            "entry_sha256": scientific_digest(entry)}

    def resolve(self, reference):
        if reference != self.reference(reference["option_id"]):
            raise ContractError("fixture_option_identity_mismatch")
        return deepcopy(self.entries[reference["option_id"]])

    def headers(self):
        return tuple({"option_ref": self.reference(option_id), "name": entry["name"],
            "description": entry["description"]} for option_id, entry in sorted(self.entries.items()))


class ContractServices:
    def __init__(self):
        self.available = [deepcopy(PRIMITIVE), {"name": "fixture.excluded",
            "description": "Must not leak into the child", "input_schema": obj({})}]
        self.calls, self.preparations, self.preparation_reads = [], {}, []
        self.received, self.semantic_refs = [], set()
        self.frozen = {}

    def reference_in_scope(self, reference, scope, namespace):
        return (plain(scope) == SCOPE and reference in {EVIDENCE, SUBJECT}
            and (namespace is None or reference == EVIDENCE and namespace == "observation"))

    def tool_catalog(self, scope):
        assert plain(scope) == SCOPE
        return deepcopy(self.available)

    async def execute_tool(self, name, arguments, *, scope, operation_key):
        self.calls.append((name, deepcopy(arguments), plain(scope), operation_key))
        return {"status": "completed", "record_refs": [], "changed_record_refs": [],
                "result": {"observed": arguments["value"]}}

    def scientific_preparation(self, context, preparation_ref, *, owner="self"):
        self.preparation_reads.append((context.path, preparation_ref, owner))
        path = context.path if owner == "self" else context.path[:-1]
        expected = scientific_invocation_ref(context.run_id, path)
        result = self.preparations.get((expected, preparation_ref))
        if result is None:
            raise ValueError("fixture_completed_preparation_unavailable")
        return deepcopy(result)

    def record_preparation(self, context, arguments, outcome):
        assert outcome["status"] == "completed"
        owner = scientific_invocation_ref(context.run_id, context.path)
        self.preparations[(owner, outcome["operation_ref"])] = {
            "operation_ref": outcome["operation_ref"], "owner_invocation_ref": owner,
            "owner_selection": plain(context.assignment["selection"]),
            "arguments": deepcopy(arguments), "proposal": deepcopy(outcome["result"]),
            "revision_origin": deepcopy(outcome["revision_origin"])}

    def scientific_received_results(self, context):
        return deepcopy(self.received)

    def scientific_frozen_results(self, context):
        return deepcopy(self.frozen.get(context.episode_id))

    def scientific_reference(self, context, reference, namespace):
        return ((namespace, reference) in self.semantic_refs
            or namespace is None and any(ref == reference for _, ref in self.semantic_refs))

    def scientific_credit(self, context, receiver_selection):
        return {"credit": 7, "binding": "unchanged_fixture_projection"}

    def scientific_support_routes(self, context, *, observation_kinds):
        from gene_annotation_episode.scientific_support_metadata import annotation_policy_routes
        return annotation_policy_routes(None, None, observation_kinds=observation_kinds)


def selection(library, *, thought="P01", tools=("fixture.inspect",)):
    return {"version": "scientific_process_selection_v2",
        "annotation_ref": library.reference("A01"), "thought_ref": library.reference(thought),
        "tools": list(tools)}


def prepared(binding, *, thought="P01", tools=("fixture.inspect",), evidence_refs=None, parent=None,
             revision_origin=None, schema=None):
    assignment = {"selection": selection(binding.library, thought=thought, tools=tools),
        "evidence_refs": [EVIDENCE] if evidence_refs is None else evidence_refs,
        "constraints": {"reference_subjects_only": True}, "context": {"condition": "fixture"}}
    if revision_origin is not None:
        assignment["revision_origin"] = deepcopy(revision_origin)
    invocation = deepcopy(INVOCATION)
    if schema is not None:
        invocation["report_schema"] = deepcopy(schema)
    return binding.prepare_invocation(parent or SimpleNamespace(role="annotation", path=(("annotation", "root"),)), "scientific_process",
        assignment, SCOPE, "original-operation", invocation=invocation)


def make_context(binding, *, path=None, **kwargs):
    value = prepared(binding, **kwargs)
    path = path or (("annotation", "root"), ("scientific_process", "child_0"))
    return BindingContext("fixture-run", "fixture-child", "scientific_process",
        path, SCOPE,
        value["assignment"], {"goal": {"objective": INVOCATION["objective"]},
            "report_contract": {"decision": INVOCATION["purpose"],
                                "measurements": {"schema": deepcopy(kwargs.get("schema") or SCHEMA)}},
            "message": {"scope": deepcopy(SCOPE),
                "scientific_invocation_ref": scientific_invocation_ref("fixture-run", path),
                "initial_report": deepcopy(INVOCATION["initial_report"]),
                "episode_assignment": value["assignment"],
                "scientific_process": value["scientific_process"]}})


@pytest.fixture
def mother(tmp_path):
    library, services = ContractLibrary(), ContractServices()
    from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
    tools = ScientificToolLibrary.freeze(tmp_path / "tools", catalog=services.available)
    binding = ScientificProcessEpisodes(services, library=library,
        tool_library=tools,
        child_roles=("scientific_process", "literature", "resource_launch", "monitor", "resource_results"))
    return binding, services


def test_one_registered_role_accepts_new_data_defined_thought_without_altering_form(mother):
    binding, _ = mother
    registry = EpisodeBindingRegistry([binding])
    assert registry.roles == ("scientific_process",)
    first, second = make_context(binding), make_context(binding, thought="P99")
    assert type(first) is type(second)
    assert binding.decision_context(first, {})["scientific_process"]["thought"]["id"] == "P01"
    assert binding.decision_context(second, {})["scientific_process"]["thought"]["id"] == "P99"
    assert plain(second.request["report_contract"]["measurements"]["schema"]) == SCHEMA
    assert plain(second.request["message"]["initial_report"]) == INVOCATION["initial_report"]
    assert "operation_kind" not in json.dumps(plain(second.request))
    assert set(prepared(binding)) == {"assignment", "scientific_process"}


def test_evidence_is_validated_and_exposed_only_as_inherited_references(mother):
    binding, services = mother
    child = make_context(binding)
    assert binding.initial_references(child) == [EVIDENCE]
    assert binding.credit_view(child, {}) == {"credit": 7, "binding": "unchanged_fixture_projection"}
    assert not services.calls
    assert binding.initial_references(SimpleNamespace(role="annotation")) == []
    for refs in ([EVIDENCE, EVIDENCE], ["observation_" + "d" * 24], ["@invented"], ["E-A01-01"]):
        with pytest.raises(ValueError):
            prepared(binding, evidence_refs=refs)


@pytest.mark.parametrize("bad", [{"invalid": float("nan")}, {"invalid": float("inf")},
                                  {1: "coerced"}, {"unsupported": {1, 2}}])
def test_assignment_uses_finite_canonical_json_without_key_coercion(mother, bad):
    binding, _ = mother
    assignment = {"selection": selection(binding.library), "evidence_refs": [],
                  "constraints": bad, "context": {}}
    with pytest.raises(ValueError):
        binding.prepare_invocation(SimpleNamespace(role="annotation", path=(("annotation", "root"),)), "scientific_process",
            assignment, SCOPE, "finite-json", invocation=INVOCATION)


@pytest.mark.parametrize("change", ["objective", "scope", "initial_report", "purpose",
                                   "form", "assignment", "binding", "binding_version", "selection", "invocation_ref"])
def test_original_request_digests_detect_changed_parent_inputs(mother, change):
    binding, _ = mother
    child = make_context(binding)
    request, assignment, scope = plain(child.request), plain(child.assignment), deepcopy(SCOPE)
    if change == "objective":
        request["goal"]["objective"] = "Different job"
    elif change == "scope":
        request["message"]["scope"]["subject_refs"] = []
    elif change == "initial_report":
        request["message"]["initial_report"]["status"] = "qualified"
    elif change == "purpose":
        request["report_contract"]["decision"] = "Different requested meaning"
    elif change == "form":
        request["report_contract"]["measurements"]["schema"]["properties"]["status"]["enum"].append("other")
    elif change == "assignment":
        assignment["constraints"]["reference_subjects_only"] = False
        request["message"]["episode_assignment"] = assignment
    elif change == "binding":
        request["message"]["scientific_process"]["mechanics_binding"]["configuration"]["child_roles"] = []
    elif change == "binding_version":
        request["message"]["scientific_process"]["mechanics_binding"]["version"] = "scientific_process_episodes_v1"
    elif change == "invocation_ref":
        request["message"]["scientific_invocation_ref"] = scientific_invocation_ref("foreign", child.path)
    else:
        request["message"]["scientific_process"]["selection"]["thought_ref"] = binding.library.reference("P99")
    changed = BindingContext(child.run_id, child.episode_id, child.role, child.path, scope, assignment, request)
    with pytest.raises(ValueError, match="scientific_filled_identity_mismatch"):
        binding.validate_context(changed)


def test_frame_contains_selected_guidance_and_binding_limits_without_source_cases(mother):
    binding, _ = mother
    child = make_context(binding)
    frame = binding.decision_context(child, {})["scientific_process"]
    assert frame["thought"]["live_alternatives"]
    assert frame["thought"]["outcome_contingencies"]
    assert frame["annotation"]["support"] == binding.library.entries["A01"]["support"]
    assert frame["annotation_support_routes"]["reason"] == "annotation_score_unbound"
    assert [entry["name"] for entry in frame["tools"]] == ["fixture.inspect"]
    assert frame["permitted_children"] == list(binding.child_roles("scientific_process"))
    serialized = json.dumps(frame)
    assert "example_structured_values" not in serialized
    assert "source_locator" not in serialized and "E-A01-01" not in serialized
    assert "mappings" not in serialized and "fixture.excluded" not in serialized


def test_catalog_and_execution_enforce_same_selected_schema_scope_and_operation(mother):
    binding, services = mother
    child = make_context(binding)
    names = [row["name"] for row in binding.catalog(child)]
    assert names == ["fixture.inspect", "process.revise"]
    success = asyncio.run(binding.execute(child, "fixture.inspect", {"value": 2}, "selected-key"))
    assert success["status"] == "completed"
    assert services.calls == [("fixture.inspect", {"value": 2}, SCOPE, "selected-key")]
    for name, arguments in [("fixture.inspect", {"value": 11}), ("fixture.excluded", {}),
                            ("fixture.inspect", {"value": 2, "extra": True})]:
        invalid = asyncio.run(binding.execute(child, name, arguments, "invalid-key"))
        assert invalid["status"] == "invalid" and not invalid["record_refs"]
    assert len(services.calls) == 1
    whitelist = binding.common_tool_names(child)
    assert "fixture.inspect" in whitelist and "process.revise" in whitelist
    assert "episode.estimate_wait" in whitelist and "process.sources" in whitelist
    assert "fixture.excluded" not in whitelist


def test_unbound_tool_context_is_visible_and_does_not_reject_invocation(mother):
    binding, _ = mother
    child = make_context(binding, tools=())
    assert [row["name"] for row in binding.catalog(child)] == ["process.revise"]
    tools = binding.decision_context(child, {})["scientific_process"]["tools"]
    assert tools == []
    outcome = asyncio.run(binding.execute(child, "fixture.inspect", {"value": 2}, "unbound"))
    assert outcome["status"] == "invalid"


def test_revision_prepares_copyable_child_origin_and_leaves_original_frame_fixed(mother):
    binding, services = mother
    child = make_context(binding)
    original = plain(child.request)
    arguments = {"thought_ref": binding.library.reference("P99"), "tools": []}
    outcome = asyncio.run(binding.execute(child, "process.revise", arguments, "revision-key"))
    assert outcome["status"] == "completed"
    proposal = outcome["result"]
    assert set(proposal) == {"version", "parent_selection_sha256", "selection"}
    assert proposal["version"] == "scientific_process_child_selection_v1"
    assert proposal["parent_selection_sha256"] == scientific_digest(plain(child.assignment["selection"]))
    assert outcome["operation_ref"] == identity("operation", {
        "key": "revision-key", "name": "process.revise", "arguments": arguments})
    assert outcome["revision_origin"] == {"version": "scientific_process_revision_origin_v1",
        "parent_invocation_ref": scientific_invocation_ref(child.run_id, child.path),
        "preparation_operation_ref": outcome["operation_ref"]}
    assert outcome["record_refs"] == outcome["changed_record_refs"] == []
    frame = binding.decision_context(child, {})["scientific_process"]
    assert frame["thought"]["id"] == "P01" and [entry["name"] for entry in frame["tools"]] == ["fixture.inspect"]
    assert "revision" not in frame and "revision_decision_index" not in frame
    assert frame["selection"]["annotation_ref"] == plain(child.assignment["selection"]["annotation_ref"])
    assert plain(child.request) == original
    assert not services.calls and not services.preparation_reads
    repeated = asyncio.run(binding.execute(child, "process.revise", arguments, "repeat-key"))
    assert repeated["result"] == proposal
    assert repeated["revision_origin"]["preparation_operation_ref"] != outcome["operation_ref"]
    assert repeated["record_refs"] == repeated["changed_record_refs"] == []
    assert binding.credit_view(child, {})["credit"] == 7


def test_revision_cannot_change_annotation_or_library_or_add_freehand_fields(mother):
    binding, _ = mother
    child = make_context(binding)
    base = {"thought_ref": binding.library.reference("P99"), "tools": []}
    for update in ({"annotation_ref": binding.library.reference("A01")}, {"findings": "invented"}):
        outcome = asyncio.run(binding.execute(child, "process.revise", {**base, **update}, "invalid"))
        assert outcome["status"] == "invalid"
    foreign = deepcopy(base)
    foreign["thought_ref"]["library_id"] = "f" * 64
    outcome = asyncio.run(binding.execute(child, "process.revise", foreign, "foreign"))
    assert outcome["status"] == "invalid"


def test_revision_origin_authenticates_one_preparation_on_fill_and_restoration(mother):
    binding, services = mother
    parent = make_context(binding)
    arguments = {"thought_ref": binding.library.reference("P99"), "tools": []}
    outcome = asyncio.run(binding.execute(parent, "process.revise", arguments, "prepared-revision"))
    with pytest.raises(ValueError, match="completed_preparation_unavailable"):
        prepared(binding, thought="P99", tools=(), parent=parent,
            revision_origin=outcome["revision_origin"])
    services.record_preparation(parent, arguments, outcome)
    children = [make_context(binding, thought="P99", tools=(), parent=parent,
        revision_origin=outcome["revision_origin"],
        path=(*parent.path, ("scientific_process", f"revision_{index}"))) for index in range(2)]
    for child in children:
        binding.validate_context(child)
        assert plain(child.assignment["revision_origin"]) == outcome["revision_origin"]
        assert binding.decision_context(child, {})["scientific_process"]["thought"]["id"] == "P99"
    assert {row[2] for row in services.preparation_reads} == {"self", "parent"}
    assert binding.decision_context(parent, {})["scientific_process"]["thought"]["id"] == "P01"
    # Restoring the same filled request under another parent cannot reuse it.
    moved = BindingContext(children[0].run_id, children[0].episode_id, children[0].role,
        (("annotation", "other"), *children[0].path[1:]), SCOPE,
        plain(children[0].assignment), {**plain(children[0].request), "message": {
            **plain(children[0].request["message"]), "scientific_invocation_ref":
            scientific_invocation_ref(children[0].run_id,
                (("annotation", "other"), *children[0].path[1:]))}})
    with pytest.raises(ValueError, match="completed_preparation_unavailable"):
        binding.validate_context(moved)


@pytest.mark.parametrize("change", ["owner", "operation", "origin", "digest", "arguments", "selection", "fields"])
def test_revision_origin_rejects_foreign_or_mismatched_preparation_records(mother, change):
    binding, services = mother
    parent = make_context(binding)
    arguments = {"thought_ref": binding.library.reference("P99"), "tools": []}
    outcome = asyncio.run(binding.execute(parent, "process.revise", arguments, "prepared-revision"))
    services.record_preparation(parent, arguments, outcome)
    key = (scientific_invocation_ref(parent.run_id, parent.path), outcome["operation_ref"])
    row = services.preparations[key]
    if change == "owner":
        row["owner_invocation_ref"] = scientific_invocation_ref("foreign", parent.path)
    elif change == "operation":
        row["operation_ref"] = "operation_" + "e" * 24
    elif change == "origin":
        row["revision_origin"]["preparation_operation_ref"] = "operation_" + "e" * 24
    elif change == "digest":
        row["proposal"]["parent_selection_sha256"] = "e" * 64
    elif change == "arguments":
        row["arguments"]["thought_ref"] = binding.library.reference("P01")
    elif change == "selection":
        row["proposal"]["selection"]["tools"] = ["fixture.inspect"]
    else:
        row["findings"] = "unrequested"
    with pytest.raises(ValueError, match="scientific_revision_preparation"):
        prepared(binding, thought="P99", tools=(), parent=parent,
            revision_origin=outcome["revision_origin"])


def test_revision_origin_is_not_required_for_other_parent_selected_processes(mother):
    binding, services = mother
    parent = make_context(binding)
    arguments = {"thought_ref": binding.library.reference("P99"), "tools": []}
    outcome = asyncio.run(binding.execute(parent, "process.revise", arguments, "unselected-proposal"))
    services.record_preparation(parent, arguments, outcome)
    ordinary = make_context(binding, thought="P99", tools=("fixture.inspect",), parent=parent,
        path=(*parent.path, ("scientific_process", "ordinary")))
    assert "revision_origin" not in plain(ordinary.assignment)
    assert not services.preparation_reads


def test_semantic_invocation_and_origin_records_are_finite_exact_and_stable():
    path = (("annotation", "root"), ("scientific_process", "child_0"))
    reference = scientific_invocation_ref("fixture-run", path)
    assert reference == scientific_invocation_ref("fixture-run", [list(part) for part in path])
    assert reference == identity("scientific_invocation", {"run_id": "fixture-run",
        "path": [list(part) for part in path]})
    assert validate_invocation_ref(reference) == reference
    for run_id, bad_path in [(None, path), ("", path), ("fixture-run", []),
                             ("fixture-run", [("role", 2)]), ("fixture-run", "role/key")]:
        with pytest.raises(ValueError):
            scientific_invocation_ref(run_id, bad_path)
    origin = {"version": "scientific_process_revision_origin_v1", "parent_invocation_ref": reference,
              "preparation_operation_ref": "operation_" + "a" * 24}
    parsed = validate_revision_origin(origin)
    parsed["preparation_operation_ref"] = "operation_" + "b" * 24
    assert parsed != origin
    for bad in ({**origin, "extra": 1}, {**origin, "parent_invocation_ref": "episode_" + "a" * 24},
                {**origin, "preparation_operation_ref": "operation_" + "a" * 64}):
        with pytest.raises(ValueError):
            validate_revision_origin(bad)


def test_historical_revision_parser_remains_an_inspection_only_wire_parser(mother):
    binding, _ = mother
    historical = {"version": "scientific_process_revision_v1",
        "initial_selection_sha256": "a" * 64, "previous_selection_sha256": "b" * 64,
        "selection": selection(binding.library, thought="P99")}
    assert validate_revision(historical) == historical
    frame = binding.decision_context(make_context(binding), {})["scientific_process"]
    assert frame["thought"]["id"] == "P01" and "revision" not in frame


def test_ordinary_child_with_different_process_does_not_infer_revision_origin(mother):
    binding, services = mother
    child = make_context(binding, thought="P99", tools=())
    frame = binding.decision_context(child, {})["scientific_process"]
    assert frame["thought"]["id"] == "P99" and frame["tools"] == []
    assert "revision_origin" not in plain(child.assignment)
    assert not services.preparation_reads


def test_closing_form_and_credit_use_original_binding_without_reading_private_revisions(mother):
    binding, services = mother
    child = make_context(binding)
    binding.validate_report(child, {"status": "qualified", "basis": [EVIDENCE]}, SCHEMA)
    assert binding.facts(child, {}) == {"scientific_process_results": []}
    # Additional registered action readers may expose their own recorded facts.
    assert {
        "scientific_process_results", "reference_site_rows", "blast_hsp_column_rows",
        "restriction_mapping_results"} <= set(binding.fact_sources(child.role))
    assert binding.initial_references(child) == [EVIDENCE]
    assert binding.credit_view(child, {})["credit"] == 7
    with pytest.raises(ValueError):
        binding.validate_report(child, {"status": "invented", "basis": []}, SCHEMA)
    with pytest.raises(ValueError):
        binding.validate_report(child, {"status": "qualified", "basis": ["observation_" + "e" * 24]}, SCHEMA)


def test_requested_process_facts_copy_closed_credit_and_merge_only_received_rows(mother):
    binding, services = mother
    source = binding.fact_sources("scientific_process")["scientific_process_results"]
    schema = obj({**SCHEMA["properties"], "processes": deepcopy(source["report_schema"])})
    child = make_context(binding, schema=schema)
    parent_ref = scientific_invocation_ref(child.run_id, child.path[:-1])
    snapshot = {"completion": {"ended_by": "yield_stop", "end_reason": "", "units_consumed": 3},
        "own_action_count": 3, "initial_credit": 11, "credit": 7, "controller_credit": None,
        "episode_yield": None, "parent_invocation_ref": parent_ref}
    own = binding.facts(child, snapshot)["scientific_process_results"][0]
    assert own == {"version": "scientific_process_result_v3", "proposed_annotation_ref": None,
        "invocation_ref": scientific_invocation_ref(child.run_id, child.path),
        "parent_invocation_ref": parent_ref, "origin_kind": "ordinary_child",
        "preparation_operation_ref": None, "selection": {
            "version": "scientific_process_selection_report_v1",
            "source_version": "scientific_process_selection_v2",
            "evidence_axis": binding.library.reference("A01"),
            "thought_pattern": binding.library.reference("P01"),
            "child_tool_info": [{"name": "fixture.inspect", "resources": None}]},
        "initial_credit": 11, "credit": 7, "credit_kind": None, "credit_binding_ref": None,
        "completed_actions": 3, "episode_yield": None}
    received = {**deepcopy(own), "invocation_ref": scientific_invocation_ref(child.run_id,
        (*child.path, ("scientific_process", "received"))),
        "parent_invocation_ref": own["invocation_ref"], "initial_credit": 30, "credit": 25,
        "completed_actions": 2}
    services.received = [received, own, received]
    assert binding.facts(child, snapshot) == {"scientific_process_results": [own, received]}
    assert binding.facts(child, {"completion": None}) == {
        "scientific_process_results": [received, own]}
    assert binding.credit_view(child, {}) == {"credit": 7, "binding": "unchanged_fixture_projection"}
    assert not services.calls
    services.received.append({**received, "credit": 24})
    with pytest.raises(ValueError):
        binding.facts(child, snapshot)


def test_mother_report_resolver_honors_process_metadata_and_validates_result_bodies(mother):
    binding, services = mother
    child = make_context(binding)
    result = binding.facts(child, {"completion": {"ended_by": "yield_stop", "end_reason": "",
        "units_consumed": 1}, "own_action_count": 1, "initial_credit": 9, "credit": 7,
        "controller_credit": None, "episode_yield": None,
        "parent_invocation_ref": scientific_invocation_ref(child.run_id, child.path[:-1])})[
            "scientific_process_results"][0]
    for reference in (result["invocation_ref"], result["parent_invocation_ref"]):
        services.semantic_refs.add(("scientific_invocation", reference))
    for ref in result["selection"].values():
        if isinstance(ref, dict):
            services.semantic_refs.add(("scientific_process_library", ref["library_id"]))
            services.semantic_refs.add(("scientific_option_digest", ref["entry_sha256"]))
    schema = obj({"chosen_name": binding.fact_sources(child.role)["scientific_process_results"]["report_schema"]})
    services.frozen[child.episode_id] = [deepcopy(result)]
    binding.validate_report(child, {"chosen_name": [result]}, schema)
    assert binding.resolve(child, result["invocation_ref"], "scientific_invocation")
    assert binding.resolve(child, EVIDENCE, "observation")
    assert not binding.resolve(child, EVIDENCE, "scientific_invocation")
    forged = deepcopy(result)
    forged["selection"]["thought_pattern"]["option_id"] = "P99"
    with pytest.raises(ValueError):
        binding.validate_report(child, {"chosen_name": [forged]}, schema)
    # Shape-valid scalar/selection changes still fail against the actual frozen
    # source; library membership alone cannot authenticate a returned result.
    from gene_annotation_episode.communication import ReportBoundaryError
    for field, value in (("credit", 100), ("initial_credit", 0), ("completed_actions", 2)):
        forged = deepcopy(result)
        forged[field] = value
        with pytest.raises(ReportBoundaryError) as failure:
            binding.validate_report(child, {"chosen_name": [forged]}, schema)
        assert failure.value.diagnostic["code"] == "scientific_process_result_source_mismatch"
        assert failure.value.diagnostic["field"] == "chosen_name"
    other = binding.library.reference("P99")
    services.semantic_refs.add(("scientific_option_digest", other["entry_sha256"]))
    forged = deepcopy(result)
    forged["selection"]["thought_pattern"] = other
    with pytest.raises(ReportBoundaryError) as failure:
        binding.validate_report(child, {"chosen_name": [forged]}, schema)
    assert failure.value.diagnostic["code"] == "scientific_process_result_source_mismatch"
    services.frozen.pop(child.episode_id)
    with pytest.raises(ReportBoundaryError) as failure:
        binding.validate_report(child, {"chosen_name": [result]}, schema)
    assert failure.value.diagnostic["code"] == "scientific_process_result_source_mismatch"
    services.frozen[child.episode_id] = [deepcopy(result)]
    services.semantic_refs.remove(("scientific_invocation", result["parent_invocation_ref"]))
    with pytest.raises(ValueError):
        binding.validate_report(child, {"chosen_name": [result]}, schema)


def test_declared_child_edges_keep_specialist_branches_separate(mother):
    binding, _ = mother
    child = make_context(binding)
    assert binding.allowed_children(child, ()) == ("scientific_process", "literature", "resource_launch",
                                                   "monitor", "resource_results")
    assert "literature_strategy" not in binding.roles
    assert binding.permitted_common_actions(child) == ("tool", "reason", "child", "wait", "redeliver_report")
    with pytest.raises(ValueError):
        ScientificProcessEpisodes(binding.services, library=binding.library,
            tool_library=binding.tool_library, child_roles=("literature",))


def test_setup_freezes_descriptor_without_executable_services_and_reopens_original(tmp_path):
    from gene_annotation_episode.episode_composition import reopen_scientific_binding
    from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
    from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
    from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
    descriptor = prepare_scientific_binding(run_directory=tmp_path, source_directory=CATALOG,
        tool_catalog=[{**PRIMITIVE, "resources": "local"}],
        child_roles=("scientific_process", "literature"))
    assert descriptor["version"] == "scientific_process_episodes_v10"
    assert set(descriptor["configuration"]) == {"library", "tool_library", "child_roles"}
    library = ScientificProcessLibrary(tmp_path / "scientific-process-library")
    tools = ScientificToolLibrary(tmp_path / "scientific-tool-library")
    reopened = ScientificProcessEpisodes(None, library=library, tool_library=tools,
        child_roles=("scientific_process", "literature"))
    assert reopened.as_record() == descriptor
    assert reopen_scientific_binding(None, descriptor=descriptor,
        directory=tmp_path).as_record() == descriptor
    assert prepare_scientific_binding(run_directory=tmp_path, source_directory=tmp_path / "missing-source",
        tool_catalog=[{**PRIMITIVE, "resources": "local"}],
        child_roles=("scientific_process", "literature")) == descriptor


def test_scientific_task_yield_uses_its_own_credit_units_and_cutoff():
    assignment = {'proposed_annotation_ref': 'hypothesis_' + 'c' * 24,
        'context': {'evidence_task': {'version': 'evidence_axis_task_v1',
            'kind': 'whole_axis_findings', 'evidence_axis': 'A105', 'credit_unit': 3}}}
    context = BindingContext('run_fixture', 'episode_fixture', 'scientific_process',
        (('annotation', 'root'), ('scientific_process', 'child')), SCOPE,
        assignment, {'message': {'scope': SCOPE, 'episode_assignment': assignment}})
    owner = ScientificProcessEpisodes.__new__(ScientificProcessEpisodes)
    owner._original_selection = lambda _: {'version': 'scientific_process_selection_v3',
        'evidence_axis': {'option_id': 'A105'}}
    owner.library = SimpleNamespace(resolve=lambda _: {'entry_version': 'evidence_axis_instruction_v1'})
    credit = owner.credit_projector(context).as_record()
    owner._yield_bindings = {'A105:whole_axis_findings': {'kind': 'accumulation',
        'cutoff': .075, 'parameters': {'uncertainty_alpha': .05},
        'credit_definition': credit}}
    controller = owner.yield_controller(context, 3, 'scientific_epoch')
    assert controller.initial_credit == 3 and controller.cost == .075
    assert controller.settings.uncertainty_alpha == .05
    owner._yield_bindings['A105:whole_axis_findings']['credit_definition'] = {'kind': 'wrong_units'}
    with pytest.raises(ContractError, match='scientific_yield_credit_definition_mismatch'):
        owner.yield_controller(context, 3, 'scientific_epoch')
    owner._yield_bindings.clear()
    with pytest.raises(ContractError, match='scientific_yield_binding_missing_for_task'):
        owner.yield_controller(context, 3, 'scientific_epoch')


def test_bounded_sequence_task_privately_binds_its_native_score_range():
    from gene_annotation_episode.numerical import BoundedYieldController
    assignment = {'proposed_annotation_ref': 'hypothesis_' + 'c' * 24, 'context': {}}
    context = BindingContext('run_fixture', 'episode_fixture', 'scientific_process',
        (('annotation', 'root'), ('scientific_process', 'child')), SCOPE,
        assignment, {'message': {'scope': SCOPE, 'episode_assignment': assignment}})
    owner = ScientificProcessEpisodes.__new__(ScientificProcessEpisodes)
    owner._original_selection = lambda _: {'version': 'scientific_process_selection_v3',
        'evidence_axis': {'option_id': 'A101'}}
    owner.library = SimpleNamespace(resolve=lambda _: {'entry_version': 'evidence_axis_instruction_v1'})
    projector = owner.credit_projector(context)
    task = owner.continuation_task(context)
    owner._yield_bindings = {task: {'kind': 'bounded_quality', 'cutoff': .02,
        'parameters': {'uncertainty_alpha': .05},
        'credit_definition': projector.as_record()}}
    controller = owner.yield_controller(context, .8, 'sequence_epoch')
    assert isinstance(controller, BoundedYieldController)
    assert controller.maximum_credit == 1. and controller.cost == .02
    owner._yield_bindings[task]['kind'] = 'accumulation'
    with pytest.raises(ContractError, match='scientific_yield_method_credit_mismatch'):
        owner.yield_controller(context, .8, 'sequence_epoch')


def test_a104_panel_task_privately_binds_delivered_artifact_completion():
    from gene_annotation_episode.numerical import CompletionYieldController
    assignment = {'proposed_annotation_ref': 'hypothesis_' + 'c' * 24,
        'context': {'a104_task': {'name': 'panel_identity'}}}
    context = BindingContext('run_fixture', 'episode_fixture', 'scientific_process',
        (('annotation', 'root'), ('scientific_process', 'child')), SCOPE,
        assignment, {'message': {'scope': SCOPE, 'episode_assignment': assignment}})
    owner = ScientificProcessEpisodes.__new__(ScientificProcessEpisodes)
    owner._original_selection = lambda _: {'version': 'scientific_process_selection_v3',
        'evidence_axis': {'option_id': 'A104'}}
    owner.library = SimpleNamespace(resolve=lambda _: {'entry_version': 'evidence_axis_instruction_v1'})
    projector = owner.credit_projector(context)
    task = owner.continuation_task(context)
    assert projector.as_record()['kind'] == 'a104_panel_identity_delivered'
    assert task == 'A104:panel_identity'
    owner._yield_bindings = {task: {'kind': 'completion', 'cutoff': .075,
        'parameters': {'uncertainty_alpha': .05},
        'credit_definition': projector.as_record()}}
    controller = owner.yield_controller(context, 0, 'panel_epoch')
    assert isinstance(controller, CompletionYieldController)
    assert controller.cost == .075


def test_private_scientific_credit_rejects_missing_proposed_annotation():
    assignment = {'context': {}}
    context = BindingContext('run_fixture', 'episode_fixture', 'scientific_process',
        (('annotation', 'root'), ('scientific_process', 'child')), SCOPE,
        assignment, {'message': {'scope': SCOPE, 'episode_assignment': assignment}})
    owner = ScientificProcessEpisodes.__new__(ScientificProcessEpisodes)
    owner._yield_bindings = {}
    with pytest.raises(ContractError, match='scientific_task_proposed_annotation_required'):
        owner.credit_projector(context)
