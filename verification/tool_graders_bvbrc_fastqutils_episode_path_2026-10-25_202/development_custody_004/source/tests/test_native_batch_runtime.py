"""Actual Store/runtime with explicitly synthetic predictor output, no model calls.

Only the native predictor function is replaced. Publication, paging, source
custody, fixed-scope credit, child forms and recovery use production paths.
"""
import asyncio
import json

import pytest

from gene_annotation_episode.runtime import _references_in, run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import SequenceWork, ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


def response(selection):
    return {"selection":selection,"report_update":{}}


def setup(tmp_path,monkeypatch,*,count=32,broken_tail=False):
    calls=[]
    def synthetic_predictor(sequence,*,code,mode):
        calls.append((code,mode))
        candidates=[{"start":6*i,"end":6*i+6,"strand":"+","code":code,
            "partial_begin":False,"partial_end":False,"protein_sequence":"MK",
            "native_confidence":99.,"native_score":10.} for i in range(count)]
        if broken_tail:
            candidates.append({**candidates[-1],"start":len(sequence)+6,"end":len(sequence)+12})
        return {"candidates":candidates,"mode":mode,"translation_code":code,
            "limitations":["explicitly_synthetic_predictor_fixture_not_biological_validation"]}
    async def synthetic_worker(self, operation, arguments, *, directory):
        assert operation == "predict_genes"
        output = directory / "synthetic-result.json"
        output.write_text(json.dumps(synthetic_predictor(**arguments)))
        return SequenceWork(output, {"execution": "explicitly_synthetic_test_worker"})
    monkeypatch.setattr(ToolRegistry, "_sequence_worker_async", synthetic_worker)
    store=Store(tmp_path/"state")
    subject=store.create_problem(raw_sequence="ATGAAA"*count,molecule="dna",role="assembly")["subject_refs"][0]
    return store,ToolRegistry(store),subject,calls


def genes(subject,code=11):
    return {"kind":"tool","tool":"genes.predict","arguments":{"subject_ref":subject,"code":code,"mode":"meta"}}


def own_native_actions(store):
    return [json.loads(row[0]) for row in store.db.execute(
        "SELECT result FROM runtime_actions WHERE json_extract(action,'$.tool')='genes.predict' "
        "AND result IS NOT NULL ORDER BY decision_index")]


def assert_presented_basis(context,store,scope):
    expected=_references_in({"working_state":context["working_state"],
        "last_local_outcome":context["last_local_outcome"],"visual_evidence":context["visual_evidence"]},store.get,
        forms=[(context["current_report_update"],{"type":"object","properties":{}})],
        reference_subset=lambda refs:store.reference_subset(refs,scope))
    assert set(context["visible_record_refs"]) == set(expected)


@pytest.mark.parametrize("preview_size",[0,2])
def test_gene_batch_context_publication_page_exact_record_and_complete_child_form(tmp_path,monkeypatch,preview_size):
    store,tools,subject,calls=setup(tmp_path,monkeypatch)
    with store:
        scope={"subject_refs":[subject]};selected={}
        form={"type":"object","additionalProperties":False,"required":["all","last"],"properties":{
            "all":{"type":"array","items":{"type":"string","format":"reference"},"x-source":"committed_record_refs"},
            "last":{"type":"array","items":{"type":"string","format":"reference"},"x-source":"last_outcome_refs"}}}
        def read_omitted(context):
            first,=own_native_actions(store)
            shown=context["last_local_outcome"];meta=shown["automatic_preview"]
            assert len(first["record_refs"]) == 98 and len(first["result"]["records"]) == 12
            assert meta["kind"] == "native_publication_batch"
            assert meta["record_refs"] == {"total":98,"included":preview_size,"truncated":True}
            assert meta["rows"] == {"total":32,"included":preview_size,"truncated":True}
            assert len(shown["record_refs"]) == len(shown["result"]["records"]) == preview_size
            assert meta["publication_query"]["decision_index"] == 0
            assert meta["publication_query"]["limit"] == max(1,preview_size)
            assert meta["observation_query"]["references"] == [first["result"]["source_ref"]]
            assert_presented_basis(context,store,scope)
            # Independent of the production basis walker: at least one real
            # native publication was not already disclosed by working state
            # or the automatic prefix. Recover that actually unseen ID.
            unseen=[(index,ref) for index,ref in enumerate(first["record_refs"])
                if ref not in set(context["visible_record_refs"])]
            assert unseen
            selected["index"],selected["id"]=unseen[-1]
            assert selected["id"] not in context["visible_record_refs"]
            assert selected["id"] not in shown["record_refs"]
            return response({"kind":"tool","tool":"episode.history","arguments":{
                "view":"publications","decision_index":0,"offset":selected["index"],"limit":1}})
        def inspect_exact(context):
            page=context["last_local_outcome"]
            assert page["record_refs"] == [] and "automatic_preview" not in page
            assert page["result"]["records"] == [{"publication_index":selected["index"],"record_ref":selected["id"]}]
            assert page["result"]["total"] == 98 and page["result"]["offset"] == selected["index"]
            assert selected["id"] in context["visible_record_refs"]
            return response({"kind":"tool","tool":"state.query","arguments":{"refs":[selected["id"]]}})
        def second_model(context):
            query=context["last_local_outcome"]
            assert query["result"]["records"][0]["id"] == selected["id"]
            assert "automatic_preview" not in query
            return response(genes(subject,4))
        def parent_uses_facts(context):
            delivered,=context["child_reports"]
            batches=own_native_actions(store)
            assert len(batches) == 2
            complete=list(dict.fromkeys(ref for batch in batches for ref in batch["record_refs"]))
            assert delivered == {"all":complete,"last":batches[-1]["record_refs"]}
            assert len(delivered["last"]) == 98 and len(delivered["all"]) > 98
            assert "automatic_preview" not in delivered
            return response({"kind":"tool","tool":"state.query","arguments":{"refs":[delivered["last"][-1]]}})
        provider=ScriptedProvider([response({"kind":"child","goal":"Iteratively compare candidate models and inspect actual selected publications",
            "scope":scope,"purpose":"Return complete recorded publication identities for a later exact inspection",
            "schema_json":json.dumps(form),"initial_report_json":"{}"}),response(genes(subject)),
            read_omitted,inspect_exact,second_model,parent_uses_facts])
        summary=asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/"run",
            restoration_settings={"preview_size":preview_size},
            controller_factory=lambda path,initial:FixtureController(str(path),initial,2 if len(path)==1 else 4)))
        assert calls == [(11,"meta"),(4,"meta")]
        assert summary["completed_actions"] == 2 and summary["credit"] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 6
        assert not store.current_annotations()


