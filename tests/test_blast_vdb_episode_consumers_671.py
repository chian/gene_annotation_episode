"""Configured generic episode consumers over controlled VDB protocol fixtures.

No native bioinformatics executable or external acquisition runs here. Native
start/status and wrapper output are explicit fixtures. Real reservation,
producer, capture, deterministic workers, publication and return readers run
inside the existing bounded529 test service.
"""
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, ValidationError

from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode import native_blast_utility_driver as driver
from gene_annotation_episode import native_blast_vdb_utility_execution as offline
from gene_annotation_episode.blast_utility_result_views import (
    FACT_SOURCES, IDENTIFIER_NAMESPACES, NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA,
    NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V2_SCHEMA, PROJECTION_V2_FIELDS,
    projection_identifiers,
)
from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, LAUNCH_VERSION, RESULTS_VERSION
from gene_annotation_episode.execution_progress import describe_execution_target
from gene_annotation_episode.native_blast_utility_contracts import (
    JOB_VERSION_V3, requested_job_from_native_blast_utility,
)
from gene_annotation_episode.native_blast_utility_local import local_blast_utility_plan
from gene_annotation_episode.numerical import NumericBand, YieldParameters
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import assess_validations, validate_assignment
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_blast_utility_episode_wiring_632 import assignment, context
from test_blast_vdb_native_context_668 import controlled_job, controlled_dependency_job, _reseal_manifest
from test_blast_vdb_publication_returns_669 import selector, sequence_selection, report_schema
from test_native_blast_utility_practical_630 import publish as publish_practical, environment as old_environment
from test_native_blast_utility_producer_628 import POLICY, job_fixture
from test_native_blast_utility_publication_631 import inline_workers, selector as old_selector
from test_practical_yield import completion_context


VARIANTS = ("entry", "entry_batch", "all_native_sequences", "all_references", "info", "paths", "paths_all")


def binding(job):
    params = job["operation"]["parameters"]
    selected = params["selection"]
    return {"program": "blast_vdb_cmd", "mode": job["operation"]["mode"],
        "software": deepcopy(job["software"]), "molecules": ["dna"], "variants": [{
            "database_source": params["database_selection"]["source"], "database_input_kind": "path",
            "selection_kind": None if selected is None else selected["kind"],
            "entry_source": None if selected is None else selected.get("source"),
            "include_filtered_reads": params["include_filtered_reads"]}]}


@pytest.fixture
def hosts(tmp_path):
    stores = []
    def make(variant="entry", database_source="db", *, filtered=False, job=None):
        root = tmp_path / str(len(stores))
        root.mkdir()
        job = controlled_job(root, variant, database_source) if job is None else deepcopy(job)
        job["operation"]["parameters"]["include_filtered_reads"] = filtered
        store = Store(root / "store")
        stores.append(store)
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"]}
        journal = Journal(store, "controlled-vdb-671-" + str(len(stores)))
        config = {"kind": "local", "workspace": str(root), "policy": deepcopy(POLICY),
            "native_blast_utility": [binding(job)]}
        family = ExecutionEpisodes(None, store=store, directory=root / "run", run_id=journal.run_id,
            resources={"selected-local": config}, initial_information={}, tool_registry=ToolRegistry(store),
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=32, log_roles=["stdout", "stderr"])
        return SimpleNamespace(store=store, scope=scope, journal=journal, job=job, family=family,
            configuration=config, tmp_path=root, receipts=EpisodeReceipts(store, journal.run_id))
    yield make
    for store in stores:
        store.close()


def launch_request(h, selected=None):
    return {"version": LAUNCH_VERSION, "requests": {"selected-local": selected or assignment(h)},
        "immutable_input_versions": [], "constraints": {}}


