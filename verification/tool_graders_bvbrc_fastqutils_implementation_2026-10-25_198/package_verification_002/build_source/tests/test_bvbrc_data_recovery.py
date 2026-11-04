"""D6 host custody/replay checks using actual executor and host qualification.

Selected Journal rows and SourceSnapshots are controlled engineering fixtures.
No network, model, native analysis, scientific annotation or Workflow run occurs.
The separate episode-path suite exercises the full shared-loop communication.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.api_bvbrc import DATA_QUERY_OPERATION, DATA_RESULT_OPERATION
from gene_annotation_episode.api_service_execution import APIServiceExecution
from gene_annotation_episode.bvbrc_data_schema import json_digest
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from bvbrc_host_fixture import HostFixture, envelope, request, selector
from test_api_bvbrc_data_v2 import row_selector


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("host custody/replay verification attempted network access")
    monkeypatch.setattr("urllib.request.OpenerDirector.open", forbidden)
    monkeypatch.setattr("socket.create_connection", forbidden)


@pytest.fixture
def host(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        yield HostFixture(store, tmp_path / "run", monkeypatch)


def read(path):
    return json.loads(path.read_bytes())


def forbid_recomputation(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("saved acquisition attempted compilation, calculation or transport")
    for module, names in {
        "api_bvbrc": ["encode_native_query"],
        "bvbrc_data_query": ["encode_native_query"],
        "bvbrc_data_publication": ["calculate_page_counts", "calculate_facet_fractions", "calculate_feature_sequence_counts"],
        "bvbrc_data_calculators": ["calculate_page_counts", "calculate_facet_fractions", "calculate_feature_sequence_counts"],
    }.items():
        for name in names:
            monkeypatch.setattr("gene_annotation_episode." + module + "." + name, forbidden)
    monkeypatch.setattr("gene_annotation_episode.api_bvbrc.BVBRCDataClient.query_prepared", forbidden)
    monkeypatch.setattr("gene_annotation_episode.api_bvbrc.BVBRCDataClient._query_once", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)


def test_persisted_preparation_native_bytes_full_grading_receipt_and_host_admission(host):
    selection = row_selector(numbers=["genome_length"])
    child, outcome = host.acquire(selection=selection, body=envelope([
        {"genome_id": "g0", "genome_length": 12}, {"genome_id": "g1", "genome_length": 19}]),
        sources=("execution_bvbrc_numeric_rows",))
    reference = outcome["result"]["source_ref"]
    qualified = host.api.read_bvbrc_result(reference, context=child)
    action = host.directory_for(child)
    prepared = read(action / "intent.json")["prepared"]["prepared_query"]
    inputs = read(action / "publication_inputs.json")
    receipt = read(action / "acquisition.json")
    assert qualified["grading"]["prepared"] == prepared == inputs["prepared"]
    assert qualified["grading"]["selector"] == selection
    assert receipt["publication_inputs_sha256"] == json_digest(inputs)
    source = host.store.get(reference)
    raw = host.store.get_artifact(source["artifact_ref"])
    assert qualified["binding"]["native_sha256"] == hashlib.sha256(raw).hexdigest()
    assert source["auxiliary_artifact_refs"] == [qualified["binding"]["grading_artifact_ref"]]
    assert qualified["grading"]["page_components"]["native_row_count"] == 2
    assert [row["numerical_cells"][0]["value"] for row in
        qualified["grading"]["parse_result"]["sheet"]["rows"]] == [12, 19]
    assert qualified["host_qualification"]["possession_basis"] == "own_completed_action"
    actions_before = host.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0]
    assert host.admit(child) == [reference]
    assert host.admit(child) == [reference]
    assert host.store.db.execute("SELECT count(*) FROM runtime_bvbrc_admissions").fetchone()[0] == 1
    assert host.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == actions_before
    assert host.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    received = host.api.read_bvbrc_result(reference, context=host.parent)
    assert received["host_qualification"]["possession_basis"] == "admitted_return"
    values, = host.api.received_bvbrc_context(host.parent)
    assert len(values["facts"]) == 1
    assert values["facts"][0]["measurements"][0]["value"] == 12
    assert len(host.calls) == 1


@pytest.mark.parametrize("stage", ["decode", "publish"])
def test_interrupted_original_action_resumes_retained_response_without_get_or_recompile(host, monkeypatch, stage):
    _, handoff = host.launch()
    child = host.results_context(handoff)
    key = host.select(child, DATA_RESULT_OPERATION)
    service = host.api.services["bvbrc"]
    original = getattr(service, stage)

    def interrupt(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(service, stage, interrupt)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(host.api.execute(child, DATA_RESULT_OPERATION, {}, key))
    action = host.directory_for(child)
    assert (action / "intent.json").exists()
    assert (action / "snapshot.json").exists()
    assert not (action / "outcome.json").exists()
    prepared = read(action / "intent.json")["prepared"]["prepared_query"]
    monkeypatch.setattr(service, stage, original)
    host.api = host.reopen()

    def forbidden(*args, **kwargs):
        pytest.fail("recovery recompiled or requested an already retained response")

    monkeypatch.setattr("gene_annotation_episode.api_bvbrc.encode_native_query", forbidden)
    monkeypatch.setattr("gene_annotation_episode.bvbrc_data_query.encode_native_query", forbidden)
    monkeypatch.setattr("gene_annotation_episode.api_bvbrc.BVBRCDataClient.query_prepared", forbidden)
    outcome = host.execute(child, DATA_RESULT_OPERATION, select=False)
    assert outcome["status"] == "completed", outcome
    qualified = host.api.read_bvbrc_result(outcome["record_refs"][0], context=child)
    assert qualified["grading"]["prepared"] == prepared
    assert len(host.calls) == 1
    assert len(list(action.parent.glob("*/intent.json"))) == 1


def test_launch_decode_interruption_keeps_actual_get_response_for_original_action(host, monkeypatch):
    query = request("genome", fields=["genome_id", "genome_length"])
    child = host.launch_context(query)
    host.responses.append(envelope([{"genome_id": "g", "genome_length": 12}]))
    key = host.select(child, DATA_QUERY_OPERATION)

    def interrupt(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr(host.api.services["bvbrc"], "decode", interrupt)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(host.api.execute(child, DATA_QUERY_OPERATION, {}, key))
    action = host.directory_for(child)
    original_prepared = read(action / "intent.json")["prepared"]
    original_snapshot = read(action / "snapshot.json")
    assert len(host.calls) == 1 and not (action / "handoff_receipt.json").exists()
    host.api = host.reopen()
    forbid_recomputation(monkeypatch)
    completed = host.execute(child, DATA_QUERY_OPERATION, select=False)
    assert completed["status"] == "completed", completed
    assert read(action / "intent.json")["prepared"] == original_prepared
    assert read(action / "snapshot.json") == original_snapshot
    assert host.api.read_target(completed["result"]["handoff_ref"], host.scope)["origin_episode_id"] == child.episode_id
    assert len(host.calls) == 1


def test_completed_replay_and_receipt_reads_do_not_compile_calculate_or_acquire(host, monkeypatch):
    child, original = host.acquire()
    host.admit(child)
    before = host.api.received_bvbrc_context(host.parent)
    forbid_recomputation(monkeypatch)
    host.api = host.reopen()
    assert host.execute(child, DATA_RESULT_OPERATION, select=False) == original
    assert host.api.read_bvbrc_result(original["record_refs"][0], context=child)["grading"]["page_components"]
    assert host.api.received_bvbrc_context(host.parent) == before
    assert host.api.completion_for_action(child, f"{child.run_id}:{child.episode_id}:0") is not None
    assert len(host.calls) == 1


def test_interruption_after_saved_publication_reuses_sheet_without_calculator(host, monkeypatch):
    import gene_annotation_episode.api_service_execution as executor
    _, handoff = host.launch()
    child = host.results_context(handoff)
    key = host.select(child, DATA_RESULT_OPERATION)
    save = executor._immutable

    def interrupt_receipt(path, body):
        if path.name == "acquisition.json":
            raise asyncio.CancelledError()
        return save(path, body)

    monkeypatch.setattr(executor, "_immutable", interrupt_receipt)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(host.api.execute(child, DATA_RESULT_OPERATION, {}, key))
    action = host.directory_for(child)
    published = read(action / "publication.json")
    grading_before = host.store.get_artifact(published["result"]["grading_artifact_ref"])
    assert not (action / "acquisition.json").exists()
    assert host.journal.row("runtime_actions", child.episode_id, 0)["result"] is None
    monkeypatch.setattr(executor, "_immutable", save)
    forbid_recomputation(monkeypatch)
    host.api = host.reopen()
    outcome = host.execute(child, DATA_RESULT_OPERATION, select=False)
    assert outcome["status"] == "completed", outcome
    qualified = host.api.read_bvbrc_result(outcome["record_refs"][0], context=child)
    assert qualified["binding"]["grading_artifact_ref"] == published["result"]["grading_artifact_ref"]
    assert host.store.get_artifact(qualified["binding"]["grading_artifact_ref"]) == grading_before
    assert read(action / "publication.json") == published
    assert len(host.calls) == 1


def test_same_scope_unreceived_and_forged_contexts_cannot_qualify_existing_result(host):
    child, outcome = host.acquire()
    reference = outcome["record_refs"][0]
    # Receipt/index visibility alone is deliberately insufficient.
    assert host.api.read_result(reference, host.scope)["source_ref"] == reference
    other = host.context("annotation", {}, parent=host.parent)
    for receiver in (host.parent, other):
        with pytest.raises(ValueError, match="bvbrc_host_reference_not_received"):
            host.api.read_bvbrc_result(reference, context=receiver)
    with pytest.raises(ValueError, match="bvbrc_host_context_conflict"):
        host.api.read_bvbrc_result(reference, context=replace(child, run_id="unrelated-run"))
    with pytest.raises(ValueError, match="bvbrc_host_context_conflict"):
        host.api.read_bvbrc_result(reference, context=replace(child, episode_id="arbitrary-same-scope-label"))
    altered = plain(child.request)
    altered["goal"]["objective"] = "Altered original assignment wording"
    with pytest.raises(ValueError, match="bvbrc_host_original_context_conflict"):
        host.api.read_bvbrc_result(reference, context=replace(child, request=altered))


def test_original_source_is_not_a_result_in_another_run_or_narrower_scope(host):
    child, outcome = host.acquire()
    reference = outcome["record_refs"][0]
    target, = host.scope["subject_refs"]
    scope = {"subject_refs": [target], "segments": [
        {"target_ref": target, "start": 0, "end": 4, "unit": "aa"}]}
    host.store.validate_scope(scope)
    narrow = host.context("annotation", {}, parent=host.parent, scope=scope)
    with pytest.raises(ContractError, match="scope_segments_outside_parent"):
        host.api.read_bvbrc_result(reference, context=narrow)
    other_run = "unrelated-authentic-run"
    other_api = APIServiceExecution(host.store, run_id=other_run, directory=host.directory,
        configuration=host.configuration, tool_registry=ToolRegistry(host.store), handoff_unit=3, acquired_record_unit=2)
    identity = EpisodeRef(other_run, (("annotation", "root"),))
    other = BindingContext(other_run, identity.episode_id, "annotation", identity.path,
        host.scope, {}, plain(host.parent.request))
    Journal(host.store, other_run).save("runtime_episodes", {"episode_id": other.episode_id,
        "path": canonical(other.path), "request": canonical(plain(other.request)),
        "initial_credit": 0, "state": "active"})
    with pytest.raises(ValueError, match="not_an_api_acquired_result"):
        other_api.read_bvbrc_result(reference, context=other)
    assert host.api.read_bvbrc_result(reference, context=child)["binding"]["source_ref"] == reference


@pytest.mark.parametrize("defect", ["missing_attempt", "different_form", "failed_attempt", "different_child"])
def test_admission_requires_actual_successful_exact_child_return(host, defect):
    child, outcome = host.acquire()
    reference = outcome["record_refs"][0]
    form, schema, key = host.record_return(child)
    original_form = deepcopy(form)
    if defect == "missing_attempt":
        host.store.db.execute("DELETE FROM runtime_report_attempts WHERE run_id=?", (host.run_id,))
        code = "successful_return_required"
    elif defect == "different_form":
        form["facts_0"][0]["reported_total"] = 400
        code = "admitted_form_conflict"
    elif defect == "failed_attempt":
        host.store.db.execute("UPDATE runtime_report_attempts SET failure=? WHERE run_id=?",
            (canonical({"code": "fixture_delivery_failure"}), host.run_id))
        code = "successful_return_required"
    else:
        unrelated = host.context("annotation", {}, parent=host.parent)
        host.store.db.execute("UPDATE runtime_report_attempts SET child_episode_id=? WHERE run_id=?",
            (unrelated.episode_id, host.run_id))
        code = "return_child_contract_conflict|commission_child_conflict|closed_child_facts_required"
    with pytest.raises(ValueError, match="bvbrc_host_(?:" + code + ")"):
        host.api.record_bvbrc_admission(host.parent, form, schema, key)
    assert host.api.received_bvbrc_context(host.parent) == []
    if defect == "different_form":
        # Rejection of a different proposed form does not erase the valid
        # exact successful return already recorded in the journal.
        assert host.api.record_bvbrc_admission(host.parent, original_form, schema, key) == [reference]
    else:
        with pytest.raises(ValueError):
            host.api.read_bvbrc_result(reference, context=host.parent)


@pytest.mark.parametrize("component", ["source", "raw_bytes", "grading_bytes", "grading_link",
    "original_request", "snapshot_request", "selector", "input_custody", "runtime_action", "runtime_result"])
def test_completed_result_rejects_altered_original_custody(host, component):
    child, outcome = host.acquire()
    reference = outcome["record_refs"][0]
    qualified = host.api.read_bvbrc_result(reference, context=child)
    proof = host.api.completion_for_action(child, f"{child.run_id}:{child.episode_id}:0")
    assert proof is not None
    source = host.store.get(reference)
    action = host.directory_for(child)
    if component in {"source", "grading_link"}:
        if component == "source":
            source["uri"] += "&unselected=true"
        else:
            source["auxiliary_artifact_refs"] = [source["artifact_ref"]]
        host.store.db.execute("UPDATE records SET data=? WHERE id=?", (canonical(source), reference))
    elif component in {"raw_bytes", "grading_bytes"}:
        artifact = source["artifact_ref"] if component == "raw_bytes" else qualified["binding"]["grading_artifact_ref"]
        checksum = artifact.removeprefix("artifact_")
        path = host.store.path / "artifacts" / checksum[:2] / checksum
        path.write_bytes(path.read_bytes() + b" ")
    elif component == "original_request":
        intent = read(action / "intent.json")
        intent["prepared"]["prepared_query"]["original_request"]["filters"] = [
            {"field": "genome_id", "operator": "eq", "value": "unselected"}]
        (action / "intent.json").write_text(canonical(intent) + "\n")
    elif component == "selector":
        receipt = read(action / "acquisition.json")
        receipt["selector"]["page"] = {"offset": 1, "limit": 1}
        (action / "acquisition.json").write_text(canonical(receipt) + "\n")
    elif component == "snapshot_request":
        metadata = read(action / "snapshot.json")
        metadata["request"]["limit"] = 99
        (action / "snapshot.json").write_text(canonical(metadata) + "\n")
    elif component == "input_custody":
        inputs = read(action / "publication_inputs.json")
        inputs["prepared"]["original_request"]["limit"] = 19
        (action / "publication_inputs.json").write_text(canonical(inputs) + "\n")
    elif component == "runtime_action":
        selected = json.loads(host.journal.row("runtime_actions", child.episode_id, 0)["action"])
        selected["tool"] = DATA_QUERY_OPERATION
        host.store.db.execute("UPDATE runtime_actions SET action=? WHERE run_id=? AND episode_id=? AND decision_index=0",
            (canonical(selected), host.run_id, child.episode_id))
    else:
        host.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0",
            (host.run_id, child.episode_id))
    with pytest.raises((ValueError, ContractError), match="(?:bvbrc_host_|api_|artifact_digest_mismatch)"):
        host.api.read_bvbrc_result(reference, context=child)
    assert not host.api.verify_completion(child, proof)
    assert len(host.calls) == 1


def feature_selection(source=None, *, collection="feature_sequence", include_sequence_values=True):
    return selector({"family": "feature_sequence", "feature_ids": ["feature-a", "feature-b"],
        "sequence_kind": "AA", "feature_metadata_fields": [],
        "include_sequence_values": include_sequence_values},
        inputs=[] if source is None else [{"collection": collection, "source_ref": source}])


def feature_inputs(host, *, admit=True):
    sequence = "MACDEFGH"
    checksum = hashlib.md5(sequence.encode()).hexdigest()
    child, outcome = host.acquire(request("feature_sequence", fields=["md5", "sequence_type", "sequence"]),
        body=envelope([{"md5": checksum, "sequence_type": "AA", "sequence": sequence}]))
    reference = outcome["record_refs"][0]
    if admit:
        host.admit(child)
    features = [{"feature_id": identifier, "aa_sequence_md5": checksum, "aa_length": len(sequence)}
                for identifier in ("feature-a", "feature-b")]
    query = request("genome_feature", fields=["feature_id", "aa_sequence_md5", "aa_length"])
    return child, reference, query, envelope(features)


def test_explicit_join_uses_only_parent_received_named_input_pages(host):
    input_child, reference, query, body = feature_inputs(host)
    child, outcome = host.acquire(query, feature_selection(reference), body=body,
        sources=("execution_bvbrc_feature_sequence_rows",))
    qualified = host.api.read_bvbrc_result(outcome["record_refs"][0], context=child)
    assert qualified["grading"]["input_bindings"] == [
        host.api.read_bvbrc_result(reference, context=input_child)["binding"]]
    assert len(qualified["input_results"]) == 1
    assert host.api.read_bvbrc_result(reference, context=child)["host_qualification"]["possession_basis"] == "parent_assignment"
    joined = qualified["grading"]["feature_sequence_sheet"]
    assert [edge["feature_id"] for edge in joined["edges"]] == ["feature-a", "feature-b"]
    assert all(edge["join_status"] == "joined" for edge in joined["edges"])
    assert len({edge["native_md5"] for edge in joined["edges"]}) == 1
    assert len(host.calls) == 2
    # The same host has the sequence page, but omitting it from this selector
    # must preserve a missing-page requirement and make no hidden acquisition.
    missing, partial = host.acquire(query, feature_selection(), body=body,
        sources=("execution_bvbrc_feature_sequence_rows",))
    unavailable = host.api.read_bvbrc_result(partial["record_refs"][0], context=missing)
    assert unavailable["input_results"] == []
    assert unavailable["grading"]["feature_sequence_sheet"]["requirements"]
    assert all(not edge["sequence_rows"] for edge in unavailable["grading"]["feature_sequence_sheet"]["edges"])
    with pytest.raises(ValueError, match="bvbrc_host_reference_not_received"):
        host.api.read_bvbrc_result(reference, context=missing)
    assert len(host.calls) == 3


@pytest.mark.parametrize("invalid", ["unreceived", "wrong_collection", "other_parent"])
def test_join_rejects_unreceived_wrong_collection_or_unrelated_parent_input(host, invalid):
    _, reference, query, body = feature_inputs(host, admit=invalid != "unreceived")
    selection = feature_selection(reference, collection="genome_feature" if invalid == "wrong_collection" else "feature_sequence")
    parent = host.context("annotation", {}, parent=host.parent) if invalid == "other_parent" else host.parent
    _, handoff = host.launch(query, body=body, parent=parent)
    child = host.results_context(handoff, selection, parent=parent)
    before = len(host.calls)
    outcome = host.execute(child, DATA_RESULT_OPERATION)
    assert outcome["status"] in {"invalid", "failed"}, outcome
    assert outcome["record_refs"] == []
    assert outcome["feedback"]["code"] == (
        "bvbrc_host_join_input_conflict" if invalid == "wrong_collection" else "bvbrc_host_reference_not_received")
    assert len(host.calls) == before
    assert host.api.completion_for_action(child, f"{child.run_id}:{child.episode_id}:0") is None


def test_same_acquisition_reprojection_is_zero_new_record_credit_but_changed_page_is_distinct(host):
    query = request("genome", fields=["genome_id", "genome_length"], limit=1)
    _, handoff = host.launch(query, body=envelope([{"genome_id": "g0", "genome_length": 12}], total=2))
    first = host.results_context(handoff, selector())
    original = host.execute(first, DATA_RESULT_OPERATION)
    second = host.results_context(handoff, row_selector(numbers=["genome_length"]))
    projected = host.execute(second, DATA_RESULT_OPERATION)
    old_ref, new_ref = original["record_refs"][0], projected["record_refs"][0]
    assert old_ref != new_ref  # Different retained local selections/sheets.
    assert host.api.result_identity(old_ref, host.scope) == host.api.result_identity(new_ref, host.scope)
    credit = host.api.credit_view(second, {"known_record_refs": [old_ref, new_ref], "initial_known_record_refs": [old_ref]})
    assert credit["new_acquired_record_count"] == 0
    assert credit["operational_credit"] == 0
    assert credit["operational_credit_binding"]["scientific_credit"] is False
    assert credit["operational_credit_binding"]["monitoring_credit"] is False
    assert len(host.calls) == 1
    changed = host.results_context(handoff, selector(page={"offset": 1, "limit": 1}))
    host.responses.append(envelope([{"genome_id": "g1", "genome_length": 19}], start=1, total=2))
    next_page = host.execute(changed, DATA_RESULT_OPERATION)
    next_ref = next_page["record_refs"][0]
    assert host.api.result_identity(next_ref, host.scope) != host.api.result_identity(old_ref, host.scope)
    credit = host.api.credit_view(changed, {"known_record_refs": [old_ref, next_ref], "initial_known_record_refs": [old_ref]})
    assert credit["new_acquired_record_count"] == 1 and credit["operational_credit"] == 2
    assert len(host.calls) == 2
    assert host.store.db.execute("SELECT count(*) FROM records WHERE record_type IN ('observation','hypothesis','annotation')").fetchone()[0] == 0


def supplied_metadata(host, *, received=True, units=True, raw_provenance=False):
    """Retain synthetic design JSON in an actually acquired source artifact.

    The extra envelope member is explicit fixture data, not a claim that the
    deployed Solr service emits an experimental-design field. Its exact bytes
    and receipt exercise the source/JSON-pointer host boundary without faking
    a source-completion action or a qualification object.
    """
    data = {"result_id": "result-µ", "bioset_id": "bioset-β", "sample_ids": [],
        "biological_replicate_ids": None, "technical_replicate_ids": [],
        "measurement_units": [{"field": "counts", "unit": "intensity µmol / L"}] if units else [],
        "normalization_method": None, "pvalue_correction_method": None,
        "contrast": {"numerator_condition": "条件 β", "denominator_condition": "基線"}}
    raw_data = {**data, "provenance": {"literal_extra_field": True}} if raw_provenance else data
    child, result = host.acquire(request("genome", fields=["genome_id"]),
        body=envelope([{"genome_id": "metadata-reference"}], **{"design/block~": [raw_data]}))
    source = result["record_refs"][0]
    if received:
        host.admit(child)
    return {**data, "provenance": {"source_ref": source, "record_path": "/design~1block~0/0"}}


def molecular_selection(supplied, *, metadata=()):
    return selector({"family": "molecular_experiment", "result_ids": ["result-µ"],
        "measurement_fields": ["counts"], "metadata_fields": [
            {"source_level": "supplied", "field": name} for name in metadata]}, supplied=[supplied])


def molecular_query():
    return request("bioset_result", fields=["id", "exp_id", "bioset_id", "feature_id", "counts"],
        filters=[{"field": "bioset_id", "operator": "eq", "value": "bioset-β"}])


def molecular_body():
    return envelope([{"id": "result-µ", "exp_id": "experiment-e", "bioset_id": "bioset-β",
                      "feature_id": "feature-f", "counts": -1.25}])


@pytest.mark.parametrize("units", [True, False])
def test_supplied_metadata_exact_object_unicode_hash_and_null_empty_values_survive_host(host, monkeypatch, units):
    supplied = supplied_metadata(host, units=units)
    selection = molecular_selection(supplied, metadata=("sample_ids", "biological_replicate_ids",
        "technical_replicate_ids", "measurement_units", "normalization_method", "contrast"))
    child, outcome = host.acquire(molecular_query(), selection, body=molecular_body(),
        sources=("execution_bvbrc_expression_rows",))
    assert outcome["status"] == "completed", outcome
    reference = outcome["record_refs"][0]
    qualified = host.api.read_bvbrc_result(reference, context=child)
    prepared = qualified["grading"]["prepared"]
    expected_prepared = hashlib.sha256(json.dumps(prepared, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
    assert qualified["grading"]["parse_result"]["sheet"]["custody"]["prepared_sha256"] == expected_prepared
    assert qualified["binding"]["acquisition_assignment_sha256"] == digest(child.assignment)
    assert qualified["binding"]["selector_sha256"] == digest(selection)
    metadata = {key: value for key, value in supplied.items() if key != "provenance"}
    expected = hashlib.sha256(json.dumps(metadata, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
    binding, = qualified["grading"]["metadata_bindings"]
    assert binding["metadata_sha256"] == expected
    assert binding["metadata_sha256"] != hashlib.sha256(json.dumps(metadata, sort_keys=True,
        separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    assert binding["record_path"] == "/design~1block~0/0"
    assert binding["native_sha256"] == hashlib.sha256(host.store.get_artifact(binding["native_artifact_ref"])).hexdigest()
    assert qualified["grading"]["molecular_sheet"]["supplied_metadata"] == [supplied]
    host.admit(child)
    materialized = next(value for value in host.api.received_bvbrc_context(host.parent)
                        if value["fact_source"] == "execution_bvbrc_expression_rows")
    fact, = materialized["facts"]
    measurement, = fact["measurements"]
    assert measurement["value"] == -1.25
    cells = [cell for cell in materialized["cells"] if cell["source_level"] == "supplied"]
    sample, = [cell for cell in cells if cell["field"] == "sample_ids"]
    assert (sample["presence"], sample["native_shape"], sample["atoms"]) == ("present", "array", [])
    missing, = [cell for cell in cells if cell["field"] == "biological_replicate_ids"]
    assert (missing["presence"], missing["native_shape"], missing["atoms"], missing["status"]) == ("null", "null", [], "missing")
    assert all(cell["collection"] is None and cell["native_id"] is None and cell["row_ref"] is None for cell in cells)
    if units:
        unit_ref, = measurement["unit_value_refs"]
        unit, = [cell for cell in cells if cell["cell_ref"] == unit_ref]
        assert unit["atoms"][0]["string_value"] == "intensity µmol / L"
        assert unit_ref.endswith("/design~1block~0/0/measurement_units/0/unit")
    else:
        assert measurement["unit_value_refs"] == []
        empty, = [cell for cell in cells if cell["field"] == "measurement_units"]
        assert (empty["presence"], empty["native_shape"], empty["atoms"]) == ("present", "array", [])
        assert {"field": "measurement_units", "source_level": "supplied", "reason": "unknown_units"} in fact["metadata_unavailable"]
    assert len(host.calls) == 2
    saved = host.api.received_bvbrc_context(host.parent)
    forbid_recomputation(monkeypatch)
    host.api = host.reopen()
    assert host.execute(child, DATA_RESULT_OPERATION, select=False) == outcome
    assert host.api.read_bvbrc_result(reference, context=child)["grading"]["metadata_bindings"] == [binding]
    assert host.api.received_bvbrc_context(host.parent) == saved


@pytest.mark.parametrize("invalid", ["unreceived", "different_value", "wrong_pointer", "provenance_is_data"])
def test_supplied_metadata_rejects_unreceived_source_or_nonidentical_pointed_object(host, invalid):
    supplied = supplied_metadata(host, received=invalid != "unreceived", raw_provenance=invalid == "provenance_is_data")
    if invalid == "different_value":
        supplied["measurement_units"][0]["unit"] = "invented unit"
    elif invalid == "wrong_pointer":
        supplied["provenance"]["record_path"] = "/response/docs/0"
    _, handoff = host.launch(molecular_query(), body=molecular_body())
    child = host.results_context(handoff, molecular_selection(supplied),
        sources=("execution_bvbrc_expression_rows",))
    outcome = host.execute(child, DATA_RESULT_OPERATION)
    assert outcome["status"] in {"invalid", "failed"}
    assert outcome["record_refs"] == []
    assert outcome["feedback"]["code"] == ("bvbrc_host_reference_not_received" if invalid == "unreceived"
                                            else "bvbrc_host_metadata_values_conflict")
    assert len(host.calls) == 2


def test_interrupted_join_replay_retains_original_input_bindings_without_recalculation(host, monkeypatch):
    import gene_annotation_episode.api_service_execution as executor
    _, reference, query, body = feature_inputs(host)
    _, handoff = host.launch(query, body=body)
    child = host.results_context(handoff, feature_selection(reference),
        sources=("execution_bvbrc_feature_sequence_rows",))
    key = host.select(child, DATA_RESULT_OPERATION)
    save = executor._immutable

    def interrupt_receipt(path, body):
        if path.name == "acquisition.json":
            raise asyncio.CancelledError()
        return save(path, body)

    monkeypatch.setattr(executor, "_immutable", interrupt_receipt)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(host.api.execute(child, DATA_RESULT_OPERATION, {}, key))
    action = host.directory_for(child)
    frozen = read(action / "publication_inputs.json")
    assert [item["binding"]["source_ref"] for item in frozen["input_results"]] == [reference]
    original_bytes = (action / "publication_inputs.json").read_bytes()
    monkeypatch.setattr(executor, "_immutable", save)
    forbid_recomputation(monkeypatch)
    host.api = host.reopen()
    completed = host.execute(child, DATA_RESULT_OPERATION, select=False)
    assert completed["status"] == "completed", completed
    result = host.api.read_bvbrc_result(completed["record_refs"][0], context=child)
    assert result["input_results"] == frozen["input_results"]
    assert (action / "publication_inputs.json").read_bytes() == original_bytes
    assert read(action / "acquisition.json")["publication_inputs_sha256"] == json_digest(frozen)
    assert len(host.calls) == 2


@pytest.mark.parametrize("altered", ["input_receipt", "frozen_input_binding"])
def test_completed_join_rechecks_original_input_receipt_and_bound_grading(host, altered):
    input_child, reference, query, body = feature_inputs(host)
    child, outcome = host.acquire(query, feature_selection(reference), body=body,
        sources=("execution_bvbrc_feature_sequence_rows",))
    source = outcome["record_refs"][0]
    qualified = host.api.read_bvbrc_result(source, context=child)
    assert qualified["input_results"][0]["binding"]["source_ref"] == reference
    proof = host.api.completion_for_action(child, f"{child.run_id}:{child.episode_id}:0")
    assert proof is not None
    if altered == "input_receipt":
        host.store.db.execute("UPDATE runtime_actions SET result=NULL WHERE run_id=? AND episode_id=? AND decision_index=0",
            (host.run_id, input_child.episode_id))
    else:
        path = host.directory_for(child) / "publication_inputs.json"
        frozen = read(path)
        frozen["input_results"][0]["binding"]["grading_artifact_ref"] = qualified["binding"]["grading_artifact_ref"]
        path.write_text(canonical(frozen) + "\n")
    with pytest.raises(ValueError, match="bvbrc_host_(completed_acquisition_required|publication_inputs_conflict)"):
        host.api.read_bvbrc_result(source, context=child)
    assert not host.api.verify_completion(child, proof)
    assert len(host.calls) == 2

