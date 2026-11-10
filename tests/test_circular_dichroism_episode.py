"""One ordinary CD calculation and literal delivery along a real investigation.

The question, supplied measurements, decisions and stopping controller are
engineering fixtures. The scientific binding, selected action, owned worker,
Source publication and typed return protocol are real. Biomni is never run.
"""
import asyncio
import builtins
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

from gene_annotation_episode import circular_dichroism_contracts as contracts
from gene_annotation_episode import circular_dichroism_measurements as core
from gene_annotation_episode import circular_dichroism_tools as adapter
from gene_annotation_episode import molecular_measurement_tools as ordinary
from gene_annotation_episode.communication import ReportBoundaryError, plain
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.materials import source_for_artifact
from gene_annotation_episode.runtime import TypedReportContract, Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries
from gene_annotation_episode.tools import ToolRegistry
from test_circular_dichroism_measurements import supplied
from test_liftover_tool import _files, _tables
from test_runtime import FixtureController


PUBLICATION = Path(__file__).resolve().parents[1] / "research/slotted_process_library/publications/2026-10-24-001"
QUESTION = ("For the supplied protein CD measurement File, what source-defined signed spectral point counts, "
    "thermal relative signals, sampled midpoint and N-point width are retained, and do explicitly selected "
    "saved views preserve the full original measurement populations and qualifications?")


def _forbidden(*args, **kwargs):
    raise AssertionError("CD saved delivery or closed replay attempted unselected work")


class _Decisions:
    """Only valid controlled decisions; no production continuation is replaced."""
    def __init__(self, script):
        self.script, self.contexts = iter(script), []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == "REASONING" and context.get("feedback") is None, context.get("feedback")
        self.contexts.append(deepcopy(context))
        selected = next(self.script)
        return selected(context) if callable(selected) else deepcopy(selected)

    async def release(self, episode_id):
        pass