@pytest.mark.parametrize("variant,database_source,filtered", [
    (variant, source, filtered)
    for source in ("db", "dbs_file") for variant in VARIANTS
    for filtered in ((False, True) if variant in {"entry", "entry_batch", "all_native_sequences"} else (False,))
])
def test_exact_bound_vdb_variants_use_existing_launch_resource_route(hosts, variant, database_source, filtered):
    h = hosts(variant, database_source, filtered=filtered)
    selected = assignment(h)
    assert validate_assignment(selected) == selected
    Draft202012Validator(h.family.assignment_schema("launch_local")).validate(selected)
    assert h.family._validate_request(selected) == selected
    parent = context(h, "annotation", {})
    launch = launch_request(h, selected)
    assert h.family.prepare_assignment(parent, "launch", launch, h.scope, "launch") == launch
    launch_context = context(h, "launch", launch, parent=parent)
    assert h.family.prepare_assignment(launch_context, "launch_local", selected, h.scope, "local") == selected
    assert h.family.allowed_children(parent, ("launch", "launch_local", "results")) == ()
    assert h.family.allowed_children(launch_context, ("launch_local",)) == ("launch_local",)
    name = "native.blast_vdb_cmd." + h.job["operation"]["mode"]
    row, = [row for row in h.family.resource_tool_contracts() if row["name"] == name]
    assert row["invocation_route"]["routes"] == [{"entry_role": "launch", "resource_id": "selected-local",
        "resource_role": "launch_local"}]
    Draft202012Validator(row["input_schema"]).validate(selected["requested_job"])
    assert [r["name"] for r in h.family.catalog(launch_context)] == ["execution.capabilities"]
    assert not list(h.tmp_path.glob(".episode-operations/*/*/native.json"))


@pytest.mark.parametrize("fault", ["software", "variant", "resource", "kind", "allocation", "workspace", "unbound"])
def test_vdb_assignment_rejects_changed_selection_before_execution(hosts, fault):
    h = hosts()
    selected = assignment(h)
    if fault in {"software", "variant"}:
        job = deepcopy(h.job)
        if fault == "software":
            job["software"]["engine_version"] = "unbound-version"
        else:
            job["operation"]["parameters"]["include_filtered_reads"] = True
        selected["requested_job"] = requested_job_from_native_blast_utility(job)
    elif fault == "resource": selected["resource_id"] = "other"
    elif fault == "kind": selected["resource_kind"] = "hpc"
    elif fault == "allocation": selected["constraints"]["allocation"]["scratch_bytes"] -= 1
    elif fault == "workspace": selected["workspace"] = "/outside-selected-workspace"
    else: h.family._practical["selected-local"].resources["local"]["native_blast_utility"] = []
    with pytest.raises(ValueError):
        h.family._validate_request(selected)
    assert not list(h.tmp_path.glob(".episode-operations/*/*/native.json"))


@pytest.mark.parametrize("kind", ["pbs_ssh", "api"])
def test_vdb_is_not_exposed_as_an_unbound_resource(hosts, kind):
    h = hosts()
    with pytest.raises(ValueError, match="native_blast_utility_resource_execution_binding_unfinished"):
        ExecutionEpisodes(None, store=h.store, directory=h.tmp_path / "invalid", run_id=h.journal.run_id,
            resources={"selected-local": {**h.configuration, "kind": kind}}, initial_information={},
            tool_registry=h.family.tool_registry, handoff_unit=3, acquired_record_unit=2,
            log_window_bytes=32, log_roles=[])


def test_results_assignment_schema_admits_exact_two_selector_versions(hosts):
    h = hosts()
    schema = h.family.assignment_schema("results")
    utility, = [row for row in schema["properties"]["selector"]["allOf"]
        if row["if"]["properties"]["version"].get("enum") == [
            "native_blast_utility_result_selector_v1", "native_blast_utility_result_selector_v2"]]
    assert utility["then"] == NATIVE_BLAST_UTILITY_RESULT_SELECTOR_SCHEMA
    for selected in (selector(), old_selector()):
        request = {"version": RESULTS_VERSION, "handoff_ref": "selected-handoff", "selector": selected}
        Draft202012Validator(schema).validate(request)
        assert h.family._utility_selector(request)
        invalid = deepcopy(request)
        invalid["selector"]["unrequested"] = True
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate(invalid)
    assert not h.family._utility_selector({"selector": {"version": "native_blast_utility_result_selector_v3"}})


