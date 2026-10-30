"""Current-code replay of the original completed live job, with no new work."""
import asyncio
import hashlib
import json
from pathlib import Path
import runpy
import shutil
from types import CodeType, FunctionType

from method_loop.archive import iter_json

from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.rfam_batch_transport import RfamBatchHTTP
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "verification/tool_graders_rfam_live_workflow_2026-10-26_243/live_001"
RUN_ID = "rfam-live-composed-243"
GOAL = "Measure Rfam family-model matches and query coverage for the three selected public nucleotide input occurrences"
HISTORY_TABLES = ("runtime_episodes", "runtime_actions", "runtime_observations",
    "runtime_model_calls", "runtime_report_attempts", "runtime_forms")


def _load(name):
    return json.loads((LIVE / name).read_text())


def _history(store):
    return {table: [dict(row) for row in store.db.execute(
        "SELECT * FROM " + table + " WHERE run_id=? ORDER BY rowid", (RUN_ID,))]
        for table in HISTORY_TABLES}


def _hashes(directory=LIVE, *, include_sqlite=True):
    # Original evidence, including SQLite state, must not be rewritten. Only the
    # working copy's journal bookkeeping is compared through its history below.
    paths = [path for path in directory.rglob("*") if path.is_file()
        and (include_sqlite or path.name not in
            {"state.sqlite3", "state.sqlite3-wal", "state.sqlite3-shm"})]
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths}


def test_current_code_replays_original_live_rfam_without_new_work(tmp_path, monkeypatch):
    before = _hashes()
    working = tmp_path / "historical_replay"
    shutil.copytree(LIVE, working)
    # Store recovery needs writable local bookkeeping; the retained live run
    # stays frozen, and the isolated copy starts with exactly its saved bytes.
    working.chmod(0o700)
    for path in working.rglob("*"):
        path.chmod(0o700 if path.is_dir() else 0o600)
    assert _hashes(working) == before
    working_before = _hashes(working, include_sqlite=False)
    expected_archive = _load("archive.json")
    expected_history = _load("history.json")
    expected_publication = _load("publication.json")
    scope = _load("caller-selected-inputs.json")["scope"]
    run_directory = working / "run"

    def forbidden(*args, **kwargs):
        raise AssertionError("Saved live replay attempted new network, parsing, calculation, model or execution work")

    for name in ("socket.create_connection", "socket.socket.connect", "socket.socket.connect_ex",
                 "urllib.request.OpenerDirector.open", "subprocess.run", "subprocess.Popen",
                 "gene_annotation_episode.rfam_batch_table.populate_rfam_batch_tblout_sheet",
                 "gene_annotation_episode.rfam_batch_table_grader.calculate_rfam_batch_table_components",
                 "gene_annotation_episode.infernal_search_inputs.populate_infernal_search_sheet",
                 "gene_annotation_episode.infernal_search_grader.calculate_infernal_search_scores",
                 "gene_annotation_episode.rfam_batch_report.populate_rfam_batch_report_sheet",
                 "gene_annotation_episode.rfam_batch_report_grader.calculate_rfam_batch_report_components",
                 "gene_annotation_episode.infernal_search_cells.upgrade_saved_infernal_search_sheet",
                 "gene_annotation_episode.rfam_batch_infernal.upgrade_saved_rfam_search_sheet"):
        monkeypatch.setattr(name, forbidden)
    monkeypatch.setattr(RfamBatchHTTP, "_request", forbidden)

    class NoModel:
        async def complete(self, *args, **kwargs):
            forbidden()

        async def release(self, episode_id):
            pass

    # Reuse the ACTUAL original verification controller code, never a rewritten
    # equivalent. Its qualified function identity is part of saved forecasts.
    # Loading the module under this name does not invoke main or launch work.
    original = runpy.run_path(str(LIVE.parent / "run_live.py"), run_name="saved_rfam_verification")
    controller_code, = [code for code in original["main"].__code__.co_consts
        if isinstance(code, CodeType) and code.co_name == "controllers"]
    assert not controller_code.co_freevars
    controllers = FunctionType(controller_code,
        {**original, "__name__": "__main__", "DIRECTORY": working})

    with Store(working / "state") as store:
        assert _history(store) == expected_history
        tools = ToolRegistry(store)
        factory = ExecutionServiceFactory(
            {"rfam": {"kind": "api", "service": "rfam_batch", "timeout": 90.0}}, {}, 3, 2, .5)
        application = factory(store, run_id=RUN_ID, directory=run_directory,
            tool_registry=tools, tool_catalog=tools.catalog())
        descriptor = ScientificProcessEpisodes(None,
            library=ScientificProcessLibrary(run_directory / "scientific-process-library"),
            tool_library=ScientificToolLibrary(run_directory / "scientific-tool-library"),
            child_roles=("scientific_process", "launch", "results")).as_record()
        workflow = Workflow(store, tools, NoModel(), run_directory, RUN_ID,
            controller_factory=controllers, project_credit=lambda *_: 0,
            episode_binding_descriptors=(descriptor, *application.episode_binding_descriptors),
            role_credit_bindings=application.role_credit_bindings,
            job_progress_provider=application.job_progress_provider,
            annotation_child_roles=("scientific_process",), episode_record_receipts=True,
            initial_known_record_refs=[])
        root = workflow.build("annotation", "root", GOAL, scope)

        async def execute():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return json.loads("".join(iter_json(record.as_record())))

        try:
            actual_archive = asyncio.run(execute())
        except Exception as error:
            trace = error.__traceback__
            while trace is not None:
                local = trace.tb_frame.f_locals
                if trace.tb_frame.f_code.co_name == "on_unit" and "old" in local and "data" in local:
                    expected = json.loads(local["old"]["observation"])
                    actual = local["data"]
                    differences = {key: {"saved": expected.get(key), "replayed": actual.get(key)}
                        for key in expected.keys() | actual.keys() if expected.get(key) != actual.get(key)}
                    raise AssertionError(json.dumps(differences, indent=2, sort_keys=True)) from error
                trace = trace.tb_next
            raise
        assert actual_archive == expected_archive
        api = workflow.episode_bindings.for_role("results").api_execution
        final_ref = expected_publication["source_ref"]
        assert api.rfam_returns.read(final_ref, scope) == expected_publication
        scientific = expected_archive["units"][0]["child"]
        launch, results = (unit["child"] for unit in scientific["units"])
        launched_api = launch["units"][0]["child"]
        for episode in (launched_api, results):
            context = api.rfam_returns.context(episode["episode_id"])
            for path in api._action_paths(context.episode_id):
                intent = json.loads(path.read_text())
                outcome = json.loads((path.parent / "outcome.json").read_text())
                assert asyncio.run(api.execute(context, intent["name"], intent["arguments"],
                    intent["operation_key"])) == outcome
        assert _history(store) == expected_history
        forms = expected_history["runtime_forms"]
        for episode, filename in ((scientific, "scientific-return.json"), (results, "results-return.json")):
            row, = [row for row in forms if row["episode_id"] == episode["episode_id"]]
            assert json.loads(row["form"]) == _load(filename)
    assert _hashes(working, include_sqlite=False) == working_before
    assert _hashes() == before
