"""V3 value reuse and live custody checks, only in bounded529.

Copy the completed675 engineering Store and receipts. No original acquisition,
worker, parser, helper or service runs. Its physical-target and capture ports
remain explicitly controlled, exactly as in675; all validators under test run.
"""
from contextlib import contextmanager
from contextvars import copy_context
from copy import deepcopy
import ast
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import shutil
from types import MethodType, SimpleNamespace

import pytest

from gene_annotation_episode import form_reference_validation as frames
from gene_annotation_episode import native_blast_utility_contracts as contracts
from gene_annotation_episode import native_blast_utility_results as results
from gene_annotation_episode import native_blast_utility_result_publication as publication
from gene_annotation_episode import native_blast_utility_result_worker as worker
from gene_annotation_episode import blast_utility_result_views as views
from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_blast_utility_acquisition import _validate_saved
from gene_annotation_episode.native_blast_utility_returns import NativeBLASTUtilityReturns
from gene_annotation_episode.practical_execution_state import _immutable
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading
from test_blast_utility_episode_wiring_632 import context
from test_native_blast_utility_producer_628 import job_fixture
from test_native_blast_preparation_649 import preparation_job
from test_result_validation_cost_675 import _profile


BASELINE = Path("verification/tool_graders_hmmer_map_verification_2026-10-28_529/check133_result_validation675")
CASE = BASELINE / "temporary/pytest/test_one_retained_case_profile0"
NAMESPACE = "native_blast_utility_contracts.validate_native_blast_utility_job.v1"
UNCACHED = "_validate_native_blast_utility_job"


def _save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _count(call):
    profile = cProfile.Profile()
    result = profile.runcall(call)
    count = sum(row[1] for key, row in pstats.Stats(profile).stats.items()
        if key[0] == contracts.__file__ and key[2] == UNCACHED)
    return result, count


def _answer(value, *, uncached=False):
    try:
        checked = (contracts._validate_native_blast_utility_job(contracts.finite_json_copy(value))
            if uncached else contracts.validate_native_blast_utility_job(value))
        return {"value": canonical(checked)}
    except ValueError as error:
        return {"exception": type(error).__name__, "message": str(error)}


@contextmanager
def _memo(monkeypatch, enabled):
    """Disable only the new pure-value boundary; every validator still runs."""
    original = frames.form_validation_value
    def selected(key, produce):
        return produce() if key[0] == NAMESPACE else original(key, produce)
    with monkeypatch.context() as patch:
        if not enabled:
            patch.setattr(frames, "form_validation_value", selected)
        yield


def _forbidden(*args, **kwargs):
    pytest.fail("retained676 attempted acquisition, native work or result preparation")