def test_selector_version_and_requested_ordinal_belong_to_original_operation(hosts):
    h = hosts()
    target = {"resource_kind": "local", "assignment": assignment(h)}
    with pytest.raises(ValueError):
        h.family._selector({"selector": old_selector()}, target)
    with pytest.raises(ValueError):
        h.family._selector({"selector": selector(sequences=sequence_selection(1))}, target)
    old = job_fixture(h.tmp_path / "classic", "extract_sequences")
    with pytest.raises(ValueError):
        h.family._selector({"selector": selector()}, {"resource_kind": "local", "assignment": {
            "requested_job": requested_job_from_native_blast_utility(old)}})
    with pytest.raises(ValueError, match="native_blast_utility_result_target_conflict"):
        h.family._selector({"selector": selector()}, {**target, "resource_kind": "hpc"})


@pytest.mark.parametrize("supporting", [False, True])
def test_selected_inputs_require_actual_receipt_and_exact_original_identity(hosts, tmp_path, supporting):
    job = controlled_dependency_job(tmp_path / "dependencies") if supporting else controlled_job(tmp_path / "inputs")
    h = hosts(job=job)
    parent = context(h, "annotation", {})
    database = (h.job["vdb_context_request"]["dependency_databases"][0] if supporting else h.job["databases"][0])
    descriptor = database["manifest"]["preparation"]["receipt"]
    reference = h.store.artifact(Path(descriptor["path"]).read_bytes())
    descriptor["artifact_ref"] = reference
    _reseal_manifest(database)
    selected = launch_request(h)
    with pytest.raises(ValueError, match="original_input_not_received"):
        h.family.prepare_assignment(parent, "launch", selected, h.scope, "before-receipt")
    h.receipts.receive(parent.episode_id, [reference], kind="initial")
    assert h.family.prepare_assignment(parent, "launch", selected, h.scope, "received") == selected
    assert h.family._utility_inputs(parent, assignment(h)) == [reference]
    other = h.store.artifact(b"different original input")
    h.receipts.receive(parent.episode_id, [other], kind="initial")
    descriptor["artifact_ref"] = other
    _reseal_manifest(database)
    with pytest.raises(ValueError, match="original_input_identity_conflict"):
        h.family.prepare_assignment(parent, "launch", launch_request(h), h.scope, "wrong-bytes")


def practical(h, monkeypatch, *, native_returncode=0):
    """Real selected reservations and receipts; controlled native start/output."""
    run, episode = h.journal.run_id, "controlled-local-671"
    key = f"{run}:{episode}:0"
    root = h.tmp_path / ".episode-operations" / digest({"run": run, "episode": episode}) / digest(key)
    selected = assignment(h)
    selected["endpoint"] = "completed_job_outputs"
    selected["progress_requirements"] = [{"key": "outputs", "credit": 3,
        "predicate": {"kind": "requested_job_outputs", "output_paths": [str(root / "blast-utility-attempt/bundle.json")]}}]
    selected["completion_keys"] = ["outputs"]
    operations = LocalPracticalOperations(h.configuration)
    state = PracticalState(h.tmp_path / "practical", run, episode, selected,
        initial_outcome=operations.initial_outcome(selected))
    e = SimpleNamespace(assignment=selected, configuration=h.configuration, operations=operations,
        state=state, root=root, attempt=root / "blast-utility-attempt", key=key, starts=[], views={},
        run=run, episode=episode, resource="selected-local", tmp_path=h.tmp_path, wrapper_calls=[])

    def start(handle):
        e.starts.append(str(handle.path))
        body = handle.read()
        body["stage"] = "released"
        handle.path.write_text(json.dumps(body))
        e.views[str(handle.path)] = {"state": "running", "terminal": False,
            "metadata": {**body["metadata"], "native_returncode": None}}

    monkeypatch.setattr(native, "start_prepared", start)
    monkeypatch.setattr(native, "resume_start", lambda *a, **k: pytest.fail("unselected resubmission"))
    monkeypatch.setattr(native, "status", lambda handle: deepcopy(e.views[str(handle.path)]))

    def act(index, tool="practical.job.start", arguments=None):
        arguments = {} if arguments is None else arguments
        selected_key = f"{run}:{episode}:{index}"
        intent = state.begin(selected_key, tool, arguments)
        if intent["state"] == "completed":
            return intent["receipt"]
        outcome, after = operations._execute(state, tool, arguments, selected_key)
        return state.finish(selected_key, outcome, assess_validations(selected, outcome,
            state.context() if after is None else after, tool_name=tool), context_after=after)

    def seal():
        handle = native.NativeJobHandle(root / "native.json")
        plan = local_blast_utility_plan(selected, str(handle.path))
        def wrapper(argv, **kwargs):
            e.wrapper_calls.append(list(argv))
            fd, = kwargs["pass_fds"]
            os.write(fd, ('{"child-pid":91}\n{"exit-code":' + str(native_returncode) + '}\n').encode())
            mode = h.job["operation"]["mode"]
            raw = (b"controlled_read\taccession\t4\tacgt\n" if mode == "extract_sequences" else
                ("VDB(s): \n" + h.job["databases"][0]["native_paths"][0] +
                 "\nVDB Alias File(s): None\nBlats DB Alias File(s): None\n").encode())
            kwargs["stdout"].write(raw)
            return SimpleNamespace(returncode=native_returncode)
        monkeypatch.setattr(offline.subprocess, "run", wrapper)
        bundle = driver.run_native_blast_utility(plan)
        e.views[str(handle.path)] = {"state": "returned", "terminal": True,
            "metadata": {**handle.read()["metadata"], "native_returncode": 0 if not bundle["failures"] else 1,
                "duration_measure": "service_wall_seconds", "elapsed_seconds": 2.5}}
        return plan, bundle

    e.act, e.seal = act, seal
    return e