def test_selected_cd_worker_saved_views_and_source_only_onward(tmp_path, monkeypatch):
    """One existing-core worker; one saved calculation; no original Biomni call."""
    from gene_annotation_episode import native_lifecycle, tool_grading_artifacts

    directory = tmp_path / "run"; directory.mkdir()
    original_import, original_open = builtins.__import__, Path.open
    def no_biomni(name, *args, **kwargs):
        assert name != "biomni" and not name.startswith("biomni."), "original Biomni was imported"
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_biomni)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", _forbidden)
    worker_calls, native_calls, authenticated, saved_calculations = [], [], [], []
    original, onward_values = {}, []
    allow_saved = [False]

    with Store(tmp_path / "store") as store:
        scope = dict(subject_refs=store.create_problem(raw_sequence="MPEPTIDE", molecule="protein")["subject_refs"])
        raw = json.dumps(supplied(), ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
        input_file = store.artifact(raw, "application/json")
        input_source = source_for_artifact(store, input_file)
        assert input_source["artifact_ref"] == input_file
        initial = [input_source["id"], input_file]
        assert store.reference_subset(initial, scope) == initial
        tools = ToolRegistry(store, job_limits=dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3))
        contract = tools.catalog()[contracts.CD_TOOL]
        assert contract["resources"] == "local"
        assert contract["input_schema"] == contracts.circular_dichroism_tool_argument_schema()
        descriptor = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=["scientific_process"])
        library = ScientificProcessLibrary(directory / "scientific-process-library")
        selected = dict(version="scientific_process_selection_v3", evidence_axis=library.reference("A101"),
            thought_pattern=library.reference("P01"),
            child_tool_info=[dict(name=contracts.CD_TOOL, resources="local")])
        for option in ("A101", "P01"):
            assert (directory / "scientific-process-library/entries" / (option + ".json")).read_bytes() == (
                PUBLICATION / "entries" / (option + ".json")).read_bytes()
        form = obj(dict(summaries=contracts.circular_dichroism_fact_sources()[contracts.FACT_SOURCE]["report_schema"]))

        def commission(question, selection, evidence):
            return dict(selection=dict(kind="episode_child", role="scientific_process", goal=question,
                scope=scope, purpose="Return the exact full-population CD summaries actually received for this question.",
                schema_json=json.dumps(form), initial_report_json="{}", assignment=dict(selection=selection,
                    evidence_refs=evidence, constraints=dict(original_biomni_execution=False),
                    context=dict(question=question))), report_update={})

        def action(arguments):
            return dict(selection=dict(kind="tool", tool=contracts.CD_TOOL, arguments=arguments), report_update={})

        calculate_args = dict(mode="calculate", input=dict(namespace="source", reference=input_source["id"]), view=None)
        read_view = dict(spectrum_ordinals=[2, 0, 2], thermal_ordinals=[4, 2, 2, 99], issue_ordinals=[99])
        saved_view = dict(spectrum_ordinals=[], thermal_ordinals=[0], issue_ordinals=[])
        prepare, worker = native_lifecycle.prepare_job, tools._sequence_worker_async
        authenticate, calculate = ordinary.authenticate_molecular_invocation, core.calculate_circular_dichroism_components

        def observe_prepare(command, **kwargs):
            payload = json.loads(Path(command[-2]).read_bytes())
            assert command[:3] == [sys.executable, "-m", "gene_annotation_episode.sequence_worker"]
            assert payload["operation"] == "circular_dichroism"
            assert kwargs["policy"].to_dict() == tools.local_job_policy.to_dict()
            assert Path(payload["arguments"]["input_path"]).read_bytes() == raw
            native_calls.append(deepcopy(payload))
            return prepare(command, **kwargs)

        async def observe_worker(operation, arguments, **kwargs):
            assert operation == "circular_dichroism" and kwargs["directory"] == kwargs["owned_directory"]
            result = await worker(operation, arguments, **kwargs)
            worker_calls.append(dict(output=str(result.output_path), metadata=deepcopy(result.metadata),
                handle=json.loads((result.output_path.parent / "native-handle.json").read_bytes())))
            return result

        def observe_authentication(registry, name, arguments, current_scope, key):
            result = authenticate(registry, name, arguments, current_scope, key)
            context, reader = result
            assert context.role == "scientific_process" and callable(reader) and plain(context.scope) == current_scope == scope
            authenticated.append(dict(episode_id=context.episode_id, mode=arguments["mode"], operation_key=key))
            return result

        def saved_calculation(sheet):
            assert allow_saved[0], "read_stored or frozen delivery calculated CD values"
            allow_saved[0] = False
            saved_calculations.append(deepcopy(sheet))
            return calculate(sheet)

        monkeypatch.setattr(native_lifecycle, "prepare_job", observe_prepare)
        monkeypatch.setattr(tools, "_sequence_worker_async", observe_worker)
        monkeypatch.setattr(ordinary, "authenticate_molecular_invocation", observe_authentication)
        monkeypatch.setattr(core, "calculate_circular_dichroism_components", saved_calculation)
        original_get_artifact = store.get_artifact

        def after_calculate(context):
            assert context["goal"]["objective"] == QUESTION
            assert context["scientific_process"]["selection"] == selected
            information, = context["scientific_process"]["child_tool_info"]
            assert set(information) == {"name", "description", "resources", "instructions"}
            assert information["name"] == contracts.CD_TOOL and information["resources"] == "local"
            assert information["description"] == contract["description"]
            assert len(worker_calls) == len(native_calls) == 1 and saved_calculations == []
            assert worker_calls[0]["metadata"]["native_returncode"] == 0
            assert worker_calls[0]["metadata"]["verified_cgroup"]["memory_max"] == 20 * 1024**3
            assert worker_calls[0]["metadata"]["verified_cgroup"]["memory_swap_max"] == 0
            assert worker_calls[0]["metadata"]["policy"] == tools.local_job_policy.to_dict()
            outcome = context["last_local_outcome"]
            assert outcome["status"] == "completed" and outcome["feedback"] is None
            projection = outcome["result"]; source = store.get(projection["source_ref"])
            stored = json.loads(store.get_artifact(source["artifact_ref"]))
            control = json.loads(store.get_artifact(source["request_ref"]))
            grading, = source_tool_grading_entries(store, source["id"])
            assert canonical(grading["grading"]) == canonical(dict(sheet=stored["sheet"], scores=stored["components"]))
            assert stored["version"] == contracts.RESULT_VERSION
            assert stored["request"]["input_file"] == control["request"]["received_input"]["file"]
            assert stored["request"]["input_file"] == dict(artifact_ref=input_file,
                sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), format="json")
            assert control["version"] == "ordinary_cd_publication_v1"
            assert set(control["request"]) == {"version", "arguments", "invocation", "received_input", "request"}
            assert control["request"]["version"] == "ordinary_cd_request_v1"
            assert control["request"]["arguments"] == calculate_args
            assert control["request"]["invocation"]["operation_key"] == authenticated[0]["operation_key"]
            assert control["native_artifact_ref"] == source["artifact_ref"]
            assert control["native_handle"] == worker_calls[0]["handle"]
            assert source["parent_source_refs"] == [input_source["id"]] and "operand_refs" not in source
            assert stored["sheet"]["source_method"]["native_execution"] is False
            assert [row["count"]["value"] for row in stored["components"]["spectrum"]["features"]] == [3, 2, 1]
            thermal = stored["components"]["thermal"]
            assert [row["relative_signal"]["value"] for row in thermal["relative_signal"]] == [0., .2, .5, .8, 1.]
            cells = {row["name"]: row for row in thermal["summary"]}
            assert cells["sampled_midpoint_index"]["value"] == 2
            assert cells["sampled_midpoint_temperature"]["value"] == 40.
            assert cells["source_transition_width"]["value"] == 8.
            expected = contracts.project_circular_dichroism_return(stored, source_ref=source["id"])
            assert canonical(projection) == canonical(expected)
            assert outcome["record_refs"] == outcome["changed_record_refs"] == [source["id"]]
            original.update(source=source, stored=stored, grading_ref=grading["artifact_ref"], summary=expected,
                producer_episode_id=authenticated[0]["episode_id"], invocation=control["request"]["invocation"])
            copied = Path(native_calls[0]["arguments"]["input_path"]).resolve()
            original_path = (store.path / "artifacts" / input_file[9:11] / input_file[9:]).resolve()
            def no_input_open(path, *args, **kwargs):
                assert Path(path).resolve() not in {copied, original_path}, "saved mode reopened the original input File"
                return original_open(path, *args, **kwargs)
            def no_input_artifact(reference):
                assert reference != input_file, "saved mode read the original input artifact"
                return original_get_artifact(reference)
            monkeypatch.setattr(Path, "open", no_input_open)
            monkeypatch.setattr(store, "get_artifact", no_input_artifact)
            monkeypatch.setattr(tools, "_sequence_worker_async", _forbidden)
            monkeypatch.setattr(ordinary, "run_owned_molecular_worker", _forbidden)
            monkeypatch.setattr(adapter, "run_circular_dichroism_tool_request", _forbidden)
            return action(dict(mode="read_stored", result_ref=source["id"], view=read_view))

        def after_read(context):
            outcome = context["last_local_outcome"]
            assert outcome["status"] == "completed" and outcome["record_refs"] == [original["source"]["id"]]
            view = outcome["result"]
            assert view["selection"] == read_view and canonical(view["summary"]) == canonical(original["summary"])
            assert [row["ordinal"] for row in view["spectrum_rows"]] == [2, 0, 2]
            assert [row["ordinal"] for row in view["thermal_rows"]] == [4, 2, 2, 99]
            assert view["thermal_rows"][-1]["availability"] == "out_of_range"
            assert saved_calculations == [] and len(worker_calls) == len(native_calls) == 1
            allow_saved[0] = True
            return action(dict(mode="calculate_saved", result_ref=original["source"]["id"], view=saved_view))

        def onward(context):
            parent = workflow.binding_context(root.source)
            values = workflow.services.molecular_received_facts(parent, fact_source=contracts.FACT_SOURCE)
            assert canonical(values) == canonical([original["summary"]])
            assert len(saved_calculations) == 1 and not allow_saved[0]
            onward_values.append(deepcopy(values))
            for name in ("calculate_circular_dichroism_components", "populate_circular_dichroism_sheet", "validate_circular_dichroism_sheet"):
                monkeypatch.setattr(core, name, _forbidden)
            monkeypatch.setattr(ordinary, "read_retained_molecular_publication", _forbidden)
            monkeypatch.setattr(contracts, "project_circular_dichroism_return", _forbidden)
            following = deepcopy(selected)
            following["child_tool_info"] = [dict(name="state.query", resources="local")]
            return commission("Which full original CD summary and qualifications were received from the preceding investigation?",
                following, [original["source"]["id"]])

        def inspect(context):
            row = store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? "
                "AND json_extract(path,'$[1][1]')='child_1'", (workflow.run_id,)).fetchone()
            current = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_cd_").context(row[0])
            values = workflow.services.molecular_received_facts(current, fact_source=contracts.FACT_SOURCE)
            assert canonical(values) == canonical([original["summary"]])
            assert workflow.services.molecular_own_facts(current, fact_source=contracts.FACT_SOURCE) == []
            onward_values.append(deepcopy(values))
            return dict(selection=dict(kind="tool", tool="state.query", arguments=dict(refs=[original["source"]["id"]])), report_update={})

        provider = _Decisions([commission(QUESTION, selected, initial), action(calculate_args), after_calculate, after_read, onward, inspect])
        def make_workflow():
            return Workflow(store, tools, provider, directory, "ordinary-cd-workflow-fixture",
                lambda path, initial: FixtureController(str(path), initial,
                    2 if len(path) == 1 else 3 if path[-1][1] == "child_0" else 1),
                lambda store, scope, **kwargs: 0, project_child_credit=lambda store, scope, **kwargs: 0,
                episode_binding_descriptors=[descriptor], episode_record_receipts=True, initial_known_record_refs=initial)
        def make_root(owner):
            report = TypedReportContract("Return exactly the complete original CD summary groups actually received.", form,
                lambda reference, namespace: owner.resolver(scope, source=value.source)(reference, namespace),
                semantic_validator=lambda result: owner.validate_report(result, scope, grain="annotation", schema=form, source=value.source))
            value = owner.build("annotation", "root", QUESTION, scope, contract=report)
            return value
        workflow = make_workflow(); root = make_root(workflow)
        record = asyncio.run(root.run_async(workflow.context)); asyncio.run(root.build_result(record))
        monkeypatch.setattr(Path, "open", original_open)
        monkeypatch.setattr(store, "get_artifact", original_get_artifact)
        assert len(provider.contexts) == 6 and len(native_calls) == len(worker_calls) == len(saved_calculations) == 1
        assert onward_values == [[original["summary"]], [original["summary"]]]
        episodes = [dict(row) for row in store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=?", (workflow.run_id,))]
        assert len(episodes) == 3
        contexts = [EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_cd_").context(row["episode_id"]) for row in episodes]
        parent = workflow.binding_context(root.source)
        expected_counts = {parent.episode_id: 2, original["producer_episode_id"]: 3}
        following, = [current for current in contexts if current.role == "scientific_process" and current.episode_id != original["producer_episode_id"]]
        expected_counts[following.episode_id] = 1
        for current in contexts:
            for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
                assert store.db.execute("SELECT COUNT(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                    (workflow.run_id, current.episode_id)).fetchone()[0] == expected_counts[current.episode_id]
            returned = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (workflow.run_id, current.episode_id)).fetchone()[0])
            assert canonical(returned["summaries"]) == canonical([original["summary"]])
            known = set(workflow.receipts.known(current.episode_id))
            assert {input_file, input_source["id"], original["source"]["id"]} <= known
            for reference in (original["source"]["artifact_ref"], original["source"]["request_ref"], original["grading_ref"]):
                assert reference not in known
                assert workflow.resolver(scope, context=current)(reference, "artifact") is False
                assert workflow.services.reference_in_context(current, reference, "artifact") is False
        actions = [dict(row) for row in store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index",
            (workflow.run_id, original["producer_episode_id"]))]
        outcomes = [json.loads(row["result"]) for row in actions]
        assert [row["mode"] for row in authenticated] == ["calculate", "read_stored", "calculate_saved"]
        assert all(row["episode_id"] == original["producer_episode_id"] for row in authenticated)
        assert [row["status"] for row in outcomes] == ["completed"] * 3
        assert all(row["record_refs"] == [original["source"]["id"]] for row in outcomes)
        assert all(row["changed_record_refs"] == [] for row in outcomes[1:])
        assert outcomes[-1]["result"]["selection"] == saved_view
        assert outcomes[-1]["result"]["spectrum_rows"] == []
        assert canonical(outcomes[-1]["result"]["summary"]) == canonical(original["summary"])
        for row, auth in zip(actions, authenticated):
            operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (auth["operation_key"],)).fetchone()
            selected_action, recorded = json.loads(row["action"]), json.loads(row["result"])
            assert operation["name"] == contracts.CD_TOOL and operation["arguments"] == canonical(selected_action["arguments"])
            assert operation["scope"] == canonical(scope) and operation["id"] == recorded["operation_ref"]
            assert operation["result"] == canonical({key: value for key, value in recorded.items() if key != "pending_work_after_action"})
        assert original_get_artifact(input_file) == raw
        original_form = dict(summaries=[original["summary"]]); before = _tables(store)
        negative_run_files, negative_artifacts = _files(directory), _files(store.path / "artifacts")
        for fault in ("value", "valid_numeric_change", "unit", "bool_ordinal", "source"):
            changed = deepcopy(original_form); summary = changed["summaries"][0]
            if fault == "value": summary["spectrum"]["features"][0]["count"]["value"] = 999
            elif fault == "valid_numeric_change":
                summary["spectrum"]["features"][0]["count"].update(value=2, numerator=2)
                assert contracts.validate_circular_dichroism_return(summary) == summary
            elif fault == "unit": summary["thermal"]["summary"][0]["unit"] = "delta_epsilon"
            elif fault == "bool_ordinal":
                next(row for row in summary["thermal"]["summary"] if row["name"] == "sampled_midpoint_index")["value"] = True
            else: summary["source_ref"] = input_source["id"]
            with pytest.raises(ReportBoundaryError) as rejected:
                workflow.validate_report(changed, scope, grain="annotation", schema=form, source=root.source)
            if fault == "valid_numeric_change":
                assert rejected.value.diagnostic["code"] == "circular_dichroism_frozen_source_mismatch"
            assert _tables(store) == before
            assert _files(directory) == negative_run_files and _files(store.path / "artifacts") == negative_artifacts
        assert store.count("annotation") == store.count("observation") == 0
        before, run_files, artifact_files = _tables(store), _files(directory), _files(store.path / "artifacts")
        monkeypatch.setattr(store, "get_artifact", _forbidden)
        monkeypatch.setattr(provider, "complete", _forbidden)
        monkeypatch.setattr(ordinary, "retain_molecular_publication", _forbidden)
        monkeypatch.setattr(tool_grading_artifacts, "retain_tool_grading", _forbidden)
        for name in ("prepare_job", "resume_start", "collect", "wait_job"):
            monkeypatch.setattr(native_lifecycle, name, _forbidden)
        restored = make_workflow(); replay = make_root(restored)
        replay_record = asyncio.run(replay.run_async(restored.context)); asyncio.run(replay.build_result(replay_record))
        assert _tables(store) == before and _files(directory) == run_files and _files(store.path / "artifacts") == artifact_files
        assert len(native_calls) == len(worker_calls) == len(saved_calculations) == 1
        assert canonical(restored.services.molecular_received_facts(restored.binding_context(replay.source),
            fact_source=contracts.FACT_SOURCE)) == canonical([original["summary"]])
        (tmp_path / "CD_EPISODE.json").write_text(json.dumps(dict(version="cd_episode_verification_v1", question=QUESTION,
            qualification="Engineering question, supplied measurements, decisions and controller; one actual existing-core worker, no Biomni or live API.",
            run_id=workflow.run_id, producing_episode_id=original["producer_episode_id"], scope=scope,
            input_file=input_file, input_source_ref=input_source["id"], input_sha256=hashlib.sha256(raw).hexdigest(),
            source=original["source"], stored=original["stored"], grading_ref=original["grading_ref"], summary=original["summary"],
            native_handles=[row["handle"] for row in worker_calls], native_worker_count=len(native_calls),
            saved_public_calculator_count=len(saved_calculations), actions=[json.loads(row["action"]) for row in actions],
            outcomes=outcomes, episode_action_observation_model_counts=expected_counts,
            onward_groups=onward_values, store_directory=str(store.path), run_directory=str(directory),
            closed_replay_rows_and_files_unchanged=True), allow_nan=False, indent=2) + "\n")


