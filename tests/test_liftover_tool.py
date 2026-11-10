"""Two native conversions and one malformed-chain outcome in one investigation.

The question, supplied chain, decisions and stopping controller are engineering
fixtures. Workflow, scientific ToolInfo, input receipts, owned workers and
Source-owned typed delivery are real. No Liftover episode or model RPC is introduced.
"""
import asyncio
import builtins
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode import liftover_contracts as core
from gene_annotation_episode import liftover_measurements, molecular_measurement_tools as ordinary
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import canonical, obj
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.liftover_tools import LIFTOVER_TOOL, liftover_tool_contract
from gene_annotation_episode.materials import source_for_artifact
from gene_annotation_episode.runtime import TypedReportContract, Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_grading_entries
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController
from test_scientific_process_library import independent_source, write


CHAIN = b"chain 9 literal.source 20 + 0 10 literal.target 20 - 0 10 1\n10\n"
MALFORMED_CHAIN = b"chain invalid-score literal.source 20 + 0 10 literal.target 20 - 0 10 1\n10\n"
POINT = dict(chromosome="literal.source", position_0based=0, strand="-")
QUESTION = ("For the supplied literal UCSC chain and source point literal.source position 0 on strand -, "
    "which native mappings are returned, and do plain and gzip representations preserve the same "
    "positions, strands, scores and unknown assembly context? What explicit failure and call state are "
    "retained for the separately supplied malformed chain?")


def _forbidden(*args, **kwargs):
    raise AssertionError("saved liftover delivery or closed replay attempted new work")


def _files(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in directory.rglob("*") if path.is_file()}


def _tables(store):
    names = [row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: [tuple((type(value).__name__, value) for value in row) for row in
        store.db.execute('SELECT * FROM "' + name.replace('"', '""') + '"')] for name in names}


def _libraries(directory, tools):
    source = directory / "engineering-instructions"
    independent_source(source)
    old = json.loads((source / "entries/A01.json").read_bytes())
    instruction = {key: old[key] for key in ("id", "name", "description", "evidence")}
    instruction.update(entry_version="evidence_axis_instruction_v1", slot="evidence_axis",
        investigation_instructions=("Engineering integration fixture. Inspect the supplied coordinate and chain "
            "without inferring assembly labels or a target annotation. Each scripted choice and stopping rule "
            "tests ordinary-tool integration; no biological investigation accuracy is claimed."))
    write(source / "entries/A01.json", instruction)
    index = json.loads((source / "index.json").read_bytes())
    for row in index["slots"]:
        if row["slot"] == "annotation_distinction": row["slot"] = "evidence_axis"
    for row in index["entries"]:
        if row["id"] == "A01": row["slot"] = "evidence_axis"
    write(source / "index.json", index)
    descriptor = prepare_scientific_binding(run_directory=directory, source_directory=source,
        tool_catalog=tools.catalog(), child_roles=["scientific_process"])
    library = ScientificProcessLibrary(directory / "scientific-process-library")
    selected = dict(version="scientific_process_selection_v3", evidence_axis=library.reference("A01"),
        thought_pattern=library.reference("P01"), child_tool_info=[dict(name=LIFTOVER_TOOL, resources="local")])
    return descriptor, selected


class _Script:
    def __init__(self, script):
        self.script, self.contexts = iter(script), []

    async def complete(self, episode_id, role, instructions, context, output_schema):
        assert role == "REASONING"
        feedback = context.get("feedback")
        assert feedback is None or (feedback.get("category") == "numerical_execution"
            and feedback.get("code") == "chain_parse_failed"), feedback
        self.contexts.append(deepcopy(context))
        selected = next(self.script)
        return selected(context) if callable(selected) else deepcopy(selected)

    async def release(self, episode_id):
        pass


def _action(arguments):
    return dict(selection=dict(kind="tool", tool=LIFTOVER_TOOL, arguments=arguments), report_update={})


