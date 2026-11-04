"""Retained399/400 CAS9 values through the actual pure provider renderer.

Every post-result placement here is an engineering presentation control.  The
original seven model contexts precede CAS9 completion; these tests do not claim
another historical dispatch, runtime admission, calculation or scientific run.
The public values and admitted forms are authenticated against immutable Stores
before their detached copies are placed in own/received/frozen display slots.
"""

import ast
import builtins
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.decision_context import apply_state_frame, state_frame
from gene_annotation_episode.domain import canonical, identity
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.molecular_result_facts import frozen_molecular_facts, received_molecular_facts
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode import reference_edit_outcomes as core
from gene_annotation_episode import scientific_process_prompt as prompt
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


NATIVE_PREFIX_SHA256 = "5f020578267f6324fa51d76cd71707d687a2c3a4d599d435e02a9c187291a81e"
SAVED_PROOF_SHA256 = "6147d32e9badb72186eadf07bba6fd822b8e228879ba6248075808eca6b5aa02"
TOOL = "analyze_cas9_mutation_outcomes"
SOURCE_VERSION = "ordinary_reference_edit_outcome_result_v1"
QUESTION = (
    "For the supplied engineering reference GACTACGTTGCA and edited GACTTCGTTGCA, "
    "which nucleotide differences are actually observed in their selected global alignment? "
    "Return the retained reference/edit outcome group and its qualifications; keep "
    "observations separate from repair mechanism inference.")


def _pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def _selected_proofs():
    fields = {
        "native": ("HMMER_NATIVE_ORACLE_REFERENCE_EDIT_RETAINED_PREFIX",
            "HMMER_NATIVE_ORACLE_REFERENCE_EDIT_RETAINED_SHA256", NATIVE_PREFIX_SHA256),
        "saved": ("HMMER_NATIVE_ORACLE_REFERENCE_EDIT_SAVED_PROOF",
            "HMMER_NATIVE_ORACLE_REFERENCE_EDIT_SAVED_SHA256", SAVED_PROOF_SHA256),
    }
    if "HMMER529_ATTEMPT" not in os.environ or any(not os.environ.get(key)
            for path_key, sha_key, _ in fields.values() for key in (path_key, sha_key)):
        pytest.skip("requires explicitly pinned successful399 and400 proof/support trees")
    result = {}
    for name, (path_key, sha_key, expected) in fields.items():
        path = Path(os.environ[path_key]).resolve(strict=True)
        assert os.environ[sha_key] == expected and _pin(path)["sha256"] == expected
        result[name] = dict(path=path, pin=_pin(path), proof=json.loads(path.read_text()))
    native, saved = (result[name]["proof"] for name in ("native", "saved"))
    assert native["version"] == "reference_edit_public_workflow_prefix_v1" and native["passed"] is True
    assert native["native_execution_verified"] is True and native["native_call_count"] == 1
    assert native["question"] == QUESTION
    assert saved["version"] == "reference_edit_public_saved_proof_v1" and saved["passed"] is True
    assert saved["retained_prefix"]["sha256"] == NATIVE_PREFIX_SHA256
    assert saved["original_database"] == native["database_file"]
    assert saved["new_native_call_state"] == "not_requested"
    assert saved["explicit_saved_calculator_events"] == ["call", "return"]
    assert saved["original_records_unchanged"] is saved["original_native_and_model_work_unchanged"] is True
    return result