@pytest.fixture
def retained(tmp_path, monkeypatch):
    attempt = Path(os.environ["HMMER529_ATTEMPT"])
    selected = json.loads((attempt / "selected_request.json").read_text())
    assert selected["policy"] == {"memory_bytes": 21474836480,
        "scratch_bytes": 4294967296, "wall_seconds": None}
    assert selected["swap_bytes"] == 0
    root = Path(__file__).resolve().parents[1]
    case = json.loads((root / BASELINE / "profile675/selected_case.json").read_text())
    equality = json.loads((root / BASELINE / "profile675/equality_and_inputs.json").read_text())
    for name in ("store", "run"):
        shutil.copytree(root / CASE / name, tmp_path / name, copy_function=shutil.copyfile)
        for path in [tmp_path / name, *(tmp_path / name).rglob("*")]:
            path.chmod(0o700 if path.is_dir() else 0o600)
    store = Store(tmp_path / "store")
    body = case["body"]
    target = deepcopy(body["target"])
    owner = SimpleNamespace(store=store, directory=tmp_path / "run", run_id=body["run_id"],
        resources={"local": {"policy": deepcopy(selected["policy"])}}, acquired_record_unit=2, handoff_unit=3)
    owner._target = lambda ctx: deepcopy(target)
    owner._selected_result_action = MethodType(ExecutionEpisodes._selected_result_action, owner)
    owner._result_directory = MethodType(ExecutionEpisodes._result_directory, owner)
    owner.job_progress_provider = SimpleNamespace(targets=SimpleNamespace(
        read_target=lambda reference, scope: deepcopy(target), observe_target=_forbidden))
    owner.native_blast_utility_results = results.NativeBLASTUtilityResults(owner)
    owner.native_blast_utility_returns = reader = NativeBLASTUtilityReturns(owner)
    def saved_capture(store, *, target, directory):
        return _validate_saved(store, json.loads((directory / "capture.json").read_text()))
    monkeypatch.setattr(results, "capture_local_utility_bundle", saved_capture)
    monkeypatch.setattr(results, "prepare_native_blast_utility_result", _forbidden)
    monkeypatch.setattr(publication, "run_local_job", _forbidden)
    monkeypatch.setattr(publication, "_execute_worker", _forbidden)
    monkeypatch.setattr(worker, "run", _forbidden)
    monkeypatch.setattr(worker, "_parse_original", _forbidden)
    monkeypatch.setattr(worker, "_project_saved", _forbidden)
    h = SimpleNamespace(store=store, family=owner, provider=owner.native_blast_utility_results,
        reader=reader, body=body, target=target, scope=body["scope"], schema=case["schema"],
        form=equality["form"], assignment=case["assignment"],
        parent=reader.context(case["parent_context"]["episode_id"]),
        child=reader.context(case["child_context"]["episode_id"]),
        journal=Journal(store, body["run_id"]), receipts=EpisodeReceipts(store, body["run_id"]),
        tmp_path=tmp_path, attempt=attempt)
    h.job = body["capture"]["plan"]["requested_job"]["native_blast_utility"]
    h.directory = h.provider._saved_directory(body["episode_id"], body["operation_key"])
    h.admission_key = f"{h.parent.run_id}:{h.parent.episode_id}:0:typed_form"
    try:
        yield h
    finally:
        store.close()


def test_pure_reuse_detaches_inputs_and_returns_and_runs_finite_admission(retained):
    job = retained.job
    original = _answer(job, uncached=True)
    def run():
        with frames.form_reference_validation():
            supplied = deepcopy(job)
            first = contracts.validate_native_blast_utility_job(supplied)
            first["operation"]["parameters"]["selection"]["selectors"][0]["value"] = "poison"
            supplied["software"]["engine_version"] = "changed by caller"
            assert _answer(deepcopy(job)) == original
            assert _answer(supplied) == _answer(supplied, uncached=True)
            # Warm a valid value, then reject non-finite and non-JSON values
            # before the memo producer, on every public call.
            for invalid in (float("nan"), float("inf"), object(), (1,)):
                candidate = deepcopy(job)
                candidate["software"]["engine_version"] = invalid
                assert _answer(candidate) == {"exception": "ValueError", "message": "native_blast_finite_json_required"}
    _, count = _count(run)
    assert count == 3  # Two distinct memo misses plus one explicit oracle call.