def test_vdb_status_uses_original_attempt_and_replays_without_acquisition(hosts, monkeypatch):
    h = hosts()
    e = practical(h, monkeypatch)
    started = e.act(0)
    handoff = publish_practical(h.store, e, started, scope=h.scope)
    parent = context(h, "annotation", {})
    h.receipts.receive(parent.episode_id, [handoff], kind="initial")
    selected = {"version": RESULTS_VERSION, "handoff_ref": handoff, "selector": selector()}
    child = context(h, "results", selected, parent=parent)
    h.family.initialize(child)
    key = f"{child.run_id}:{child.episode_id}:0"
    h.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": 0,
        "action": canonical({"kind": "tool", "tool": "execution.results.status", "arguments": {}}), "result": None})
    result = asyncio.run(h.family.execute(child, "execution.results.status", {}, key))
    assert result["status"] == "completed", result
    body = result["result"]
    assert body["version"] == "native_blast_utility_acquired_result_v2"
    assert body["capture"] is None and body["prepared"] is None and body["source_ref"] is None
    assert all(body[field] == [] for field in ("paths", "path_sections", "vdb_context"))
    assert result["record_refs"] == [] and not body["complete"]
    h.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=?",
        (canonical(result), child.run_id, child.episode_id))
    monkeypatch.setattr(native, "status", lambda *a, **k: pytest.fail("saved status observed again"))
    assert asyncio.run(h.family.execute(child, "execution.results.status", {}, key)) == result
    assert h.family.completion_for_action(child, key) is None
    assert h.family.project_credit(child, {"known_record_refs": [], "initial_known_record_refs": []})["credit"] == 0
    assert len(e.starts) == 1 and e.wrapper_calls == []
    assert h.store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (child.episode_id,)).fetchone()[0] == 1
    assert h.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


