"""729 record joins, receipt history and frozen returns, without fresh science.

The engineering_case fixture explicitly stubs only the 725/726 authority seam;
it supplies no scientific measurements and proves SQL/receipt behavior only.
The retained_case fixture uses root728's actual saved-only original operation,
which reuses the one original726 native result. It never rebinds its native key.
No public catalog is installed or injected by these checks.
"""
from copy import deepcopy
from dataclasses import replace
import builtins
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.communication import plain, ReportBoundaryError
from gene_annotation_episode.domain import canonical, identity
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.restriction_mapping_action_records import RestrictionMappingActionRecords
from gene_annotation_episode.restriction_mapping_returns import (
    restriction_mapping_fact_sources, requested_restriction_projections,
    project_restriction_action_return, validate_frozen_restriction_return,
)
from gene_annotation_episode.state import Store


SOURCE = "restriction_mapping_results"
RUN = "restriction729-engineering"
ALIAS = "find_restriction_sites"
SELECTOR = Path(__file__).resolve().parents[1] / (
    "verification/tool_graders_restriction_registry_2026-10-29_728/SAVED_SELECTOR_001.json")


def requested(policy="all_own_completed_results", sequence_ref=None):
    fields = restriction_mapping_fact_sources()[SOURCE]["report_schema"]
    group = fields["items"]["properties"]
    group["selection_policy"] = {"type": "string", "const": policy}
    if policy == "matching_sequence":
        group["sequence_ref"]["const"] = sequence_ref
    return {"type": "object", "properties": {"selected": fields},
        "required": ["selected"], "additionalProperties": False}


def saved_context(case, *, schema=None, name="child_0", parent=None, role="scientific_process"):
    path = (("root", "root"), (role, name)) if parent is None else (*parent.path, (role, name))
    episode_id = EpisodeRef(RUN, path).episode_id
    request = {"message": {"scope": case.scope, "episode_assignment": {}},
        "report_contract": {"measurements": {"schema": requested() if schema is None else schema}}}
    case.journal.save("runtime_episodes", {"episode_id": episode_id,
        "path": canonical(path), "request": canonical(request), "initial_credit": 0., "state": "active"})
    case.receipts.bind(episode_id, None if parent is None else parent.episode_id)
    return BindingContext(RUN, episode_id, role, path, case.scope, {}, request)


def engineering_action(case, context, index=3, *, mode="native", tool=ALIAS,
        sequence_ref=None, status="partial", runtime_extra=None):
    """Clearly labelled authority stub, not a published native measurement."""
    sequence_ref = sequence_ref or case.sequence
    args = ({"mode": "native", "sequence_ref": sequence_ref,
             **({"enzyme_names": ["EcoRI"]} if tool == ALIAS else {})}
        if mode == "native" else {"mode": "saved", "result_source_ref": case.prior})
    key = f"{RUN}:{context.episode_id}:{index}"
    operation_ref = identity("operation", {"key": key, "name": tool, "arguments": args})
    source = "engineering_source_" + str(index) + "_" + context.episode_id
    binding = {"sequence_ref": sequence_ref, "namespace": "subject", "source_ref": case.input_source}
    body = {"operation_key": key, "operation_ref": operation_ref, "tool_name": tool,
        "arguments": args, "scope": case.scope, "status": status, "work_mode": mode,
        "input_source_ref": case.input_source, "prior_result_source_ref": case.prior if mode == "saved" else None,
        "files": {"native": {"artifact_ref": case.native_artifact}, "mapping": None},
        "failure_code": "reader_unavailable"}
    result = {"source_ref": source, "sequence_ref": sequence_ref, "namespace": "subject",
        "input_source_ref": case.input_source, "work_mode": mode,
        "native_artifact_ref": case.native_artifact, "mapping_artifact_ref": None,
        "data_status": "unavailable", "topology": None, "population": None, "issue_codes": []}
    outcome = {"status": status, "operation_ref": operation_ref,
        "record_refs": [case.input_source, source], "result": result, "feedback": None}
    case.store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)",
        (key, operation_ref, tool, canonical(args), canonical(case.scope), canonical(outcome)))
    case.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
        "action": canonical({"kind": "tool", "tool": tool, "arguments": args}),
        "result": canonical({**outcome, **(runtime_extra or {})}), "credit": 0.})
    case.states[key] = {"published_source_ref": source, "published_outcome": deepcopy(outcome)}
    # This tiny dictionary is a labelled namespace-test stub, never native output.
    case.sources[source] = {"source": {"id": source}, "body": body, "sequence_binding": binding,
        "mapping": None, "native": {"catalog": {"enzymes": [{"name": "EcoRI"}]}}, "catalog": None}
    return outcome