def test_full_content_keys_typed_values_lists_and_invalid_errors(retained, monkeypatch):
    job = retained.job
    mutations = [
        lambda v: v["inputs"][0].update(sha256="a" * 64),
        lambda v: v["inputs"][0].update(path="/other/selected-list.txt"),
        lambda v: v["outputs"].reverse(),
        lambda v: v["vdb_context_request"]["source_inputs"][0]["snapshot"].update(release="different"),
        lambda v: v["offline_execution"]["launcher"].update(sha256="b" * 64),
        lambda v: v["offline_execution"]["runtime_files"][0].update(sha256="b" * 64),
        lambda v: v["software"].update(engine_version="different"),
    ]
    candidates = [deepcopy(job) for _ in mutations]
    for mutation, value in zip(mutations, candidates):
        mutation(value)
    for number in (True, 1, 1.0):
        value = deepcopy(job)
        value["operation"]["parameters"]["line_length"] = number
        candidates.append(value)
    for version in (None, [], {}, "other"):
        candidates.append(version)
    keys, original_helper = [], frames.form_validation_value
    def observe_key(key, produce):
        if key[0] == NAMESPACE:
            keys.append(key)
            assert key[1] == json.dumps(json.loads(key[1]), sort_keys=True,
                separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        return original_helper(key, produce)
    monkeypatch.setattr(frames, "form_validation_value", observe_key)
    expected = [_answer(v, uncached=True) for v in candidates]
    with frames.form_reference_validation():
        assert _answer(job) == _answer(job, uncached=True)
        actual = [_answer(v) for v in candidates]
    assert actual == expected
    assert len(set(keys)) == 11
    assert len({key[1] for key in keys[-3:]}) == 3
    invalid = deepcopy(job)
    invalid["operation"]["parameters"]["selection"]["selectors"][0]["value"] = "all"
    def repeated_failure():
        with frames.form_reference_validation():
            return [_answer(invalid), _answer(deepcopy(invalid))]
    answers, count = _count(repeated_failure)
    assert answers == [_answer(invalid, uncached=True)] * 2 and count == 2


def test_separate_nested_and_inactive_copied_frames(retained):
    job = retained.job
    def run():
        check = lambda: contracts.validate_native_blast_utility_job(deepcopy(job))
        check(); check()
        with frames.form_reference_validation():
            outer = frames._current.get()
            check(); check()
            with frames.form_reference_validation():
                inner = frames._current.get()
                assert inner is not outer
                check(); check()
            assert not inner.active and inner.values == {} and frames._current.get() is outer
            check()
            copied = copy_context()
        assert not outer.active and outer.values == {}
        copied.run(check); copied.run(check)
        with frames.form_reference_validation():
            check(); check()
    _, count = _count(run)
    assert count == 7


@pytest.mark.parametrize("version", [1, 2])
def test_legacy_jobs_remain_uncached_with_identical_values_and_errors(tmp_path, version):
    job = job_fixture(tmp_path) if version == 1 else preparation_job(tmp_path, "inspect_seqid_list")
    expected = _answer(job, uncached=True)
    assert "value" in expected
    def run():
        with frames.form_reference_validation():
            return [_answer(job), _answer(deepcopy(job))]
    actual, count = _count(run)
    assert actual == [expected, expected] and count == 2
    invalid = deepcopy(job)
    invalid["outputs"][0]["relative_path"] = "../escape"
    assert _answer(invalid) == _answer(invalid, uncached=True)


def test_same_retained_case_full_body_facts_admission_and_resolution_profile(retained, monkeypatch):
    h = retained
    evidence = h.attempt / "validation676"
    evidence.mkdir(exist_ok=False)
    before = {table: h.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]
        for table in ("artifacts", "runtime_actions", "runtime_observations", "runtime_report_attempts")}
    phases = {
        "saved_body": lambda: h.provider._validate_body(h.body, h.scope),
        "own_facts": lambda: h.provider.facts(h.child),
        "child_report": lambda: h.reader.validate_received_report(h.child, h.form, h.schema),
        "parent_admission": lambda: h.reader.record_admission(h.parent, h.form, h.schema, h.admission_key),
    }
    def received():
        with frames.form_reference_validation():
            h.reader.validate_received_report(h.parent, h.form, h.schema)
            rows = [[namespace, ref, h.reader.resolve_received(h.parent, ref, namespace)]
                for namespace in views.IDENTIFIER_NAMESPACES
                for ref in views.projection_identifiers(h.body, namespace)]
            rows += [["execution_result", ref, h.reader.resolve_received(h.parent, ref, "execution_result")]
                for ref in h.body["record_refs"]]
            return rows
    phases["received_report_and_references"] = received
    answers, measured = {}, []
    for enabled in (False, True):
        with _memo(monkeypatch, enabled):
            for name, call in phases.items():
                phase = ("enabled_" if enabled else "disabled_") + name
                value = _profile(evidence, phase, call)
                if not enabled:
                    answers[name] = value
                else:
                    assert canonical(value) == canonical(answers[name])
                summary = json.loads((evidence / (phase + ".summary.json")).read_text())
                rows = json.loads((evidence / (phase + ".calls.json")).read_text())
                counts = {function: sum(row["total_calls"] for row in rows if row["function"] == function)
                    for function in (UNCACHED, "validate_native_blast_utility_job", "_validate_body",
                        "_retained", "_validate_saved", "validate_prepared_utility_result",
                        "validate_utility_publication", "validate_vdb_context_authentication", "_received")}
                measured.append({"phase": name, "memo_enabled": enabled,
                    **{key: summary[key] for key in ("elapsed_seconds", "process_seconds", "total_calls")},
                    "counts": counts})
    for name in phases:
        old, new = [row for row in measured if row["phase"] == name]
        assert old["counts"][UNCACHED] == old["counts"]["validate_native_blast_utility_job"]
        assert new["counts"][UNCACHED] == new["counts"]["_validate_body"] == 1
        assert new["counts"]["validate_native_blast_utility_job"] == old["counts"]["validate_native_blast_utility_job"]
        for function in ("_retained", "_validate_saved", "validate_prepared_utility_result",
                         "validate_utility_publication", "validate_vdb_context_authentication", "_received"):
            assert new["counts"][function] == old["counts"][function]
    assert answers["saved_body"] == h.body
    assert form_with_facts({}, h.schema, answers["own_facts"]) == h.form
    assert answers["parent_admission"] == h.body["record_refs"]
    assert all(row[2] is True for row in answers["received_report_and_references"])
    assert h.form["sequences"][0]["fields"] == {"returned_symbol_count": 4}
    assert h.form["sequences"][0]["sequences"] == {"normalized_sequence": "ACGT"}
    assert "vdb_identity" not in h.form["sequences"][0]
    assert before == {table: h.store.db.execute("SELECT count(*) FROM " + table).fetchone()[0] for table in before}
    _save(evidence / "comparison.json", {"measurements": measured, "record_counts_before_and_after": before,
        "original675_case_reused": True, "acquisitions": 0, "observations": 0, "worker_calls": 0,
        "native_helper_executed": False, "projection_fact_form_equality": True,
        "normalized_sequence": "ACGT", "returned_symbol_count": 4,
        "explicit_reference_decisions": answers["received_report_and_references"]})