def test_partial_gene_batch_retains_complete_survivors_but_only_presents_requested_preview(tmp_path,monkeypatch):
    store,tools,subject,calls=setup(tmp_path,monkeypatch,count=18,broken_tail=True)
    with store:
        def read_retained(context):
            actual,=own_native_actions(store)
            assert actual["status"] == "partial" and len(actual["record_refs"]) == 56
            assert actual["result"]["retained_record_refs"] == actual["record_refs"]
            assert actual["published_batch"]["published_rows_total"] == 18
            shown=context["last_local_outcome"]
            assert len(shown["record_refs"]) == len(shown["result"]["retained_record_refs"]) == 2
            assert shown["automatic_preview"]["retained_record_refs"] == {"total":56,"included":2,"truncated":True}
            # Partial work completed; its exact diagnostic stays inside the
            # ordinary outcome rather than becoming a failed-action signal.
            assert shown["feedback"] == actual["feedback"] and context["feedback"] is None
            assert context["controller"]["scores"] == [0]
            return response({"kind":"tool","tool":"episode.history","arguments":{
                "view":"publications","decision_index":0,"offset":55,"limit":1}})
        provider=ScriptedProvider([response(genes(subject)),read_retained])
        summary=asyncio.run(run_workflow(store,tools,provider=provider,run_dir=tmp_path/"partial",
            restoration_settings={"preview_size":2},
            controller_factory=lambda path,initial:FixtureController(str(path),initial,2)))
        last=json.loads(store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=1").fetchone()[0])
        assert last["result"]["total"] == 56 and len(last["result"]["records"]) == 1
        assert summary["completed_actions"] == 2 and len(calls) == 1
        assert store.count("feature") == store.count("product") == store.count("observation") == 18
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 2


def test_resume_preserves_complete_saved_batch_and_pages_it_without_predictor_rerun(tmp_path,monkeypatch):
    store,tools,subject,calls=setup(tmp_path,monkeypatch)
    with store:
        directory=tmp_path/"resume";factory=lambda path,initial:FixtureController(str(path),initial,2)
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(run_workflow(store,tools,provider=ScriptedProvider([response(genes(subject)),KeyboardInterrupt()]),
                run_dir=directory,controller_factory=factory,restoration_settings={"preview_size":2}))
        saved=store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=0").fetchone()[0]
        count=store.db.execute("SELECT count(*) FROM records").fetchone()[0]
        def restored(context):
            assert context["last_local_outcome"]["automatic_preview"]["record_refs"] == {
                "total":98,"included":2,"truncated":True}
            assert context["controller"]["scores"] == [0]
            return response({"kind":"tool","tool":"episode.history","arguments":{
                "view":"publications","decision_index":0,"offset":97,"limit":1}})
        summary=asyncio.run(run_workflow(store,tools,provider=ScriptedProvider([restored]),resume=True,
            controller_factory=factory))
        assert len(calls) == 1 and store.db.execute("SELECT count(*) FROM records").fetchone()[0] == count
        assert store.db.execute("SELECT result FROM runtime_actions WHERE decision_index=0").fetchone()[0] == saved
        assert summary["completed_actions"] == 2 and summary["credit"] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 2