def _guards(patch, artifact_roots, attempts):
    """Deny scientific and model work; permit selected proof/SQLite reads only."""
    def forbidden(*args, **kwargs):
        attempts.append("scientific_or_model_entry")
        raise AssertionError("CAS9 presentation attempted scientific work, model dispatch or a File read")
    patch.setattr(Store, "get_artifact", forbidden)
    for name in ("complete", "_rpc", "_session"):
        patch.setattr(_SessionConnection, name, forbidden)
    for name in ("execute", "execute_async", "_execute_operation_async", "_sequence_worker_async", "_prepare_alignment_async", "_sequence"):
        patch.setattr(ToolRegistry, name, forbidden)
    for name in ("calculate_reference_edit_outcome_components", "populate_reference_edit_outcome_sheet"):
        patch.setattr(core, name, forbidden)
    patch.setattr("gene_annotation_episode.sequence_ops.align_pair", forbidden)
    for name in ("prepare_job", "start_prepared", "resume_start", "wait_job", "collect", "status", "cancel", "release"):
        patch.setattr("gene_annotation_episode.native_lifecycle." + name, forbidden)
    patch.setattr("gene_annotation_episode.materials._verified_artifact_path", forbidden)
    patch.setattr("gene_annotation_episode.native_file_capture._verified_artifact_path", forbidden)
    patch.setattr("gene_annotation_episode.acquisition.PublicClients._http", forbidden)
    patch.setattr("socket.create_connection", forbidden)
    actual_open, actual_path_open = builtins.open, Path.open
    def check(file):
        if isinstance(file, (str, bytes, os.PathLike)):
            candidate = Path(os.fsdecode(file)).absolute()
            if any(candidate.is_relative_to(root) for root in artifact_roots):
                attempts.append("direct_scientific_File")
                raise AssertionError("CAS9 presentation attempted a direct retained scientific File read")
    def open_file(file, *args, **kwargs):
        check(file)
        return actual_open(file, *args, **kwargs)
    def open_path(file, *args, **kwargs):
        check(file)
        return actual_path_open(file, *args, **kwargs)
    patch.setattr(builtins, "open", open_file)
    patch.setattr(Path, "open", open_path)


def _immutable_store(database):
    assert _pin(database["path"]) == database
    assert not Path(database["path"] + "-wal").exists()
    store = Store.__new__(Store)
    store.path = Path(database["path"]).parent
    store.db = sqlite3.connect(Path(database["path"]).as_uri() + "?mode=ro&immutable=1", uri=True)
    store.db.row_factory = sqlite3.Row
    store._savepoint = 0
    store.db.create_function("library_scope_record", 2, store._scope_filter_record)
    return store


def _receipts(store):
    return [tuple(row) for row in store.db.execute("SELECT * FROM runtime_record_receipts ORDER BY rowid")]


def _authenticate_phase(store, phase):
    """Join literal public values to the actual action, Source and admitted form."""
    run_id = phase["run_id"]
    records = EpisodeReturnRecords(store, run_id, failure_prefix="reference_edit_presentation_")
    episodes = list(store.db.execute("SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY json_array_length(path)", (run_id,)))
    assert len(episodes) == 2
    parent, child = [records.context(row[0]) for row in episodes]
    operation = store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (phase["operation"]["operation_key"],)).fetchone()
    assert dict(operation) == phase["operation"] and operation["name"] == TOOL
    arguments, outcome = json.loads(operation["arguments"]), json.loads(operation["result"])
    decision_index = 1 if phase["mode"] == "analyze" else 0
    key = f"{run_id}:{child.episode_id}:{decision_index}"
    assert operation["operation_key"] == key and arguments["mode"] == phase["mode"]
    assert operation["scope"] == canonical(plain(child.scope))
    assert operation["id"] == identity("operation", dict(key=key, name=TOOL, arguments=arguments))
    action = store.db.execute("SELECT * FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=?",
        (run_id, child.episode_id, decision_index)).fetchone()
    assert json.loads(action["action"]) == dict(kind="tool", tool=TOOL, arguments=arguments)
    assert EpisodeReturnRecords._equal({key: value for key, value in json.loads(action["result"]).items()
        if key != "pending_work_after_action"}, outcome)
    public = core.validate_reference_edit_outcome_return(phase["public"])
    assert public == outcome["result"] and outcome["record_refs"] == [public["source_ref"]]
    source = store.get(public["source_ref"])
    payload = {key: value for key, value in source.items() if key not in ("id", "origin", "record_type")}
    assert source["id"] == identity("source", dict(origin=source["origin"], record=payload))
    assert source == phase["source"] and source["provider"] == TOOL and source["version"] == SOURCE_VERSION
    frozen = frozen_molecular_facts(store, run_id, child, fact_source="reference_edit_outcomes")
    assert frozen == received_molecular_facts(store, run_id, parent, fact_source="reference_edit_outcomes") == [public]
    _, form, _ = records._attempt(parent, 0)
    assert form == phase["returned"] == dict(outcomes=[public])
    calls = [dict(row) for row in store.db.execute("SELECT * FROM runtime_model_calls WHERE run_id=? ORDER BY rowid", (run_id,))]
    assert len(calls) == len(phase["provider_dispatches"]) == (3 if phase["mode"] == "analyze" else 2)
    contexts = []
    for row, dispatch, retained_context in zip(calls, phase["provider_dispatches"], phase["provider_contexts"]):
        context = json.loads(row["request"])["context"]
        assert context == retained_context and row["episode_id"] == dispatch["episode_id"]
        assert json.loads(row["response"]) == dispatch["response"]
        assert context["goal"]["objective"] == context["goal"]["task_context"]["root_objective"] == QUESTION
        assert context["child_reports"] == []
        assert (context.get("last_local_outcome") or {}).get("result", {}).get("version") != core.RETURN_VERSION
        assert core.RETURN_VERSION not in dispatch["rendered"]
        contexts.append(context)
    # Use the actual first child context, before alignment/saved work.  The
    # detached later placements below are engineering inputs, not fabricated
    # historical contexts or additions to the immutable model-call table.
    assert contexts[1]["last_local_outcome"] is None
    assert contexts[1]["scientific_process"]["selection"]["evidence_axis"]["option_id"] == "A101"
    assert contexts[1]["scientific_process"]["selection"]["thought_pattern"]["option_id"] == "P01"
    return dict(public=public, outcome=outcome, form=form, frozen=frozen,
        source=source, parent_context=contexts[0], child_context=contexts[1],
        parent_instructions=phase["provider_dispatches"][0]["instructions"],
        child_instructions=phase["provider_dispatches"][1]["instructions"],
        original_episode_ids=[parent.episode_id, child.episode_id], original_operation_key=key,
        original_operation_ref=operation["id"])