@pytest.mark.parametrize("mutation", ["artifact_bytes", "scope", "action", "assignment",
    "intent", "observation", "target", "plan_identity", "proof_pointer", "proof_list",
    "frozen_projection", "commission", "schema", "returned_artifact"])
def test_warm_job_keeps_current_custody_rejections_identical(retained, monkeypatch, mutation):
    h = retained
    original_files, original_sql = {}, []
    def change_file(path, raw):
        original_files[path] = path.read_bytes()
        path.write_bytes(raw)
    def change_sql(table, column, episode, value, *, parent=False):
        field = "parent_episode_id" if parent else "episode_id"
        where = f"run_id=? AND {field}=?"
        args = (h.child.run_id, episode)
        old = h.store.db.execute(f"SELECT {column} FROM {table} WHERE {where}", args).fetchone()[0]
        original_sql.append((f"UPDATE {table} SET {column}=? WHERE {where}", (old, *args)))
        h.store.db.execute(f"UPDATE {table} SET {column}=? WHERE {where}", (canonical(value), *args))
    call = lambda: h.provider._validate_body(h.body, h.scope)
    before = canonical(h.body)
    if mutation == "artifact_bytes":
        ref = h.body["artifacts"][0]["artifact_ref"]
        sha = ref.removeprefix("artifact_")
        path = h.store.path / "artifacts" / sha[:2] / sha
        original_files[path] = path.read_bytes()
        mutate = lambda: path.write_bytes(b"changed bytes under original ID")
    elif mutation == "scope":
        narrow = h.store.validate_scope({"subject_refs": h.scope["subject_refs"], "segments": [
            {"target_ref": h.scope["subject_refs"][0], "start": 0, "end": 1, "unit": "nt"}]})
        call = lambda: h.provider._validate_body(h.body, narrow)
        mutate = lambda: None
    elif mutation == "action":
        mutate = lambda: change_sql("runtime_actions", "action", h.child.episode_id,
            {"kind": "tool", "tool": "execution.results.status", "arguments": {}})
    elif mutation == "assignment":
        request = plain(h.child.request)
        request["message"]["episode_assignment"]["selector"]["vdb_context"] = False
        mutate = lambda: change_sql("runtime_episodes", "request", h.child.episode_id, request)
    elif mutation in {"intent", "observation"}:
        path = h.directory / (mutation + ".json")
        value = json.loads(path.read_text())
        value["unexpected"] = True
        mutate = lambda: change_file(path, (canonical(value) + "\n").encode())
    elif mutation == "target":
        mutate = lambda: h.target.update(resource_id="different")
    elif mutation == "plan_identity":
        plan = deepcopy(h.body["capture"]["plan"])
        plan["identity"]["attempt_id"] = "0" * 64
        call = lambda: contracts.validate_native_blast_utility_plan(plan)
        mutate = lambda: None
    elif mutation in {"proof_pointer", "proof_list"}:
        prepared = deepcopy(h.body["prepared"])
        stable = publication._stable(h.store, prepared)
        receipt = publication._json(h.store, stable["worker_receipt_artifact_ref"])
        proof = receipt["manifest"]["context_authentication"]
        if mutation == "proof_pointer":
            proof["provenance"][0]["pointer"] = "/unselected"
        else:
            proof["lists"][0]["entries"][0]["byte_start"] += 1
        stable["worker_receipt_artifact_ref"] = h.store.artifact(canonical(receipt), "application/json")
        prepared["source_grading_artifact_ref"] = retain_tool_grading(h.store,
            provider="episode.execution_result", native_artifact_ref=prepared["bundle_artifact_ref"], grading=stable)
        call = lambda: publication.validate_prepared_utility_result(h.store, prepared)
        mutate = lambda: None
    elif mutation == "frozen_projection":
        value = json.loads((h.directory / "publication.json").read_text())
        value["sequences"][0]["fields"]["returned_symbol_count"] = 5
        mutate = lambda: change_file(h.directory / "publication.json", (canonical(value) + "\n").encode())
    elif mutation in {"commission", "schema"}:
        row = h.store.db.execute("SELECT action FROM runtime_actions WHERE episode_id=?", (h.parent.episode_id,)).fetchone()
        action = json.loads(row[0])
        if mutation == "commission":
            action["assignment"]["selector"]["vdb_context"] = False
        else:
            action["schema_json"] = canonical({"type": "object", "properties": {}, "required": [], "additionalProperties": False})
        mutate = lambda: change_sql("runtime_actions", "action", h.parent.episode_id, action)
        call = lambda: h.reader.record_admission(h.parent, h.form, h.schema, h.admission_key)
    else:
        form = deepcopy(h.form)
        form["artifacts"][0]["artifact_ref"] = h.body["capture"]["bundle_artifact_ref"]
        call = lambda: h.reader.record_admission(h.parent, form, h.schema, h.admission_key)
        mutate = lambda: None
    try:
        answers = []
        for enabled in (False, True):
            with _memo(monkeypatch, enabled), frames.form_reference_validation():
                contracts.validate_native_blast_utility_job(h.job)
                if not enabled:
                    mutate()
                with pytest.raises(ValueError) as error:
                    call()
                answers.append((type(error.value).__name__, str(error.value)))
                assert _answer(h.job) == _answer(h.job, uncached=True)
        assert answers[0] == answers[1]
        semantic_errors = {
            "intent": "native_blast_utility_result_original_intent_conflict",
            "observation": "native_blast_utility_result_observation_conflict",
            "frozen_projection": "native_blast_utility_publication_frozen_values_conflict",
        }
        if mutation in semantic_errors:
            assert answers[0][1] == semantic_errors[mutation]
        with (h.attempt / "tamper676.jsonl").open("a") as stream:
            stream.write(json.dumps({"mutation": mutation, "disabled": answers[0], "enabled": answers[1]}) + "\n")
    finally:
        for path, raw in original_files.items():
            path.write_bytes(raw)
        for sql, args in original_sql:
            h.store.db.execute(sql, args)
        h.target.clear(); h.target.update(deepcopy(h.body["target"]))
    assert canonical(h.body) == before
    assert h.provider._validate_body(h.body, h.scope) == h.body