@pytest.fixture
def engineering_case(tmp_path, monkeypatch):
    fasta = tmp_path / "engineering.fa"
    fasta.write_text(">selected\nAAAAGAATTCTTTT\n>other\nTTTTGAATTCAAAA\n")
    with Store(tmp_path / "engineering-store") as store:
        sequence, other = store.create_problem(fasta, molecule="dna")["subject_refs"]
        store.db.execute("CREATE TABLE tool_operations(operation_key TEXT PRIMARY KEY,id TEXT NOT NULL,"
            "name TEXT NOT NULL,arguments TEXT NOT NULL,scope TEXT NOT NULL,result TEXT NOT NULL)")
        prior = store.put("source", {"provider": "engineering729.prior", "accession": None, "uri": None,
            "artifact_ref": store.artifact("engineering prior source, no measurement"), "text_ref": None,
            "request_ref": None, "version": "engineering", "retrieved_at": None}, origin="tool")["id"]
        case = SimpleNamespace(store=store, sequence=sequence, other=other, prior=prior,
            input_source=prior, native_artifact=store.artifact("engineering authority stub, no native data"),
            scope=store.validate_scope(), journal=Journal(store, RUN), receipts=EpisodeReceipts(store, RUN),
            service=RestrictionMappingActionRecords(store, RUN), states={}, sources={})
        import gene_annotation_episode.restriction_mapping_jobs as jobs
        import gene_annotation_episode.restriction_mapping_publication as publication
        def state(self, key):
            if key not in case.states:
                raise ValueError("engineering_unbound_operation")
            return deepcopy(case.states[key])
        def published(store, source_ref, *, scope):
            if source_ref not in case.sources:
                raise ValueError("engineering_unbound_source")
            return deepcopy(case.sources[source_ref])
        monkeypatch.setattr(jobs.RestrictionMappingJobs, "publication_state", state)
        monkeypatch.setattr(publication, "read_published_restriction_result", published)
        yield case


def page(case, context, *, after=None, limit=64, selection=None):
    selected = requested_restriction_projections(
        plain(context.request)["report_contract"]["measurements"]["schema"])[SOURCE]
    return case.service.own_action_results(context,
        selection=selected["selection"] if selection is None else selection,
        after_decision_index=after, limit=limit)


def initial(case, context, *, saved=False, sequence=None):
    case.receipts.receive(context.episode_id,
        [sequence or case.sequence, *([case.prior] if saved else [])], kind="initial")


@pytest.mark.parametrize("alias", [ALIAS, "find_restriction_enzymes"])
def test_engineering_native_join_is_detached_and_has_no_invented_numbers(engineering_case, alias):
    case = engineering_case
    context = saved_context(case)
    initial(case, context)
    engineering_action(case, context, tool=alias)
    record, = page(case, context)["records"]
    assert record["mapping"] is None and record["failure_code"] == "reader_unavailable"
    fields = requested_restriction_projections(requested())[SOURCE]["fields"]
    view = project_restriction_action_return(record, fields)
    assert view["population"] is None and view["enzyme_rows"] is None
    assert view["data_status"] == "unavailable"
    record["sequence_ref"] = "changed detached output"
    assert page(case, context)["records"][0]["sequence_ref"] == case.sequence


@pytest.mark.parametrize("limit,after", [(True,None),(0,None),(-1,None),(257,None),(1,True),(1,-1),(1,1.0)])
def test_engineering_explicit_page_bounds(engineering_case, limit, after):
    case = engineering_case
    with pytest.raises(ValueError, match="explicit_page_required"):
        page(case, saved_context(case), limit=limit, after=after)


def test_engineering_selection_filter_precedes_page_limit_and_excludes_siblings(engineering_case):
    case = engineering_case
    context = saved_context(case, schema=requested("matching_sequence", case.sequence))
    sibling = saved_context(case, name="child_1")
    for owner in (context, sibling):
        initial(case, owner)
        case.receipts.receive(owner.episode_id, [case.other], kind="initial")
    for index, seq in [(0,case.other),(1,case.sequence),(2,case.other),(3,case.sequence)]:
        engineering_action(case, context, index, sequence_ref=seq)
    engineering_action(case, sibling, 4)
    # Nonmatching broken work cannot consume a requested page.
    case.store.db.execute("DELETE FROM tool_operations WHERE operation_key=?",
        (f"{RUN}:{context.episode_id}:0",))
    first = page(case, context, limit=1)
    second = page(case, context, limit=1, after=first["next_after_decision_index"])
    assert [r["decision_index"] for r in first["records"]] == [1]
    assert [r["decision_index"] for r in second["records"]] == [3]
    assert second["next_after_decision_index"] is None


