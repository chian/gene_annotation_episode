"""Opt-in ordinary HPA acquisition in one real current episode.

The model and continuation choices are scripted. One real selected GET supplies
data for later use; this does not analyze an expression matrix or native claims.
Failure preserves its original prefix and never authorizes another GET.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
import os

import pytest

from fluorescence_flowio_test_support import require_bounded_runtime
from gene_annotation_episode.acquisition import AcquisitionError, PublicClients
from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode import molecular_provider_acquisition as provider
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_prompt import text_instructions
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_molecular_provider_acquisition_host import (
    ReceivingProvider, _artifacts, _assert_retained_source, _credit, _scope,
    _session, _tables, _two_step_controller, forbidden,
)
from test_molecular_provider_acquisition_live import _counts
from test_runtime import ScriptedProvider
from test_scientific_process_runtime import action


GATE = "HMMER_NATIVE_ORACLE_HPA_GENE_LIVE_JSON"
OPERATION = "public.hpa.gene"
GENE_ID = "ENSG00000141510"
MAX_BYTES = 8388608
TIMEOUT_SECONDS = 30


class LostOriginalReply(RuntimeError):
    """Test-only loss after the real original ToolOp and response are durable."""


class OriginalFailedPrefixObserved(RuntimeError):
    """Stop the actual failed prefix before selecting any replacement request."""


def _checkpoint(path, proof):
    pending = path.with_suffix(".pending.json")
    with pending.open("w", encoding="utf-8") as stream:
        json.dump(proof, stream, ensure_ascii=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, path)


class LiveHPAClients(PublicClients):
    """Observe the real selected transport; never substitute a response."""
    def __init__(self, directory, proof, output):
        super().__init__(ncbi_email=None, timeout=TIMEOUT_SECONDS, access_dir=directory)
        self.proof, self.output = proof, output
        self.calls, self.captures, self.transport_failures = [], [], []

    def _http(self, service, url, params, media_type, **kwargs):
        if self.calls:
            raise AssertionError("ordinary HPA verification attempted another GET")
        self.calls.append(dict(service=service, url=url, params=deepcopy(params),
            media_type=media_type, **deepcopy(kwargs)))
        self.proof.update(phase="original_http_dispatch_observed", client_calls=self.calls)
        _checkpoint(self.output, self.proof)
        assert self.calls == [dict(service="hpa",
            url="https://www.proteinatlas.org/" + GENE_ID + ".json", params={},
            media_type="application/json", max_bytes=MAX_BYTES,
            timeout_seconds=TIMEOUT_SECONDS, follow_redirects=False)]
        try:
            snapshot = super()._http(service, url, params, media_type, **kwargs)
        except AcquisitionError as error:
            self.transport_failures.append(dict(code=error.code, phase=error.phase,
                response_retained=error.snapshot is not None,
                diagnostic=deepcopy(error.diagnostic), operational=deepcopy(error.operational)))
            self.proof["transport_failures"] = self.transport_failures
            if error.snapshot is not None:
                self._retain(error.snapshot)
            self.proof["phase"] = "original_http_failure_retained"
            _checkpoint(self.output, self.proof)
            raise
        self._retain(snapshot)
        return snapshot

    def _retain(self, snapshot):
        self.captures.append(snapshot)
        path = self.output.parent / "native-response.bin"
        with path.open("xb") as stream:
            stream.write(snapshot.content)
            stream.flush()
            os.fsync(stream.fileno())
        self.proof["native_response_pin"] = dict(path=str(path.resolve()),
            sha256=hashlib.sha256(snapshot.content).hexdigest(), size_bytes=len(snapshot.content))
        self.proof["actual_snapshot"] = dict(service=snapshot.service, url=snapshot.url,
            request=deepcopy(snapshot.request), retrieved_at=snapshot.retrieved_at,
            media_type=snapshot.media_type, transport=deepcopy(snapshot.transport))
        self.proof["phase"] = "original_native_bytes_retained_before_publication"
        _checkpoint(self.output, self.proof)


def _publication_checkpoint(store, outcome, proof, output):
    """Save actual rows and custody before fragile verification assertions."""
    proof.update(outcome=deepcopy(outcome), tables_after_original_publication=_tables(store),
        counts_after_original_publication=_counts(store), phase="original_toolop_durable")
    _checkpoint(output, proof)
    retained = []
    for source in store.list("source"):
        if source["provider"] != "hpa":
            continue
        raw = store.get_artifact(source["artifact_ref"])
        retained.append(dict(source=source,
            raw=dict(artifact_ref=source["artifact_ref"], sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw)),
            request_control=json.loads(store.get_artifact(source["request_ref"])),
            private_values=[dict(artifact_ref=ref, value=json.loads(store.get_artifact(ref)))
                for ref in source["auxiliary_artifact_refs"]]))
    proof.update(retained_sources=retained, phase="original_source_and_controls_retained")
    _checkpoint(output, proof)


def test_live_hpa_gene_current_episode_receiving_recovery_cache_and_closed_replay(tmp_path, monkeypatch):
    supplied = os.environ.get(GATE)
    if supplied is None:
        pytest.skip("requires an explicit ordinary HPA gene acquisition opt-in")
    gate = json.loads(supplied)
    assert type(gate) is dict and set(gate) == {
        "enabled", "gene_id", "max_bytes", "timeout_seconds", "follow_redirects"}
    assert gate["enabled"] is True and gate["gene_id"] == GENE_ID
    assert type(gate["max_bytes"]) is int and gate["max_bytes"] == MAX_BYTES
    assert type(gate["timeout_seconds"]) is int and gate["timeout_seconds"] == TIMEOUT_SECONDS
    assert gate["follow_redirects"] is False
    require_bounded_runtime()
    arguments = dict(gene_id=gate["gene_id"], max_bytes=gate["max_bytes"])
    assert provider.validate_provider_arguments(OPERATION, arguments) == arguments
    output = tmp_path / "HPA_LIVE_ORDINARY_WORKFLOW.json"
    proof = dict(version="hpa_current_ordinary_acquisition_observation_v1", passed=False,
        phase="prepared", operation=OPERATION, selected_arguments=arguments,
        acquired=False, whole_episode_completed=False, closed_replay_reached=False,
        new_child_episodes=0, external_model_calls=0, native_calculations=0,
        expression_matrix_verified=False, client_calls=[], transport_failures=[],
        qualification="One actual GET; scripted current-episode decisions; retained native assertions are data.")
    _checkpoint(output, proof)
    client = LiveHPAClients(tmp_path / "provider-access", proof, output)
    monkeypatch.setattr(client, "_skill", forbidden)
    monkeypatch.setattr("gene_annotation_episode.native_lifecycle.prepare_job", forbidden)
    try:
        with Store(tmp_path / "store") as store:
            tools = ToolRegistry(store, clients=client)
            scope, directory = _scope(store), tmp_path / "run"
            connection = _session(tmp_path / "session")
            actor = ReceivingProvider([action(OPERATION, arguments)], connection)

            def workflow(selected_actor):
                return Workflow(store, tools, selected_actor, directory, "hpa-gene-live-ordinary",
                    _two_step_controller, _credit, project_child_credit=_credit,
                    root_role="improvement", episode_record_receipts=True, initial_known_record_refs=[])

            current = workflow(actor)
            goal = ("Retain the caller-selected Human Protein Atlas gene record " + GENE_ID
                + " for a later investigation. Preserve native fields; correspondence with the supplied protein remains unresolved.")
            root = current.build("improvement", "root", goal, scope)
            baseline = set(current.receipts.known(root.source.episode_id))
            original_execute, lost = ToolRegistry.execute_async, []

            async def lose_original_reply(registry, name, selected, **kwargs):
                outcome = await original_execute(registry, name, selected, **kwargs)
                if name == OPERATION and not lost:
                    _publication_checkpoint(store, outcome, proof, output)
                    lost.append(deepcopy(outcome))
                    raise LostOriginalReply()
                return outcome

            with monkeypatch.context() as original:
                original.setattr(ToolRegistry, "execute_async", lose_original_reply)
                with pytest.raises(LostOriginalReply):
                    asyncio.run(root.run_async(current.context))
            assert len(lost) == len(actor.contexts) == len(client.calls) == 1
            outcome = lost[0]
            receipt = provider.validate_provider_receipt(outcome["result"])
            proof.update(receipt=receipt, acquired=receipt["acquired"], expected_original_reply_loss=True)
            _checkpoint(output, proof)

            def read_acquired(context):
                observed = context["last_local_outcome"]
                assert type(observed) is dict and {"status", "result", "record_refs"} <= set(observed)
                actual_receipt = provider.validate_provider_receipt(observed["result"])
                assert actual_receipt == receipt and observed["record_refs"] == outcome["record_refs"]
                proof["actual_receiving_context"] = deepcopy(context)
                _checkpoint(output, proof)
                if not actual_receipt["acquired"]:
                    raise OriginalFailedPrefixObserved("original failed HPA acquisition retained; no replacement selected")
                assert context["requested_form"] is None
                return action("source.read", dict(source_ref=actual_receipt["source_ref"],
                    representation="original", offset=0, limit=1024))

            monkeypatch.setattr(client, "_http", forbidden)
            for name in ("provider_value", "publish_molecular_provider_request"):
                monkeypatch.setattr(provider, name, forbidden)
            recovered_actor = ReceivingProvider([read_acquired], connection)
            recovered = workflow(recovered_actor)
            recovered_root = recovered.build("improvement", "root", goal, scope)
            record, failed_prefix = None, False
            try:
                record = asyncio.run(recovered_root.run_async(recovered.context))
            except OriginalFailedPrefixObserved:
                failed_prefix = True
            final = None if failed_prefix else asyncio.run(recovered_root.build_result(record)).as_record()
            proof.update(phase="original_recovery_observed", expected_failed_prefix=failed_prefix,
                whole_episode_completed=not failed_prefix, counts=_counts(store), final=final,
                scripted_dispatches=actor.dispatches + recovered_actor.dispatches)
            _checkpoint(output, proof)
            assert len(client.calls) == 1
            assert len(actor.dispatches) == len(recovered_actor.dispatches) == 1
            calls = list(store.db.execute("SELECT request,response FROM runtime_model_calls ORDER BY call_index"))
            for dispatched, call in zip(proof["scripted_dispatches"], calls):
                assert json.loads(call["request"])["context"] == dispatched["context"]
                assert dispatched["wire"].startswith("TASK\n") and "\n\nSTEERING\n" in dispatched["wire"]
                assert goal in dispatched["wire"]
                assert "Absent: no parent return form was supplied." in dispatched["wire"]
                assert dispatched["model_instructions"] == text_instructions(dispatched["instructions"])
                assert dispatched["context"]["goal"] == root.source.request.goal.as_record()
                assert dispatched["context"]["requested_form"] is None
            assert len(calls) == 2
            assert calls[0]["response"] is not None
            assert (calls[1]["response"] is None) is failed_prefix
            context = recovered.binding_context(recovered_root.source)
            known = set(recovered.receipts.known(context.episode_id))
            assert known == baseline | set(outcome["record_refs"])
            row, = list(store.db.execute("SELECT * FROM tool_operations WHERE name=?", (OPERATION,)))
            assert row["arguments"] == canonical(arguments) and row["scope"] == canonical(scope)
            assert json.loads(row["result"]) == outcome
            if client.captures:
                assert len(client.captures) == 1
                value, source = _assert_retained_source(store, outcome, client, OPERATION, arguments)
                proof.update(source=source, response=value["response"], issues=value["issues"])
                private = {source["request_ref"], *source["auxiliary_artifact_refs"]}
                assert private.isdisjoint(known)
                assert all(reference not in dispatched["wire"]
                    for dispatched in proof["scripted_dispatches"] for reference in private)
                resolve = recovered.resolver(plain(context.scope), context=context)
                assert resolve(source["id"], "source") is True
                assert resolve(source["artifact_ref"], "artifact") is receipt["acquired"]
                assert all(resolve(ref, "artifact") is False for ref in private)
                if receipt["acquired"]:
                    raw = store.get_artifact(source["artifact_ref"])
                    native = json.loads(raw)
                    assert type(native) is dict and native["Ensembl"] == arguments["gene_id"]
                    assert value["native_json"] == native and source["version"] is None
                    assert source["accession"] == native["Ensembl"]
                    assert raw == client.captures[0].content
                    assert hashlib.sha256(raw).hexdigest() == proof["native_response_pin"]["sha256"]
                    assert len(raw) == proof["native_response_pin"]["size_bytes"]
            else:
                assert receipt == provider.failed_provider_receipt("data_acquisition_failed")
                assert outcome["record_refs"] == []
            counts = _counts(store)
            assert counts == dict(runtime_episodes=1, runtime_actions=1 if failed_prefix else 2,
                runtime_observations=(1 if outcome["status"] == "partial" else 0) if failed_prefix else 2,
                runtime_model_calls=2, tool_operations=1 if failed_prefix else 2,
                runtime_forms=0, runtime_report_attempts=0)
            assert store.db.execute("SELECT count(*) FROM runtime_record_receipts WHERE receipt_kind='child_form'").fetchone()[0] == 0
            proof["phase"] = "actual_custody_and_receiving_context_verified"
            _checkpoint(output, proof)
            before, files, archives = _tables(store), _artifacts(store.path / "artifacts"), _artifacts(directory / "archive")
            monkeypatch.setattr(Store, "get_artifact", forbidden)
            monkeypatch.setattr(Store, "artifact", forbidden)
            monkeypatch.setattr(ToolRegistry, "_source", forbidden)
            assert tools.execute(OPERATION, arguments, scope=scope, operation_key=row["operation_key"]) == outcome
            if not failed_prefix:
                monkeypatch.setattr(ToolRegistry, "execute_async", forbidden)
                restored_actor = ScriptedProvider([])
                restored = workflow(restored_actor)
                restored_root = restored.build("improvement", "root", goal, scope)
                restored_record = asyncio.run(restored_root.run_async(restored.context))
                assert asyncio.run(restored_root.build_result(restored_record)).as_record() == final
                assert restored_actor.contexts == []
            assert _tables(store) == before and _artifacts(store.path / "artifacts") == files
            assert _artifacts(directory / "archive") == archives
            proof.update(passed=receipt["acquired"], phase="verified" if receipt["acquired"] else "failed_prefix_verified",
                exact_same_key_cache=True, closed_replay_reached=not failed_prefix,
                rows_artifacts_archives_unchanged=True, new_HTTP_after_original=0)
    except BaseException as error:
        proof["verification_failure"] = dict(exception_type=type(error).__name__, message=str(error))
        raise
    finally:
        _checkpoint(output, proof)
    if not proof["acquired"]:
        pytest.skip("original HPA request did not acquire the selected gene; retained without retry or completion credit")