def test_prepared_bytes_remain_live_within_same_warm_frame(retained, monkeypatch):
    h = retained
    ref = h.body["artifacts"][0]["artifact_ref"]
    sha = ref.removeprefix("artifact_")
    path = h.store.path / "artifacts" / sha[:2] / sha
    raw, errors = path.read_bytes(), []
    try:
        for enabled in (False, True):
            path.write_bytes(raw)
            with _memo(monkeypatch, enabled), frames.form_reference_validation():
                assert publication.validate_prepared_utility_result(h.store, h.body["prepared"]) == h.body["prepared"]
                path.write_bytes(b"tampered retained bytes")
                with pytest.raises(ValueError) as error:
                    publication.validate_prepared_utility_result(h.store, h.body["prepared"])
                errors.append((type(error.value).__name__, str(error.value)))
        assert errors[0] == errors[1]
        assert "capture_artifact_measurement_conflict" in errors[0][1]
    finally:
        path.write_bytes(raw)


def test_each_body_gets_fresh_frame_and_restores_its_outer_frame(retained):
    h = retained
    def run():
        with frames.form_reference_validation():
            outer = frames._current.get()
            contracts.validate_native_blast_utility_job(h.job)
            value = h.provider._validate_body(h.body, h.scope)
            assert frames._current.get() is outer
            value["sequences"][0]["fields"]["returned_symbol_count"] = 99
            assert h.provider._validate_body(h.body, h.scope) == h.body
            assert frames._current.get() is outer
            contracts.validate_native_blast_utility_job(h.job)
        assert not outer.active and outer.values == {}
    _, count = _count(run)
    assert count == 3