@pytest.fixture(scope="module")
def retained_values():
    proofs = _selected_proofs()
    stores = {name: _immutable_store(selected["proof"]["database_file"]) for name, selected in proofs.items()}
    before = {name: _receipts(store) for name, store in stores.items()}
    attempts = []
    roots = [store.path / "artifacts" for store in stores.values()]
    try:
        with pytest.MonkeyPatch.context() as patch:
            _guards(patch, roots, attempts)
            native = proofs["native"]["proof"]
            saved = proofs["saved"]["proof"]
            selected = [_authenticate_phase(stores["native"], native),
                *[_authenticate_phase(stores["saved"], phase) for phase in saved["phases"]]]
            assert [phase["mode"] for phase in saved["phases"]] == ["read_stored", "calculate_saved"]
            assert selected[0]["public"] == selected[1]["public"]
            assert selected[2]["public"]["source_ref"] != selected[0]["public"]["source_ref"]
            assert selected[2]["source"]["parent_source_refs"] == [selected[0]["public"]["source_ref"]]
            forbidden_literals = {selected_proof["pin"]["sha256"] for selected_proof in proofs.values()}
            forbidden_literals.update(selected_proof["proof"]["database_file"]["sha256"] for selected_proof in proofs.values())
            forbidden_literals.add(native["native_handles"][0]["prepared"]["unit"])
            for item in selected:
                forbidden_literals.update([*item["original_episode_ids"], item["original_operation_key"], item["original_operation_ref"],
                    item["source"]["artifact_ref"], item["source"]["request_ref"], *item["source"]["auxiliary_artifact_refs"]])
            yield dict(selected=selected, attempts=attempts, forbidden_literals=forbidden_literals)
            assert attempts == []
            for name, store in stores.items():
                assert store.db.total_changes == 0 and _receipts(store) == before[name]
                assert _pin(proofs[name]["proof"]["database_file"]["path"]) == proofs[name]["proof"]["database_file"]
                assert _pin(proofs[name]["path"]) == proofs[name]["pin"]
    finally:
        for store in stores.values():
            store.db.close()


def _connection():
    connection = object.__new__(_SessionConnection)
    connection.scientific_prompt_states = {}
    return connection


def _engineering_placement(selected, carrier):
    receiving = carrier == "received"
    base = deepcopy(selected["parent_context" if receiving else "child_context"])
    state = deepcopy(base)
    if carrier == "own":
        state["last_local_outcome"] = deepcopy(selected["outcome"])
        lookup = deepcopy(selected["outcome"])
    elif receiving:
        state["child_reports"] = [deepcopy(selected["form"])]
        lookup = dict(status="completed", result=dict(admitted_child_return=deepcopy(selected["form"])))
    else:
        # An authenticated frozen form in a detached display slot; not a new
        # interpretation, receipt grant, report update or runtime action.
        state["current_report_update"] = deepcopy(selected["form"])
        lookup = dict(status="completed", result=dict(frozen_return=deepcopy(selected["form"])))
    instructions = selected["parent_instructions" if receiving else "child_instructions"]
    return base, state, lookup, instructions