def test_engineering_caller_cannot_broaden_parent_selection(engineering_case):
    case = engineering_case
    context = saved_context(case, schema=requested("matching_sequence", case.sequence))
    with pytest.raises(ValueError, match="selection_conflict"):
        page(case, context, selection={"policy":"all_own_completed_results","sequence_ref":None})


@pytest.mark.parametrize("change", ["run","episode","scope","request","missing","role"])
def test_engineering_context_authentication(engineering_case, change):
    case = engineering_case
    context = saved_context(case, role="root" if change == "role" else "scientific_process")
    if change == "run":
        context = replace(context, run_id="foreign")
    elif change == "episode":
        context = replace(context, episode_id="foreign")
    elif change == "scope":
        context = replace(context, scope={"subject_refs":[]})
    elif change == "request":
        changed = plain(context.request); changed["unexpected"] = True
        context = replace(context, request=changed)
    elif change == "missing":
        case.store.db.execute("DELETE FROM runtime_episodes WHERE episode_id=?", (context.episode_id,))
    with pytest.raises(ValueError, match="restriction_mapping_return_"):
        page(case, context)


@pytest.mark.parametrize("field", ["missing","id","name","arguments","scope","result"])
def test_engineering_original_operation_and_outcome_joins(engineering_case, field):
    case = engineering_case
    context = saved_context(case); initial(case, context)
    engineering_action(case, context)
    key = f"{RUN}:{context.episode_id}:3"
    if field == "missing":
        case.store.db.execute("DELETE FROM tool_operations WHERE operation_key=?", (key,))
    else:
        value = {"id":"wrong-operation", "name":"find_restriction_enzymes", "arguments":canonical({}),
            "scope":canonical({"subject_refs":[]}), "result":canonical({"status":"partial"})}[field]
        case.store.db.execute(f"UPDATE tool_operations SET {field}=? WHERE operation_key=?", (value,key))
    with pytest.raises(ValueError, match="restriction_mapping_return_"):
        page(case, context)


def test_engineering_only_existing_pending_metadata_augmentation_is_accepted(engineering_case):
    case = engineering_case
    context = saved_context(case); initial(case, context)
    outcome = engineering_action(case, context, runtime_extra={"pending_work_after_action":{"known":True}})
    assert len(page(case, context)["records"]) == 1
    case.store.db.execute("UPDATE runtime_actions SET result=? WHERE episode_id=?",
        (canonical({**outcome,"unrequested_extra":True}),context.episode_id))
    with pytest.raises(ValueError, match="operation_outcome_conflict"):
        page(case, context)


@pytest.mark.parametrize("kind,index,allowed", [("initial",None,True),("decision_input",3,True),
    ("decision_input",4,False),("own_action",2,True),("own_action",3,False),
    ("child_form",2,True),("child_form",3,False),("report_redelivery",2,True)])
def test_engineering_native_receipt_precedes_selection(engineering_case, kind, index, allowed):
    case = engineering_case
    context = saved_context(case)
    engineering_action(case, context)
    case.receipts.receive(context.episode_id, [case.sequence], kind=kind, source_index=index)
    if allowed:
        assert len(page(case, context)["records"]) == 1
    else:
        with pytest.raises(ValueError, match="original_sequence_receipt_required"):
            page(case, context)


@pytest.mark.parametrize("received_sequence,received_source", [(True,False),(False,True),(True,True)])
def test_engineering_saved_needs_both_original_received_operands(engineering_case, received_sequence, received_source):
    case = engineering_case
    context = saved_context(case)
    engineering_action(case, context, mode="saved")
    refs = ([case.sequence] if received_sequence else []) + ([case.prior] if received_source else [])
    case.receipts.receive(context.episode_id, refs, kind="initial")
    if received_sequence and received_source:
        assert page(case, context)["records"][0]["work_mode"] == "saved"
    else:
        with pytest.raises(ValueError, match="original_(sequence|saved_source)_receipt_required"):
            page(case, context)