def test_original_validator_bodies_and_existing_frame_helper_are_unchanged():
    root = Path(__file__).resolve().parents[1]
    def parsed(path):
        return ast.parse(path.read_text())
    def function(module, name):
        return next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name)
    def dump(body):
        return [ast.dump(node, include_attributes=False) for node in body]
    old = parsed(root / BASELINE / "source_snapshot/gene_annotation_episode/native_blast_utility_contracts.py")
    new = parsed(Path(contracts.__file__))
    assert dump(function(old, "validate_native_blast_utility_job").body[1:]) == dump(
        function(new, UNCACHED).body[1:])
    assert dump(function(old, "validate_native_blast_utility_job").body[:1]) == dump(
        function(new, "validate_native_blast_utility_job").body[:1])
    old = parsed(root / BASELINE / "source_snapshot/gene_annotation_episode/native_blast_utility_results.py")
    new = parsed(Path(results.__file__))
    before = next(node for node in old.body if isinstance(node, ast.ClassDef) and node.name == "NativeBLASTUtilityResults")
    after = next(node for node in new.body if isinstance(node, ast.ClassDef) and node.name == before.name)
    assert dump(function(before, "_validate_body").body) == dump(function(after, "_validate_body_in_frame").body)
    assert hashlib.sha256(Path(frames.__file__).read_bytes()).hexdigest() == "d5185145c1a910ca54566980d0f4286be5a902ce67dc2445bd5b0ae7f57c688a"