def _cd_retained_pins(directory):
    return dict(database=hashlib.sha256((directory / "store/state.sqlite3").read_bytes()).hexdigest(),
        artifacts=_files(directory / "store/artifacts"), run=_files(directory / "run"))


def _cd_scientific_run_files(directory):
    return {name: digest for name, digest in _files(directory).items()
        if name.split("/", 1)[0] not in {"tool-knowledge", "launch-instructions"}}


def _clone_retained_cd(tmp_path, *, environment_name="HMMER_NATIVE_ORACLE_CD_RETAINED",
        expected_database_sha256="08a50c612ea08e9ca95650a4f27b35bd8f48d4e80bba363486ab188bcdffaebb",
        clone_name="retained-cd319"):
    import os
    import shutil

    selected = os.environ.get(environment_name)
    assert selected, "the authentic closed CD Store/run fixture must be explicitly selected"
    original = Path(selected).resolve()
    for suffix in ("-wal", "-shm"):
        path = original / ("store/state.sqlite3" + suffix)
        assert not path.exists() or path.stat().st_size == 0, "the selected database must be quiescent"
    pins = _cd_retained_pins(original)
    assert pins["database"] == expected_database_sha256
    directory = tmp_path / clone_name
    (directory / "store").mkdir(parents=True)
    shutil.copyfile(original / "store/state.sqlite3", directory / "store/state.sqlite3")
    shutil.copytree(original / "store/artifacts", directory / "store/artifacts")
    # Canonical instruction sources regenerate operational guides. The two
    # original indexes remain metadata witnesses, never index-only libraries.
    shutil.copytree(original / "run", directory / "run",
        ignore=lambda path, names: {"tool-knowledge", "launch-instructions"}
            if Path(path) == original / "run" else set())
    for path in (directory, *directory.rglob("*")):
        path.chmod(0o755 if path.is_dir() else 0o644)
    assert _cd_retained_pins(original) == pins
    return original, directory, pins