def test_registered_liftover_native_source_delivery_and_saved_views(tmp_path, monkeypatch):
    """The sole native selector: two real conversions and one pre-conversion failure."""
    from gene_annotation_episode import native_lifecycle, tool_grading_artifacts
    directory = tmp_path / "run"; directory.mkdir()
    native_calls, worker_visits, authenticated, originals, failures, saved_calls = [], [], [], [], [], []
    with Store(tmp_path / "store") as store:
        scope = dict(subject_refs=store.create_problem(raw_sequence="ACGTACGT", molecule="dna")["subject_refs"])
        chain_file = store.artifact(CHAIN, "application/octet-stream")
        chain_source = source_for_artifact(store, chain_file)
        compressed = gzip.compress(CHAIN, mtime=0)
        gzip_file = store.artifact(compressed, "application/gzip")
        gzip_source = source_for_artifact(store, gzip_file)
        malformed_file = store.artifact(MALFORMED_CHAIN, "application/octet-stream")
        malformed_source = source_for_artifact(store, malformed_file)
        assert gzip_source["artifact_ref"] == gzip_file and malformed_source["artifact_ref"] == malformed_file
        evidence = [chain_source["id"], chain_file, gzip_file, malformed_file]
        assert store.reference_subset(evidence, scope) == evidence
        tools = ToolRegistry(store, job_limits=dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3))
        contract = tools.catalog()[LIFTOVER_TOOL]
        assert contract["resources"] == "local" and contract["input_schema"] == liftover_tool_contract()["input_schema"]
        descriptor, selected = _libraries(directory, tools)
        form = obj(dict(sources={"type": "array", "items": {"type": "string", "format": "reference",
            "x-reference-namespace": "source"}, "x-source": "changed_record_refs"},
            mappings=core.liftover_fact_sources()[core.FACT_SOURCE]["report_schema"]))
        commission = dict(selection=dict(kind="episode_child", role="scientific_process", goal=QUESTION,
            scope=scope, purpose="Return the original native mappings and malformed-chain failure with literal Source-owned qualifications.",
            schema_json=json.dumps(form), initial_report_json="{}", assignment=dict(selection=selected,
                evidence_refs=[chain_source["id"], chain_file, gzip_file, malformed_file], constraints=dict(chain_acquisition=False),
                context=dict(question=QUESTION, point=POINT, assembly_labels="not_supplied"))), report_update={})
        plain_args = dict(mode="convert", input=dict(namespace="source", reference=chain_source["id"]),
            chain_format="ucsc_chain", point=deepcopy(POINT))
        gzip_args = dict(mode="convert", input=dict(namespace="artifact", reference=gzip_file),
            chain_format="ucsc_chain_gzip", point=deepcopy(POINT))
        malformed_args = dict(mode="convert", input=dict(namespace="artifact", reference=malformed_file),
            chain_format="ucsc_chain", point=deepcopy(POINT))
        prepare, worker = native_lifecycle.prepare_job, tools._sequence_worker_async
        authenticate = ordinary.authenticate_molecular_invocation
        assert authenticate is ordinary.authenticate_itc_invocation

        def observe_prepare(command, **kwargs):
            payload = json.loads(Path(command[-2]).read_bytes())
            assert command[:3] == [sys.executable, "-m", "gene_annotation_episode.sequence_worker"]
            assert payload["operation"] == "liftover_point"
            assert kwargs["policy"].to_dict() == tools.local_job_policy.to_dict()
            native_calls.append(deepcopy(payload))
            return prepare(command, **kwargs)

        async def observe_worker(operation, arguments, **kwargs):
            assert operation == "liftover_point" and kwargs["directory"] == kwargs["owned_directory"]
            work = await worker(operation, arguments, **kwargs)
            worker_visits.append(dict(output=str(work.output_path),
                handle=json.loads((work.output_path.parent / "native-handle.json").read_bytes())))
            return work

        def observe_authentication(registry, name, arguments, current_scope, key):
            result = authenticate(registry, name, arguments, current_scope, key)
            context, reader = result
            assert context.role == "scientific_process" and callable(reader)
            assert plain(context.scope) == current_scope == scope
            authenticated.append(dict(episode_id=context.episode_id, mode=arguments["mode"], key=key))
            return result

        monkeypatch.setattr(native_lifecycle, "prepare_job", observe_prepare)
        monkeypatch.setattr(tools, "_sequence_worker_async", observe_worker)
        monkeypatch.setattr(ordinary, "authenticate_molecular_invocation", observe_authentication)
        calculate = core.calculate_liftover_components
        allow_saved_calculation = [False]

        def selected_saved_calculation(sheet, *, mapping_ordinals=None):
            assert allow_saved_calculation[0], "read_stored invoked the public calculator"
            saved_calls.append(deepcopy(mapping_ordinals))
            return calculate(sheet, mapping_ordinals=mapping_ordinals)

        original_import = builtins.__import__
        def no_pyliftover_import(name, *args, **kwargs):
            assert name != "pyliftover" and not name.startswith("pyliftover."), "saved mode imported PyLiftover"
            return original_import(name, *args, **kwargs)

        def observe_original(context):
            outcome = context["last_local_outcome"]
            assert outcome["status"] == "completed" and outcome["feedback"] is None
            projection = outcome["result"]; source = store.get(projection["source_ref"])
            stored = json.loads(store.get_artifact(source["artifact_ref"]))
            control = json.loads(store.get_artifact(source["request_ref"]))
            grade, = source_tool_grading_entries(store, source["id"])
            assert canonical(grade["grading"]) == canonical(dict(sheet=stored["sheet"], scores=stored["components"]))
            assert stored["sheet"]["observation"]["native_result"] == [["literal.target", 19, "+", 9]]
            assert stored["sheet"]["observation"]["software"] == dict(name="pyliftover", version="0.4.1")
            assert stored["sheet"]["observation"]["conversion_call_state"] == "returned"
            assert stored["sheet"]["observation"]["conversion_call_count"] == 1
            assert projection["point"] == POINT and projection["selected_mapping_ordinals"] == [0]
            assert projection["rows"] == stored["components"]["rows"]
            assert projection["population"] == stored["components"]["population"]
            assert projection["population"]["point_state"] == "unique"
            assert projection["population"]["mapping_count"] == 1
            assert all(value == dict(state="unavailable", label=None, reason="not_provided")
                for value in projection["assembly_context"].values())
            assert source["parent_source_refs"] == ([chain_source["id"]] if not originals else [])
            assert "operand_refs" not in source and control["native_artifact_ref"] == source["artifact_ref"]
            assert control["native_handle"] == worker_visits[len(originals)]["handle"]
            assert [source["id"]] == outcome["record_refs"] == outcome["changed_record_refs"]
            originals.append(dict(source=source, stored=stored, control=control, grading_ref=grade["artifact_ref"],
                projection=deepcopy(projection)))

        def after_plain(context):
            assert context["goal"]["objective"] == QUESTION
            assert context["scientific_process"]["selection"] == selected
            assert {entry["name"] for entry in context["tools"]} >= {LIFTOVER_TOOL}
            observe_original(context)
            return _action(gzip_args)

        def after_gzip(context):
            observe_original(context)
            assert len(native_calls) == len(worker_visits) == 2
            return _action(malformed_args)

        def after_malformed(context):
            outcome = context["last_local_outcome"]
            assert outcome["status"] == "partial"
            projection = outcome["result"]; source = store.get(projection["source_ref"])
            stored = json.loads(store.get_artifact(source["artifact_ref"]))
            control = json.loads(store.get_artifact(source["request_ref"]))
            grade, = source_tool_grading_entries(store, source["id"])
            assert canonical(grade["grading"]) == canonical(dict(sheet=stored["sheet"], scores=stored["components"]))
            observation = stored["sheet"]["observation"]
            assert observation["conversion_call_state"] == "not_started" and observation["conversion_call_count"] == 0
            assert observation["native_result"] is None and observation["result_state"] == "unavailable"
            assert observation["failure"]["stage"] == "chain_parse" and observation["failure"]["code"] == "chain_parse_failed"
            assert outcome["feedback"] == dict(category="numerical_execution", code="chain_parse_failed", source_ref=source["id"])
            assert projection["failure"] == dict(stage="chain_parse", code="chain_parse_failed", location_code="native_failure", occurrence=0)
            assert projection["rows"] == [] and projection["selected_mapping_ordinals"] == []
            assert projection["population"]["mapping_count"] is None and projection["population"]["native_row_count"] is None
            assert projection["population"]["point_state"] == "not_started"
            assert source["parent_source_refs"] == [] and control["native_handle"] == worker_visits[2]["handle"]
            assert [source["id"]] == outcome["record_refs"] == outcome["changed_record_refs"]
            failures.append(dict(source=source, stored=stored, grading_ref=grade["artifact_ref"], projection=deepcopy(projection)))
            assert len(native_calls) == len(worker_visits) == 3
            monkeypatch.setattr(tools, "_sequence_worker_async", _forbidden)
            monkeypatch.setattr(ordinary, "run_owned_molecular_worker", _forbidden)
            monkeypatch.setattr(liftover_measurements, "run_liftover_tool_request", _forbidden)
            monkeypatch.setattr(core, "calculate_liftover_components", selected_saved_calculation)
            monkeypatch.setattr(builtins, "__import__", no_pyliftover_import)
            return _action(dict(mode="read_stored", result_ref=originals[0]["source"]["id"], mapping_ordinals=[0]))

        def after_read(context):
            assert canonical(context["last_local_outcome"]["result"]) == canonical(originals[0]["projection"])
            assert saved_calls == []
            allow_saved_calculation[0] = True
            return _action(dict(mode="calculate_saved", result_ref=originals[0]["source"]["id"], mapping_ordinals=[]))

        def after_saved(context):
            projection = context["last_local_outcome"]["result"]
            assert projection["source_ref"] == originals[0]["source"]["id"]
            assert projection["selected_mapping_ordinals"] == [] and projection["rows"] == []
            assert projection["population"] == originals[0]["projection"]["population"]
            assert saved_calls == [[]]
            allow_saved_calculation[0] = False
            return _action(dict(mode="read_stored", result_ref=originals[1]["source"]["id"], mapping_ordinals=[0]))

        provider = _Script([commission, _action(plain_args), after_plain, after_gzip, after_malformed, after_read, after_saved])
        workflow = Workflow(store, tools, provider, directory, "ordinary-liftover-fixture",
            lambda path, initial: FixtureController(str(path), initial, 1 if len(path) == 1 else 6),
            lambda store, scope, **kwargs: 0, project_child_credit=lambda store, scope, **kwargs: 0,
            episode_binding_descriptors=[descriptor], episode_record_receipts=True,
            initial_known_record_refs=[chain_source["id"], chain_file, gzip_file, malformed_file])
        root_form = obj(dict(mappings=deepcopy(form["properties"]["mappings"])))
        root_contract = TypedReportContract("Return the exact received mapping and failure groups for the supplied chains.",
            root_form, lambda reference, namespace: workflow.resolver(scope, source=root.source)(reference, namespace),
            semantic_validator=lambda value: workflow.validate_report(value, scope, grain="annotation", schema=root_form, source=root.source))
        root = workflow.build("annotation", "root", QUESTION, scope, contract=root_contract)
        record = asyncio.run(root.run_async(workflow.context)); asyncio.run(root.build_result(record))
        episodes = [dict(row) for row in store.db.execute("SELECT * FROM runtime_episodes")]
        assert len(episodes) == 2
        child, = [row for row in episodes if len(json.loads(row["path"])) == 2]
        assert json.loads(child["path"])[-1][0] == "scientific_process"
        actions = [dict(row) for row in store.db.execute("SELECT * FROM runtime_actions WHERE episode_id=? "
            "ORDER BY decision_index", (child["episode_id"],))]
        outcomes = [json.loads(row["result"]) for row in actions]
        assert len(actions) == 6 and len(provider.contexts) == 7
        assert [json.loads(row["action"])["tool"] for row in actions] == [LIFTOVER_TOOL] * 6
        assert [row["mode"] for row in authenticated] == ["convert", "convert", "convert", "read_stored", "calculate_saved", "read_stored"]
        assert [row["status"] for row in outcomes] == ["completed", "completed", "partial", "completed", "completed", "completed"]
        assert canonical(outcomes[-1]["result"]) == canonical(originals[1]["projection"])
        assert all(row["changed_record_refs"] == [] for row in outcomes[3:])
        assert len(native_calls) == len(worker_visits) == 3 and saved_calls == [[]]
        assert len({row["handle"]["unit"] for row in worker_visits}) == 3
        assert [call["arguments"]["request"]["chain"]["file"]["format"] for call in native_calls] == ["ucsc_chain", "ucsc_chain_gzip", "ucsc_chain"]
        assert store.get_artifact(chain_file) == CHAIN and gzip.decompress(store.get_artifact(gzip_file)) == CHAIN
        assert store.get_artifact(malformed_file) == MALFORMED_CHAIN
        assert originals[0]["source"]["id"] != originals[1]["source"]["id"]
        context = EpisodeReturnRecords(store, workflow.run_id, failure_prefix="test_").context(child["episode_id"])
        parent = workflow.binding_context(root.source)
        parent_known = set(workflow.receipts.known(parent.episode_id))
        for original in [*originals, *failures]:
            source = original["source"]
            assert source["id"] in parent_known
            assert canonical(json.loads(store.get_artifact(source["artifact_ref"]))) == canonical(original["stored"])
            for receiver in (context, parent):
                assert workflow.resolver(scope, context=receiver)(source["id"], "source") is True
                for reference in (source["artifact_ref"], source["request_ref"], original["grading_ref"]):
                    assert reference not in set(workflow.receipts.known(receiver.episode_id))
                    assert workflow.resolver(scope, context=receiver)(reference, "artifact") is False
                    assert workflow.services.reference_in_context(receiver, reference, "artifact") is False
        form_row = store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (workflow.run_id, child["episode_id"])).fetchone()
        selected_form = json.loads(form_row[0])
        expected = [row["projection"] for row in [*originals, *failures]]
        assert set(selected_form["sources"]) == {row["source"]["id"] for row in [*originals, *failures]}
        assert len(selected_form["sources"]) == 3 and canonical(selected_form["mappings"]) == canonical(expected)
        parent_form = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
            (workflow.run_id, parent.episode_id)).fetchone()[0])
        assert canonical(parent_form["mappings"]) == canonical(expected)
        assert [row["population"]["conversion_call_count"] for row in parent_form["mappings"]] == [1, 1, 0]
        assert [row["rows"] for row in parent_form["mappings"][:2]] == [originals[0]["stored"]["components"]["rows"],
            originals[1]["stored"]["components"]["rows"]]
        assert parent_form["mappings"][2]["failure"] == dict(stage="chain_parse", code="chain_parse_failed",
            location_code="native_failure", occurrence=0)
        assert parent_form["mappings"][2]["population"]["mapping_count"] is None
        assert canonical(workflow.services.molecular_received_facts(parent, fact_source=core.FACT_SOURCE)) == canonical(expected)
        assert canonical(workflow.services.molecular_frozen_facts(context, fact_source=core.FACT_SOURCE)) == canonical(expected)
        assert canonical(workflow.services.molecular_frozen_facts(parent, fact_source=core.FACT_SOURCE)) == canonical(expected)

        before, run_files, artifacts = _tables(store), _files(directory), _files(store.path / "artifacts")
        for name in ("prepare_job", "resume_start", "collect", "wait_job"):
            monkeypatch.setattr(native_lifecycle, name, _forbidden)
        for name in ("calculate_liftover_components", "_components", "_population", "populate_liftover_sheet"):
            monkeypatch.setattr(core, name, _forbidden)
        monkeypatch.setattr(ordinary, "retain_molecular_publication", _forbidden)
        monkeypatch.setattr(ordinary, "read_retained_molecular_publication", _forbidden)
        monkeypatch.setattr(tool_grading_artifacts, "retain_tool_grading", _forbidden)
        monkeypatch.setattr(provider, "complete", _forbidden)
        replay = workflow.build("annotation", "root", QUESTION, scope, contract=root_contract)
        replay_record = asyncio.run(replay.run_async(workflow.context)); asyncio.run(replay.build_result(replay_record))
        assert _tables(store) == before and _files(directory) == run_files
        assert _files(store.path / "artifacts") == artifacts
        write(tmp_path / "LIFTOVER_TOOL.json", dict(version="liftover_tool_verification_v1", question=QUESTION,
            run_id=workflow.run_id, producing_episode_id=context.episode_id, scope=scope,
            source_refs=[row["source"]["id"] for row in originals], failure_source_ref=failures[0]["source"]["id"], qualification=(
            "Engineered question/chains/choices/controller; three actual owned workers, two convert_coordinate calls. "
            "Full Source-owned numerical/failure child and parent forms with no output File grants; public saved calculation counted "
            "separately from internal saved consistency checks. No new work or math on closed replay."),
            chain_bytes_sha256=hashlib.sha256(CHAIN).hexdigest(), native_worker_count=len(native_calls),
            saved_public_calculator_count=len(saved_calls), native_conversion_count=sum(
                row["stored"]["sheet"]["observation"]["conversion_call_count"] for row in originals),
            originals=[{key: row[key] for key in ("source", "stored", "grading_ref", "projection")} for row in originals],
            failure=failures[0],
            native_handles=[row["handle"] for row in worker_visits],
            actions=[json.loads(row["action"]) for row in actions], outcomes=outcomes,
            child_form=selected_form, parent_form=parent_form, store_directory=str(store.path), run_directory=str(directory),
            closed_replay_unchanged=True))