@pytest.mark.parametrize("kind,index,allowed", [("own_action",2,True),("own_action",3,False),
    ("own_action",4,False),("decision_input",3,True),("decision_input",4,False)])
def test_engineering_saved_source_receipt_timing(engineering_case, kind, index, allowed):
    case = engineering_case
    context = saved_context(case)
    initial(case,context)  # Only the sequence is initially known.
    engineering_action(case,context,mode="saved")
    case.receipts.receive(context.episode_id,[case.prior],kind=kind,source_index=index)
    if allowed:
        assert page(case,context)["records"][0]["work_mode"] == "saved"
    else:
        with pytest.raises(ValueError,match="original_saved_source_receipt_required"):
            page(case,context)


@pytest.mark.parametrize("before", [True,False])
def test_engineering_inherited_receipt_prefix_is_frozen(engineering_case, before):
    case = engineering_case
    parent = saved_context(case, name="parent")
    if before: initial(case,parent)
    child = saved_context(case, name="descendant", parent=parent)
    if not before: initial(case,parent)
    engineering_action(case,child)
    if before:
        assert len(page(case,child)["records"]) == 1
    else:
        with pytest.raises(ValueError, match="original_sequence_receipt_required"):
            page(case,child)


def test_engineering_context_handles_do_not_replace_receipt_history(engineering_case):
    case = engineering_case
    context = saved_context(case); engineering_action(case,context)
    context = replace(context,received_record_refs=(case.sequence,))
    with pytest.raises(ValueError,match="original_sequence_receipt_required"):
        page(case,context)
    case.store.db.execute("DELETE FROM runtime_receipt_inheritance WHERE episode_id=?", (context.episode_id,))
    with pytest.raises(ValueError,match="receipt_history_unbound"):
        page(case,context)


@pytest.mark.parametrize("status", ["failed","invalid","unavailable"])
def test_engineering_incomplete_actions_do_not_become_returned_results(engineering_case,status):
    case = engineering_case
    context = saved_context(case); initial(case,context)
    engineering_action(case,context,status=status)
    assert page(case,context)["records"] == []


def test_engineering_own_catalog_namespace_is_exact_and_episode_owned(engineering_case):
    case = engineering_case
    context = saved_context(case); initial(case,context)
    sibling = saved_context(case,name="sibling"); initial(case,sibling)
    engineering_action(case,sibling)
    assert case.service.own_enzyme_reference(context,"EcoRI") is False
    engineering_action(case,context)
    assert case.service.own_enzyme_reference(context,"EcoRI") is True
    for name in ("ecori","EcoRII","BcgI","",None,True):
        assert case.service.own_enzyme_reference(context,name) is False


def test_engineering_source_or_memo_lookalike_is_rejected(engineering_case):
    case = engineering_case
    context = saved_context(case); initial(case,context)
    outcome = engineering_action(case,context)
    key = f"{RUN}:{context.episode_id}:3"
    case.states[key]["published_source_ref"] = "forged-source"
    with pytest.raises(ValueError,match="operation_source_conflict"):
        page(case,context)
    case.states[key]["published_source_ref"] = outcome["result"]["source_ref"]
    case.states[key]["published_outcome"]["result"]["sequence_ref"] = "other"
    with pytest.raises(ValueError,match="operation_authority_conflict"):
        page(case,context)


def test_engineering_frozen_state_absence_differs_from_empty_array(engineering_case):
    case = engineering_case; context = saved_context(case)
    with pytest.raises(ValueError,match="frozen_state_required"):
        case.service.frozen_facts(context,sources=(SOURCE,))
    case.journal.save("runtime_forms", {"episode_id":context.episode_id,"facts":canonical({}),"form":None})
    assert case.service.frozen_facts(context,sources=(SOURCE,)) == {}
    case.journal.save("runtime_forms", {"episode_id":context.episode_id,"facts":canonical({SOURCE:[]}),"form":None})
    assert case.service.frozen_facts(context,sources=(SOURCE,)) == {SOURCE:[]}
    assert case.service.frozen_facts(context,sources=()) == {}
    with pytest.raises(ValueError,match="requested_source_required"):
        case.service.frozen_facts(context,sources=("other",))


@pytest.mark.parametrize("value", [None,{},0,False,"[]"])
def test_engineering_frozen_source_must_be_array(engineering_case,value):
    case = engineering_case; context = saved_context(case)
    case.journal.save("runtime_forms", {"episode_id":context.episode_id,"facts":canonical({SOURCE:value}),"form":None})
    with pytest.raises(ValueError,match="frozen_source_invalid"):
        case.service.frozen_facts(context,sources=(SOURCE,))


