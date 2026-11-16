"""Engineering return-owner controls; no native or Workflow execution claim."""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.method_loop.episode import EpisodeGoal, EpisodeRequest

from gene_annotation_episode.episodic_workflow.root.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.episodic_workflow.root.library.flux_balance_model_tools import validate_flux_balance_model_view
from gene_annotation_episode.episodic_workflow.root.library.flux_balance_return_views import (
    fba_fact_sources, requested_fba_sources, validate_fba_fact_values,
)
from gene_annotation_episode.episodic_workflow.root.flux_balance_returns import FluxBalanceReturns, ORDINARY_PREFIX
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.workflow_values import TypedReportContract


MODEL = "flux_balance_model_views"
EDITED = "flux_balance_edited_models"
SAVED = "flux_balance_saved_sheets"


def unavailable_view(ordinal=0):
    return validate_flux_balance_model_view({
        "version": "flux_balance_model_view_v1",
        "selector": {"snapshot_phase": "effective", "collection": "reactions",
            "ordinals": [ordinal], "row_window": {"offset": 0, "limit": 1}},
        "population": {"basis": "captured_loaded_native_collection", "expected_count": None,
            "retained_count": 0, "snapshot_available": False},
        "page": {"selected_row_count": 1, "offset": 0, "returned_row_count": 1, "has_more": False},
        "rows": [{"ordinal": ordinal, "availability": "unavailable", "values": None}],
        "edit_state": "unknown", "source_features": [], "issues": []})


def file(format_="cobra_json"):
    return {"artifact_ref": "artifact_" + "a" * 64, "sha256": "a" * 64,
        "size_bytes": 7, "format": format_}


def schema(*sources):
    return {"type": "object", "properties": {"field_" + str(index):
        deepcopy(fba_fact_sources()[source]["report_schema"]) for index, source in enumerate(sources)},
        "required": ["field_" + str(index) for index in range(len(sources))], "additionalProperties": False}


def form(groups, declared):
    return {name: deepcopy(groups[node["x-source"]]) for name, node in declared["properties"].items()}


def record(index, source="b", **groups):
    facts = {name: [] for name in fba_fact_sources()}
    facts.update(groups)
    return {"witness": {"version": "ordinary_flux_balance_fact_witness_v1",
        "operation_key": "engineering:producer:" + str(index), "operation_ref": "operation_" + str(index),
        "result_sha256": digest(facts), "source_ref": "source_" + source * 24}, "facts": facts}


class EngineeringBackend:
    """Explicit supplied backend records, independent of producer authentication."""
    def __init__(self):
        self.rows, self.live_calls, self.frozen_calls = [], [], []

    def own_fact_records(self, context, *, sources, verify_artifacts=True):
        self.live_calls.append((tuple(sources), verify_artifacts))
        return [{"witness": deepcopy(row["witness"]), "facts": {
            source: deepcopy(row["facts"][source]) for source in sources}} for row in self.rows]

    def authenticate_frozen_fact_records(self, context, *, witnesses, sources):
        self.frozen_calls.append(deepcopy(witnesses))
        groups = {source: [] for source in sources}
        for witness in witnesses:
            matches = [row for row in self.rows if canonical(row["witness"]) == canonical(witness)]
            if len(matches) != 1:
                raise ValueError("engineering_witness_conflict")
            for source in sources:
                groups[source].extend(deepcopy(matches[0]["facts"][source]))
        return groups


