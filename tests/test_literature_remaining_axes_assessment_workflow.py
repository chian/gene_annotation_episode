"""Real episode accounting and typed parent delivery of revised experiments."""
import asyncio
from copy import deepcopy
from dataclasses import replace
from functools import partial
import json

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.tools import ToolRegistry
from test_literature_perturbation_assessments import identify
from test_runtime import FixtureController, ScriptedProvider


def case_for(axis, path):
    if axis == 'A106':
        from test_literature_perturbation_integration import setup_case
        from gene_annotation_episode.literature_perturbation_storage import LiteraturePerturbationRepository as Repo, perturbation_cells_schema as schema
        return (*setup_case(path), Repo, schema, 'perturbation', 'intervention_response')
    if axis == 'A110':
        from test_literature_reaction_integration import setup_case
        from gene_annotation_episode.literature_reaction_storage import LiteratureReactionRepository as Repo, reaction_cells_schema as schema
        return (*setup_case(path), Repo, schema, 'reaction', 'reaction_prediction')
    if axis == 'A111':
        from test_literature_structure_integration import setup_case
        from gene_annotation_episode.literature_structure_storage import LiteratureStructureRepository as Repo, structure_cells_schema as schema
        return (*setup_case(path), Repo, schema, 'structure', 'structural_feature_geometry')
    from test_literature_partner_integration import setup_case
    from gene_annotation_episode.literature_partner_storage import LiteraturePartnerRepository as Repo, partner_cells_schema as schema
    return (*setup_case(path, case='matched'), Repo, schema, 'partner', 'partner_requirement')


@pytest.mark.parametrize('axis', ['A106', 'A110', 'A111', 'A107'])
def test_two_selected_assessments_reach_parent_as_one_experiment_without_synthetic_credit(tmp_path, axis):
    store, context, args, Repo, schema, family, experiment_type = case_for(axis, tmp_path/'state')
    try:
        context, args = identify(store, context, args, axis+'-fixture-experiment')
        args['experiment_assessment']['experiment_type'] = experiment_type
        form = obj({'measurements': schema()})
        tool = 'literature.'+family+'.populate'
        selected_refs, received = [], []
        def revise(inputs):
            outcome = inputs['last_local_outcome']
            assert outcome['status'] == 'completed'
            selected_refs.append(outcome['result']['sheet_ref'])
            revised = deepcopy(args)
            revised['experiment_assessment'].update(revises_sheet_ref=selected_refs[-1],
                revision_reason='Qualify the inference within its actual experimental scope.',
                conclusion='The numerical result is conditional on the recorded experimental scope.')
            return {'selection': {'kind': 'tool', 'tool': tool, 'arguments': revised}, 'report_update': {}}
        def receive(inputs):
            report, = inputs['child_reports']
            rows = report['measurements']
            received.append(rows)
            assert rows and any(row['value'] is not None for row in rows)
            assert {row['experiment_ref'] for row in rows} == {args['experiment_assessment']['experiment_ref']}
            # Raw historical sheets remain addressable. One canonical assay
            # identity, and one current assessment, prevent revision counting.
            actual_run = store.db.execute('SELECT run_id FROM runtime_episodes LIMIT 1').fetchone()[0]
            repo = Repo(store, actual_run)
            current, = repo.current_assessments()
            assert len(repo.assessment_history(current['sheet_ref'])) == 2
            assert current['sheet_ref'] in {row['sheet_ref'] for row in rows}
            witness = next(value for value in args['literals'].values() if value is not None)
            source = store.get(witness['source_ref'])
            artifact = source['artifact_ref'] if witness['representation'] == 'original' else source['text_ref']
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['source_subjects'] = [{'alias': 'measured_source_subject', 'reference_type': 'assay',
                'source_ref': source['id'], 'label': witness['quote'], 'anchor': {
                    'source_ref': source['id'], 'artifact_ref': artifact,
                    **{key: witness[key] for key in ('start', 'end', 'quote')}}}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        provider = ScriptedProvider([
            {'selection': {'kind': 'episode_child', 'role': 'literature',
                'assignment': plain(context.assignment), 'goal': 'Assess the measured experimental evidence',
                'scope': plain(context.scope), 'purpose': 'Return the numerical results with experiment identity',
                'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}},
            {'selection': {'kind': 'tool', 'tool': tool, 'arguments': args}, 'report_update': {}},
            revise, receive])
        scoring = ScientificFindingProgress(FindingProgressPolicy(1))
        result = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path/'run', controller_factory=lambda path, initial: FixtureController(str(path), initial, 2),
            project_credit=scoring, initial_known_record_refs=list(context.received_record_refs),
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            binding_definitions={'credit': scoring.as_record()}))
        assert len(received) == 1 and result['credit'] == 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 4
        assert store.db.execute(f'SELECT count(*) FROM literature_{family}_operations').fetchone()[0] == 2
        assert not store.list('observation') and not store.list('assessment')
    finally:
        store.close()


@pytest.mark.parametrize('axis', ['A110', 'A111', 'A107'])
def test_shared_revision_custody_keeps_distinct_experiments(tmp_path, axis):
    store, context, args, Repo, _, _, experiment_type = case_for(axis, tmp_path/'state')
    try:
        context, args = identify(store, context, args, 'first-actual-experiment')
        args['experiment_assessment']['experiment_type'] = experiment_type
        repo = Repo(store, context.run_id)
        first = repo.populate(context, args, 'first')
        context = replace(context, received_record_refs=tuple(dict.fromkeys(
            (*context.received_record_refs, *first['record_refs']))))
        revision = deepcopy(args)
        revision['experiment_assessment'].update(
            revises_sheet_ref=first['result']['sheet_ref'],
            revision_reason='Clarify the measured endpoint.',
            conclusion='The result concerns the measured endpoint and conditions.')
        revised = repo.populate(context, revision, 'revised')
        other_context, other_args = identify(store, context, args, 'second-actual-experiment')
        other_args['experiment_assessment']['experiment_type'] = experiment_type
        other = repo.populate(other_context, other_args, 'other')
        heads = repo.current_assessments()
        assert len(heads) == len({row['experiment_ref'] for row in heads}) == 2
        assert {row['sheet_ref'] for row in heads} == {
            revised['result']['sheet_ref'], other['result']['sheet_ref']}
        assert len(repo.assessment_history(revised['result']['sheet_ref'])) == 2
        assert len(repo.assessment_history(other['result']['sheet_ref'])) == 1
    finally:
        store.close()
