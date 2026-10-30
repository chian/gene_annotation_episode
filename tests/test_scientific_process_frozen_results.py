"""Original closing-source access; this is not a scientific scoring test."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from method_loop import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.runtime import Record
from gene_annotation_episode.scientific_process_provenance import ScientificProcessProvenance
from gene_annotation_episode.scientific_process_records import scientific_invocation_ref
from gene_annotation_episode.state import Store


def saved_context(store, journal, *, key="root", save=True, scope=None):
    if scope is None:
        problem = store.create_problem(raw_sequence="MKWAA", molecule="protein")
        scope = {"subject_refs": problem["subject_refs"]}
    path = (("annotation", key),)
    episode_id = EpisodeRef(journal.run_id, path).episode_id
    request = EpisodeRequest(
        EpisodeGoal.root(objective="Check the original requested return",
                         result_contract={"role": "annotation"}),
        Record({"scope": scope, "initial_report": {}, "episode_assignment": {},
                "scientific_invocation_ref": scientific_invocation_ref(journal.run_id, path)}),
        None).as_record()
    context = BindingContext(journal.run_id, episode_id, "annotation", path,
                             scope, {}, request)
    if save:
        journal.save("runtime_episodes", {"episode_id": episode_id,
            "path": json.dumps(path), "request": json.dumps(request),
            "initial_credit": 0, "state": "closed", "completion": None,
            "archive": None})
    return context


def literal_result(context):
    # A literal compatibility fixture, not a claimed historical run. This port
    # preserves the stored representation; the report parser checks its schema.
    option = {"version": "scientific_process_option_ref_v1",
        "library_id": "a" * 64, "slot": "annotation_distinction",
        "option_id": "A01", "entry_sha256": "b" * 64}
    return {"version": "scientific_process_result_v1",
        "invocation_ref": scientific_invocation_ref(context.run_id, context.path),
        "parent_invocation_ref": None, "origin_kind": "ordinary_child",
        "preparation_operation_ref": None,
        "selection": {"version": "scientific_process_selection_v2",
            "annotation_ref": option,
            "thought_ref": {**option, "slot": "thought_pattern", "option_id": "P01",
                            "entry_sha256": "c" * 64}, "tools": []},
        "initial_credit": 15.25, "credit": 14.5, "credit_kind": None,
        "credit_binding_ref": None, "completed_actions": 2, "episode_yield": None}


def close_source(journal, context, facts):
    journal.save("runtime_forms", {"episode_id": context.episode_id,
        "facts": json.dumps(facts), "form": None})


def test_missing_source_empty_source_and_literal_saved_values_are_distinct(tmp_path):
    with Store(tmp_path / "state") as store:
        journal = Journal(store, "frozen-source-fixture")
        context = saved_context(store, journal)
        provenance = ScientificProcessProvenance(store, journal, library=None)
        assert provenance.frozen_results(context) is None
        close_source(journal, context, {"credit": 999})
        assert provenance.frozen_results(context) is None
        close_source(journal, context, {"scientific_process_results": []})
        assert provenance.frozen_results(context) == []

        original = [literal_result(context)]
        close_source(journal, context, {"scientific_process_results": original,
            "interpretations": {"private": "must not be returned"}, "credit": 999})
        returned = provenance.frozen_results(context)
        assert returned == original
        returned[0]["credit"] = 42
        returned[0]["selection"]["annotation_ref"]["slot"] = "evidence_axis"
        assert provenance.frozen_results(context) == original


@pytest.mark.parametrize("value", [None, {}, "unavailable", 0, True])
def test_explicit_nonarray_source_is_invalid_not_absent(tmp_path, value):
    with Store(tmp_path / "state") as store:
        journal = Journal(store, "frozen-source-fixture")
        context = saved_context(store, journal)
        close_source(journal, context, {"scientific_process_results": value})
        provenance = ScientificProcessProvenance(store, journal, library=None)
        with pytest.raises(ValueError, match="^scientific_frozen_results_invalid$"):
            provenance.frozen_results(context)


def test_source_read_authenticates_original_owner_and_never_hydrates_histories(tmp_path):
    with Store(tmp_path / "state") as store:
        journal = Journal(store, "frozen-source-fixture")
        context = saved_context(store, journal)
        unrelated = saved_context(store, journal, key="unrelated", scope=context.as_record()["scope"])
        expected = [literal_result(context)]
        close_source(journal, context, {"scientific_process_results": expected})
        close_source(journal, unrelated, {"scientific_process_results": []})
        provenance = ScientificProcessProvenance(store, journal, library=None)
        statements = []
        store.db.set_trace_callback(statements.append)
        before = store.db.total_changes
        assert provenance.frozen_results(context) == expected
        store.db.set_trace_callback(None)
        assert store.db.total_changes == before
        assert not any(name in sql.lower() for sql in statements for name in
            ("runtime_actions", "runtime_observations", "runtime_model_calls", "runtime_report_attempts"))
        source_reads = [sql for sql in statements if "from runtime_forms" in sql.lower()]
        assert len(source_reads) == 1
        assert "select *" not in source_reads[0].lower()

        changed = deepcopy(context.as_record())
        changed["request"]["message"]["initial_report"] = {"qualification": "changed"}
        with pytest.raises(ValueError, match="scientific_provenance_original_request_mismatch"):
            provenance.frozen_results(BindingContext(**changed))
        missing = saved_context(store, journal, key="not-saved", save=False,
                                scope=context.as_record()["scope"])
        with pytest.raises(ValueError, match="scientific_provenance_saved_owner_required"):
            provenance.frozen_results(missing)


def test_service_port_uses_qualified_provenance_and_rejects_wrong_run(tmp_path):
    with Store(tmp_path / "state") as store:
        journal = Journal(store, "frozen-source-fixture")
        context = saved_context(store, journal)
        close_source(journal, context, {"scientific_process_results": []})
        provenance = ScientificProcessProvenance(store, journal, library=None)
        services = WorkflowServices(SimpleNamespace(run_id=journal.run_id,
            scientific_provenance=provenance))
        assert services.scientific_frozen_results(context) == []
        changed = context.as_record()
        changed["run_id"] = "another-run"
        with pytest.raises(ValueError, match="scientific_provenance_receiver_identity_mismatch"):
            services.scientific_frozen_results(BindingContext(**changed))