def test_forwarded_original_subset_preserves_namespaces_and_no_auxiliary_grants(retained, monkeypatch):
    """Add typed-return engineering records using existing675 result bytes only."""
    h = retained
    science = context(h, "scientific_process", {}, parent=h.parent, index=1, schema=h.schema)
    def commission(parent, child, index):
        h.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
            "action": canonical({"kind": "episode_child", "role": child.role, "scope": h.scope,
                "assignment": plain(child.assignment),
                "schema_json": canonical(child.request["report_contract"]["measurements"]["schema"]),
                "purpose": child.request["report_contract"]["decision"]}), "result": None})
    commission(h.parent, science, 1)
    def freeze_delivery(parent, child, index, facts, form, schema):
        h.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
        h.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
            "decision_index": index, "delivery_ref": "retained676-" + child.episode_id,
            "child_episode_id": child.episode_id, "contract": canonical(child.request["report_contract"]),
            "form": canonical(form), "failure": None})
        key = f"{parent.run_id}:{parent.episode_id}:{index}:typed_form"
        refs = h.reader.record_admission(parent, form, schema, key)
        h.receipts.receive(parent.episode_id, refs, kind="child_form", source_index=index)
        return refs
    def deliver_result(index, schema):
        child = context(h, "results", h.assignment, parent=science, index=index, schema=schema)
        commission(science, child, index)
        body = deepcopy(h.body)
        body.update(episode_id=child.episode_id, operation_key=f"{child.run_id}:{child.episode_id}:0")
        directory = h.provider._saved_directory(child.episode_id, body["operation_key"])
        (directory / "capture").mkdir(parents=True)
        _immutable(directory / "receipt.json", body)
        _immutable(directory / "intent.json", {key: body[key] for key in
            ("target", "assignment", "operation_key", "tool_name", "arguments", "scope")})
        _immutable(directory / "observation.json", body["observation"])
        _immutable(directory / "capture/capture.json", body["capture"])
        shutil.copyfile(h.directory / "publication.json", directory / "publication.json")
        outcome = {"status": "completed", "result": body, "record_refs": body["record_refs"]}
        h.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": 0,
            "action": canonical({"kind": "tool", "tool": body["tool_name"], "arguments": {}}),
            "result": canonical(outcome)})
        h.receipts.receive(child.episode_id, body["record_refs"], kind="own_action", source_index=0)
        facts = h.provider.facts(child)
        form = form_with_facts({}, schema, facts)
        return freeze_delivery(science, child, index, facts, form, schema)
    narrow = deepcopy(h.schema)
    del narrow["properties"]["artifacts"]
    narrow["required"].remove("artifacts")
    assert deliver_result(0, narrow) == [h.body["source_ref"]]
    facts = h.reader.received_facts(science, h.schema)
    frozen = form_with_facts({}, h.schema, facts)
    assert frozen["artifacts"] == []
    assert freeze_delivery(h.parent, science, 1, facts, frozen, h.schema) == [h.body["source_ref"]]
    # Later explicit byte delivery expands current facts but cannot rewrite the
    # older frozen science return or turn a provenance pointer into byte access.
    assert deliver_result(1, h.schema) == h.body["record_refs"]
    stable = publication._stable(h.store, h.body["prepared"])
    proof = publication._json(h.store, stable["worker_receipt_artifact_ref"])["manifest"]["context_authentication"]
    private = proof["documents"][0]["artifact_ref"]
    key = f"{h.parent.run_id}:{h.parent.episode_id}:1:typed_form"
    for enabled in (False, True):
        with _memo(monkeypatch, enabled), frames.form_reference_validation():
            assert h.reader.record_admission(h.parent, frozen, h.schema, key) == [h.body["source_ref"]]
            assert h.reader.received_facts(science, h.schema)["execution.blast_utility_artifacts"]
            for receiver in (science, h.parent):
                assert h.provider.retained_reference_access(receiver, private, "artifact") is False
                assert h.reader.resolve_received_reference_metadata(receiver, h.body["source_ref"], "artifact") is False
                for namespace in views.IDENTIFIER_NAMESPACES:
                    for ref in views.projection_identifiers(h.body, namespace):
                        assert h.reader.resolve_received(receiver, ref, namespace) is True
                        assert h.reader.resolve_received(receiver, ref, "artifact") is not True
    saved = h.store.db.execute("SELECT form FROM runtime_forms WHERE episode_id=?", (science.episode_id,)).fetchone()[0]
    assert json.loads(saved) == frozen and frozen["artifacts"] == []


def test_child_report_profile_with_equal_schema_cache_warmth(retained, monkeypatch):
    """Resolve the first profile's pre-existing cold form-schema cache effect."""
    h = retained
    h.reader.validate_received_report(h.child, h.form, h.schema)
    directory = h.attempt / "report_warm676"
    directory.mkdir()
    rows = []
    for enabled in (False, True):
        name = "enabled" if enabled else "disabled"
        with _memo(monkeypatch, enabled):
            assert _profile(directory, name, lambda: h.reader.validate_received_report(
                h.child, h.form, h.schema)) is None
        summary = json.loads((directory / (name + ".summary.json")).read_text())
        calls = json.loads((directory / (name + ".calls.json")).read_text())
        counts = {key: sum(row["total_calls"] for row in calls if row["function"] == key)
            for key in (UNCACHED, "validate_native_blast_utility_job", "_compiled_schema_content",
                        "_retained", "_validate_saved", "validate_vdb_context_authentication")}
        rows.append({"memo_enabled": enabled,
            **{key: summary[key] for key in ("elapsed_seconds", "process_seconds", "total_calls")}, "counts": counts})
    assert rows[0]["counts"][UNCACHED] == 171 and rows[1]["counts"][UNCACHED] == 1
    for key in rows[0]["counts"].keys() - {UNCACHED}:
        assert rows[0]["counts"][key] == rows[1]["counts"][key]
    assert rows[0]["counts"]["_compiled_schema_content"] == 0
    _save(directory / "comparison.json", rows)
