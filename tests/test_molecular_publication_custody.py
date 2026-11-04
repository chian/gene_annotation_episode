"""Engineered saved publications through actual Store/EPR/receipt authority.

No native conversion or registered scientific invocation is performed. Source
receipt shape and shared reader custody are exercised, not a global private
File resolver guard or a configured Workflow/tool route.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode import liftover_contracts as core
from gene_annotation_episode import molecular_measurement_tools as publications
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical, identity
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.molecular_sequence_input_bindings import MolecularSequenceInputBindings
from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading
from gene_annotation_episode.tools import ToolRegistry
from test_molecular_sequence_input_bindings import actual_received_input_owner


TOOL = "liftover_coordinates"


def forbidden(*_args, **_kwargs):
    raise AssertionError("saved publication attempted new work or premature private-byte access")


def all_rows(store):
    return {row[0]: sorted(tuple(value) for value in store.db.execute('SELECT * FROM "' + row[0] + '"'))
        for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def services_for(value):
    """Real Services routing with an engineered metadata-only Workflow facade."""
    return WorkflowServices(SimpleNamespace(store=value.store, run_id=value.owner.run_id,
        tools=None, initial_known_record_refs=(), episode_bindings=SimpleNamespace(
            resolve_received_reference=value.owner.resolve_received_reference)))


def scientific_value(request, state):
    if state == "unknown":
        call_state, count, result_state, native = "uncertain", None, "unavailable", None
        failure = dict(stage="execution", code="execution_unconfirmed", exception_type=None, exception_message=None)
    elif state == "not_started":
        call_state, count, result_state, native, failure = "not_started", 0, "unavailable", None, None
    else:
        call_state, count, result_state, failure = "returned", 1, "captured", None
        native = [] if state == "empty" else [["engineering_target", 17, "+", 91]]
    observation = dict(version=core.OBSERVATION_VERSION, request_sha256=core.liftover_request_sha256(request),
        chain_file=deepcopy(request["chain"]["file"]), software=dict(name="pyliftover", version=None),
        conversion_call_state=call_state, conversion_call_count=count, result_state=result_state,
        native_result=native, failure=failure)
    sheet = core.populate_liftover_sheet(request, native_observation=observation)
    return dict(version="ordinary_liftover_result_v1", request=deepcopy(request), sheet=sheet,
        components=core.calculate_liftover_components(sheet))


def save_operation(case, *, index, arguments, source_ref, name=TOOL):
    context, store, registry = case.producer, case.value.store, case.registry
    key = f"{context.run_id}:{context.episode_id}:{index}"
    operation_ref = identity("operation", dict(key=key, name=name, arguments=arguments))
    outcome = dict(status="completed", operation_ref=operation_ref, record_refs=[source_ref],
        result=dict(source_ref=source_ref), feedback=None)
    with store.transaction():
        registry._save(key, name, arguments, plain(context.scope), outcome)
        # Runtime adds pending-work context after the committed ToolOp. It is
        # not another producer or a scientific result change.
        recorded = {**outcome, "pending_work_after_action": dict(version="pending_work_v1", items=[],
            captured_at="2026-10-30T00:00:00+00:00")}
        store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,?)", (context.run_id, context.episode_id,
            index, canonical(dict(kind="tool", tool=name, arguments=arguments)), canonical(recorded)))
    return key


@contextmanager
def publication_case(tmp_path, *, state="mapping", corruption=None, deliver=True, producer=True, origin="tool"):
    raw = b"engineering supplied chain bytes; never parsed or converted\n"
    with actual_received_input_owner(tmp_path, raw=raw, namespace="artifact") as value:
        registry = ToolRegistry(value.store)
        received, path = value.binding.read_received_file(value.context, value.artifact_ref,
            "artifact", file_format="ucsc_chain")
        assert received["failure"] is None and path is not None
        request = dict(version=core.REQUEST_VERSION,
            chain=dict(file=deepcopy(received["input"]["file"]), source_ref=None),
            point=dict(chromosome="engineering_source", position_0based=7, strand="+"))
        # The prospective argument keys are explicitly selected by the host
        # design. These engineered committed records do not claim that a
        # registered tool or native operation accepted or executed them.
        witness = received["input"]["witness"]
        arguments = dict(mode="convert", input=dict(namespace=witness["namespace"], reference=witness["reference"]),
            chain_format=received["input"]["file"]["format"], point=deepcopy(request["point"]))
        if corruption == "input_file":
            other = value.store.get(value.text_ref)
            request["chain"]["file"].update(artifact_ref=other["id"], sha256=other["sha256"], size_bytes=other["size"])
        elif corruption == "input_format": request["chain"]["file"]["format"] = "ucsc_chain_gzip"
        elif corruption == "input_source": request["chain"]["source_ref"] = value.source_ref
        elif corruption == "input_point": request["point"]["position_0based"] += 1
        elif corruption == "input_selection": arguments["input"]["reference"] = value.text_ref
        stored = scientific_value(request, state)
        if corruption == "native_shape":
            stored["version"] = "not_the_selected_native_version"
        elif corruption == "native_components":
            stored["components"]["population"]["requested_point_count"] = 2
        native = value.store.artifact(canonical(stored), "application/json")
        invocation = dict(run_id=value.context.run_id, episode_id=value.context.episode_id,
            operation_key=f"{value.context.run_id}:{value.context.episode_id}:0", decision_index=0,
            request_sha256=hashlib.sha256(canonical(plain(value.context.request)).encode()).hexdigest(),
            scope=plain(value.context.scope))
        selected = dict(version="ordinary_liftover_request_v1", arguments=deepcopy(arguments),
            invocation=invocation, received_input=received["input"], request=deepcopy(request))
        control = dict(version="ordinary_liftover_publication_v1", request=selected, native_artifact_ref=native,
            execution_selection=None, native_handle=None, execution=None)
        grading = dict(sheet=deepcopy(stored["sheet"]), scores=deepcopy(stored["components"]))
        provider, grading_native = TOOL, native
        if corruption == "control_version": control["version"] = "another_publication_version"
        elif corruption == "control_request_version": selected["version"] = "another_request_version"
        elif corruption == "control_request_extra": selected["unrequested_control"] = None
        elif corruption == "control_native": control["native_artifact_ref"] = value.artifact_ref
        elif corruption == "control_arguments": selected["arguments"]["mode"] = "read_stored"
        elif corruption == "control_invocation": selected["invocation"]["operation_key"] += ":foreign"
        elif corruption == "control_scientific": selected["request"]["point"]["position_0based"] += 1
        elif corruption == "control_parent":
            selected["received_input"]["witness"]["namespace"] = "source"
            selected["received_input"]["witness"]["reference"] = value.source_ref
        elif corruption == "grading_provider": provider = "engineering_other"
        elif corruption == "grading_native": grading_native = value.artifact_ref
        elif corruption == "grading_values": grading["scores"]["population"]["requested_point_count"] = 2
        grade = retain_tool_grading(value.store, provider=provider, native_artifact_ref=grading_native, grading=grading)
        control_ref = value.store.artifact(canonical(control), "application/json")
        source_fields = dict(provider=TOOL, accession=None, uri=None, artifact_ref=native,
            text_ref=None, request_ref=control_ref, version="ordinary_liftover_result_v1", retrieved_at=None,
            **(dict(parent_source_refs=[], auxiliary_artifact_refs=[grade]) if origin == "tool" else {}))
        source = value.store.put("source", source_fields, origin=origin)
        case = SimpleNamespace(value=value, registry=registry, producer=value.context, source=source,
            arguments=arguments, stored=stored, control=control, native=native, control_ref=control_ref,
            grade=grade, private_refs={native, control_ref, grade}, services=services_for(value))
        if producer:
            case.operation_key = save_operation(case, index=0, arguments=arguments, source_ref=source["id"])
        before = set(value.receipts.known(value.parent.episode_id))
        if deliver:
            value.receipts.receive(value.parent.episode_id, [source["id"]], kind="decision_input", source_index=1)
            assert set(value.receipts.known(value.parent.episode_id)) == before | {source["id"]}
        case.receiver = value.child(1)
        assert not case.private_refs.intersection(value.receipts.known(case.receiver.episode_id))
        yield case


def read(case, *, reference=None, context=None):
    return publications.read_retained_molecular_publication(case.registry, context or case.receiver,
        case.services.read_received_molecular_input, reference or case.source["id"], tool_name=TOOL)


def guard_work(case, monkeypatch):
    from gene_annotation_episode import liftover_measurements, native_lifecycle
    monkeypatch.setattr(core, "calculate_liftover_components", forbidden)
    monkeypatch.setattr(liftover_measurements, "run_liftover_tool_request", forbidden)
    monkeypatch.setattr(publications, "run_owned_molecular_worker", forbidden)
    monkeypatch.setattr(case.registry.clients, "_http", forbidden)
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", forbidden)
    monkeypatch.setattr(case.value.receipts, "receive", forbidden)
    for name in ("prepare_job", "start_prepared", "resume_start", "collect", "wait_job"):
        monkeypatch.setattr(native_lifecycle, name, forbidden)
    # Liftover must use the actual Source-metadata service branch, not either
    # old File/JSON reader to obtain an ungranted native artifact.
    monkeypatch.setattr(MolecularSequenceInputBindings, "read_received", forbidden)
    monkeypatch.setattr(MolecularSequenceInputBindings, "read_received_file", forbidden)


@pytest.mark.parametrize("state", ["mapping", "unknown", "not_started", "empty"])
def test_source_only_publication_reads_exact_saved_cells_without_work_or_file_grants(tmp_path, monkeypatch, state):
    with publication_case(tmp_path, state=state) as case:
        guard_work(case, monkeypatch)
        before, changes = all_rows(case.value.store), case.value.store.db.total_changes
        result = read(case)
        assert result["admission_kind"] == "source_only"
        assert canonical(result["stored"]) == canonical(case.stored)
        assert canonical(result["control"]) == canonical(case.control)
        assert result["source"] == case.source and result["grading_ref"] == case.grade
        assert set(result["received_input"]) == {"receiver", "scope", "inheritance_manifest", "witness"}
        assert result["stored"]["sheet"]["observation"] == case.stored["sheet"]["observation"]
        assert not case.private_refs.intersection(case.value.receipts.known(case.receiver.episode_id))
        assert all_rows(case.value.store) == before and case.value.store.db.total_changes == changes


@pytest.mark.parametrize("original_present", [True, False])
def test_stored_read_rereturn_is_not_an_original_producer(tmp_path, monkeypatch, original_present):
    with publication_case(tmp_path) as case:
        save_operation(case, index=1, arguments=dict(mode="read_stored", result_ref=case.source["id"]),
            source_ref=case.source["id"])
        if not original_present:
            case.value.store.db.execute("DELETE FROM tool_operations WHERE operation_key=?", (case.operation_key,))
        guard_work(case, monkeypatch)
        if original_present:
            assert read(case)["control"]["request"]["invocation"]["decision_index"] == 0
        else:
            monkeypatch.setattr(case.value.store, "get_artifact", forbidden)
            with pytest.raises(ValueError, match="ordinary_liftover_publication_conflict"):
                read(case)


@pytest.mark.parametrize("change", ["missing_operation", "missing_action", "selected_name", "arguments", "scope",
    "operation_ref", "operation_key", "foreign_run", "ambiguous", "source_membership", "runtime_outcome", "fake_source"])
def test_producer_metadata_must_authenticate_before_any_private_bytes(tmp_path, monkeypatch, change):
    with publication_case(tmp_path, producer=change != "fake_source") as case:
        store, producer = case.value.store, case.producer
        key = (producer.run_id, producer.episode_id, 0)
        if change == "missing_operation": store.db.execute("DELETE FROM tool_operations WHERE operation_key=?", (case.operation_key,))
        elif change == "missing_action": store.db.execute("DELETE FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?", key)
        elif change in {"selected_name", "operation_ref", "runtime_outcome"}:
            row = store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?", key).fetchone()
            selected, outcome = json.loads(row["action"]), json.loads(row["result"])
            if change == "selected_name": selected["tool"] = "state.query"
            elif change == "operation_ref": outcome["operation_ref"] = "operation_" + "0" * 24
            else: outcome["status"] = "partial"
            store.db.execute("UPDATE runtime_actions SET action=?,result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
                (canonical(selected), canonical(outcome), *key))
        elif change == "arguments": store.db.execute("UPDATE tool_operations SET arguments=? WHERE operation_key=?", (canonical(dict(mode="convert", changed=True)), case.operation_key))
        elif change == "scope": store.db.execute("UPDATE tool_operations SET scope='{}' WHERE operation_key=?", (case.operation_key,))
        elif change == "operation_key": store.db.execute("UPDATE tool_operations SET operation_key='foreign-operation' WHERE operation_key=?", (case.operation_key,))
        elif change == "foreign_run": store.db.execute("UPDATE runtime_actions SET run_id='foreign-run' WHERE run_id=? AND episode_id=? AND decision_index=?", key)
        elif change == "source_membership":
            outcome = json.loads(store.db.execute("SELECT result FROM tool_operations WHERE operation_key=?", (case.operation_key,)).fetchone()[0])
            outcome["record_refs"] = []
            store.db.execute("UPDATE tool_operations SET result=? WHERE operation_key=?", (canonical(outcome), case.operation_key))
        elif change == "ambiguous":
            row = store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?", key).fetchone()
            store.db.execute("INSERT INTO runtime_actions VALUES(?,?,?,?,?)", (producer.run_id, producer.episode_id, 2, row["action"], row["result"]))
        monkeypatch.setattr(store, "get_artifact", forbidden)
        with pytest.raises(ValueError): read(case)


@pytest.mark.parametrize("change", ["unreceived", "wrong_type", "caller_origin", "source_identity", "receiver_context"])
def test_invalid_or_unreceived_source_fails_before_private_bytes(tmp_path, monkeypatch, change):
    with publication_case(tmp_path, deliver=change != "unreceived", origin="caller" if change == "caller_origin" else "tool") as case:
        reference, context = case.source["id"], case.receiver
        if change == "wrong_type": reference = case.value.artifact_ref
        elif change == "source_identity":
            source = {**case.source, "version": "forged_version"}
            case.value.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(source), reference))
        elif change == "receiver_context": context = replace(context, scope={"subject_refs": []})
        monkeypatch.setattr(case.value.store, "get_artifact", forbidden)
        with pytest.raises(ValueError): read(case, reference=reference, context=context)


@pytest.mark.parametrize("corruption", ["native_shape", "native_components", "control_version", "control_native",
    "control_request_version", "control_request_extra", "control_arguments", "control_invocation", "control_scientific", "control_parent", "grading_provider",
    "grading_native", "grading_values", "input_file", "input_format", "input_source", "input_point", "input_selection"])
def test_native_control_and_grading_values_must_match_one_publication(tmp_path, monkeypatch, corruption):
    with publication_case(tmp_path, corruption=corruption) as case:
        guard_work(case, monkeypatch)
        with pytest.raises(ValueError): read(case)


@pytest.mark.parametrize("target", ["native", "control_ref", "grade"])
@pytest.mark.parametrize("change", ["catalog_sha", "catalog_size"])
def test_private_artifact_catalog_identity_is_checked_for_native_control_and_grading(tmp_path, monkeypatch, target, change):
    with publication_case(tmp_path) as case:
        reference = getattr(case, target)
        store = case.value.store
        if change == "catalog_sha":
            value = json.loads(store.get_artifact(reference))
            other = store.artifact(json.dumps(value, indent=2), store.get(reference)["media_type"])
            assert other != reference
            store.db.execute("UPDATE artifacts SET sha256=? WHERE id=?", (store.get(other)["sha256"], reference))
            # The suffix/catalog contradiction is metadata-only and must fail
            # before a private body could be substituted by that new digest.
            original_get = store.get_artifact
            def no_substituted_body(selected):
                assert selected != reference, "catalog substitution reached private body reading"
                return original_get(selected)
            monkeypatch.setattr(store, "get_artifact", no_substituted_body)
        else:
            store.db.execute("UPDATE artifacts SET size=size+1 WHERE id=?", (reference,))
        with pytest.raises(ValueError): read(case)


def test_actual_service_source_metadata_route_does_not_open_or_grant_files(tmp_path, monkeypatch):
    with publication_case(tmp_path) as case:
        monkeypatch.setattr(case.value.store, "get_artifact", forbidden)
        monkeypatch.setattr(MolecularSequenceInputBindings, "read_received", forbidden)
        monkeypatch.setattr(MolecularSequenceInputBindings, "read_received_file", forbidden)
        before = all_rows(case.value.store)
        result = case.services.read_received_molecular_input(case.receiver, case.source["id"], "source", source_metadata_only=True)
        assert result["failure"] is None and result["input"]["witness"]["record"] == case.source
        assert set(result["input"]) == {"receiver", "scope", "inheritance_manifest", "witness"}
        assert all_rows(case.value.store) == before
        assert not case.private_refs.intersection(case.value.receipts.known(case.receiver.episode_id))


@pytest.mark.parametrize("branch", ["raw", "json"])
def test_actual_service_preserves_old_raw_tuple_and_json_routes(tmp_path, monkeypatch, branch):
    raw = b'{"version":"engineering_v1","value":0}'
    with actual_received_input_owner(tmp_path, raw=raw) as value:
        services = services_for(value)
        monkeypatch.setattr(MolecularSequenceInputBindings, "read_received_source", forbidden)
        if branch == "raw":
            monkeypatch.setattr(MolecularSequenceInputBindings, "read_received", forbidden)
            result, path = services.read_received_molecular_input(value.context, value.artifact_ref,
                "artifact", file_format="binary_native")
            assert result["failure"] is None and path.read_bytes() == raw
            assert result["version"] == "molecular_sequence_received_file_result_v1"
        else:
            monkeypatch.setattr(MolecularSequenceInputBindings, "read_received_file", forbidden)
            result = services.read_received_molecular_input(value.context, value.artifact_ref, "artifact", tag_key="version")
            assert result["failure"] is None and result["input"]["content"]["value"] == json.loads(raw)
            assert result["version"] == "molecular_sequence_received_input_result_v1"


@pytest.mark.parametrize("namespace,selection", [
    ("source", {}), ("source", dict(tag_key="version", file_format="json")),
    ("source", dict(tag_key="version", source_metadata_only=True)),
    ("source", dict(file_format="raw", source_metadata_only=True)),
    ("source", dict(tag_key="version", file_format="raw", source_metadata_only=True)),
    ("artifact", dict(source_metadata_only=True)), ("source", dict(source_metadata_only=1)),
])
def test_service_rejects_mixed_empty_or_wrong_namespace_selection_before_owner_or_bytes(tmp_path, monkeypatch, namespace, selection):
    with actual_received_input_owner(tmp_path) as value:
        services = services_for(value)
        monkeypatch.setattr(MolecularSequenceInputBindings, "__init__", forbidden)
        monkeypatch.setattr(value.store, "get_artifact", forbidden)
        with pytest.raises(ValueError, match="molecular_sequence_input_invalid_selection"):
            services.read_received_molecular_input(value.context, value.reference, namespace, **selection)
