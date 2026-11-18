"""Synthetic A106 scoring and custody tests, not a live biological demonstration."""
from copy import deepcopy
from dataclasses import replace
import json

import pytest

from gene_annotation_episode.episodic_workflow.root.a106.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a106.state import Store
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_subscore import finalize_a106, SCORE_COMPONENT, REQUESTED, COMPONENTS, cells_schema
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
from gene_annotation_episode.episodic_workflow.root.a106.tests.test_literature_intervention_storage import intervention_fixture


def final_arguments(store, args, sheet_ref):
    return dict(subject_ref=store.get(args["assertion_ref"])["subject_refs"][0],
        assertion_ref=args["assertion_ref"], comparison_ref=args["comparison_ref"],
        scope_statement="Synthetic stipulated model only.",
        experiments=[dict(experiment_ref=args["experiment_ref"], sheet_ref=sheet_ref, missing_reason=None)],
        dependence=dict(status="unknown", rationale="One experiment", witnesses=[]),
        conclusion="Engineered evidence favors the assertion.", limitations=["No biological evidence."],
        revises_subscore_ref=None, revision_reason=None)


def prepared(store):
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    context, args = intervention_fixture(store)
    native = LiteratureInterventionRepository(store, context.run_id)
    first = native.populate(context, args, "assessment")
    ref = first["result"]["sheet_ref"]
    context = replace(context, received_record_refs=[*context.received_record_refs, ref],
        assignment={**context.assignment, REQUESTED: list(COMPONENTS)})
    rows = native.fact_cells(context, [ref], components=[SCORE_COMPONENT])
    return context, args, final_arguments(store, args, ref), rows