@pytest.fixture
def case(tmp_path):
    with Store(tmp_path / "store") as store:
        # These are declared engineering journals, not invented native output
        # or a substitute for the separate real Workflow/ToolOperation proof.
        run_id, path = "engineering", (("scientific_process", "root"),)
        journal = Journal(store, run_id)
        episode = EpisodeRef(run_id, path).episode_id
        manifest = EpisodeReceipts(store, run_id).bind(episode)
        requested = schema(MODEL, EDITED, SAVED)
        scope = {"subject_refs": store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]}
        contract = TypedReportContract("Return recorded values", requested, lambda *_: True)
        request = EpisodeRequest(EpisodeGoal.root(objective="Return the selected engineering model views.",
            result_contract=requested), Record({"scope": scope, "episode_assignment": {},
                "knowledge_inheritance": manifest}), contract).as_record()
        context = BindingContext(run_id, episode, "scientific_process", path,
            request["message"]["scope"], {}, request)
        journal.save("runtime_episodes", {"episode_id": episode, "path": canonical(path),
            "request": canonical(request), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        backend = EngineeringBackend()
        owner = FluxBalanceReturns(SimpleNamespace(store=store, run_id=run_id,
            native_flux_balance_results=None), ordinary_backend=backend)
        yield SimpleNamespace(store=store, context=context, backend=backend, owner=owner,
            schema=requested, journal=journal)


def freeze(case):
    groups = case.owner.facts(case.context, case.schema)
    private = case.owner.ordinary_closure_facts(case.context, case.schema)
    facts = {**groups, **private}
    outgoing = form(groups, case.schema)
    case.store.db.execute("INSERT INTO runtime_forms VALUES(?,?,?,?)",
        (case.context.run_id, case.context.episode_id, canonical(facts), canonical(outgoing)))
    case.store.db.commit()
    return facts, outgoing


def test_same_source_distinct_views_and_distinct_sources_identical_values_survive(case):
    first, second = unavailable_view(0), unavailable_view(4)
    case.backend.rows = [record(0, **{MODEL: [first]}), record(1, **{MODEL: [second]}),
        record(2, "c", **{MODEL: [first]}), record(3, **{MODEL: [first]})]
    facts = case.owner.facts(case.context, case.schema)
    assert facts[MODEL] == [first, second, first]
    assert ORDINARY_PREFIX not in facts
    assert ORDINARY_PREFIX not in case.owner.facts_for_closure(case.context, case.schema)
    frozen, outgoing = freeze(case)
    identities = frozen[ORDINARY_PREFIX]["identities"][MODEL]
    assert len({row["identity"] for row in identities}) == 3
    assert all(row["origins"] == [case.context.episode_id] for row in identities)
    assert outgoing["field_0"] == facts[MODEL]


def test_frozen_prefix_excludes_late_work_and_uses_no_live_artifact_port(case, monkeypatch):
    case.backend.rows = [record(0, **{MODEL: [unavailable_view()], EDITED: [file()]})]
    original, outgoing = freeze(case)
    case.backend.rows.append(record(1, "c", **{MODEL: [unavailable_view(8)]}))
    case.store.db.execute("INSERT INTO runtime_report_attempts "
        "(run_id,parent_episode_id,decision_index,delivery_ref,child_episode_id,contract,form,failure) "
        "VALUES(?,?,?,?,?,?,?,NULL)",
        (case.context.run_id, case.context.episode_id, 99, "late", "nonexistent_child",
            canonical({"measurements": {"schema": schema(MODEL)}}), canonical({"field_0": []})))
    case.store.db.commit()
    def forbidden(*args, **kwargs):
        raise AssertionError("closed validation consulted live science")
    monkeypatch.setattr(case.backend, "own_fact_records", forbidden)
    monkeypatch.setattr(case.store, "get_artifact", forbidden)
    monkeypatch.setattr(case.owner, "_attempt", forbidden)
    assert case.owner.facts(case.context, case.schema) == {
        source: original[source] for source in requested_fba_sources(case.schema)}
    case.owner.validate_received_report(case.context, outgoing, case.schema)
    case.owner.validate_received_report(case.context, {}, schema())
    assert case.backend.frozen_calls


@pytest.mark.parametrize("tamper", ["witness", "identity", "value"])
def test_closed_action_or_positional_binding_tampering_is_rejected(case, tamper):
    case.backend.rows = [record(0, **{MODEL: [unavailable_view()]})]
    frozen, outgoing = freeze(case)
    if tamper == "witness":
        frozen[ORDINARY_PREFIX]["witnesses"][0]["source_ref"] = "source_" + "d" * 24
    elif tamper == "identity":
        frozen[ORDINARY_PREFIX]["identities"][MODEL][0]["identity"] += "altered"
    else:
        frozen[MODEL][0]["edit_state"] = "partial"
    case.store.db.execute("UPDATE runtime_forms SET facts=?", (canonical(frozen),))
    case.store.db.commit()
    with pytest.raises(ValueError):
        case.owner.validate_received_report(case.context, outgoing, case.schema)


def test_same_source_same_selector_conflicting_values_reject(case):
    first, altered = unavailable_view(), unavailable_view()
    altered["edit_state"] = "partial"
    case.backend.rows = [record(0, **{MODEL: [first]}), record(1, **{MODEL: [altered]})]
    with pytest.raises(ValueError, match="ordinary_identity_conflict"):
        case.owner.facts(case.context, case.schema)


def test_only_selected_file_groups_resolve_never_numeric_sources_or_capsules(case):
    edited, saved = file(), file("flux_balance_sheet_v1")
    saved["artifact_ref"], saved["sha256"] = "artifact_" + "e" * 64, "e" * 64
    case.backend.rows = [record(0, **{MODEL: [unavailable_view()], EDITED: [edited], SAVED: [saved]})]
    for selected in (edited, saved):
        assert case.owner.resolve_received(case.context, selected["artifact_ref"], "artifact")
        assert not case.owner.resolve_received(case.context, selected["artifact_ref"], "source")
    assert not case.owner.resolve_received(case.context, "artifact_" + "f" * 64, "artifact")
    assert not case.owner.resolve_received(case.context, case.backend.rows[0]["witness"]["source_ref"], "source")


@pytest.mark.parametrize("format_", ["flux_balance_sheet_v1", "text", "pdbx_mmcif_text"])
def test_edited_model_source_does_not_admit_other_file_formats(format_):
    with pytest.raises(ValueError):
        validate_fba_fact_values(EDITED, [file(format_)])