def test_retained_cd_structured_forgeries_and_original_closed_replay(tmp_path, monkeypatch):
    """Post-failure319 proof, reusing its one worker and one saved calculation.

    The original test remains failed. This selector only authenticates saved
    output once, checks frozen forms/permissions and replays the closed tree.
    Metadata sheet validation is allowed only during that first saved read;
    no spectrum/thermal calculation, input reopen or new publication is allowed.
    Regenerated operational guides are distinct from immutable scientific history.
    """
    from gene_annotation_episode import native_lifecycle, tool_grading_artifacts
    from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
    from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary

    original, directory, original_pins = _clone_retained_cd(tmp_path)
    run, run_id = directory / "run", "ordinary-cd-workflow-fixture"
    source_ref = "source_25fdc85cfda3c3ed00394cc3"
    producer_id = "episode_98a3895192eb273f1e79e9c744e12a0042f88da2455d8b4fd9c2f93b3da0d409"
    original_import, original_open = builtins.__import__, Path.open

    def no_biomni(name, *args, **kwargs):
        assert name != "biomni" and not name.startswith("biomni."), "original Biomni was imported"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_biomni)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", _forbidden)
    for name in ("_spectrum", "_thermal", "calculate_circular_dichroism_components"):
        monkeypatch.setattr(core, name, _forbidden)
    monkeypatch.setattr(adapter, "run_circular_dichroism_tool_request", _forbidden)
    monkeypatch.setattr(ordinary, "run_owned_molecular_worker", _forbidden)
    monkeypatch.setattr(ordinary, "retain_molecular_publication", _forbidden)
    monkeypatch.setattr(tool_grading_artifacts, "retain_tool_grading", _forbidden)
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
    for name in ("prepare_job", "resume_start", "collect", "wait_job"):
        monkeypatch.setattr(native_lifecycle, name, _forbidden)

    with Store(directory / "store") as store:
        episodes = [dict(row) for row in store.db.execute(
            "SELECT * FROM runtime_episodes WHERE run_id=?", (run_id,))]
        assert len(episodes) == 3 and all(row["state"] == "yielded" for row in episodes)
        requests = {row["episode_id"]: json.loads(row["request"]) for row in episodes}
        root_row, = [row for row in episodes if len(json.loads(row["path"])) == 1]
        root_request, producer_request = requests[root_row["episode_id"]], requests[producer_id]
        scope = root_request["message"]["scope"]
        assert root_request["goal"]["objective"] == QUESTION
        initial = producer_request["message"]["episode_assignment"]["evidence_refs"]
        input_source, input_file = initial
        assert input_source == "source_f20a15f66ffc33c664d0177c"
        assert input_file == "artifact_90b42568fcf3d64a2d0b031e64bb36fa5abe810fa4581ff5a72e273e7e701e2b"
        source = store.get(source_ref)
        private = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
        assert len(private) == 3
        old_binding = producer_request["message"]["scientific_process"]["mechanics_binding"]
        descriptor = ScientificProcessEpisodes(None,
            library=ScientificProcessLibrary(run / "scientific-process-library"),
            tool_library=ScientificToolLibrary(run / "scientific-tool-library"),
            child_roles=["scientific_process"]).as_record()
        assert {**old_binding, "implementation_sha256": descriptor["implementation_sha256"]} == descriptor
        assert old_binding["implementation_sha256"] == "fe89110a6964fa0644919f1fcb78bfa098d01eef1181703f55f70c5d19215183"
        assert descriptor["implementation_sha256"] != old_binding["implementation_sha256"]
        tools = ToolRegistry(store, job_limits=dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3))
        provider = _Decisions([])
        monkeypatch.setattr(provider, "complete", _forbidden)

        def make_workflow():
            return Workflow(store, tools, provider, run, run_id,
                lambda path, initial: FixtureController(str(path), initial,
                    2 if len(path) == 1 else 3 if path[-1][1] == "child_0" else 1),
                lambda store, scope, **kwargs: 0, project_child_credit=lambda store, scope, **kwargs: 0,
                episode_binding_descriptors=[descriptor], episode_record_receipts=True,
                initial_known_record_refs=initial)

        form = root_request["report_contract"]["measurements"]["schema"]
        assert canonical(form) == canonical(obj(dict(summaries=
            contracts.circular_dichroism_fact_sources()[contracts.FACT_SOURCE]["report_schema"])))

        def make_root(owner):
            report = TypedReportContract(root_request["report_contract"]["decision"], form,
                lambda reference, namespace: owner.resolver(scope, source=value.source)(reference, namespace),
                semantic_validator=lambda result: owner.validate_report(result, scope, grain="annotation",
                    schema=form, source=value.source))
            value = owner.build("annotation", "root", QUESTION, scope, contract=report)
            return value

        # Capture all SQL row values before constructor/build, including saved
        # mechanics identities; only operational guide files may be generated.
        before, artifacts = _tables(store), _files(store.path / "artifacts")
        scientific_files = _cd_scientific_run_files(run)
        workflow = make_workflow(); root = make_root(workflow)
        assert _tables(store) == before and _files(store.path / "artifacts") == artifacts
        assert _cd_scientific_run_files(run) == scientific_files
        guides = {}
        for name in ("tool-knowledge", "launch-instructions"):
            retained_index = original / "run" / name / "index.json"
            assert (run / name / "index.json").read_bytes() == retained_index.read_bytes()
            manifest = json.loads(retained_index.read_bytes())
            for entry in manifest["entries"]:
                for section in entry["sections"]:
                    raw = (run / name / section["path"]).read_bytes()
                    assert hashlib.sha256(raw).hexdigest() == section["sha256"]
                    assert len(raw) == section["bytes"]
            guides[name] = _files(run / name)

        contexts = {row["episode_id"]: EpisodeReturnRecords(store, run_id,
            failure_prefix="test_cd_retained_").context(row["episode_id"]) for row in episodes}
        producer = contexts[producer_id]
        getter = store.get_artifact
        input_path = (store.path / "artifacts" / input_file[9:11] / input_file[9:]).resolve()
        integrity_read = [False]

        def no_input_open(path, *args, **kwargs):
            assert integrity_read[0] or Path(path).resolve() != input_path, "retained delivery reopened the CD input"
            return original_open(path, *args, **kwargs)

        def no_input_bytes(reference):
            assert reference != input_file, "retained delivery read the original input artifact"
            return getter(reference)

        def audit_files(path):
            integrity_read[0] = True
            try:
                return _files(path)
            finally:
                integrity_read[0] = False

        monkeypatch.setattr(Path, "open", no_input_open)
        monkeypatch.setattr(store, "get_artifact", no_input_bytes)
        saved = ordinary.read_retained_molecular_publication(tools, producer,
            workflow.services.read_received_molecular_input, source_ref, tool_name=contracts.CD_TOOL)
        assert saved["admission_kind"] == "source_only" and saved["source"] == source
        stored, control = saved["stored"], saved["control"]
        assert set(stored) == {"version", "request", "sheet", "components"}
        assert stored["version"] == contracts.RESULT_VERSION
        assert control["native_artifact_ref"] == source["artifact_ref"]
        assert control["request"]["received_input"]["file"]["artifact_ref"] == input_file
        invocation = control["request"]["invocation"]
        assert invocation["episode_id"] == producer_id and invocation["run_id"] == run_id
        assert invocation["decision_index"] == 0
        assert invocation["operation_key"] == f"{run_id}:{producer_id}:0"
        assert saved["grading_ref"] in private
        expected = contracts.project_circular_dichroism_return(stored, source_ref=source_ref)
        assert [row["count"]["value"] for row in expected["spectrum"]["features"]] == [3, 2, 1]
        thermal = stored["components"]["thermal"]
        assert [row["relative_signal"]["value"] for row in thermal["relative_signal"]] == [0., .2, .5, .8, 1.]
        cells = {row["name"]: row for row in expected["thermal"]["summary"]}
        assert cells["sampled_midpoint_index"]["value"] == 2
        assert cells["sampled_midpoint_temperature"]["value"] == 40.
        assert cells["source_transition_width"]["value"] == 8.
        assert stored["sheet"]["source_method"]["native_execution"] is False
        assert _tables(store) == before

        # All subsequent authority comes from admitted frozen forms and receipt
        # prefixes, with no native/control/grading or original-input body reads.
        private_paths = {(store.path / "artifacts" / ref[9:11] / ref[9:]).resolve() for ref in private}
        def no_scientific_payload_open(path, *args, **kwargs):
            assert integrity_read[0] or Path(path).resolve() not in private_paths | {input_path}
            return original_open(path, *args, **kwargs)
        monkeypatch.setattr(Path, "open", no_scientific_payload_open)
        monkeypatch.setattr(store, "get_artifact", _forbidden)
        monkeypatch.setattr(ordinary, "read_retained_molecular_publication", _forbidden)
        monkeypatch.setattr(contracts, "project_circular_dichroism_return", _forbidden)
        for name in ("populate_circular_dichroism_sheet", "validate_circular_dichroism_sheet"):
            monkeypatch.setattr(core, name, _forbidden)
        expected_counts = {row["episode_id"]: 2 if len(json.loads(row["path"])) == 1 else
            3 if row["episode_id"] == producer_id else 1 for row in episodes}
        for current in contexts.values():
            assert canonical(workflow.services.molecular_frozen_facts(current,
                fact_source=contracts.FACT_SOURCE)) == canonical([expected])
            received = workflow.services.molecular_received_facts(current, fact_source=contracts.FACT_SOURCE)
            assert canonical(received) == canonical([] if current.episode_id == producer_id else [expected])
            returned = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (run_id, current.episode_id)).fetchone()[0])
            assert canonical(returned) == canonical(dict(summaries=[expected]))
            known = set(workflow.receipts.known(current.episode_id))
            assert {input_file, input_source, source_ref} <= known and not private.intersection(known)
            assert workflow.resolver(scope, context=current)(source_ref, "source") is True
            for reference in private:
                assert workflow.resolver(scope, context=current)(reference, "artifact") is False
                assert workflow.services.reference_in_context(current, reference, "artifact") is False
            for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
                assert store.db.execute("SELECT COUNT(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                    (run_id, current.episode_id)).fetchone()[0] == expected_counts[current.episode_id]
        assert store.db.execute("SELECT COUNT(*) FROM tool_operations").fetchone()[0] == 4
        actions = list(store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "ORDER BY decision_index", (run_id, producer_id)))
        assert [json.loads(row["action"])["arguments"]["mode"] for row in actions] == ["calculate", "read_stored", "calculate_saved"]
        assert all(json.loads(row["result"])["status"] == "completed" for row in actions)
        assert all(json.loads(row["result"])["record_refs"] == [source_ref] for row in actions)
        parent_form = dict(summaries=[expected])
        negative_files, negative_artifacts = audit_files(run), audit_files(store.path / "artifacts")
        diagnostics = {}
        for fault in ("value", "valid_numeric_change", "unit", "bool_ordinal", "source"):
            changed = deepcopy(parent_form); summary = changed["summaries"][0]
            if fault == "value": summary["spectrum"]["features"][0]["count"]["value"] = 999
            elif fault == "valid_numeric_change":
                summary["spectrum"]["features"][0]["count"].update(value=2, numerator=2)
                assert contracts.validate_circular_dichroism_return(summary) == summary
            elif fault == "unit": summary["thermal"]["summary"][0]["unit"] = "delta_epsilon"
            elif fault == "bool_ordinal":
                next(row for row in summary["thermal"]["summary"] if row["name"] == "sampled_midpoint_index")["value"] = True
            else: summary["source_ref"] = input_source
            with pytest.raises(ReportBoundaryError) as rejected:
                workflow.validate_report(changed, scope, grain="annotation", schema=form, source=root.source)
            diagnostics[fault] = plain(rejected.value.diagnostic)
            if fault == "valid_numeric_change":
                assert diagnostics[fault]["code"] == "circular_dichroism_frozen_source_mismatch"
            assert _tables(store) == before
            assert audit_files(run) == negative_files and audit_files(store.path / "artifacts") == negative_artifacts

        restored = make_workflow(); replay = make_root(restored)
        replay_record = asyncio.run(replay.run_async(restored.context)); asyncio.run(replay.build_result(replay_record))
        assert _tables(store) == before
        assert audit_files(run) == negative_files and audit_files(store.path / "artifacts") == negative_artifacts
        assert _cd_scientific_run_files(run) == scientific_files
        assert provider.contexts == []
        assert canonical(restored.services.molecular_received_facts(restored.binding_context(replay.source),
            fact_source=contracts.FACT_SOURCE)) == canonical([expected])
        integrity_read[0] = True
        try:
            assert _cd_retained_pins(original) == original_pins
        finally:
            integrity_read[0] = False
        (tmp_path / "CD_RETAINED_REPLAY.json").write_text(json.dumps(dict(
            version="cd_retained_replay_verification_v1", qualification=
                "Original319 failed late; this retained-only case performs no worker, calculation or publication.",
            original_input_pins=original_pins, source_ref=source_ref, summary=expected,
            preserved_saved_binding=old_binding, current_binding=descriptor,
            episode_action_observation_model_counts=expected_counts, forgery_diagnostics=diagnostics,
            regenerated_operational_guides=guides, full_sql_rows_and_scientific_files_unchanged=True,
            closed_replay_payload_reads_forbidden=True), allow_nan=False, indent=2) + "\n")


