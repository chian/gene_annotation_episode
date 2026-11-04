"""Selected MinHash input custody and immutable publication recovery.

The native response is explicitly synthetic. Metadata sources are caller bytes
processed by the real material.parse operation. These focused tests journal
selected actions and original typed admissions directly; complete Workflow
execution is covered separately by the root-owned integration workload.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

from method_loop.identities import EpisodeRef

from gene_annotation_episode import api_bvbrc_minhash as module
from gene_annotation_episode.bvbrc_minhash_views import minhash_fact_sources
from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.practical_execution_state import _read
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from test_api_bvbrc_minhash import (
    CONFIGURATION, LAUNCH_OPERATIONS, RESULT_OPERATION, SERVICE,
    executor, harness, explicit_pair_inputs, request, selected_inputs,
)
from test_execution_episodes_family import select


SOURCE_SCHEMA = {"type": "object", "properties": {"source": {"type": "string",
    "format": "reference", "x-reference-namespace": "source"}},
    "required": ["source"], "additionalProperties": False}


def own_context(h, role, assignment, label, *, parent=None, index=None, schema=None):
    path = ((role, label),) if parent is None else (*parent.path, (role, "child_" + str(index)))
    episode = EpisodeRef(h.journal.run_id, path).episode_id
    contract = None if schema is None else {"decision": "Retain the requested typed result.",
        "measurements": {"schema": deepcopy(schema)}}
    message = {"scope": h.scope, "episode_assignment": deepcopy(assignment)}
    request_value = {"message": message, **({"report_contract": contract} if contract is not None else {})}
    ctx = BindingContext(h.journal.run_id, episode, role, path, h.scope, deepcopy(assignment), request_value)
    with h.store.transaction():
        if parent is not None:
            h.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
                "action": canonical({"kind": "episode_child", "role": role, "assignment": assignment}),
                "result": None, "credit": None})
        h.journal.save("runtime_episodes", {"episode_id": episode, "path": canonical(path),
            "request": canonical(request_value), "initial_credit": 0, "state": "running"})
    return ctx


def parse_selected(h, ctx, material, index=0):
    args = {"material_ref": material["id"], "format": "opaque"}
    key = f"{ctx.run_id}:{ctx.episode_id}:{index}"
    with h.store.transaction():
        h.journal.save("runtime_actions", {"episode_id": ctx.episode_id, "decision_index": index,
            "action": canonical({"kind": "tool", "tool": "material.parse", "arguments": args}),
            "result": None, "credit": None})
    outcome = h.tools.execute("material.parse", args, scope=h.scope, operation_key=key)
    assert outcome["status"] == "completed", outcome
    assert material["source_ref"] in outcome["record_refs"]
    with h.store.transaction():
        h.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(outcome), ctx.run_id, ctx.episode_id, index))
    return outcome


def admit(h, parent, child, index, form, schema, *, facts=None):
    """Persist the original immediate-child boundary used by the custody reader."""
    contract = child.request["report_contract"]
    assert contract["measurements"]["schema"] == schema
    if facts is None:
        facts = {node["x-source"]: form[name] for name, node in schema["properties"].items()
            if "x-source" in node}
    with h.store.transaction():
        h.journal.save("runtime_forms", {"episode_id": child.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        h.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": "controlled_delivery_" + str(index),
            "child_episode_id": child.episode_id, "contract": canonical(contract),
            "form": canonical(form), "failure": None})
    return h.family.minhash._attempt(parent, index)


def handoff(h, original=None, *, label="native"):
    original = request() if original is None else original
    assigned = {"version": "api_service_assignment_v1", "resource_id": "minhash",
        "service": SERVICE, "request": original, "endpoint": "usable_handoff", "constraints": {}}
    ctx = own_context(h, "launch_api", assigned, label)
    result = select(h, ctx, 0, LAUNCH_OPERATIONS[original["mode"]])
    assert result["status"] == "completed", result
    return result["record_refs"][0]


def results_context(h, parent, native, selector, index, *, schema=SOURCE_SCHEMA):
    return own_context(h, "results", {"version": "execution_results_assignment_v1",
        "handoff_ref": native, "selector": selector}, "unused", parent=parent, index=index, schema=schema)


def setup_inputs(h, *, mode="genome", values=None, child_receipt=False):
    h.client.rows = [["511145.12", "0.223144", "0.259259", "2/3"]]
    original = request(mode)
    material, metadata = explicit_pair_inputs(h, original, values=values)
    parent = own_context(h, "scientific_process", {}, "receiver")
    if child_receipt:
        child = own_context(h, "scientific_process", {}, "unused", parent=parent, index=0, schema=SOURCE_SCHEMA)
        parse_selected(h, child, material)
        admit(h, parent, child, 0, {"source": material["source_ref"]}, SOURCE_SCHEMA)
    else:
        parse_selected(h, parent, material)
    native = handoff(h, original)
    selector, expected = selected_inputs([metadata])
    return parent, native, selector, expected, material


@pytest.mark.parametrize("mode", ["genome", "fasta"])
@pytest.mark.parametrize("child_receipt", [False, True])
def test_exact_selected_source_custody_and_original_occurrences(executor, mode, child_receipt):
    h = executor
    parent, native, selector, expected, material = setup_inputs(h, mode=mode, child_receipt=child_receipt)
    validated = h.family.minhash.validate_inputs(parent, selector, request=request(mode), handoff_ref=native)
    assert validated == expected
    child = results_context(h, parent, native, selector, 1)
    assert h.family.minhash.publication_inputs(child, request=request(mode), selector=selector,
        handoff_ref=native) == expected
    duplicate, _ = selected_inputs(selector["pair_metadata"] * 2)
    bound = h.family.minhash.validate_inputs(parent, duplicate, request=request(mode), handoff_ref=native)
    assert [row["pair_metadata_index"] for row in bound["metadata_bindings"]] == [0]*4 + [1]*4
    assert bound["pair_metadata"][0] == bound["pair_metadata"][1]
    assert len(h.client.calls) == 1


@pytest.mark.parametrize("problem,code", [
    ("unreceived", "minhash_metadata_source_not_received"),
    ("missing", "minhash_metadata_source_missing"),
    ("artifact", "minhash_metadata_artifact_conflict"),
    ("pointer", "minhash_metadata_pointer_unavailable"),
    ("value", "minhash_metadata_value_conflict"),
    ("query", "minhash_metadata_query_conflict"),
    ("bytes", "minhash_metadata_artifact_conflict"),
])
def test_invalid_scalar_authority_is_specific_and_never_acquires(executor, monkeypatch, problem, code):
    h = executor
    parent, native, selector, _, material = setup_inputs(h)
    selected = deepcopy(selector)
    field = selected["pair_metadata"][0]["provenance"]["fields"][0]
    if problem == "unreceived":
        parent = own_context(h, "scientific_process", {}, "unrelated")
    elif problem == "missing":
        field["source_ref"] = "source_" + "f"*32
    elif problem == "artifact":
        field["artifact_ref"] = h.store.artifact(b"1", "application/json")
    elif problem == "pointer":
        field["record_path"] = "/absent"
    elif problem == "value":
        selected["pair_metadata"][0]["kmer_length"] = 2
    elif problem == "query":
        selected["pair_metadata"][0]["provenance"]["query_operand"] = "999.1"
    elif problem == "bytes":
        original = h.store.get_artifact
        reference = field["artifact_ref"]
        monkeypatch.setattr(h.store, "get_artifact", lambda ref: original(ref) + b" " if ref == reference else original(ref))
    count = h.store.count("source")
    with pytest.raises(ValueError, match=code) as failure:
        h.family.minhash.validate_inputs(parent, selected, request=request(), handoff_ref=native)
    if problem != "query":
        assert failure.value.detail["source_ref"] == field["source_ref"]
        assert failure.value.detail["field"] == "kmer_length"
    assert h.store.count("source") == count and len(h.client.calls) == 1


@pytest.mark.parametrize("scalar", [True, "1", 1.0])
def test_source_integer_is_not_coerced_from_boolean_string_or_float(executor, scalar):
    h = executor
    parent, native, selector, _, _ = setup_inputs(h)
    values = {"kmer_length": scalar, "query_length": 2, "reference_length": 2, "alphabet_size": 2}
    material = h.store.register_material(data=canonical(values).encode(), name="noninteger-source", format="opaque")
    parse_selected(h, parent, material, index=1)
    source = h.store.get(material["source_ref"])
    for evidence in selector["pair_metadata"][0]["provenance"]["fields"]:
        evidence.update(source_ref=source["id"], artifact_ref=source["artifact_ref"])
    with pytest.raises(ValueError, match="minhash_metadata_value_conflict"):
        h.family.minhash.validate_inputs(parent, selector, request=request(), handoff_ref=native)


def test_precommission_custody_rejects_late_receipt_and_changed_assignment(executor):
    h = executor
    h.client.rows = [["511145.12", ".1", ".2", "2/3"]]
    material, metadata = explicit_pair_inputs(h, request())
    selector, _ = selected_inputs([metadata])
    parent = own_context(h, "scientific_process", {}, "parent")
    native = handoff(h)
    child = results_context(h, parent, native, selector, 1)
    parse_selected(h, parent, material, index=2)
    with pytest.raises(ValueError, match="minhash_metadata_source_not_received"):
        h.family.minhash.validate_inputs(child, selector, request=request(), handoff_ref=native)
    parse_selected(h, parent, material, index=0)
    assert h.family.minhash.validate_inputs(child, selector, request=request(), handoff_ref=native)
    with h.store.transaction():
        h.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=1",
            (canonical({"kind": "episode_child", "role": "results", "assignment": {**child.assignment, "selector": {}}}),
                h.journal.run_id, parent.episode_id))
    with pytest.raises(ValueError, match="minhash_metadata_source_not_received"):
        h.family.minhash.validate_inputs(child, selector, request=request(), handoff_ref=native)
    with pytest.raises(ValueError, match="context_conflict"):
        h.family.minhash.validate_inputs(replace(parent, episode_id="copied-context"), selector,
            request=request(), handoff_ref=native)


@pytest.mark.parametrize("stage", ["inputs_frozen", "publication_committed"])
def test_interrupted_v2_uses_immutable_inputs_before_any_reextraction(executor, monkeypatch, stage):
    h = executor
    parent, native, selector, expected, _ = setup_inputs(h)
    child = results_context(h, parent, native, selector, 1)
    original = h.service.publish if stage == "inputs_frozen" else h.family._index_result
    first = True

    def interrupt_once(*args, **kwargs):
        nonlocal first
        if first:
            first = False
            raise asyncio.CancelledError()
        return original(*args, **kwargs)

    monkeypatch.setattr(h.service if stage == "inputs_frozen" else h.family,
        "publish" if stage == "inputs_frozen" else "_index_result", interrupt_once)
    with pytest.raises(asyncio.CancelledError):
        select(h, child, 0, RESULT_OPERATION)
    key = f"{child.run_id}:{child.episode_id}:0"
    directory = h.family._episode_directory(child.episode_id) / "actions" / digest(key)
    assert _read(directory / "publication_inputs.json") == expected
    frozen = (directory / "publication_inputs.json").read_bytes()

    def prohibited(*args, **kwargs):
        raise AssertionError("Recovery must use original frozen inputs and publications")

    monkeypatch.setattr(h.family.minhash, "metadata_bindings", prohibited)
    monkeypatch.setattr(h.family.minhash, "publication_inputs", prohibited)
    monkeypatch.setattr(h.client, "rpc", prohibited)
    if stage == "publication_committed":
        monkeypatch.setattr(h.service, "publish", prohibited)
        monkeypatch.setattr(module, "parse_minhash_result", prohibited)
        monkeypatch.setattr(module, "calculate_minhash_components", prohibited)
    result = asyncio.run(h.family.execute(child, RESULT_OPERATION, {}, key))
    assert result["status"] == "completed", result
    with h.store.transaction():
        h.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(result), child.run_id, child.episode_id))
    source = result["result"]["source_ref"]
    assert h.family.minhash.read_own(source, context=child)["grading"]["publication_inputs"] == expected
    assert result["result"]["acquisition_receipt"]["publication_inputs_sha256"] == digest(expected)
    assert (directory / "publication_inputs.json").read_bytes() == frozen
    assert asyncio.run(h.family.execute(child, RESULT_OPERATION, {}, key)) == result
    assert len(h.client.calls) == 1


def test_saved_selection_and_new_metadata_keep_original_acquisition_identity(executor, monkeypatch):
    h = executor
    parent, native, selector, _, _ = setup_inputs(h)
    first_child = results_context(h, parent, native, {}, 1)
    first = select(h, first_child, 0, RESULT_OPERATION)
    first_source = first["result"]["source_ref"]
    admit(h, parent, first_child, 1, {"source": first_source}, SOURCE_SCHEMA)
    original_bytes = h.store.get_artifact(first["result"]["grading_artifact_ref"])
    second_child = results_context(h, parent, native, selector, 2)
    second = select(h, second_child, 0, RESULT_OPERATION)
    second_source = second["result"]["source_ref"]
    admit(h, parent, second_child, 2, {"source": second_source}, SOURCE_SCHEMA)
    assert first_source != second_source
    assert h.family.result_identity(first_source, h.scope) == h.family.result_identity(second_source, h.scope)
    assert h.family.credit_view(second_child, {"known_record_refs": [first_source, second_source],
        "initial_known_record_refs": [first_source]})["new_acquired_record_count"] == 0
    changed_material, metadata = explicit_pair_inputs(h, request(), values={"kmer_length": 2,
        "query_length": 2, "reference_length": 2, "alphabet_size": 2})
    parse_selected(h, parent, changed_material, index=3)
    saved_selector = {"version": "bvbrc_minhash_result_selector_v2", "mode": "saved_sheet",
        "saved_result_ref": second_source, "pair_metadata": [metadata]}
    saved_inputs = h.family.minhash.validate_inputs(parent, saved_selector, request=request(), handoff_ref=native)
    third_child = results_context(h, parent, native, saved_selector, 4)
    monkeypatch.setattr(module, "parse_minhash_result", lambda *a, **k: pytest.fail("No native extraction for saved selection"))
    third = select(h, third_child, 0, RESULT_OPERATION)
    assert third["status"] == "completed", third
    third_source = third["result"]["source_ref"]
    grade = h.family.minhash.read_own(third_source, context=third_child)["grading"]
    assert grade["publication_inputs"] == saved_inputs
    assert grade["components"]["rows"][0]["recomputed_distance"] == pytest.approx(.11157177565710488)
    assert grade["components"]["rows"][0]["recomputed_pvalue"] == pytest.approx(.10400000000000001)
    assert len({h.family.result_identity(ref, h.scope) for ref in [first_source, second_source, third_source]}) == 1
    assert h.family.credit_view(third_child, {"known_record_refs": [second_source, third_source],
        "initial_known_record_refs": [second_source]})["new_acquired_record_count"] == 0
    assert h.store.get_artifact(first["result"]["grading_artifact_ref"]) == original_bytes
    assert len(h.client.calls) == 1


@pytest.mark.parametrize("conflict", ["request", "response", "receiver"])
def test_saved_source_requires_original_native_association_and_receipt(executor, conflict):
    h = executor
    parent, native, _, _, _ = setup_inputs(h)
    child = results_context(h, parent, native, {}, 1)
    published = select(h, child, 0, RESULT_OPERATION)
    source = published["result"]["source_ref"]
    admit(h, parent, child, 1, {"source": source}, SOURCE_SCHEMA)
    selector = {"version": "bvbrc_minhash_result_selector_v2", "mode": "saved_sheet",
        "saved_result_ref": source, "pair_metadata": []}
    original = request()
    if conflict == "receiver":
        parent = own_context(h, "scientific_process", {}, "other-receiver")
        code = "minhash_saved_result_not_received"
    else:
        if conflict == "request":
            original = request(max_hits=11)
        else:
            h.client.rows = [["511145.12", ".9", ".8", "1/3"]]
        native = handoff(h, original, label="different-native")
        code = "minhash_saved_result_" + conflict + "_conflict"
    count = h.store.count("source")
    with pytest.raises(ValueError, match=code):
        h.family.minhash.validate_inputs(parent, selector, request=original, handoff_ref=native)
    assert h.store.count("source") == count


def test_calculation_only_admission_resolves_genome_without_match_hydration(executor):
    h = executor
    parent, native, selector, _, _ = setup_inputs(h)
    schema = {"type": "object", "properties": {"calculations":
        minhash_fact_sources()["bvbrc_minhash_calculations"]["report_schema"]},
        "required": ["calculations"], "additionalProperties": False}
    child = results_context(h, parent, native, selector, 1, schema=schema)
    outcome = select(h, child, 0, RESULT_OPERATION)
    assert outcome["status"] == "completed", outcome
    facts = h.family.minhash.facts(child, schema)
    form = {"calculations": facts["bvbrc_minhash_calculations"]}
    admit(h, parent, child, 1, form, schema)
    assert h.family.minhash.resolve_received(parent, "511145.12", "bvbrc_minhash_genome")
    assert h.family.minhash.received_context(parent) == [{"fact_source": "bvbrc_minhash_calculations",
        "facts": form["calculations"]}]
    assert h.family.minhash.received_facts(parent, {"properties": {"matches":
        minhash_fact_sources()["bvbrc_minhash_matches"]["report_schema"]}}) == {"bvbrc_minhash_matches": []}
    assert validate_form(form, schema, lambda ref, namespace: h.family.minhash.resolve_received(parent, ref, namespace)) == form


def test_diagnostics_pattern_is_registered_only_as_the_exact_top_level_fact():
    field = minhash_fact_sources()["bvbrc_minhash_calculation_diagnostics"]["report_schema"]
    schema = {"type": "object", "properties": {"diagnostics": field},
        "required": ["diagnostics"], "additionalProperties": False}
    assert validate_closed_schema(schema) == schema
    altered = deepcopy(schema)
    altered["properties"]["diagnostics"]["items"]["properties"]["path"]["pattern"] = ".*"
    nested = {"type": "object", "properties": {"nested": schema},
        "required": ["nested"], "additionalProperties": False}
    unregistered = deepcopy(schema)
    del unregistered["properties"]["diagnostics"]["x-source"]
    for invalid in [altered, nested, unregistered]:
        with pytest.raises(ReportBoundaryError):
            validate_closed_schema(invalid)



def test_explicit_auxiliary_grading_artifact_keeps_original_source_binding(executor):
    h = executor
    parent, native, selector, _, _ = setup_inputs(h)
    child = results_context(h, parent, native, selector, 1)
    result = select(h, child, 0, RESULT_OPERATION)
    source = result["result"]["source_ref"]
    admit(h, parent, child, 1, {"source": source}, SOURCE_SCHEMA)
    selected = deepcopy(selector)
    evidence = selected["pair_metadata"][0]["provenance"]["fields"][0]
    evidence.update(source_ref=source, artifact_ref=result["result"]["grading_artifact_ref"],
        record_path="/grading/components/rows/0/calculation_inputs/kmer_length")
    inputs = h.family.minhash.validate_inputs(parent, selected, request=request(), handoff_ref=native)
    binding = inputs["metadata_bindings"][0]
    assert binding["source_ref"] == source and binding["artifact_ref"] == result["result"]["grading_artifact_ref"]
    assert binding["value"] == 1
    evidence["artifact_ref"] = result["result"]["raw_artifact_ref"]
    with pytest.raises(ValueError, match="minhash_metadata_pointer_unavailable"):
        h.family.minhash.validate_inputs(parent, selected, request=request(), handoff_ref=native)


def test_scalar_pointer_uses_rfc6901_escapes_and_exact_array_indices(executor):
    h = executor
    parent, native, selector, _, _ = setup_inputs(h)
    material = h.store.register_material(data=b'{"rows":[{"k/~":1}]}', name="escaped-pointer", format="opaque")
    parse_selected(h, parent, material, index=1)
    source = h.store.get(material["source_ref"])
    record = selector["pair_metadata"][0]
    record.update(query_length=None, reference_length=None, alphabet_size=None)
    record["provenance"]["fields"] = [{"field": "kmer_length", "source_ref": source["id"],
        "artifact_ref": source["artifact_ref"], "record_path": "/rows/0/k~1~0"}]
    inputs = h.family.minhash.validate_inputs(parent, selector, request=request(), handoff_ref=native)
    assert inputs["metadata_bindings"][0]["value"] == 1
    record["provenance"]["fields"][0]["record_path"] = "/rows/00/k~1~0"
    with pytest.raises(ValueError, match="minhash_metadata_pointer_unavailable"):
        h.family.minhash.validate_inputs(parent, selector, request=request(), handoff_ref=native)


def test_frozen_input_snapshot_cannot_disagree_with_original_grade_and_receipt(executor):
    h = executor
    parent, native, selector, _, _ = setup_inputs(h)
    child = results_context(h, parent, native, selector, 1)
    result = select(h, child, 0, RESULT_OPERATION)
    key = f"{child.run_id}:{child.episode_id}:0"
    path = h.family._episode_directory(child.episode_id) / "actions" / digest(key) / "publication_inputs.json"
    inputs = _read(path)
    # A closed but different supplied-input selection cannot replace the
    # original immutable snapshot, grade and acquisition receipt together.
    inputs["metadata_bindings"].reverse()
    path.write_text(canonical(inputs))
    with pytest.raises(ValueError, match="minhash_publication_inputs_conflict"):
        h.family.minhash.read_own(result["result"]["source_ref"], context=child)