@pytest.mark.parametrize("native_returncode", [0, 7])
@pytest.mark.parametrize("variant", ["entry", "paths_all"])
def test_configured_capture_result_return_and_replay_preserve_original_credit(hosts, monkeypatch, variant, native_returncode):
    h = hosts(variant, "dbs_file")
    e = practical(h, monkeypatch, native_returncode=native_returncode)
    e.act(0)
    plan, bundle = e.seal()
    closed = e.act(1, "practical.job.collect")
    assert closed["validations"][0]["satisfied"] is (native_returncode == 0)
    assert len(e.starts) == len(e.wrapper_calls) == 1
    assert bundle["output_completeness_basis"] == "captured_bytes"
    assert [r["role"] for r in bundle["artifacts"]] == ["stdout", "stderr"]
    frozen_practical = deepcopy(e.state.receipts())
    handoff = publish_practical(h.store, e, closed, scope=h.scope)
    target = h.family.job_progress_provider.targets.read_target(handoff, h.scope)
    assert target["execution_id"] == plan["identity"]["execution_id"]
    assert h.family.job_progress_provider.targets.returnable_handoff(target)
    chosen = selector(vdb_context=True, saved_data=["result"],
        sequences=sequence_selection(0, fields=("native_reported_length", "native_length_basis", "returned_symbol_count"))
            if variant == "entry" else None,
        paths=None if variant == "entry" else {"kinds": ["vdb", "vdb_alias", "blast_db_alias"],
            "native_path_ordinals": None, "include_sections": True})
    schema = report_schema("sequences", "paths", "path_sections", "vdb_context", "saved_data", "status")
    parent = context(h, "annotation", {}, schema=schema)
    selected = {"version": RESULTS_VERSION, "handoff_ref": handoff, "selector": chosen}
    with pytest.raises(ValueError, match="original_handoff_not_received"):
        h.family.prepare_assignment(parent, "results", selected, h.scope, "unreceived")
    h.receipts.receive(parent.episode_id, [handoff], kind="initial")
    assert h.family.prepare_assignment(parent, "results", selected, h.scope, "results") == selected
    child = context(h, "results", selected, parent=parent, schema=schema)
    h.family.initialize(child)
    assert h.family.initial_references(child) == [handoff]
    assert [r["name"] for r in h.family.catalog(child)] == ["execution.results.status", "execution.results.collect"]
    rejected = asyncio.run(h.family.execute(child, "execution.results.read", {}, "unselected"))
    assert rejected["status"] == "invalid" and rejected["record_refs"] == []
    descriptor = h.family.job_progress_provider.targets.describe_target(handoff, h.scope, selector=chosen)
    assert descriptor["native_job_version"] == JOB_VERSION_V3
    assert descriptor["native_output_format"] == h.job["operation"]["parameters"]["output_format"]
    assert descriptor["result_selector_schema"] == NATIVE_BLAST_UTILITY_RESULT_SELECTOR_V2_SCHEMA
    assert descriptor["result_selection"] == chosen
    assert descriptor["extractors"][1]["return_fact_sources"] == list(FACT_SOURCES)
    assert "execution.results.read" not in descriptor["acquisition_operations"]
    with pytest.raises(ValueError):
        h.family.job_progress_provider.targets.describe_target(handoff, h.scope, selector=old_selector())
    workers = inline_workers(monkeypatch)
    key = f"{child.run_id}:{child.episode_id}:0"
    h.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": 0,
        "action": canonical({"kind": "tool", "tool": "execution.results.collect", "arguments": {}}), "result": None})
    result = asyncio.run(h.family.execute(child, "execution.results.collect", {}, key))
    assert result["status"] == "completed", result
    body = result["result"]
    assert body["version"] == "native_blast_utility_acquired_result_v2" and body["complete"], body
    assert body["status"]["native_state"] == ("succeeded" if native_returncode == 0 else "failed")
    h.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=?",
        (canonical(result), child.run_id, child.episode_id))
    facts = h.family.facts(child, {})
    form = form_with_facts({}, schema, facts)
    h.family.validate_report(child, form, schema)
    if variant == "entry":
        assert form["sequences"][0]["fields"] == {"native_reported_length": 4,
            "native_length_basis": "returned_sequence", "returned_symbol_count": 4}
        assert form["sequences"][0]["sequences"] == {"normalized_sequence": "ACGT"}
    h.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
    h.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": 0,
        "action": canonical({"kind": "episode_child", "role": "results", "scope": h.scope,
            "assignment": selected, "schema_json": canonical(schema),
            "purpose": child.request["report_contract"]["decision"]}), "result": None})
    h.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": 0,
        "delivery_ref": "controlled-671", "child_episode_id": child.episode_id,
        "contract": canonical(child.request["report_contract"]), "form": canonical(form), "failure": None})
    admitted = h.family.received_form_references(parent, form, schema, f"{parent.run_id}:{parent.episode_id}:0:typed_form")
    assert admitted == body["record_refs"]
    h.receipts.receive(parent.episode_id, admitted, kind="child_form", source_index=0)
    h.family.validate_received_report(parent, form, schema)
    assert h.family.received_report_facts(parent)["execution.blast_utility_vdb_context"] == form["vdb_context"]
    for namespace in IDENTIFIER_NAMESPACES:
        for reference in projection_identifiers({k: body[k] for k in PROJECTION_V2_FIELDS}, namespace):
            assert h.family.resolve_received_reference(parent, reference, namespace)
            assert not h.family.resolve_received_reference(parent, reference + "-wrong", namespace)
    assert not h.family.resolve_received_reference(parent, body["capture"]["bundle_artifact_ref"], "artifact")
    for row in body["capture"]["artifacts"]:
        assert not h.family.resolve_received_reference(parent, row["artifact_ref"], "artifact")
    assert h.family.resolve_received_reference(parent, body["prepared"]["result_artifact_ref"], "artifact")
    credit = h.family.project_credit(child, {"known_record_refs": body["record_refs"], "initial_known_record_refs": []})
    assert credit["credit"] == 2 and credit["new_acquired_record_count"] == 1
    proof = h.family.completion_for_action(child, key)
    assert h.family.verify_completion(child, proof)
    estimation = completion_context(run_id=child.run_id, episode_id=child.episode_id, unit_index=0, action_index=0)
    estimation["practical_completion"].update(proof)
    estimate = h.family.practical_estimator(child)((2.0,), YieldParameters(), (estimation,))
    assert estimate.expected_next_gain == NumericBand.exact(0) and estimate.turns == 1
    monkeypatch.setattr(native, "status", lambda *a, **k: pytest.fail("closed replay polled native"))
    assert asyncio.run(h.family.execute(child, "execution.results.collect", {}, key)) == result
    assert len(workers) == 2 and len(e.starts) == len(e.wrapper_calls) == 1
    assert e.state.receipts() == frozen_practical
    assert h.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