def commissioned(store, context, proposal, *, axis='A106'):
    from gene_annotation_episode.episodic_workflow.root.a106.communication import plain
    from gene_annotation_episode.episodic_workflow.root.a106.episode_journal import Journal
    from gene_annotation_episode.episodic_workflow.root.a106.method_loop.identities import EpisodeRef
    path = (('perturbation_evidence', axis + '-original-commission'),)
    identity = EpisodeRef(context.run_id, path).episode_id
    assignment = {'selection': {'evidence_axis': {'option_id': axis}}, 'proposed_annotation_ref': proposal}
    Journal(store, context.run_id).save('runtime_episodes', {'episode_id': identity,
        'path': json.dumps(path), 'request': json.dumps({'message': {
            'scope': plain(context.scope), 'episode_assignment': assignment}}),
        'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
    return replace(context, path=(*path, *context.path),
        assignment={**context.assignment, 'proposed_annotation_ref': proposal})


def test_automatic_judgment_initial_revision_provenance_and_replay(tmp_path):
    with Store(tmp_path) as store:
        context, assessment, arguments, _ = prepared(store)
        context = commissioned(store, context, assessment['assertion_ref'])
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        request, = repo.prepare_judgments(context)
        assert 'completed_outcome' not in request
        assert request['context']['previous_final_bindings'] == []
        assert 'source_bodies' not in request['context']
        outcome = repo.complete_judgment(context, request['judgment_ref'],
            {'selection': arguments, 'unresolved_reasons': []}, provenance={'provider': 'scripted-test'})
        final = outcome['result']['sheet_ref']
        assert outcome['result']['cells'][0]['value'] == pytest.approx(7.5)
        again, = repo.prepare_judgments(context)
        assert again['completed_outcome'] == outcome
        saved = store.db.execute(f'SELECT response,provenance FROM {repo.judgment_table}').fetchone()
        assert json.loads(saved['response'])['selection'] == arguments
        assert json.loads(saved['provenance']) == {'provider': 'scripted-test'}
        revised = deepcopy(assessment)
        revised['experiment_assessment'].update(revises_sheet_ref=arguments['experiments'][0]['sheet_ref'],
            revision_reason='Synthetic attribution limitation')
        revised['interpretations']['attribution_supported'] = {'status': 'unknown', 'support_refs': []}
        context = replace(context, received_record_refs=(*context.received_record_refs, final))
        native = LiteratureInterventionRepository(store, context.run_id)
        change = native.populate(context, revised, 'revision-for-automatic-judgment')
        assert repo.current_annotation_cells(context) == []
        assert change['record_refs'] == [change['result']['sheet_ref']]
        request2, = repo.prepare_judgments(context)
        assert request2['judgment_ref'] != request['judgment_ref']
        revised_selection = deepcopy(arguments)
        revised_selection['experiments'][0]['sheet_ref'] = change['result']['sheet_ref']
        revised_selection.update(revises_subscore_ref=final, revision_reason='Use the revised current assessment')
        replacement = repo.complete_judgment(context, request2['judgment_ref'],
            {'selection': revised_selection, 'unresolved_reasons': []}, provenance={'provider': 'scripted-test'})
        assert replacement['status'] == 'completed'
        assert replacement['result']['cells'][0]['value'] is None
        assert replacement['result']['cells'][0]['dependence'] == arguments['dependence']
        assert repo.read(final)['sheet']['cells'][COMPONENTS[0]]['value'] == pytest.approx(7.5)


@pytest.mark.parametrize('failure', ['interrupted', 'invented_witness', 'unresolved'])
def test_automatic_judgment_failure_is_unresolved_without_another_call(tmp_path, failure):
    with Store(tmp_path) as store:
        context, assessment, arguments, _ = prepared(store)
        context = commissioned(store, context, assessment['assertion_ref'])
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        request, = repo.prepare_judgments(context)
        if failure == 'interrupted':
            recovered, = repo.prepare_judgments(context)
            result = recovered['completed_outcome']
            assert result['feedback']['code'] == 'a106_judgment_dispatch_interrupted'
        else:
            if failure == 'invented_witness':
                arguments['dependence']['witnesses'] = [{'source_ref': assessment['source_ref'],
                    'representation': 'original', 'start': 0, 'end': 4, 'quote': 'fake'}]
                response = {'selection': arguments, 'unresolved_reasons': []}
            else:
                response = {'selection': None, 'unresolved_reasons': ['Biological scope is unresolved.']}
            result = repo.complete_judgment(context, request['judgment_ref'], response,
                provenance={'provider': 'scripted-test'})
        assert result['status'] == 'unavailable'
        assert repo.current_annotation_cells(context) == []
        assert repo.prepare_judgments(context)[0]['completed_outcome'] == result
        scalar, _ = repo.annotation_contribution(store, context, target=arguments['subject_ref'],
            annotation=store.get(arguments['assertion_ref']), scope=context.scope)
        assert scalar['value'] is None and result['feedback']['code'] in scalar['missing_inputs']
        if failure == 'unresolved':
            assert 'Biological scope is unresolved.' in scalar['transfer']['missing_inputs']


def test_automatic_judgment_requires_original_a106_proposal_and_actual_cells(tmp_path):
    with Store(tmp_path) as store:
        context, assessment, _arguments, _ = prepared(store)
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        assert repo.prepare_judgments(context) == []
        received = commissioned(store, replace(context, episode_id='unreceived-parent'), assessment['assertion_ref'])
        assert repo.prepare_judgments(received) == []
        changed = commissioned(store, context, assessment['assertion_ref'], axis='A108')
        assert repo.prepare_judgments(changed) == []


def test_final_score_is_the_existing_signed_ratio_and_is_not_a_probability(tmp_path):
    with Store(tmp_path) as store:
        _, _, args, rows = prepared(store)
        cell = finalize_a106(args, rows)
        assert cell["value"] == pytest.approx(7.5)
        assert cell["status"] == "complete" and cell["annotation_credit"] is None
        rows[0]["value"] = -7.5
        assert finalize_a106(args, rows)["value"] == -7.5


def test_unavailable_assessment_feedback_keeps_the_typed_sheet_selection(tmp_path):
    with Store(tmp_path) as store:
        _, _, args, rows = prepared(store)
        rows[0].update(value=None, status="unavailable")
        args["experiments"][0]["missing_reason"] = "The selected assessment has unresolved inputs."
        with pytest.raises(ContractError, match="existing_assessment_requires_null_missing_reason") as caught:
            finalize_a106(args, rows)
        assert caught.value.detail["field"] == "experiments.0.missing_reason"
        assert caught.value.detail["sheet_ref"] == rows[0]["sheet_ref"]
        args["experiments"][0]["missing_reason"] = None
        final = finalize_a106(args, rows)
        assert final["value"] is None and final["selected_components"] == rows
        assert final["experiments"][0]["sheet_ref"] == rows[0]["sheet_ref"]


def test_scope_change_reports_question_mismatch_without_rewriting_predecessor(tmp_path):
    with Store(tmp_path) as store:
        context, _, args, _ = prepared(store)
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        first = repo.populate(context, args, "first-scope")
        ref = first["result"]["sheet_ref"]
        context = replace(context, received_record_refs=[*context.received_record_refs, ref])
        proposed = deepcopy(args)
        proposed.update(scope_statement="A different synthetic biological scope.",
            revises_subscore_ref=ref, revision_reason="Attempted scope expansion")
        with pytest.raises(ContractError, match="revision_question_mismatch") as caught:
            repo.populate(context, proposed, "changed-scope")
        assert caught.value.detail["different_fields"] == ["scope_statement"]
        assert caught.value.detail["previous_question"]["scope_statement"] == args["scope_statement"]
        assert repo.read(ref)["selection"] == args
        # Keep the original question when the intended correction is its conclusion.
        proposed.update(scope_statement=args["scope_statement"], conclusion="Corrected conclusion within the original scope.")
        corrected = repo.populate(context, proposed, "corrected-conclusion")
        saved = repo.read(corrected["result"]["sheet_ref"])
        assert saved["selection"]["revises_subscore_ref"] == ref
        assert saved["selection"]["scope_statement"] == args["scope_statement"]


def test_missing_conflicting_and_duplicate_evidence_preserve_their_meaning(tmp_path):
    with Store(tmp_path) as store:
        _, _, args, rows = prepared(store)
        second = deepcopy(rows[0])
        second.update(sheet_ref="source_" + "b" * 24, experiment_ref="reference_" + "b" * 24,
            value=-2., evidence_measurement_keys=["independent_observed_measurement"])
        args["experiments"].append(dict(experiment_ref=second["experiment_ref"],
            sheet_ref=second["sheet_ref"], missing_reason=None))
        unknown = finalize_a106(args, [*rows, second])
        assert unknown["value"] is None and unknown["available_value"] is None
        args["dependence"] = dict(status="independent", rationale="Stipulated independent biological units",
            witnesses=[dict(source_ref=rows[0]["evidence_source_ref"], representation="original", start=0, end=1, quote="E")])
        assert finalize_a106(args, [*rows, second])["value"] == pytest.approx(5.5)
        second["evidence_measurement_keys"] = rows[0]["evidence_measurement_keys"]
        shared = finalize_a106(args, [*rows, second])
        assert shared["value"] is None and "shared_observed_measurement" in shared["unavailable_reasons"]
        second["evidence_measurement_keys"] = ["independent_observed_measurement"]
        second.update(value=None, status="unavailable")
        partial = finalize_a106(args, [*rows, second])
        assert partial["value"] is None and partial["available_value"] == pytest.approx(7.5)
        args["experiments"].append(deepcopy(args["experiments"][0]))
        with pytest.raises(ContractError, match="duplicate_experiment"):
            finalize_a106(args, [*rows, second])


def test_final_custody_revisions_missing_experiments_and_cold_replay(tmp_path, monkeypatch):
    with Store(tmp_path) as store:
        context, assessment, args, rows = prepared(store)
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        final = repo.populate(context, args, "final")
        ref = final["result"]["sheet_ref"]
        assert final["result"]["cells"][0]["value"] == pytest.approx(7.5)
        assert repo.populate(context, args, "final") == final
        with pytest.raises(ContractError, match="latest_subscore_revision"):
            repo.populate(context, args, "duplicate")
        parent = replace(context, episode_id="parent", role="annotation", path=(("annotation", "parent"),),
            received_record_refs=[*context.received_record_refs, ref])
        delivered = final["result"]["cells"]
        repo.receive_cells(parent, delivered, "delivery")
        assert repo.fact_cells(parent, [ref], components=list(COMPONENTS)) == delivered
        # A source handle does not give another episode a private numeric cell.
        stranger = replace(parent, episode_id="stranger", path=(("annotation", "stranger"),))
        with pytest.raises(ContractError, match="component_not_received"):
            repo.populate(stranger, args, "unreceived")
        revision = deepcopy(assessment)
        revision["experiment_assessment"].update(revises_sheet_ref=rows[0]["sheet_ref"], revision_reason="Resolve a conflict")
        revision["interpretations"]["attribution_supported"] = dict(status="unknown", support_refs=[])
        native = LiteratureInterventionRepository(store, context.run_id)
        changed = native.populate(context, revision, "changed")
        context = replace(context, received_record_refs=[*context.received_record_refs, ref, changed["result"]["sheet_ref"]])
        args.update(revises_subscore_ref=ref, revision_reason="Use the revised experiment assessment")
        with pytest.raises(ContractError, match="current_assessment_required"):
            repo.populate(context, args, "stale-assessment")
        args["experiments"][0]["sheet_ref"] = changed["result"]["sheet_ref"]
        updated = repo.populate(context, args, "updated")
        assert updated["result"]["cells"][0]["value"] is None
        assert repo.read(ref)["sheet"]["cells"][COMPONENTS[0]]["value"] == pytest.approx(7.5)
    def forbidden(*args, **kwargs):
        raise AssertionError("saved final replay recalculated science")
    monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.a106.library.literature_a106_subscore_storage.finalize_a106', forbidden)
    monkeypatch.setattr(LiteratureInterventionRepository, "grade", forbidden)
    with Store(tmp_path) as store:
        store.db.execute("PRAGMA query_only=ON")
        repo = LiteratureA106SubscoreRepository(store, context.run_id)
        assert repo.fact_cells(parent, [ref], components=list(COMPONENTS)) == delivered


@pytest.mark.parametrize("repair_support", [False, True])
def test_runtime_rejects_score_only_a106_child_without_investigation_task(tmp_path, repair_support):
    from ..communication import plain
    from ..investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from .literature_admission_fixtures import admit_original_literature_credit, selected_work_rows

    with Store(tmp_path / 'state') as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args = intervention_fixture(store)
        assignment = {**plain(context.assignment), REQUESTED: list(COMPONENTS)}
        invalid_support = deepcopy(args)
        invalid_support['interpretations']['measurement_identity']['support_refs'] = [args['source_ref']]
        attempted_arguments = invalid_support if repair_support else args
        assert attempted_arguments['source_ref'] == args['source_ref']
        assert 'literature_task' not in assignment
        before_work=selected_work_rows(store,context.run_id)
        with pytest.raises(ContractError, match='literature_original_task_credit_required'):
            admit_original_literature_credit(store, replace(context, assignment=assignment))
        # Neither prospective payload is executed when the commission lacks its
        # original scientific task. Executed invalid results have separate tests.
        assert selected_work_rows(store,context.run_id)==before_work
        assert not store.db.execute("SELECT 1 FROM sqlite_master WHERE name IN "
            "('literature_intervention_grading_operations','literature_a106_subscore_received')").fetchone()
        credit = ScientificFindingProgress(FindingProgressPolicy(1))
        assert credit(store, plain(context.scope), known_assessment_refs=())['credit'] == 0
