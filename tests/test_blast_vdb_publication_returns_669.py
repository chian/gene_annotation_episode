"""VDB saved publication and controlled immediate-child returns, in bounded529.

Controlled capture/return fixtures are engineering evidence, not native VDB
execution or a production episode. No native helper or acquisition is invoked.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MethodType, SimpleNamespace

import pytest

from gene_annotation_episode import blast_utility_result_views as views
from gene_annotation_episode import native_blast_utility_result_publication as publication
from gene_annotation_episode import native_blast_utility_results as results
from gene_annotation_episode import native_blast_utility_result_worker as worker
from gene_annotation_episode import native_blast_utility_acquisition as acquisition
from gene_annotation_episode.blast_vdb_utility_inputs import parse_blast_vdb_extraction, parse_blast_vdb_inspection
from gene_annotation_episode.communication import form_with_facts, validate_form
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULTS_VERSION
from gene_annotation_episode.numerical import NumericBand, YieldParameters
from gene_annotation_episode.native_blast_utility_returns import NativeBLASTUtilityReturns
from gene_annotation_episode.practical_execution_state import _immutable
from gene_annotation_episode.practical_yield import PracticalYieldEstimator
from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading
from gene_annotation_episode.state import Store
from test_blast_utility_episode_wiring_632 import context
from test_blast_vdb_utility_inputs_663 import occurrence, supplied
from test_native_blast_utility_publication_631 import (
    capture_fixture as classic_capture_fixture, inline_workers, prepare, publish,
    selector as classic_selector,
)
from test_native_blast_utility_producer_628 import POLICY
from test_practical_yield import completion_context


def selector(**changes):
    return {"version": "native_blast_utility_result_selector_v2", "sequences": None,
        "database_fields": [], "integrity": None, "preparation": None,
        "prepared_database": False, "include_checks": False, "artifacts": [],
        "saved_data": [], "paths": None, "vdb_context": False, **changes}


def sequence_selection(*ordinals, fields=(), sequence_fields=("normalized_sequence",), identity=False):
    return {"selection": {"kind": "selector_ordinals", "values": list(ordinals)},
        "record_fields": list(fields), "sequence_fields": list(sequence_fields),
        "include_vdb_identity": identity}


def report_schema(*fields):
    properties = {name: deepcopy(views.FACT_SOURCES["execution.blast_utility_" + name]["report_schema"])
        for name in fields}
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def forbidden(*args, **kwargs):
    pytest.fail("saved publication attempted original parsing, metadata authentication, or native work")


def test_legacy_publication_and_old_body_have_no_v2_enrichment(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    store, capture = classic_capture_fixture(tmp_path)
    try:
        prepared = prepare(store, capture, tmp_path)
        chosen = classic_selector(sequences={"selector_ordinals": [0], "sequence_fields": ["original_sequence"]})
        output = publish(store, prepared, chosen, tmp_path)
        assert set(prepared) == publication._PREPARED_FIELDS
        assert set(output) == publication._PUBLICATION_FIELDS
        assert output["version"] == publication.PUBLICATION_VERSION
        envelope = publication._json(store, output["projection_artifact_ref"])
        assert envelope["version"] == publication.PROJECTION_VERSION
        assert set(envelope["projection"]) == set(views.PROJECTION_FIELDS)
        h = return_host(tmp_path, store, {"resource_kind": "local", "assignment": {
            "requested_job": {"native_blast_utility": {"operation": prepared["operation"]}}}})
        schema = report_schema("sequences", "paths", "path_sections", "vdb_context")
        child = context(h, "results", {"selector": chosen}, schema=schema)
        body = {"version": results.VERSION, "complete": True,
            **{key: output[key] for key in views.PROJECTION_FIELDS}}
        original = deepcopy(body)
        monkeypatch.setattr(h.family.native_blast_utility_results, "_own_bodies", lambda ctx: iter([body]))
        facts = h.family.native_blast_utility_results.facts(child)
        for name in ("paths", "path_sections", "vdb_context"):
            assert facts["execution.blast_utility_" + name] == [] and name not in body
        assert body == original
    finally:
        store.close()


def return_host(tmp_path, store, target):
    """Actual journal/reader, with an explicitly controlled physical-target port."""
    scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
    journal = Journal(store, "controlled-vdb-return-669")
    owner = SimpleNamespace(store=store, directory=tmp_path / "run", run_id=journal.run_id,
        resources={"local": {"policy": deepcopy(POLICY)}}, acquired_record_unit=2, handoff_unit=3)
    owner._target = lambda ctx: deepcopy(target)
    owner._selected_result_action = MethodType(ExecutionEpisodes._selected_result_action, owner)
    owner._result_directory = MethodType(ExecutionEpisodes._result_directory, owner)
    owner.job_progress_provider = SimpleNamespace(targets=SimpleNamespace(
        read_target=lambda reference, scope: deepcopy(target)))
    owner.native_blast_utility_results = results.NativeBLASTUtilityResults(owner)
    owner.native_blast_utility_returns = NativeBLASTUtilityReturns(owner)
    return SimpleNamespace(store=store, scope=scope, journal=journal, family=owner,
        receipts=EpisodeReceipts(store, journal.run_id), tmp_path=tmp_path)


def pure_return_case(tmp_path, monkeypatch, *, mode="extract_sequences", artifacts=False):
    """Pure result fixture starts at the authenticated-body port, not capture."""
    store = Store(tmp_path / "store")
    private = store.artifact(b'{"controlled_metadata":true}')
    bundle = store.artifact(b'{"controlled_return_fixture":true}')
    source = store.put("source", {"provider": "episode.execution_result", "accession": "controlled669",
        "version": "native_blast_utility_bundle_v1", "uri": None, "artifact_ref": bundle,
        "text_ref": None, "request_ref": None, "auxiliary_artifact_refs": [private],
        "retrieved_at": "2026-10-28T00:00:00+00:00"}, origin="tool")["id"]
    raw = b"A\ta\t4\tacgt\n" if mode == "extract_sequences" else b"VDB(s): \n/supplied/tiny.vdb\nVDB Alias File(s): None\nBlats DB Alias File(s): None\n"
    args = supplied(raw, mode=mode)
    args["database_binding"]["source_ref"] = source
    for row in args["vdb_context"]["source_inputs"] + args["vdb_context"]["entry_identifier_bindings"]:
        row["source"] = {"source_ref": private, "pointer": ""}
    db = occurrence(b"controlled database", oid="db-file", role="database_file", fmt="unknown", direction="input")
    manifest = occurrence(b"controlled manifest", oid="db-manifest", role="database_manifest", fmt="json", direction="input")
    for data in (raw, b"", b"controlled database", b"controlled manifest"):
        store.artifact(data)
    full_context = {"operation": args["operation"], "native_outcome": args["outcome"],
        "database_binding": args["database_binding"], "operation_input_occurrences": [],
        "occurrences": [db, manifest, args["occurrence"], args["stderr_occurrence"]],
        "vdb_context": args["vdb_context"], "failures": []}
    result = (parse_blast_vdb_extraction if mode == "extract_sequences" else parse_blast_vdb_inspection)(raw, **args)
    chosen = selector(vdb_context=True,
        sequences=sequence_selection(0) if mode == "extract_sequences" else None,
        paths=None if mode == "extract_sequences" else {"kinds": ["vdb", "vdb_alias", "blast_db_alias"],
            "native_path_ordinals": None, "include_sections": True},
        artifacts=[{"direction": "output", "role": "stdout", "ordinal": 0}] if artifacts else [])
    projection = views.project_blast_utility_result(source_ref=source, operation=args["operation"],
        native_outcome=args["outcome"], result=result, prepared_database=None,
        occurrences=full_context["occurrences"], selector=chosen, failures=[], saved_data=[], context=full_context)
    target = {"resource_kind": "local", "assignment": {"requested_job": {"native_blast_utility": {
        "operation": args["operation"]}}}}
    h = return_host(tmp_path, store, target)
    schema = report_schema("sequences", "paths", "path_sections", "vdb_context", "artifacts")
    selected = {"version": "execution_results_assignment_v1", "handoff_ref": source, "selector": chosen}
    h.parent = context(h, "annotation", {}, schema=schema)
    h.child = context(h, "results", selected, parent=h.parent, schema=schema)
    body = {"version": results.V2_VERSION, "complete": True, **projection}
    monkeypatch.setattr(h.family.native_blast_utility_results, "_own_bodies",
        lambda ctx: iter([deepcopy(body)]) if ctx.episode_id == h.child.episode_id else iter([]))
    facts = h.family.native_blast_utility_results.facts(h.child)
    form = form_with_facts({}, schema, facts)
    h.family.native_blast_utility_returns.validate_received_report(h.child, form, schema)
    h.journal.save("runtime_forms", {"episode_id": h.child.episode_id, "facts": canonical(facts), "form": canonical(form)})
    h.journal.save("runtime_actions", {"episode_id": h.parent.episode_id, "decision_index": 0,
        "action": canonical({"kind": "episode_child", "role": "results", "scope": h.scope,
            "assignment": selected, "schema_json": canonical(schema),
            "purpose": h.child.request["report_contract"]["decision"]}), "result": None})
    h.journal.save("runtime_report_attempts", {"parent_episode_id": h.parent.episode_id, "decision_index": 0,
        "delivery_ref": "controlled-return669", "child_episode_id": h.child.episode_id,
        "contract": canonical(h.child.request["report_contract"]), "form": canonical(form), "failure": None})
    h.projection, h.form, h.schema, h.private, h.bundle, h.source = projection, form, schema, private, bundle, source
    return h


@pytest.mark.parametrize("mode", ["extract_sequences", "paths_all"])
@pytest.mark.parametrize("artifacts", [False, True])
def test_controlled_immediate_child_admission_keeps_exact_fields_namespaces_and_grants(tmp_path, monkeypatch, mode, artifacts):
    h = pure_return_case(tmp_path, monkeypatch, mode=mode, artifacts=artifacts)
    try:
        reader = h.family.native_blast_utility_returns
        admitted = reader.record_admission(h.parent, h.form, h.schema,
            f"{h.parent.run_id}:{h.parent.episode_id}:0:typed_form")
        assert admitted == h.projection["record_refs"]
        assert h.private not in admitted and h.bundle not in admitted
        h.receipts.receive(h.parent.episode_id, admitted, kind="child_form", source_index=0)
        reader.validate_received_report(h.parent, h.form, h.schema)
        for namespace in views.IDENTIFIER_NAMESPACES:
            for reference in views.projection_identifiers(h.projection, namespace):
                assert reader.resolve_received(h.parent, reference, namespace)
                assert not reader.resolve_received(h.parent, reference + "-wrong", namespace)
        assert reader.resolve_received_reference_metadata(h.parent, h.source, "source")
        assert reader.resolve_received_reference_metadata(h.parent, h.source, "artifact") is False
        assert reader.resolve_received_reference_metadata(h.parent, h.private, "artifact") is None
        assert set(h.receipts.known(h.parent.episode_id)) == set(admitted)
        if mode == "extract_sequences":
            assert h.form["sequences"][0]["fields"] == {}
            assert h.form["sequences"][0]["sequences"] == {"normalized_sequence": "ACGT"}
            assert "vdb_identity" not in h.form["sequences"][0]
        assert h.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    finally:
        h.store.close()


@pytest.mark.parametrize("mutation", ["value", "source", "context", "artifact"])
def test_controlled_return_rejects_values_not_received_from_original_child(tmp_path, monkeypatch, mutation):
    h = pure_return_case(tmp_path, monkeypatch)
    try:
        changed = deepcopy(h.form)
        if mutation == "value":
            changed["sequences"][0]["sequences"]["normalized_sequence"] = "AAAA"
        elif mutation == "source":
            changed["sequences"][0]["source_ref"] = h.private
        elif mutation == "context":
            changed["vdb_context"][0]["context"]["source_inputs"][0]["source"]["source_ref"] = h.bundle
        else:
            changed["artifacts"] = [{"source_ref": h.source, **occurrence(b'{"controlled_metadata":true}',
                oid="unselected-metadata", role="database_metadata", direction="input", fmt="json")}]
        with pytest.raises(ValueError):
            h.family.native_blast_utility_returns.validate_received_report(h.parent, changed, h.schema)
    finally:
        h.store.close()


@pytest.mark.parametrize("mutation", ["sibling", "assignment", "purpose", "schema"])
def test_controlled_return_authenticates_immediate_child_commission(tmp_path, monkeypatch, mutation):
    h = pure_return_case(tmp_path, monkeypatch)
    try:
        if mutation == "sibling":
            sibling = context(h, "annotation", {}, parent=h.parent, index=2, schema=h.schema)
            with pytest.raises(ValueError):
                h.family.native_blast_utility_returns.record_admission(sibling, h.form, h.schema,
                    f"{sibling.run_id}:{sibling.episode_id}:0:typed_form")
        else:
            row = h.store.db.execute("SELECT action FROM runtime_actions WHERE episode_id=?", (h.parent.episode_id,)).fetchone()
            selected = json.loads(row["action"])
            if mutation == "assignment": selected["assignment"]["selector"]["vdb_context"] = False
            elif mutation == "purpose": selected["purpose"] = "different commission"
            else: selected["schema_json"] = canonical(report_schema("sequences"))
            h.store.db.execute("UPDATE runtime_actions SET action=? WHERE episode_id=?", (canonical(selected), h.parent.episode_id))
            with pytest.raises(ValueError):
                h.family.native_blast_utility_returns.record_admission(h.parent, h.form, h.schema,
                    f"{h.parent.run_id}:{h.parent.episode_id}:0:typed_form")
    finally:
        h.store.close()


def vdb_capture(tmp_path, *, variant="entry", stdout=b"controlled_read\taccession\t4\tacgt\n", returncode=0):
    # Shared controlled producer fixture; it supplies no native measurement.
    from test_blast_vdb_native_context_668 import controlled_capture, controlled_job
    job = controlled_job(tmp_path, variant=variant, database_source="dbs_file", metadata=True)
    return controlled_capture(tmp_path, job=job, stdout=stdout, returncode=returncode)


def forbid_original_reads(monkeypatch, capture):
    from gene_annotation_episode import blast_vdb_utility_inputs as readers
    from gene_annotation_episode import native_blast_vdb_utility_context as context_reader
    original = Path.open
    forbidden_paths = {row["original_path"] for row in capture["artifacts"]}

    def checked(path, *args, **kwargs):
        if str(path) in forbidden_paths:
            forbidden()
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked)
    monkeypatch.setattr(readers, "parse_blast_vdb_extraction", forbidden)
    monkeypatch.setattr(readers, "parse_blast_vdb_inspection", forbidden)
    monkeypatch.setattr(context_reader, "authenticate_vdb_utility_context", forbidden)


def original_receipt(store, prepared):
    stable = publication._stable(store, prepared)
    return stable, publication._json(store, stable["worker_receipt_artifact_ref"])


def replace_original_receipt(store, prepared, stable, receipt):
    """Forge a separate proposed record; original immutable artifacts stay intact."""
    changed, stable = deepcopy(prepared), deepcopy(stable)
    stable["worker_receipt_artifact_ref"] = store.artifact(canonical(receipt), "application/json")
    changed["source_grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=changed["bundle_artifact_ref"], grading=stable)
    return changed


def test_saved_vdb_publisher_authenticates_original_receipt_and_never_rereads_metadata(tmp_path, monkeypatch):
    calls = inline_workers(monkeypatch)
    store, capture = vdb_capture(tmp_path)
    try:
        prepared = prepare(store, capture, tmp_path)
        assert prepared["worker_completed"] and prepared["result_artifact_ref"] is not None
        stable, receipt = original_receipt(store, prepared)
        proof = receipt["manifest"]["context_authentication"]
        assert proof["passed"] is True and proof["documents"] and proof["provenance"] and proof["lists"]
        assert proof["request_sha256"] == digest(capture["plan"]["requested_job"])
        assert proof["context_sha256"] == digest(receipt["plan"]["context"])
        assert set(prepared) == publication._PREPARED_FIELDS
        assert set(stable) == publication._STABLE_FIELDS
        assert set(receipt) == {"version", "plan", "returncode", "manifest", "outputs", "failures",
            "diagnostic_artifact_refs", "exception"}
        assert set(receipt["plan"]) == {"version", "task", "directory", "context", "files", "capture", "bundle_file"}
        chosen = selector(sequences=sequence_selection(0, fields=("native_reported_length", "native_length_basis"), identity=True),
            vdb_context=True)
        forbid_original_reads(monkeypatch, capture)
        output = publish(store, prepared, chosen, tmp_path)
        assert output["version"] == publication.PUBLICATION_V2_VERSION
        assert set(output) == publication._PUBLICATION_V2_FIELDS
        assert output["sequences"][0]["fields"] == {"native_reported_length": 4, "native_length_basis": "returned_sequence"}
        assert output["sequences"][0]["sequences"] == {"normalized_sequence": "ACGT"}
        assert output["record_refs"] == [capture["source_ref"]]
        assert output["sequences"][0]["vdb_identity"]["sample_links"]
        for row in proof["documents"]:
            assert row["artifact_ref"] not in output["record_refs"]
        envelope = publication._json(store, output["projection_artifact_ref"])
        selected_receipt = publication._json(store, envelope["worker_receipt_artifact_ref"])
        assert envelope["version"] == publication.PROJECTION_V2_VERSION
        assert set(envelope) == {"version", "source_ref", "prepared_sha256", "selector", "projection",
            "worker_receipt_artifact_ref", "selected_projection_artifact_ref"}
        assert selected_receipt["plan"]["context_authentication"] == proof
        assert selected_receipt["manifest"]["context_authentication"] == proof
        assert selected_receipt["plan"]["context"] == receipt["plan"]["context"]
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        assert prepare(store, capture, tmp_path) == prepared
        assert publish(store, prepared, chosen, tmp_path) == output
        assert len(calls) == 2
    finally:
        store.close()


@pytest.mark.parametrize("mutation", ["proof_hash", "proof_namespace", "proof_pointer", "proof_list", "proof_document", "plan_context", "output_hash"])
def test_vdb_prepared_rejects_original_proof_plan_or_result_hash_tampering(tmp_path, monkeypatch, mutation):
    inline_workers(monkeypatch)
    store, capture = vdb_capture(tmp_path)
    try:
        prepared = prepare(store, capture, tmp_path)
        stable, receipt = original_receipt(store, prepared)
        proof = receipt["manifest"]["context_authentication"]
        if mutation == "proof_hash": proof["context_sha256"] = "0" * 64
        elif mutation == "proof_namespace": proof["provenance"][0]["source_namespace"] = "source"
        elif mutation == "proof_pointer": proof["provenance"][0]["pointer"] = "/unselected"
        elif mutation == "proof_list": proof["lists"][0]["entries"][0]["byte_start"] += 1
        elif mutation == "proof_document": proof["documents"][0]["occurrence_id"] = "other-occurrence"
        elif mutation == "plan_context":
            receipt["plan"]["context"]["vdb_context"]["source_inputs"][0]["snapshot"]["release"] = "other release"
            receipt["manifest"]["plan_sha256"] = digest(receipt["plan"])
        else: receipt["manifest"]["outputs"]["result"]["sha256"] = "0" * 64
        changed = replace_original_receipt(store, prepared, stable, receipt)
        forbid_original_reads(monkeypatch, capture)
        with pytest.raises(ValueError):
            publication.validate_prepared_utility_result(store, changed)
        assert publication.validate_prepared_utility_result(store, prepared) == prepared
    finally:
        store.close()


def test_vdb_saved_result_from_other_context_rejects_even_with_consistent_replacement_hashes(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    store, capture = vdb_capture(tmp_path)
    try:
        prepared = prepare(store, capture, tmp_path)
        stable, receipt = original_receipt(store, prepared)
        result = publication._json(store, prepared["result_artifact_ref"])
        result["vdb_context"]["source_inputs"][0]["snapshot"]["release"] = "other capture release"
        reference = store.artifact(canonical(result), "application/json")
        descriptor = publication._descriptor(store, reference)
        receipt["outputs"]["result"] = descriptor
        receipt["manifest"]["outputs"]["result"].update({key: descriptor[key] for key in ("sha256", "size_bytes")})
        stable["payload_artifacts"]["result"] = descriptor
        stable["result_artifact_ref"] = reference
        candidate = {**prepared, "result_artifact_ref": reference}
        candidate = replace_original_receipt(store, candidate, stable, receipt)
        forbid_original_reads(monkeypatch, capture)
        with pytest.raises(ValueError, match="prepared_vdb_result_context_conflict"):
            publication.validate_prepared_utility_result(store, candidate)
    finally:
        store.close()


def test_saved_projection_proof_cannot_be_replaced_by_self_consistent_other_request_digest(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    store, capture = vdb_capture(tmp_path)
    try:
        prepared = prepare(store, capture, tmp_path)
        chosen = selector(sequences=sequence_selection(0))
        output = publish(store, prepared, chosen, tmp_path)
        envelope = publication._json(store, output["projection_artifact_ref"])
        receipt = publication._json(store, envelope["worker_receipt_artifact_ref"])
        receipt["plan"]["context_authentication"]["request_sha256"] = "0" * 64
        receipt["manifest"]["context_authentication"] = deepcopy(receipt["plan"]["context_authentication"])
        receipt["manifest"]["plan_sha256"] = digest(receipt["plan"])
        envelope["worker_receipt_artifact_ref"] = store.artifact(canonical(receipt), "application/json")
        changed = {**output, "projection_artifact_ref": store.artifact(canonical(envelope), "application/json")}
        forbid_original_reads(monkeypatch, capture)
        with pytest.raises(ValueError, match="publication_vdb_context_authentication_conflict"):
            publication.validate_utility_publication(store, source_ref=capture["source_ref"], prepared=prepared,
                selector=chosen, publication=changed)
    finally:
        store.close()


def test_native_failed_saved_vdb_rows_remain_deliverable_with_explicit_bytes_only(tmp_path, monkeypatch):
    inline_workers(monkeypatch)
    raw = b"controlled_read\taccession\t4\tacgt\nmalformed\ncontrolled_read\taccession\t4\tACGT\n"
    store, capture = vdb_capture(tmp_path, stdout=raw, returncode=2)
    try:
        prepared = prepare(store, capture, tmp_path)
        assert prepared["result_artifact_ref"] is not None
        chosen = selector(sequences=sequence_selection(0, fields=("returned_symbol_count",)),
            artifacts=[{"direction": "output", "role": "stdout", "ordinal": 0}], saved_data=["result"])
        forbid_original_reads(monkeypatch, capture)
        output = publish(store, prepared, chosen, tmp_path)
        assert output["status"]["state"] == "complete" and output["status"]["native_state"] == "failed"
        assert output["status"]["writer_closed"] and output["status"]["inventory_complete"]
        assert [row["native_row_ordinal"] for row in output["sequences"]] == [0, 2]
        assert [row["fields"]["returned_symbol_count"] for row in output["sequences"]] == [4, 4]
        assert output["record_refs"] == [capture["source_ref"], output["artifacts"][0]["artifact_ref"], prepared["result_artifact_ref"]]
        assert any(row["code"] == "native_nonzero_exit" for row in output["failures"])
    finally:
        store.close()


def selected_result_host(tmp_path, monkeypatch, *, stdout=b"controlled_read\taccession\t4\tacgt\n"):
    store, capture = vdb_capture(tmp_path, stdout=stdout)
    target = {"resource_kind": "local", "resource_id": "local", "assignment": {
        "requested_job": capture["plan"]["requested_job"]}}
    h = return_host(tmp_path, store, target)
    handoff = store.put("source", {"provider": "controlled_handoff669", "accession": None,
        "version": "controlled_handoff669_v1", "uri": None, "artifact_ref": store.artifact(b"controlled handoff"),
        "text_ref": None, "request_ref": None, "retrieved_at": "2026-10-28T00:00:00+00:00"}, origin="tool")["id"]
    chosen = selector(sequences=sequence_selection(0, fields=("returned_symbol_count",)), vdb_context=True,
        artifacts=[{"direction": "output", "role": "stdout", "ordinal": 0}])
    schema = report_schema(*[name for name in views.PROJECTION_V2_FIELDS if name != "record_refs"])
    assignment = {"version": RESULTS_VERSION, "handoff_ref": handoff, "selector": chosen}
    h.parent = context(h, "annotation", {}, schema=schema)
    h.receipts.receive(h.parent.episode_id, [handoff], kind="initial")
    h.child = context(h, "results", assignment, parent=h.parent, schema=schema)
    h.capture, h.target, h.assignment, h.schema = capture, target, assignment, schema
    h.worker_calls, h.acquisitions, h.observations = inline_workers(monkeypatch), [], []

    def retained(store, *, target, directory):
        saved = directory / "capture.json"
        if not saved.is_file():
            h.acquisitions.append(str(directory))
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(saved, capture)
        return acquisition._validate_saved(store, json.loads(saved.read_text()))

    def observe(target, *, operation_key):
        h.observations.append(operation_key)
        return {"state": "succeeded", "returncode": 0, "observed_at": "2026-10-28T00:00:00+00:00"}

    monkeypatch.setattr(results, "capture_local_utility_bundle", retained)
    h.family.job_progress_provider.targets.observe_target = observe
    assert h.family.native_blast_utility_results.validate_selected_inputs(h.child, assignment) == [handoff]
    return h


def selected_collect(h, index):
    key = f"{h.child.run_id}:{h.child.episode_id}:{index}"
    h.journal.save("runtime_actions", {"episode_id": h.child.episode_id, "decision_index": index,
        "action": canonical({"kind": "tool", "tool": "execution.results.collect", "arguments": {}}), "result": None})
    outcome = asyncio.run(h.family.native_blast_utility_results.execute(h.child, h.target,
        "execution.results.collect", {}, key))
    h.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
        (canonical(outcome), h.child.run_id, h.child.episode_id, index))
    h.receipts.receive(h.child.episode_id, outcome["record_refs"], kind="own_action", source_index=index)
    return outcome


def test_selected_vdb_repair_reuses_original_capture_and_keeps_failure_history_and_credit(tmp_path, monkeypatch):
    from gene_annotation_episode import native_blast_vdb_utility_context as context_reader
    h = selected_result_host(tmp_path, monkeypatch)
    original_authenticate = context_reader.authenticate_vdb_utility_context
    attempts = []

    def fail_once(*args, **kwargs):
        attempts.append(True)
        if len(attempts) == 1:
            raise ValueError("controlled_original_context_read_failure669")
        return original_authenticate(*args, **kwargs)

    monkeypatch.setattr(context_reader, "authenticate_vdb_utility_context", fail_once)
    try:
        first = selected_collect(h, 0)
        before = deepcopy(first["result"])
        assert before["version"] == results.V2_VERSION
        assert before["prepared"] is not None and before["prepared"]["result_artifact_ref"] is None
        assert before["status"]["state"] == "partial" and not before["complete"]
        assert before["vdb_context"] == [] and before["failures"]
        directory = h.family.native_blast_utility_results._saved_directory(h.child.episode_id, before["operation_key"])
        original_files = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob("*") if p.is_file()}
        replay = asyncio.run(h.family.native_blast_utility_results.execute(h.child, h.target,
            "execution.results.collect", {}, before["operation_key"]))
        assert replay == first and len(attempts) == 1
        repaired = selected_collect(h, 1)["result"]
        assert repaired["complete"] and repaired["status"]["state"] == "complete"
        assert repaired["capture"] == before["capture"] and repaired["observation"] == before["observation"]
        assert repaired["reused_from"] == {key: before[key] for key in ("run_id", "episode_id", "operation_key")}
        assert len(attempts) == 2 and len(h.acquisitions) == len(h.observations) == 1
        assert len(h.worker_calls) == 4
        assert original_files == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob("*") if p.is_file()}
        assert json.loads((directory / "receipt.json").read_text()) == before
        known = list(h.receipts.known(h.child.episode_id))
        credit = h.family.native_blast_utility_results.credit_view(h.child,
            {"known_record_refs": known, "initial_known_record_refs": []})
        assert credit["credit"] == 2 and credit["new_acquired_record_count"] == 1
        proof = h.family.native_blast_utility_results.completion(h.child)
        assert proof is not None
        current = completion_context(run_id=h.child.run_id, episode_id=h.child.episode_id, unit_index=1, action_index=1)
        current["practical_completion"].update(proof)
        history = (2.0, 0.0)
        estimate = PracticalYieldEstimator(lambda p: p == h.family.native_blast_utility_results.completion(h.child))(
            history, YieldParameters(), (None, current))
        assert estimate.turns == 2 and estimate.expected_next_gain == NumericBand.exact(0)
        assert history == (2.0, 0.0)
        assert h.store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (h.child.episode_id,)).fetchone()[0] == 2
        monkeypatch.setattr(results, "prepare_native_blast_utility_result", forbidden)
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        assert asyncio.run(h.family.native_blast_utility_results.execute(h.child, h.target,
            "execution.results.collect", {}, before["operation_key"])) == first
    finally:
        h.store.close()


def test_selected_vdb_partial_parsed_result_is_never_reparsed_on_later_collect(tmp_path, monkeypatch):
    h = selected_result_host(tmp_path, monkeypatch, stdout=b"unselected_read\tother\t4\tacgt\n")
    try:
        first = selected_collect(h, 0)["result"]
        assert first["prepared"]["result_artifact_ref"] is not None and not first["complete"]
        assert first["status"]["state"] == "partial" and first["missing"]
        monkeypatch.setattr(results, "prepare_native_blast_utility_result", forbidden)
        second = selected_collect(h, 1)["result"]
        assert second["prepared"] == first["prepared"] and second["missing"] == first["missing"]
        assert len([plan for plan in h.worker_calls if plan["task"] == "parse_original"]) == 1
        assert len(h.acquisitions) == len(h.observations) == 1
        for key in ("capture", "observation", "source_ref"):
            assert second[key] == first[key]
    finally:
        h.store.close()


def test_controlled_saved_collection_reaches_actual_immediate_child_admission(tmp_path, monkeypatch):
    h = selected_result_host(tmp_path, monkeypatch)
    try:
        body = selected_collect(h, 0)["result"]
        assert body["complete"]
        assert set(body) == {"version", "run_id", "episode_id", "scope", "assignment", "operation_key",
            "tool_name", "arguments", "target", "observation", "capture", "prepared", "source_ref",
            "reused_from", "operational_failures", "complete", *views.PROJECTION_V2_FIELDS}
        for candidate in ({**body, "context_authentication": {}}, {**body, "version": results.VERSION}):
            with pytest.raises(ValueError, match="receipt_invalid"):
                h.family.native_blast_utility_results._validate_body(candidate, h.scope)
        forbid_original_reads(monkeypatch, h.capture)
        monkeypatch.setattr(publication, "run_local_job", forbidden)
        reader = h.family.native_blast_utility_returns
        facts = h.family.native_blast_utility_results.facts(h.child)
        form = form_with_facts({}, h.schema, facts)
        reader.validate_received_report(h.child, form, h.schema)
        h.journal.save("runtime_forms", {"episode_id": h.child.episode_id,
            "facts": canonical(facts), "form": canonical(form)})
        h.journal.save("runtime_actions", {"episode_id": h.parent.episode_id, "decision_index": 0,
            "action": canonical({"kind": "episode_child", "role": "results", "scope": h.scope,
                "assignment": h.assignment, "schema_json": canonical(h.schema),
                "purpose": h.child.request["report_contract"]["decision"]}), "result": None})
        h.journal.save("runtime_report_attempts", {"parent_episode_id": h.parent.episode_id,
            "decision_index": 0, "delivery_ref": "controlled-saved-return669", "child_episode_id": h.child.episode_id,
            "contract": canonical(h.child.request["report_contract"]), "form": canonical(form), "failure": None})
        admitted = reader.record_admission(h.parent, form, h.schema,
            f"{h.parent.run_id}:{h.parent.episode_id}:0:typed_form")
        assert admitted == body["record_refs"]
        h.receipts.receive(h.parent.episode_id, admitted, kind="child_form", source_index=0)
        reader.validate_received_report(h.parent, form, h.schema)
        assert form["sequences"][0]["fields"] == {"returned_symbol_count": 4}
        assert form["sequences"][0]["sequences"] == {"normalized_sequence": "ACGT"}
        assert "vdb_identity" not in form["sequences"][0]
        private = original_receipt(h.store, body["prepared"])[1]["manifest"]["context_authentication"]["documents"][0]["artifact_ref"]
        assert private not in admitted
        assert h.family.native_blast_utility_results.retained_reference_access(h.parent, private, "artifact") is False
        assert len(h.acquisitions) == len(h.observations) == 1 and len(h.worker_calls) == 2
    finally:
        h.store.close()