def test_selected_cd_partial_spectrum_preserves_thermal_and_saved_view(tmp_path, monkeypatch):
    """One distinct partial input; one worker, literal saved view, no Biomni."""
    from gene_annotation_episode import native_lifecycle, tool_grading_artifacts

    question = ("For this supplied protein CD File with seven wavelengths and six spectral signals, "
        "which spectral measurements are unavailable because the arrays do not pair, and which "
        "thermal relative signals, sampled midpoint and N-point width remain available?")
    measurements = supplied()
    measurements["spectrum"]["cd_signal_data"].pop()
    assert len(measurements["spectrum"]["wavelength_data"]) == 7
    assert len(measurements["spectrum"]["cd_signal_data"]) == 6
    assert measurements["thermal"] == supplied()["thermal"]
    raw = json.dumps(measurements, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()
    directory = tmp_path / "run"; directory.mkdir()
    original_import, original_open = builtins.__import__, Path.open

    def no_biomni(name, *args, **kwargs):
        assert name != "biomni" and not name.startswith("biomni."), "original Biomni was imported"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_biomni)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", _forbidden)
    # The selected worker is a separate process. No parent-side saved or
    # report-delivery path may perform either numerical branch or calculator.
    for name in ("_spectrum", "_thermal", "calculate_circular_dichroism_components"):
        monkeypatch.setattr(core, name, _forbidden)
    workers, launches, original, feedback_seen = [], [], {}, []

    class PartialDecisions(_Decisions):
        async def complete(self, episode_id, role, instructions, context, output_schema):
            assert role == "REASONING" and context.get("feedback") is None
            outcome = context.get("last_local_outcome")
            if outcome is not None:
                assert outcome["status"] == "partial"
                feedback = outcome["feedback"]
                expected = dict(category="numerical_input", code="circular_dichroism_partial_measurements",
                    source_ref=outcome["result"]["source_ref"])
                assert feedback == outcome["feedback"] == expected
                feedback_seen.append(deepcopy(feedback))
            self.contexts.append(deepcopy(context))
            selected_action = next(self.script)
            return selected_action(context) if callable(selected_action) else deepcopy(selected_action)

    with Store(tmp_path / "store") as store:
        scope = dict(subject_refs=store.create_problem(raw_sequence="MPEPTIDE", molecule="protein")["subject_refs"])
        input_file = store.artifact(raw, "application/json")
        input_source = source_for_artifact(store, input_file)
        initial = [input_source["id"], input_file]
        tools = ToolRegistry(store, job_limits=dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3))
        descriptor = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=["scientific_process"])
        library = ScientificProcessLibrary(directory / "scientific-process-library")
        selected = dict(version="scientific_process_selection_v3", evidence_axis=library.reference("A101"),
            thought_pattern=library.reference("P01"),
            child_tool_info=[dict(name=contracts.CD_TOOL, resources="local")])
        for option in ("A101", "P01"):
            assert (directory / "scientific-process-library/entries" / (option + ".json")).read_bytes() == (
                PUBLICATION / "entries" / (option + ".json")).read_bytes()
        form = obj(dict(summaries=contracts.circular_dichroism_fact_sources()[contracts.FACT_SOURCE]["report_schema"]))
        calculate_args = dict(mode="calculate", input=dict(namespace="source", reference=input_source["id"]), view=None)
        view = dict(spectrum_ordinals=[6, 6, 99], thermal_ordinals=[0, 2, 0, 99], issue_ordinals=[0, 0, 99])
        prepare, worker, getter = native_lifecycle.prepare_job, tools._sequence_worker_async, store.get_artifact

        def observe_prepare(command, **kwargs):
            payload = json.loads(Path(command[-2]).read_bytes())
            assert command[:3] == [sys.executable, "-m", "gene_annotation_episode.sequence_worker"]
            assert payload["operation"] == "circular_dichroism"
            assert kwargs["policy"].to_dict() == tools.local_job_policy.to_dict()
            assert Path(payload["arguments"]["input_path"]).read_bytes() == raw
            launches.append(deepcopy(payload))
            return prepare(command, **kwargs)

        async def observe_worker(operation, arguments, **kwargs):
            assert operation == "circular_dichroism" and kwargs["directory"] == kwargs["owned_directory"]
            result = await worker(operation, arguments, **kwargs)
            workers.append(dict(output=str(result.output_path), metadata=deepcopy(result.metadata),
                handle=json.loads((result.output_path.parent / "native-handle.json").read_bytes())))
            return result

        monkeypatch.setattr(native_lifecycle, "prepare_job", observe_prepare)
        monkeypatch.setattr(tools, "_sequence_worker_async", observe_worker)

        def tool_action(arguments):
            return dict(selection=dict(kind="tool", tool=contracts.CD_TOOL, arguments=arguments), report_update={})

        def after_partial(context):
            assert context["goal"]["objective"] == question
            assert context["scientific_process"]["selection"] == selected
            assert len(workers) == len(launches) == 1
            assert workers[0]["metadata"]["native_returncode"] == 0
            assert workers[0]["metadata"]["verified_cgroup"]["memory_max"] == 20 * 1024**3
            assert workers[0]["metadata"]["verified_cgroup"]["memory_swap_max"] == 0
            assert workers[0]["metadata"]["policy"] == tools.local_job_policy.to_dict()
            outcome = context["last_local_outcome"]
            assert outcome["status"] == "partial"
            source = store.get(outcome["result"]["source_ref"])
            stored = json.loads(getter(source["artifact_ref"]))
            control = json.loads(getter(source["request_ref"]))
            grading, = source_tool_grading_entries(store, source["id"])
            assert canonical(grading["grading"]) == canonical(dict(sheet=stored["sheet"], scores=stored["components"]))
            assert stored["version"] == contracts.RESULT_VERSION
            assert stored["request"]["input_file"] == control["request"]["received_input"]["file"] == dict(
                artifact_ref=input_file, sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw), format="json")
            assert control["version"] == "ordinary_cd_publication_v1"
            assert control["native_artifact_ref"] == source["artifact_ref"]
            assert control["native_handle"] == workers[0]["handle"]
            assert control["request"]["version"] == "ordinary_cd_request_v1"
            assert control["request"]["arguments"] == calculate_args
            assert source["parent_source_refs"] == [input_source["id"]] and "operand_refs" not in source
            invocation = control["request"]["invocation"]
            assert invocation["run_id"] == workflow.run_id and invocation["decision_index"] == 0
            assert invocation["scope"] == scope
            assert invocation["operation_key"] == f'{workflow.run_id}:{invocation["episode_id"]}:0'
            assert stored["sheet"]["source_method"]["native_execution"] is False
            assert stored["sheet"]["measurements"]["spectrum"]["state"] == "invalid_input"
            assert stored["components"]["spectrum"] == dict(state="invalid_input", features=[], source_structure_label=None)
            assert stored["components"]["issues"] == [dict(code="paired_length_mismatch", field="/spectrum")]
            thermal = stored["components"]["thermal"]
            assert thermal["state"] == "present"
            assert [row["relative_signal"]["value"] for row in thermal["relative_signal"]] == [0., .2, .5, .8, 1.]
            cells = {row["name"]: row for row in thermal["summary"]}
            assert cells["sampled_midpoint_temperature"]["value"] == 40.
            assert cells["source_transition_width"]["value"] == 8.
            summary = contracts.project_circular_dichroism_return(stored, source_ref=source["id"])
            assert canonical(outcome["result"]) == canonical(summary)
            assert summary["spectrum"]["features"] == [] and summary["spectrum"]["source_structure_label"] is None
            assert summary["spectrum"]["wavelength_count"] == 7 and summary["spectrum"]["signal_count"] == 6
            assert summary["issue_codes"] == ["paired_length_mismatch"]
            assert outcome["record_refs"] == outcome["changed_record_refs"] == [source["id"]]
            original.update(source=source, stored=stored, control=control, grading_ref=grading["artifact_ref"],
                summary=summary, invocation=invocation, first_outcome=deepcopy(outcome))
            copied = Path(launches[0]["arguments"]["input_path"]).resolve()
            original_path = (store.path / "artifacts" / input_file[9:11] / input_file[9:]).resolve()
            def no_input_open(path, *args, **kwargs):
                assert Path(path).resolve() not in {copied, original_path}, "saved view reopened the original input File"
                return original_open(path, *args, **kwargs)
            def no_input_artifact(reference):
                assert reference != input_file, "saved view read the original input artifact"
                return getter(reference)
            monkeypatch.setattr(Path, "open", no_input_open)
            monkeypatch.setattr(store, "get_artifact", no_input_artifact)
            monkeypatch.setattr(tools, "_sequence_worker_async", _forbidden)
            monkeypatch.setattr(ordinary, "run_owned_molecular_worker", _forbidden)
            monkeypatch.setattr(ordinary, "retain_molecular_publication", _forbidden)
            return tool_action(dict(mode="read_stored", result_ref=source["id"], view=view))

        commission = dict(selection=dict(kind="episode_child", role="scientific_process", goal=question,
            scope=scope, purpose="Return the full original partial CD summary with its surviving thermal values and input qualifications.",
            schema_json=json.dumps(form), initial_report_json="{}", assignment=dict(selection=selected,
                evidence_refs=initial, constraints=dict(original_biomni_execution=False), context=dict(question=question))), report_update={})
        provider = PartialDecisions([commission, tool_action(calculate_args), after_partial])
        def make_workflow():
            return Workflow(store, tools, provider, directory, "ordinary-cd-partial-workflow-fixture",
                lambda path, initial: FixtureController(str(path), initial, 1 if len(path) == 1 else 2),
                lambda store, scope, **kwargs: 0, project_child_credit=lambda store, scope, **kwargs: 0,
                episode_binding_descriptors=[descriptor], episode_record_receipts=True, initial_known_record_refs=initial)
        def make_root(owner):
            report = TypedReportContract("Return exactly the original partial CD summary received from the scientific investigation.",
                form, lambda reference, namespace: owner.resolver(scope, source=value.source)(reference, namespace),
                semantic_validator=lambda result: owner.validate_report(result, scope, grain="annotation", schema=form, source=value.source))
            value = owner.build("annotation", "root", question, scope, contract=report)
            return value
        workflow = make_workflow(); root = make_root(workflow)
        record = asyncio.run(root.run_async(workflow.context)); asyncio.run(root.build_result(record))
        monkeypatch.setattr(Path, "open", original_open)
        monkeypatch.setattr(store, "get_artifact", getter)
        assert len(provider.contexts) == 3 and len(workers) == len(launches) == len(feedback_seen) == 1
        source_ref, producer_id = original["source"]["id"], original["invocation"]["episode_id"]
        producer_request = json.loads(store.db.execute("SELECT request FROM runtime_episodes WHERE run_id=? AND episode_id=?",
            (workflow.run_id, producer_id)).fetchone()[0])
        assert original["invocation"]["request_sha256"] == hashlib.sha256(canonical(producer_request).encode()).hexdigest()
        actions = [dict(row) for row in store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "ORDER BY decision_index", (workflow.run_id, producer_id))]
        outcomes = [json.loads(row["result"]) for row in actions]
        assert [row["status"] for row in outcomes] == ["partial", "partial"]
        expected_feedback = dict(category="numerical_input", code="circular_dichroism_partial_measurements", source_ref=source_ref)
        assert all(row["feedback"] == expected_feedback and row["record_refs"] == [source_ref] for row in outcomes)
        assert outcomes[1]["changed_record_refs"] == []
        saved_view = outcomes[1]["result"]
        assert saved_view["selection"] == view and canonical(saved_view["summary"]) == canonical(original["summary"])
        assert [row["ordinal"] for row in saved_view["spectrum_rows"]] == [6, 6, 99]
        assert saved_view["spectrum_rows"][0] == saved_view["spectrum_rows"][1]
        missing = saved_view["spectrum_rows"][0]
        assert missing["availability"] == "present" and missing["wavelength"]["value"] == 310.
        assert missing["signal"] == dict(state="missing", input_kind="missing", value=None, unit="mdeg", issue_codes=[])
        assert saved_view["spectrum_rows"][-1]["availability"] == "out_of_range"
        assert [row["ordinal"] for row in saved_view["thermal_rows"]] == [0, 2, 0, 99]
        observed_zero = saved_view["thermal_rows"][0]
        assert observed_zero["signal"]["state"] == observed_zero["relative_signal"]["state"] == "present"
        assert observed_zero["signal"]["value"] == observed_zero["relative_signal"]["value"] == 0.
        assert saved_view["thermal_rows"][-1]["availability"] == "out_of_range"
        assert [row["ordinal"] for row in saved_view["issues"]] == [0, 0, 99]
        assert saved_view["issues"][0]["issue"] == dict(code="paired_length_mismatch", field="/spectrum")
        assert saved_view["issues"][-1] == dict(ordinal=99, availability="out_of_range", issue=None)
        for row in actions:
            action, outcome = json.loads(row["action"]), json.loads(row["result"])
            key = f'{workflow.run_id}:{producer_id}:{row["decision_index"]}'
            operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (key,)).fetchone()
            assert operation["name"] == contracts.CD_TOOL and operation["arguments"] == canonical(action["arguments"])
            assert operation["scope"] == canonical(scope) and operation["id"] == outcome["operation_ref"]
            assert operation["result"] == canonical({key: value for key, value in outcome.items() if key != "pending_work_after_action"})
        assert store.db.execute("SELECT COUNT(*) FROM records WHERE record_type='source' "
            "AND json_extract(data,'$.provider')=?", (contracts.CD_TOOL,)).fetchone()[0] == 1
        episodes = [dict(row) for row in store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=?", (workflow.run_id,))]
        assert len(episodes) == 2 and all(row["state"] == "yielded" for row in episodes)
        private = {original["source"]["artifact_ref"], original["source"]["request_ref"], original["grading_ref"]}
        expected_counts = {}
        for row in episodes:
            current = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_cd_partial_").context(row["episode_id"])
            count = 2 if current.episode_id == producer_id else 1
            expected_counts[current.episode_id] = count
            for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
                assert store.db.execute("SELECT COUNT(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                    (workflow.run_id, current.episode_id)).fetchone()[0] == count
            returned = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (workflow.run_id, current.episode_id)).fetchone()[0])
            assert canonical(returned) == canonical(dict(summaries=[original["summary"]]))
            assert canonical(workflow.services.molecular_frozen_facts(current, fact_source=contracts.FACT_SOURCE)) == canonical([original["summary"]])
            known = set(workflow.receipts.known(current.episode_id))
            assert {input_file, input_source["id"], source_ref} <= known and not private.intersection(known)
            for reference in private:
                assert workflow.resolver(scope, context=current)(reference, "artifact") is False
                assert workflow.services.reference_in_context(current, reference, "artifact") is False
        assert canonical(workflow.services.molecular_received_facts(workflow.binding_context(root.source),
            fact_source=contracts.FACT_SOURCE)) == canonical([original["summary"]])

        before, run_files, artifact_files = _tables(store), _files(directory), _files(store.path / "artifacts")
        monkeypatch.setattr(store, "get_artifact", _forbidden)
        monkeypatch.setattr(provider, "complete", _forbidden)
        monkeypatch.setattr(ordinary, "read_retained_molecular_publication", _forbidden)
        monkeypatch.setattr(tool_grading_artifacts, "retain_tool_grading", _forbidden)
        for name in ("populate_circular_dichroism_sheet", "validate_circular_dichroism_sheet"):
            monkeypatch.setattr(core, name, _forbidden)
        for name in ("project_circular_dichroism_return", "project_circular_dichroism_view"):
            monkeypatch.setattr(contracts, name, _forbidden)
        for name in ("prepare_job", "resume_start", "collect", "wait_job"):
            monkeypatch.setattr(native_lifecycle, name, _forbidden)
        private_paths = {(store.path / "artifacts" / reference[9:11] / reference[9:]).resolve()
            for reference in private | {input_file}}
        def no_replay_payload_open(path, *args, **kwargs):
            assert Path(path).resolve() not in private_paths, "closed partial replay opened a scientific payload"
            return original_open(path, *args, **kwargs)
        monkeypatch.setattr(Path, "open", no_replay_payload_open)
        restored = make_workflow(); replay = make_root(restored)
        replay_record = asyncio.run(replay.run_async(restored.context)); asyncio.run(replay.build_result(replay_record))
        monkeypatch.setattr(Path, "open", original_open)
        assert _tables(store) == before and _files(directory) == run_files and _files(store.path / "artifacts") == artifact_files
        assert len(provider.contexts) == 3 and len(workers) == len(launches) == 1
        assert canonical(restored.services.molecular_received_facts(restored.binding_context(replay.source),
            fact_source=contracts.FACT_SOURCE)) == canonical([original["summary"]])
        (tmp_path / "CD_PARTIAL_EPISODE.json").write_text(json.dumps(dict(version="cd_partial_episode_verification_v1",
            qualification="Distinct engineered incomplete spectrum; one existing-core worker, no original Biomni or saved calculation.",
            question=question, run_id=workflow.run_id, scope=scope, input_source_ref=input_source["id"], input_file=input_file,
            input_sha256=hashlib.sha256(raw).hexdigest(), source=original["source"], stored=original["stored"],
            control=original["control"], grading_ref=original["grading_ref"], summary=original["summary"], outcomes=outcomes,
            native_handles=[row["handle"] for row in workers], native_worker_count=1, saved_public_calculator_count=0,
            partial_feedback=feedback_seen, episode_action_observation_model_counts=expected_counts,
            closed_replay_rows_and_files_unchanged=True), allow_nan=False, indent=2) + "\n")