@pytest.mark.parametrize("fault", ["attempt", "owner", "allocation", "handoff"])
def test_vdb_handoff_cannot_change_original_identity(hosts, monkeypatch, fault):
    h = hosts()
    e = practical(h, monkeypatch)
    receipt = deepcopy(e.act(0))
    if fault == "attempt": receipt["outcome"]["native_outcome"]["attempt_id"] = "a" * 64
    elif fault == "owner": receipt["outcome"]["native_outcome"]["native_blast_utility_plan"]["identity"]["episode_id"] = "other"
    elif fault == "allocation": receipt["outcome"]["native_outcome"]["metadata"]["policy"]["memory_bytes"] -= 1
    else: receipt["outcome"]["facts"]["requested_job"]["handoff"]["execution_id"] = str(h.tmp_path / "other-native.json")
    with pytest.raises(ValueError):
        reference = publish_practical(h.store, e, receipt, scope=h.scope)
        h.family.job_progress_provider.targets.read_target(reference, h.scope)
    assert len(e.starts) == 1 and e.wrapper_calls == []


def test_legacy_execution_descriptor_shape_is_unchanged(tmp_path):
    job = job_fixture(tmp_path, "extract_sequences")
    target = {"resource_kind": "local", "assignment": {"requested_job": {"native_blast_utility": job}}}
    assert describe_execution_target(target) == {"resource_kind": "local", "service_or_program": "blastdbcmd",
        "operation": "extract_sequences", "mode": "extract_sequences", "molecule": "dna",
        "selected_outputs": job["outputs"], "output_format": "native_blast_utility_bundle_v1"}


def test_legacy_complete_progress_descriptor_has_no_new_fields(tmp_path, monkeypatch):
    from gene_annotation_episode.execution_progress import ExecutionTargetReader
    e = old_environment(tmp_path, monkeypatch, mode="extract_sequences")
    started = e.act(0)
    with Store(tmp_path / "store") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
        reference = publish_practical(store, e, started, scope=scope)
        reader = ExecutionTargetReader(store, run_id=e.run, directory=tmp_path / "progress",
            resources={e.resource: e.configuration}, api_execution=None)
        target = reader.read_target(reference, scope)
        value = reader.describe_target(reference, scope, selector=old_selector())
        assert set(value) == {*describe_execution_target(target), "called_operation", "status_operations",
            "acquisition_operations", "extractors", "status_meanings"}
        assert value["extractors"][1] == {"operation": "execution.results.collect",
            "implementation": "gene_annotation_episode.native_blast_utility_results.NativeBLASTUtilityResults.execute",
            "scientific_annotation_score": False}
        with pytest.raises(ValueError):
            reader.describe_target(reference, scope, selector=selector())