def _leaf_items(value, path=()):
    """Enumerate typed public JSON leaves independently of the renderer."""
    if type(value) is dict and value:
        for name, child in value.items():
            yield from _leaf_items(child, (*path, name))
    elif type(value) is list and value:
        for index, child in enumerate(value):
            yield from _leaf_items(child, (*path, index))
    else:
        yield path, value


def _field_path(prefix, segments):
    result = prefix
    for segment in segments:
        result += "[" + str(segment) + "]" if type(segment) is int else "." + segment
    return result


def _literal_cell(value):
    if value == [] and type(value) is list:
        return "empty array"
    if value == {} and type(value) is dict:
        return "empty object"
    if value is None:
        return "null"
    if type(value) is bool:
        return "true" if value else "false"
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _displayed_group(text, prefix):
    rows = []
    for line in text.splitlines():
        if line.startswith("| ") and line.endswith(" |"):
            cells = line[2:-2].split(" | ")
            if len(cells) == 2 and cells[0].startswith(prefix + "."):
                rows.append(tuple(cells))
    return rows


def _assert_scientific_meanings(public, phase):
    """Assert recorded values and their meanings, without deriving new values."""
    pair, = public["pairs"]
    assert public["alignment_unit"] == "nt" and public["coordinate_system"] == "zero_based_half_open_local_operands"
    assert pair["coverage_scope"] == "full_global" and pair["full_global_pair"] is True
    assert pair["observed_change_types"] == ["substitution"] and pair["whole_pair_type"] == "substitution_only"
    assert pair["native"]["molecule"] == "dna" and pair["native"]["mode"] == "global"
    assert pair["native"]["score"] == 21.0 and type(pair["native"]["score"]) is float
    assert pair["native"]["score_unit"] == "native_alignment_score" and pair["native"]["version"] == "1.88"
    assert pair["native"]["parameters"] == dict(matrix="match_2_mismatch_minus_1", gap_open=-10.0, gap_extend=-0.5)
    assert pair["counts"] == dict(alignment_columns=12, paired_positions=12, identical_positions=11,
        substituted_positions=1, query_gap_columns=0, reference_gap_columns=0,
        query_aligned_positions=12, reference_aligned_positions=12)
    event, = pair["events"]
    assert event["kind"] == "substitution" and event["event_ordinal"] == 0
    assert event["reference_sequence"] == "A" and event["query_sequence"] == "T"
    assert event["alignment_column_interval"] == event["reference_interval"] == event["query_interval"] == [4, 5]
    assert event["reference_boundary"] is None
    for role, subject in (("reference", pair["reference_ref"]), ("query", pair["edited_ref"])):
        assert event[role + "_mapping"] == dict(status="available", reason=None,
            intervals=[dict(subject_ref=subject, start=4, end=5, unit="nt", strand="+")])
    for population in [public["populations"]["overall"], public["populations"]["by_reference"][0]["population"],
            public["populations"]["by_group"][0]["population"]]:
        assert population["declared_pair_count"] == population["classified_pair_count"] == 1
        assert population["unclassified_pair_count"] == population["not_selected_pair_count"] == 0
        assert [category["kind"] for category in population["categories"]] == [
            "unchanged", "substitution_only", "insertion_only", "deletion_only", "mixed"]
        assert [category["count"] for category in population["categories"]] == [0, 1, 0, 0, 0]
        for category in population["categories"]:
            assert category["fraction_of_classified"] == category["observed_fraction_of_declared"]
            assert category["fraction_of_classified"]["denominator"] == 1
            assert category["fraction_of_classified"]["unit"] == "fraction"
    assert public["guide_comparisons"] == public["template_comparisons"] == []
    assert public["issue_codes"] == pair["issue_codes"] == []
    if phase == 2:
        assert public["gap_bins"] == dict(deletion_upper_bounds_nt=[1, 4], insertion_upper_bounds_nt=[2, 5])
        # Known zero gaps do not become a missing count or an invented bin.
        assert pair["gap_bins"] == dict(deletion=None, insertion=None)
    else:
        assert public["gap_bins"] is pair["gap_bins"] is None