def test_retained_cd_partial_views_and_original_closed_replay(tmp_path, monkeypatch):
    """Complete323's post-worker assertions without another CD calculation.

    The selected fixture is the original failed test's actual closed Store/run.
    One initial authenticated saved-publication read allows sheet metadata
    validation. Frozen delivery and closed replay then forbid all scientific
    payload reads, sheet validation, projectors, workers and model calls.
    """
    from gene_annotation_episode import native_lifecycle, tool_grading_artifacts
    from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
    from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary

    original, directory, original_pins = _clone_retained_cd(tmp_path,
        environment_name="HMMER_NATIVE_ORACLE_CD_PARTIAL_RETAINED",
        expected_database_sha256="61663a6d07a9af374918e6fdf5c5965ed19fd918c400693d8c1afc1c71e57783",
        clone_name="retained-cd323")
    run, run_id = directory / "run", "ordinary-cd-partial-workflow-fixture"
    source_ref = "source_1e4a4c087c2b4d6d3c0d7c71"
    producer_id = "episode_7817305dc2ab6305e7e7afecbffe442a79f5d944b39da4f462c0fec510a7bb92"
    original_import, original_open = builtins.__import__, Path.open

    def no_biomni(name, *args, **kwargs):
        assert name != "biomni" and not name.startswith("biomni."), "original Biomni was imported"
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_biomni)
    monkeypatch.setattr("socket.create_connection", _forbidden)
    monkeypatch.setattr("urllib.request.OpenerDirector.open", _forbidden)
    for name in ("_spectrum", "_thermal", "calculate_circular_dichroism_components"):
        monkeypatch.setattr(core, name, _forbidden)
    monkeypatch.setattr(adapter, "run_circular_dichroism_tool_request", _forbidden)
    monkeypatch.setattr(ordinary, "run_owned_molecular_worker", _forbidden)
    monkeypatch.setattr(ordinary, "retain_molecular_publication", _forbidden)
    monkeypatch.setattr(tool_grading_artifacts, "retain_tool_grading", _forbidden)
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", _forbidden)
    for name in ("prepare_job", "resume_start", "collect", "wait_job"):
        monkeypatch.setattr(native_lifecycle, name, _forbidden)

    with Store(directory / "store") as store:
        episodes = [dict(row) for row in store.db.execute(
            "SELECT * FROM runtime_episodes WHERE run_id=?", (run_id,))]
        assert len(episodes) == 2 and all(row["state"] == "yielded" for row in episodes)
        requests = {row["episode_id"]: json.loads(row["request"]) for row in episodes}
        root_row, = [row for row in episodes if len(json.loads(row["path"])) == 1]
        root_request, producer_request = requests[root_row["episode_id"]], requests[producer_id]
        scope, question = root_request["message"]["scope"], root_request["goal"]["objective"]
        initial = producer_request["message"]["episode_assignment"]["evidence_refs"]
        input_source, input_file = initial
        assert input_source == "source_cb748fa3b316f94bc0cfe800"
        assert input_file == "artifact_ad8de53badde9134b1f28effda1aadbb231ddd683d2bfd6a1b2c775d9c165229"
        source = store.get(source_ref)
        private = {source["artifact_ref"], source["request_ref"], *source["auxiliary_artifact_refs"]}
        assert len(private) == 3
        saved_binding = producer_request["message"]["scientific_process"]["mechanics_binding"]
        descriptor = ScientificProcessEpisodes(None,
            library=ScientificProcessLibrary(run / "scientific-process-library"),
            tool_library=ScientificToolLibrary(run / "scientific-tool-library"),
            child_roles=["scientific_process"]).as_record()
        assert {**saved_binding, "implementation_sha256": descriptor["implementation_sha256"]} == descriptor
        tools = ToolRegistry(store, job_limits=dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3))
        provider = _Decisions([])
        monkeypatch.setattr(provider, "complete", _forbidden)
        form = root_request["report_contract"]["measurements"]["schema"]
        assert canonical(form) == canonical(obj(dict(summaries=
            contracts.circular_dichroism_fact_sources()[contracts.FACT_SOURCE]["report_schema"])))

        def make_workflow():
            return Workflow(store, tools, provider, run, run_id,
                lambda path, initial: FixtureController(str(path), initial, 1 if len(path) == 1 else 2),
                lambda store, scope, **kwargs: 0, project_child_credit=lambda store, scope, **kwargs: 0,
                episode_binding_descriptors=[descriptor], episode_record_receipts=True, initial_known_record_refs=initial)

        def make_root(owner):
            report = TypedReportContract(root_request["report_contract"]["decision"], form,
                lambda reference, namespace: owner.resolver(scope, source=value.source)(reference, namespace),
                semantic_validator=lambda result: owner.validate_report(result, scope, grain="annotation",
                    schema=form, source=value.source))
            value = owner.build("annotation", "root", question, scope, contract=report)
            return value

        before, artifacts = _tables(store), _files(store.path / "artifacts")
        scientific_files = _cd_scientific_run_files(run)
        workflow = make_workflow(); root = make_root(workflow)
        assert _tables(store) == before and _files(store.path / "artifacts") == artifacts
        assert _cd_scientific_run_files(run) == scientific_files
        guides = {}
        for name in ("tool-knowledge", "launch-instructions"):
            retained_index = original / "run" / name / "index.json"
            assert (run / name / "index.json").read_bytes() == retained_index.read_bytes()
            for entry in json.loads(retained_index.read_bytes())["entries"]:
                for section in entry["sections"]:
                    raw = (run / name / section["path"]).read_bytes()
                    assert hashlib.sha256(raw).hexdigest() == section["sha256"] and len(raw) == section["bytes"]
            guides[name] = _files(run / name)
        contexts = {row["episode_id"]: EpisodeReturnRecords(store, run_id,
            failure_prefix="test_cd_partial_retained_").context(row["episode_id"]) for row in episodes}
        getter = store.get_artifact
        input_path = (store.path / "artifacts" / input_file[9:11] / input_file[9:]).resolve()
        integrity_read = [False]

        def no_input_open(path, *args, **kwargs):
            assert integrity_read[0] or Path(path).resolve() != input_path, "retained partial delivery reopened input"
            return original_open(path, *args, **kwargs)

        def no_input_bytes(reference):
            assert reference != input_file, "retained partial delivery read its original input"
            return getter(reference)

        def audit_files(path):
            integrity_read[0] = True
            try:
                return _files(path)
            finally:
                integrity_read[0] = False

        monkeypatch.setattr(Path, "open", no_input_open)
        monkeypatch.setattr(store, "get_artifact", no_input_bytes)
        saved = ordinary.read_retained_molecular_publication(tools, contexts[producer_id],
            workflow.services.read_received_molecular_input, source_ref, tool_name=contracts.CD_TOOL)
        assert saved["admission_kind"] == "source_only" and saved["source"] == source
        stored, control = saved["stored"], saved["control"]
        assert set(stored) == {"version", "request", "sheet", "components"}
        assert stored["version"] == contracts.RESULT_VERSION
        assert control["native_artifact_ref"] == source["artifact_ref"]
        assert control["request"]["received_input"]["file"]["artifact_ref"] == input_file
        assert control["request"]["request"] == stored["request"]
        invocation = control["request"]["invocation"]
        assert invocation["run_id"] == run_id and invocation["episode_id"] == producer_id
        assert invocation["operation_key"] == f"{run_id}:{producer_id}:0" and invocation["decision_index"] == 0
        assert invocation["request_sha256"] == hashlib.sha256(canonical(producer_request).encode()).hexdigest()
        assert saved["grading_ref"] in private
        assert source["parent_source_refs"] == [input_source]
        assert stored["sheet"]["source_method"]["native_execution"] is False
        assert stored["components"]["spectrum"] == dict(state="invalid_input", features=[], source_structure_label=None)
        assert stored["components"]["issues"] == [dict(code="paired_length_mismatch", field="/spectrum")]
        assert stored["components"]["thermal"]["state"] == "present"
        assert [row["relative_signal"]["value"] for row in stored["components"]["thermal"]["relative_signal"]] == [0., .2, .5, .8, 1.]
        expected = contracts.project_circular_dichroism_return(stored, source_ref=source_ref)
        assert expected["spectrum"]["state"] == "invalid_input" and expected["spectrum"]["features"] == []
        assert expected["spectrum"]["wavelength_count"] == 7 and expected["spectrum"]["signal_count"] == 6
        assert expected["issue_codes"] == ["paired_length_mismatch"]
        cells = {row["name"]: row for row in expected["thermal"]["summary"]}
        assert cells["sampled_midpoint_index"]["value"] == 2
        assert cells["sampled_midpoint_temperature"]["value"] == 40. and cells["source_transition_width"]["value"] == 8.
        actions = [dict(row) for row in store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? "
            "ORDER BY decision_index", (run_id, producer_id))]
        outcomes = [json.loads(row["result"]) for row in actions]
        assert [json.loads(row["action"])["arguments"]["mode"] for row in actions] == ["calculate", "read_stored"]
        partial_feedback = dict(category="numerical_input", code="circular_dichroism_partial_measurements", source_ref=source_ref)
        assert all(row["status"] == "partial" and row["feedback"] == partial_feedback and row["record_refs"] == [source_ref]
            for row in outcomes)
        assert outcomes[0]["changed_record_refs"] == [source_ref] and outcomes[1]["changed_record_refs"] == []
        assert canonical(outcomes[0]["result"]) == canonical(expected)
        view = outcomes[1]["result"]
        assert canonical(view["summary"]) == canonical(expected)
        assert view["selection"] == dict(spectrum_ordinals=[6, 6, 99], thermal_ordinals=[0, 2, 0, 99], issue_ordinals=[0, 0, 99])
        assert [row["ordinal"] for row in view["spectrum_rows"]] == [6, 6, 99]
        missing = view["spectrum_rows"][0]
        assert missing == view["spectrum_rows"][1] and missing["availability"] == "present"
        assert missing["wavelength"]["value"] == 310.
        assert missing["signal"] == dict(state="missing", input_kind="missing", value=None, unit="mdeg", issue_codes=[])
        assert view["spectrum_rows"][-1]["availability"] == "out_of_range"
        assert [row["ordinal"] for row in view["thermal_rows"]] == [0, 2, 0, 99]
        zero = view["thermal_rows"][0]
        assert zero == view["thermal_rows"][2]
        assert zero["signal"]["state"] == zero["relative_signal"]["state"] == "present"
        assert zero["signal"]["value"] == zero["relative_signal"]["value"] == 0.
        assert view["thermal_rows"][-1]["availability"] == "out_of_range"
        assert [row["ordinal"] for row in view["issues"]] == [0, 0, 99]
        assert view["issues"][0]["issue"] == dict(code="paired_length_mismatch", field="/spectrum")
        assert view["issues"][0] == view["issues"][1] and view["issues"][-1] == dict(ordinal=99, availability="out_of_range", issue=None)
        for row, outcome in zip(actions, outcomes):
            operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?",
                (f'{run_id}:{producer_id}:{row["decision_index"]}',)).fetchone()
            assert operation["name"] == contracts.CD_TOOL and operation["arguments"] == canonical(json.loads(row["action"])["arguments"])
            assert operation["scope"] == canonical(scope) and operation["id"] == outcome["operation_ref"]
            assert operation["result"] == canonical({key: value for key, value in outcome.items() if key != "pending_work_after_action"})
        calls = [json.loads(row[0])["context"] for row in store.db.execute("SELECT request FROM runtime_model_calls "
            "WHERE run_id=? AND episode_id=? ORDER BY call_index", (run_id, producer_id))]
        assert len(calls) == 2 and all(row["feedback"] is None for row in calls)
        assert calls[0]["last_local_outcome"] is None
        assert calls[1]["last_local_outcome"]["status"] == "partial"
        assert calls[1]["last_local_outcome"]["feedback"] == partial_feedback
        assert _tables(store) == before

        private_paths = {(store.path / "artifacts" / ref[9:11] / ref[9:]).resolve() for ref in private | {input_file}}
        def no_payload_open(path, *args, **kwargs):
            assert integrity_read[0] or Path(path).resolve() not in private_paths, "closed partial delivery read a payload"
            return original_open(path, *args, **kwargs)
        monkeypatch.setattr(Path, "open", no_payload_open)
        monkeypatch.setattr(store, "get_artifact", _forbidden)
        monkeypatch.setattr(ordinary, "read_retained_molecular_publication", _forbidden)
        for name in ("project_circular_dichroism_return", "project_circular_dichroism_view"):
            monkeypatch.setattr(contracts, name, _forbidden)
        for name in ("populate_circular_dichroism_sheet", "validate_circular_dichroism_sheet"):
            monkeypatch.setattr(core, name, _forbidden)
        expected_counts = {}
        for current in contexts.values():
            count = 2 if current.episode_id == producer_id else 1
            expected_counts[current.episode_id] = count
            for table in ("runtime_actions", "runtime_observations", "runtime_model_calls"):
                assert store.db.execute("SELECT COUNT(*) FROM " + table + " WHERE run_id=? AND episode_id=?",
                    (run_id, current.episode_id)).fetchone()[0] == count
            returned = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
                (run_id, current.episode_id)).fetchone()[0])
            assert canonical(returned) == canonical(dict(summaries=[expected]))
            assert canonical(workflow.services.molecular_frozen_facts(current, fact_source=contracts.FACT_SOURCE)) == canonical([expected])
            received = workflow.services.molecular_received_facts(current, fact_source=contracts.FACT_SOURCE)
            assert canonical(received) == canonical([] if current.episode_id == producer_id else [expected])
            known = set(workflow.receipts.known(current.episode_id))
            assert {input_file, input_source, source_ref} <= known and not private.intersection(known)
            for reference in private:
                assert workflow.resolver(scope, context=current)(reference, "artifact") is False
                assert workflow.services.reference_in_context(current, reference, "artifact") is False
        assert store.db.execute("SELECT COUNT(*) FROM tool_operations").fetchone()[0] == 2
        assert store.db.execute("SELECT COUNT(*) FROM records WHERE record_type='source' AND json_extract(data,'$.provider')=?",
            (contracts.CD_TOOL,)).fetchone()[0] == 1
        run_files, artifact_files = audit_files(run), audit_files(store.path / "artifacts")
        restored = make_workflow(); replay = make_root(restored)
        replay_record = asyncio.run(replay.run_async(restored.context)); asyncio.run(replay.build_result(replay_record))
        assert _tables(store) == before and audit_files(run) == run_files and audit_files(store.path / "artifacts") == artifact_files
        assert _cd_scientific_run_files(run) == scientific_files and provider.contexts == []
        assert canonical(restored.services.molecular_received_facts(restored.binding_context(replay.source),
            fact_source=contracts.FACT_SOURCE)) == canonical([expected])
        integrity_read[0] = True
        try:
            assert _cd_retained_pins(original) == original_pins
        finally:
            integrity_read[0] = False
        (tmp_path / "CD_PARTIAL_RETAINED_REPLAY.json").write_text(json.dumps(dict(
            version="cd_partial_retained_replay_verification_v1", qualification=
                "Original323 failed after its one distinct-input worker; this case uses only retained values and closed history.",
            original_input_pins=original_pins, source_ref=source_ref, summary=expected, outcomes=outcomes,
            missing_spectral_signal=missing["signal"], observed_thermal_zero=zero,
            episode_action_observation_model_counts=expected_counts, partial_feedback=partial_feedback,
            regenerated_operational_guides=guides, saved_binding=saved_binding, current_binding=descriptor,
            new_worker_count=0, new_scientific_calculation_count=0, new_publication_count=0,
            closed_replay_rows_and_scientific_files_unchanged=True), allow_nan=False, indent=2) + "\n")
