"""030 synthetic test design; not installed/run until shared ownership release."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, obj
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_experimental_prompt import _values
from gene_annotation_episode.literature_rate_storage import rate_source_cells_schema
from gene_annotation_episode.runtime import ActionFailure, DecisionSource, run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_rate_episode_integration import service_binding
from test_literature_rate_native_integration import parent_reason
from test_literature_rate_native_storage import setup_native_store
from test_runtime import FixtureController, ScriptedProvider


def selected(raw, actual, quote, representation="original"):
    start = raw.index(actual.encode())
    return {"source_ref": "source_synthetic", "representation": representation,
            "start": start, "end": start + len(actual.encode()), "quote": quote}


@pytest.mark.parametrize("actual,quote,first", [
    ("abc", "abd", 2), ("abc", "abcd", 3), ("abcd", "abc", 3),
    ("Δµ", "Δμ", 2), ("é", "ê", 1), ("é", "e\u0301", 0), ("Δ", "Δx", 2),
])
@pytest.mark.parametrize("representation", ["original", "text"])
def test_mismatch_details_are_exact_authorized_selected_bytes(actual, quote, first, representation):
    raw = ("前\n" + actual + "\nnever expose adjacent bytes").encode()
    calls = []
    def read(ref, rep):
        calls.append((ref, rep))
        return {"artifact_ref": "artifact_" + rep, "content": raw}
    sources = _Sources(read)
    witness = selected(raw, actual, quote, representation)
    before = deepcopy(witness)
    with pytest.raises(ExperimentalContractError) as caught:
        sources.witness(witness, "experiment")
    error = caught.value
    assert error.code == "source_quote_mismatch" and error.field == "experiment"
    assert str(error) == "source_quote_mismatch:experiment"
    assert error.args == (str(error),)
    assert error.detail == {
        "kind": "selected_source_span_observation", "source_ref": witness["source_ref"],
        "artifact_ref": "artifact_" + representation, "representation": representation,
        "start": witness["start"], "end": witness["end"],
        "actual_utf8_length": len(actual.encode()), "nominated_utf8_length": len(quote.encode()),
        "first_mismatch_utf8_byte": first, "selected_span_text": actual,
        "selected_span_text_json": json.dumps(actual),
    }
    assert calls == [("source_synthetic", representation)]
    assert witness == before and "adjacent" not in str(error.detail)
    assert sources.cache[("source_synthetic", representation)]["content"] == raw


def test_json_literal_preserves_pipes_markup_control_unicode_and_literal_escapes():
    actual = 'Δé|<span>\tline\r\n\x00 literal \\u007c "quote"'
    raw = actual.encode()
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": raw})
    with pytest.raises(ExperimentalContractError) as caught:
        sources.witness(selected(raw, actual, actual + "x"), "experiment")
    detail = caught.value.detail
    literal = detail["selected_span_text_json"]
    assert detail["selected_span_text"] == actual and json.loads(literal) == actual
    assert all(char not in literal for char in "|<>\t\r\n\x00")
    for token in (r"\u007c", r"\u003c", r"\u003e", r"\t", r"\r", r"\n", r"\u0000"):
        assert token in literal
    assert literal in _values({"detail": detail})


def test_lone_surrogate_nomination_preserves_original_mismatch():
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": b"abc"})
    with pytest.raises(ExperimentalContractError) as caught:
        sources.witness(selected(b"abc", "abc", "ab\ud800"), "experiment")
    assert str(caught.value) == "source_quote_mismatch:experiment"
    assert caught.value.detail["selected_span_text"] == "abc"
    assert caught.value.detail["nominated_utf8_length"] is None
    assert caught.value.detail["first_mismatch_utf8_byte"] is None


def test_exception_detail_is_optional_detached_and_success_return_is_unchanged():
    legacy = ExperimentalContractError("other", "field")
    assert legacy.detail is None and legacy.args == ("other:field",)
    detail = {"nested": {"value": "selected"}}
    rich = ExperimentalContractError("source_quote_mismatch", "field", detail=detail)
    detail["nested"]["value"] = "changed"
    assert rich.detail == {"nested": {"value": "selected"}}
    raw = "前abc".encode()
    witness = selected(raw, "abc", "abc")
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": raw})
    assert sources.witness(witness, "field") == {**witness, "artifact_ref": "artifact_synthetic"}


@pytest.mark.parametrize("raw,start,end,code", [
    (b"abc", 0, 4, "source_span_out_of_bounds"),
    (b"abc", 1, 1, "nonempty_source_span_required"),
    (b"abc", -1, 1, "nonnegative_integer_offset_required"),
    (b"\xffabc", 0, 1, "source_span_utf8_boundary_required"),
    ("éabc".encode(), 1, 2, "source_span_utf8_boundary_required"),
])
def test_other_span_failures_have_no_selected_content(raw, start, end, code):
    sources = _Sources(lambda *_: {"artifact_ref": "artifact_synthetic", "content": raw})
    with pytest.raises(ExperimentalContractError) as caught:
        sources.witness({"source_ref": "source_synthetic", "representation": "original",
            "start": start, "end": end, "quote": "nomination"}, "experiment")
    assert caught.value.code == code and caught.value.detail is None


@pytest.mark.parametrize("code", ["source_unknown", "literature_source_not_received",
    "literature_source_outside_scope", "literature_reading_outside_assigned_source"])
def test_authorization_failure_precedes_content(code):
    def denied(*_):
        raise ContractError(code)
    sources = _Sources(denied)
    with pytest.raises(ContractError) as caught:
        sources.witness(selected(b"abc", "abc", "abd"), "experiment")
    assert str(caught.value) == code and caught.value.detail == {}
    assert sources.cache == {} and sources.references == []


def test_c7_denied_receipt_never_reads_or_attaches_source_content(tmp_path, monkeypatch):
    store, context, args = setup_native_store(tmp_path)
    try:
        _, binding = service_binding(store, context)
        invalid = deepcopy(args)
        invalid["experiment"]["quote"] += "x"
        def forbidden(*_):
            raise AssertionError("denied source must not be read")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        outcome = asyncio.run(binding.execute(replace(context, received_record_refs=()),
            "literature.rate.source.populate", invalid, "unreceived"))
        assert outcome["feedback"] == {"category": "arguments_or_reference",
            "code": "literature_source_not_received", "field": None}
        assert outcome["record_refs"] == [] and outcome["result"] is None
    finally:
        store.close()


@pytest.mark.parametrize("error", [ContractError("other_custody_failure", detail={"unused": "detail"}),
    ExperimentalContractError("other_reader_failure", "experiment", detail={"unused": "detail"})])
def test_c7_other_failures_keep_their_original_feedback_shape(tmp_path, monkeypatch, error):
    store, context, args = setup_native_store(tmp_path)
    try:
        services, binding = service_binding(store, context)
        def fail(*_args):
            raise error
        monkeypatch.setattr(services, "literature_rate_repository", lambda: SimpleNamespace(populate_native=fail))
        outcome = asyncio.run(binding.execute(context, "literature.rate.source.populate", args, "other_failure"))
        assert outcome["feedback"] == {"category": "arguments_or_reference", "code": str(error),
            "field": getattr(error, "field", None)}
    finally:
        store.close()


@pytest.mark.parametrize("failure", ["scope", "ancestry", "representation"])
def test_c7_rejects_custody_before_selected_span_observation(tmp_path, monkeypatch, failure):
    store, context, args = setup_native_store(tmp_path)
    try:
        _, binding = service_binding(store, context)
        invalid = deepcopy(args)
        invalid["experiment"]["quote"] += "x"
        expected = "literature_source_outside_scope"
        if failure == "scope":
            context = replace(context, assignment={**plain(context.assignment), "source_refs": []})
            monkeypatch.setattr(store, "reference_subset", lambda *_: [])
        elif failure == "ancestry":
            artifact = store.artifact(b"unrelated synthetic source", "text/plain")
            unrelated = store.put("source", {"provider": "synthetic_unrelated", "accession": None,
                "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
                "version": None, "retrieved_at": None}, origin="caller")
            root = store.get(args["source_ref"])
            context = replace(context, role="literature_page", assignment={"version": "page_assignment_v1",
                "source_ref": root["id"], "representation": "original", "artifact_ref": root["artifact_ref"],
                "question_context_refs": [], "prior_delivery_refs": []},
                received_record_refs=(*context.received_record_refs, unrelated["id"]))
            invalid["experiment"]["source_ref"] = unrelated["id"]
            expected = "literature_reading_outside_assigned_source"
        else:
            # Native text has no fallback to original; its missing representation
            # is a custody failure before any selected quote comparison.
            original_get = store.get
            def no_text(ref):
                row = original_get(ref)
                if ref == args["source_ref"]:
                    row = {**row, "text_ref": None}
                return row
            monkeypatch.setattr(store, "get", no_text)
            invalid["experiment"]["representation"] = "text"
            expected = "literature_source_representation_unavailable"
        original_read = store.get_artifact
        def forbidden(ref):
            # The root original representation is read before the experiment's
            # deliberately absent text representation in this one case.
            if failure == "representation":
                return original_read(ref)
            raise AssertionError("denied source bytes must not be read")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        outcome = asyncio.run(binding.execute(context, "literature.rate.source.populate", invalid, failure))
        assert outcome["feedback"]["code"] == expected
        assert "selected_span_text" not in str(outcome)
        assert outcome["record_refs"] == [] and outcome["result"] is None
    finally:
        store.close()


def replay_invalid(store, run_id, row):
    journal = Journal(store, run_id)
    def forbidden(*_args, **_kwargs):
        raise AssertionError("saved invalid action must not dispatch or read source")
    workflow = SimpleNamespace(journal=journal, store=store, execution_binding=None,
        execute=forbidden, receive_native_outcome=lambda *_: None)
    source = SimpleNamespace(workflow=workflow, episode_id=row["episode_id"],
        last_outcome=None, last_outcome_index=None)
    before = store.db.total_changes
    with pytest.raises(ActionFailure) as caught:
        asyncio.run(DecisionSource.execute(source, json.loads(row["action"]), row["decision_index"]))
    assert caught.value.feedback == json.loads(row["result"])["feedback"]
    assert journal.row("runtime_actions", row["episode_id"], row["decision_index"]) == dict(row)
    assert store.db.total_changes == before


def test_saved_legacy_failure_is_not_enriched_on_replay(tmp_path, monkeypatch):
    store, context, args = setup_native_store(tmp_path)
    try:
        journal = Journal(store, context.run_id)
        action = {"kind": "tool", "tool": "literature.rate.source.populate", "arguments": args}
        legacy = {"status": "invalid", "record_refs": [], "changed_record_refs": [], "result": None,
            "feedback": {"category": "arguments_or_reference", "code": "source_quote_mismatch:experiment",
                "field": "experiment"}}
        journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": 0,
            "action": json.dumps(action), "result": json.dumps(legacy), "credit": None})
        row = journal.row("runtime_actions", context.episode_id, 0)
        def forbidden(*_args, **_kwargs):
            raise AssertionError("old failure must not be enriched from source")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        replay_invalid(store, context.run_id, row)
        assert "detail" not in json.loads(journal.row("runtime_actions", context.episode_id, 0)["result"])["feedback"]
    finally:
        store.close()


def test_selected_failure_fixture_chosen_repair_typed_return_and_saved_replay(tmp_path, monkeypatch):
    store, context, args = setup_native_store(tmp_path / "state")
    try:
        invalid = deepcopy(args)
        invalid["experiment"]["quote"] += "x"
        original_invalid = deepcopy(invalid)
        components = ["rate_difference", "difference_se"]
        form = obj({"native_results": rate_source_cells_schema()})
        assignment = {**plain(context.assignment), "requested_rate_components": components}
        def work(arguments):
            return {"selection": {"kind": "tool", "tool": "literature.rate.source.populate",
                "arguments": arguments}, "report_update": {}}
        seen = []
        def fixture_chooses_repair(inputs):
            feedback = inputs["feedback"]
            assert feedback["code"] == "source_quote_mismatch:experiment"
            assert inputs["last_local_outcome"]["feedback"] == feedback
            assert feedback["detail"]["selected_span_text"] == args["experiment"]["quote"]
            assert invalid == original_invalid
            assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 0
            assert store.db.execute("select count(*) from runtime_observations").fetchone()[0] == 0
            seen.append(feedback)
            # This predetermined fixture response owns the exact repair. The
            # reader never returns replacement arguments or selects this work.
            return work(deepcopy(args))
        def receive(inputs):
            report, = inputs["child_reports"]
            cells = report["native_results"]
            assert [cell["component"] for cell in cells] == components
            assert cells[0]["value"] == pytest.approx(.009)
            assert cells[1]["value"] is None
            return parent_reason(store, args["source_ref"])
        provider = ScriptedProvider([
            {"selection": {"kind": "episode_child", "role": "literature", "assignment": assignment,
                "goal": "Compare the synthetic source rates and retain unavailable uncertainty.",
                "scope": plain(context.scope), "purpose": "Return the requested saved numerical cells.",
                "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}},
            work(invalid), fixture_chooses_repair, receive])
        controllers = []
        def controller(path, initial):
            result = FixtureController(str(path), initial, 2 if len(path) == 1 else 1)
            controllers.append(result)
            return result
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[args["source_ref"]],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0 and len(seen) == 1
        assert [c.scores for c in controllers] == [[0, 0], [0]]
        assert store.db.execute("select count(*) from runtime_actions").fetchone()[0] == 4
        assert store.db.execute("select count(*) from runtime_observations").fetchone()[0] == 3
        assert store.db.execute("select count(*) from literature_rate_operations").fetchone()[0] == 1
        assert store.db.execute("select count(*) from literature_rate_source_received").fetchone()[0] == 1
        row, = store.db.execute("select * from runtime_actions where json_extract(result,'$.status')='invalid'").fetchall()
        assert row["credit"] is None
        assert json.loads(row["action"])["arguments"] == original_invalid
        assert json.loads(row["result"])["feedback"] == seen[0]
        def forbidden(*_args, **_kwargs):
            raise AssertionError("saved failure replay must not inspect source bytes")
        monkeypatch.setattr(store, "get_artifact", forbidden)
        replay_invalid(store, row["run_id"], row)
        assert store.db.execute("select count(*) from runtime_observations").fetchone()[0] == 3
    finally:
        store.close()