@pytest.mark.parametrize("phase", [0, 1, 2], ids=["original399", "literal_stored400", "derived_saved400"])
@pytest.mark.parametrize("carrier", ["own", "received", "frozen"])
@pytest.mark.parametrize("transport", ["full", "bootstrap", "update", "lookup"])
def test_actual_session_renderer_preserves_authenticated_reference_edit_leaves_without_dispatch(
        retained_values, phase, carrier, transport):
    selected = retained_values["selected"][phase]
    base, state, lookup, instructions = _engineering_placement(selected, carrier)
    before = canonical(dict(base=base, state=state, lookup=lookup, selected=selected))
    connection, episode = _connection(), "engineering-post-result-reference-edit"
    if transport == "full":
        supplied = state
    elif transport == "bootstrap":
        supplied = state_frame(state)
        assert apply_state_frame(None, supplied) == state
    else:
        connection._presentation(episode, "REASONING", instructions, state_frame(base))
        supplied = state_frame(state, base) if transport == "update" else dict(version="decision_context_v1",
            kind="decision_lookup_result", decision_index=1, exchange_index=0, result=lookup)
        if transport == "update":
            assert apply_state_frame(base, supplied) == state
    supplied_before = canonical(supplied)
    text, wire_instructions = connection._presentation(episode, "REASONING", instructions, supplied)
    public = selected["public"]
    assert text.startswith("TASK\n") and "STEERING" in text and QUESTION in text
    assert wire_instructions == prompt.text_instructions(instructions)
    if carrier == "own":
        prefix = "result"
    elif transport == "lookup":
        prefix = "result.admitted_child_return.outcomes[0]" if carrier == "received" else "result.frozen_return.outcomes[0]"
    else:
        prefix = "[0].outcomes[0]" if carrier == "received" else "outcomes[0]"
    expected = [(_field_path(prefix, path), _literal_cell(value)) for path, value in _leaf_items(public)]
    assert len(expected) == (268 if phase == 2 else 264)
    assert _displayed_group(text, prefix) == expected
    _assert_scientific_meanings(public, phase)
    # Only real scientific provenance remains visible. Private File operands,
    # native service/DB/proof hashes and original runtime tracking do not appear.
    for literal in retained_values["forbidden_literals"]:
        assert literal not in text
    assert public["source_ref"] in text and public["pairs"][0]["source_ref"] in text
    assert "guide_comparisons | empty array |" in text and "template_comparisons | empty array |" in text
    assert "reference_boundary | null |" in text and "query_gap_columns | 0 |" in text
    assert "score | 21.0 |" in text and "score_unit | native_alignment_score |" in text
    assert canonical(supplied) == supplied_before
    assert canonical(dict(base=base, state=state, lookup=lookup, selected=selected)) == before
    assert retained_values["attempts"] == []


def test_reference_edit_typed_provenance_has_one_semantic_source_and_no_file_namespace(retained_values):
    """A rendering supplies neither an Artifact operand nor a receipt grant."""
    def declarations(node, path=()):
        if isinstance(node, dict):
            if "x-reference-namespace" in node:
                yield path, node["x-reference-namespace"]
            for name, child in node.items():
                yield from declarations(child, (*path, name))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                yield from declarations(child, (*path, index))
    assert list(declarations(core.RETURN_SCHEMA)) == [(('properties', 'source_ref'), 'source')]
    for selected in retained_values["selected"]:
        public = selected["public"]
        assert all("artifact_" not in value for _, value in _leaf_items(public) if type(value) is str)
        assert set(selected["source"]) >= {"artifact_ref", "request_ref", "auxiliary_artifact_refs"}
        assert selected["source"]["artifact_ref"] not in canonical(public)
    assert retained_values["attempts"] == []


def test_approved_reference_edit_task_and_steering_units_are_unchanged():
    source = Path(prompt.__file__).read_text()
    tree = ast.parse(source)
    pins = dict(_task="6367b05d39fd7d5c58b94b36e2714823130e28408f3b205f44c2d4b32d913e8b",
        _steering="286cc38ec22fe2a7f2c1bd3c05c0a3ddf5a332c4f127407b630ae3fb97c1f9f1")
    for name, expected in pins.items():
        unit = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        assert hashlib.sha256(ast.get_source_segment(source, unit).encode()).hexdigest() == expected