def test_engineering_frozen_return_reads_no_live_source_or_calculation(engineering_case,monkeypatch):
    case = engineering_case; context = saved_context(case); initial(case,context)
    engineering_action(case,context)
    fields = requested_restriction_projections(requested())[SOURCE]["fields"]
    expected = [project_restriction_action_return(r,fields) for r in page(case,context)["records"]]
    case.journal.save("runtime_forms", {"episode_id":context.episode_id,
        "facts":canonical({SOURCE:expected}),"form":canonical({"selected":expected})})
    def forbidden(*args,**kwargs): pytest.fail("Frozen return accessed live work")
    monkeypatch.setattr(case.service,"own_action_results",forbidden)
    monkeypatch.setattr(case.store,"get_artifact",forbidden)
    import gene_annotation_episode.restriction_mapping_publication as publication
    monkeypatch.setattr(publication,"read_published_restriction_result",forbidden)
    frozen = case.service.frozen_facts(context,sources=(SOURCE,))
    validate_frozen_restriction_return({"selected":deepcopy(expected)},requested(),frozen)
    changed = deepcopy(expected); changed[0]["namespace"] = "reference"
    with pytest.raises(ReportBoundaryError):
        validate_frozen_restriction_return({"selected":changed},requested(),frozen)
    assert case.service.frozen_facts(context,sources=(SOURCE,)) == frozen


@pytest.fixture(scope="module")
def retained_case():
    """Root's genuine saved-only job under its ORIGINAL runtime operation key."""
    selector = json.loads(SELECTOR.read_text())
    store = Store(selector["store_path"])
    service = RestrictionMappingActionRecords(store,selector["run_id"])
    context = service.context(selector["episode_id"])
    assert selector["operation_key"] == f'{selector["run_id"]}:{context.episode_id}:{selector["decision_index"]}'
    try:
        yield SimpleNamespace(store=store,service=service,context=context,selector=selector)
    finally:
        store.close()


def test_actual_saved_operation_preserves_original_numerical_mapping_without_work(retained_case,monkeypatch):
    case = retained_case
    import gene_annotation_episode.restriction_mapping_readers as readers
    import gene_annotation_episode.native_lifecycle as lifecycle
    def forbidden(*args,**kwargs): pytest.fail("Action reader repeated native/719/dispatch work")
    monkeypatch.setattr(readers,"read_restriction_mapping",forbidden)
    monkeypatch.setattr(lifecycle,"resume_start",forbidden)
    original_import = builtins.__import__
    def guarded(name,*args,**kwargs):
        if name == "Bio" or name.startswith("Bio.") or name.endswith("restriction_mapping_native"):
            pytest.fail("Action reader imported native Bio/producer")
        return original_import(name,*args,**kwargs)
    monkeypatch.setattr(builtins,"__import__",guarded)
    before = case.store.db.total_changes
    record, = page(case,case.context)["records"]
    assert record["work_mode"] == "saved" and record["source_ref"] == case.selector["source_ref"]
    assert record["mapping"]["enzyme_rows"][0]["native_search_positions_1based"] == [6]
    position, = record["mapping"]["enzyme_rows"][0]["positions"]
    assert (position["watson_boundary_0based"],position["crick_boundary_0based"]) == (5,9)
    assert record["mapping"]["enzyme_rows"][0]["recognition_match_count"] == 1
    assert case.store.db.total_changes == before
    assert case.service.own_enzyme_reference(case.context,"EcoRI") is True
    assert case.service.own_enzyme_reference(case.context,"BcgI") is False


def test_actual_saved_projection_copies_only_original_requested_fields(retained_case):
    case = retained_case
    schema = plain(case.context.request)["report_contract"]["measurements"]["schema"]
    fields = requested_restriction_projections(schema)[SOURCE]["fields"]
    record, = page(case,case.context)["records"]
    returned = project_restriction_action_return(record,fields)
    assert returned["sequence_ref"] == record["sequence_ref"]
    assert set(returned) == set(fields["items"]["properties"])
    assert record["mapping"]["population"]["recognition_match_count"] == 1
    retained = Path(os.environ["HMMER529_ATTEMPT"]) / "retained-action729"
    retained.mkdir(exist_ok=True)
    (retained/"actual_record.json").write_text(canonical(record)+"\n")
    (retained/"actual_requested_view.json").write_text(canonical(returned)+"\n")
