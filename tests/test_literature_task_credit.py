"""Explicit fixture units exercise commissioned answers, not production cutoffs."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError, canonical, obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_task_credit import (
    VERSION, SCREENING, LEADS, commissioned_task, screening_schema, lead_return_schema,
)
from gene_annotation_episode.state import Store
from test_investigation_progress import put_finding
from test_scientific_findings import target_question, quoted_observation
from test_literature_a105_aggregation_325 import parent_fixture, COMPONENTS
from test_literature_assay_experiment_instances_323 import two_experiments


def commission(context, task, proposed, returned, **assignment):
    task = {'version': VERSION, 'evidence_axis': 'A105', 'credit_unit': 7, **task}
    assignment = {**plain(context.assignment), **assignment,
        'literature_task': task, 'proposed_annotation_ref': proposed}
    request = {'goal': {'objective': 'Answer the declared source question', 'goal_id': 'test-task'},
        'message': {'episode_assignment': assignment, 'initial_report': {}},
        'report_contract': {'decision': 'Use the commissioned answer', 'measurements': {'schema': obj({'answer': returned})}}}
    return replace(context, assignment=assignment, request=request)


def binding(store, context, **options):
    from gene_annotation_episode.tools import ToolRegistry
    services = WorkflowServices(SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store)))
    return LiteratureEpisodes(services, **options)


def project(owner, context, store, known):
    request = plain(context.request)
    args = {'goal': request['goal'], 'scope': plain(context.scope),
        'purpose': request['report_contract']['decision'],
        'schema': request['report_contract']['measurements']['schema'],
        'initial_report': request['message']['initial_report'],
        'proposed_annotation_ref': context.assignment['proposed_annotation_ref']}
    return owner.credit_projector(context)(store, plain(context.scope), known_record_refs=known,
        assignment=args, run_id=context.run_id, episode_id=context.episode_id)


def assessment_return():
    return {'type': 'array', 'items': {'type': 'string', 'format': 'reference'},
        'x-source': 'changed_assessment_refs'}


def question_fixture(store):
    _, proposed = target_question(store)
    subject, observation = quoted_observation(store, accession='task', start=0, end=17)
    context = BindingContext('task-run', 'reader', 'literature', (('literature', 'reader'),),
        store.validate_scope(), {'version': 'literature_assignment_v1',
            'question_context_refs': [proposed], 'source_refs': [observation['source_ref']]}, {})
    return context, proposed, subject, observation


def target_experiments(store):
    context, first, second = two_experiments(store)
    source_claim = store.get(first['assertion_ref'])
    proposed = store.put('hypothesis', {**{key: source_claim[key]
        for key in ('predicate', 'value', 'context_refs')},
        'subject_refs': list(store.validate_scope()['subject_refs'])}, origin='reasoning')['id']
    first['assertion_ref'] = second['assertion_ref'] = proposed
    return replace(context, received_record_refs=(*context.received_record_refs, proposed)), first, second


def test_explicit_original_task_return_axis_and_unit_are_required(tmp_path):
    with Store(tmp_path) as store:
        context, proposed, _, observation = question_fixture(store)
        owner = binding(store, context)
        with pytest.raises(ContractError, match='original_task_credit_required'):
            owner.credit_projector(context)
        task = {'kind': 'source_answer', 'answer_kind': 'assessment', 'source_refs': [observation['source_ref']]}
        context = commission(context, task, proposed, assessment_return())
        assert owner.continuation_task(context) == 'A105:source_answer:assessment'
        policy = owner.credit_projector(context).as_record()
        assert policy['credit_unit'] == 7 and proposed not in canonical(policy)
        wrong = commission(context, task, proposed, {'type': 'array', 'items': {'type': 'string'}, 'x-source': 'source_refs'})
        with pytest.raises(ContractError, match='typed_return_mismatch'):
            owner.credit_projector(wrong)
        altered = replace(context, assignment={**plain(context.assignment), 'proposed_annotation_ref': 'hypothesis_other'})
        with pytest.raises(ContractError, match='original_commission_mismatch'):
            owner.credit_projector(altered)
        other_axis = commission(context, {**task, 'evidence_axis': 'A106'}, proposed, assessment_return())
        with pytest.raises(ContractError, match='original_axis_mismatch'):
            binding(store, context, rate_population=True, assay_grading_population=True).credit_projector(other_axis)


def test_only_exact_native_lead_and_screening_return_schemas_are_admitted():
    from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema
    for factory in (lead_return_schema, screening_schema):
        validate_closed_schema(obj({'answer': factory()}))
        altered = factory()
        altered['items']['properties']['unverified_free_text'] = {'type': 'string'}
        with pytest.raises(ReportBoundaryError, match='must match its registered source'):
            validate_closed_schema(obj({'answer': altered}))


def test_source_answer_counts_once_and_loses_withdrawn_assessment(tmp_path):
    with Store(tmp_path) as store:
        context, proposed, subject, observation = question_fixture(store)
        first = put_finding(store, proposed, observation, subject)
        context = commission(context, {'kind': 'source_answer', 'answer_kind': 'assessment',
            'source_refs': [observation['source_ref']]}, proposed, assessment_return())
        owner = binding(store, context)
        assert project(owner, context, store, [observation['source_ref']])['credit'] == 0
        assert project(owner, context, store, [first['id']])['credit'] == 7
        second = put_finding(store, proposed, observation, subject, revision=first['revision'],
            qualification='measurement_does_not_establish_claim')
        assert project(owner, context, store, [first['id'], second['id']])['credit'] == 7
        put_finding(store, proposed, observation, subject, revision=second['revision'], withdraw=True)
        assert project(owner, context, store, [first['id'], second['id']])['credit'] == 0


def test_search_hits_are_not_verified_leads_and_original_witnessed_judgment_is_required(tmp_path):
    with Store(tmp_path) as store:
        context, proposed, subject, observation = question_fixture(store)
        context = commission(context, {'kind': 'verified_source_leads'}, proposed,
            lead_return_schema())
        known = [proposed, subject, observation['source_ref']]
        context = replace(context, received_record_refs=tuple(known))
        owner = binding(store, context)
        assert project(owner, context, store, known)['credit'] == 0
        journal = Journal(store, context.run_id)
        selected = {'kind': 'reason', 'commit': {key: [] for key in store.reasoning_schema()['required']},
            'source_lead': {'proposed_annotation_ref': proposed, 'source_ref': observation['source_ref'],
                'subject_ref': subject, 'disposition': 'relevant',
                'relevance_rationale': 'Synthetic source describes the subject of the assigned question.',
                'witness': {key: observation['anchor'][key] for key in ('source_ref', 'start', 'end', 'quote')}}}
        selected['source_lead']['witness']['representation'] = 'original'
        bad = deepcopy(selected)
        bad['source_lead']['witness']['quote'] = 'not in source'
        assert owner.execute_reasoning(context, bad, 'bad-lead')['status'] == 'invalid'
        assert project(owner, context, store, known)['credit'] == 0
        outcome = owner.execute_reasoning(context, selected, 'lead')
        assert outcome['status'] in ('completed', 'partial'), outcome
        for index in range(2):
            journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
                'action': canonical(selected), 'result': canonical(outcome)})
        assert project(owner, context, store, known)['credit'] == 7
        returned = owner.facts(context, {'committed_record_refs': []})[LEADS]
        assert returned == [outcome['literature_source_lead']]
        from gene_annotation_episode.communication import ReportBoundaryError, validate_form
        with pytest.raises(ReportBoundaryError, match='reference is unavailable'):
            validate_form({'leads': returned}, obj({'leads': lead_return_schema()}),
                lambda ref, namespace: ref != subject)
        changed = deepcopy(returned)
        changed[0]['relevance_rationale'] = 'An invented reason absent from saved work.'
        with pytest.raises(ReportBoundaryError, match='differs from its original saved work'):
            owner.validate_received_report(context, {'leads': changed}, obj({'leads': lead_return_schema()}))
        assert not store.db.execute("SELECT 1 FROM records WHERE record_type='assessment'").fetchone()
        selected['source_lead']['disposition'] = 'not_relevant'
        withdrawn = owner.execute_reasoning(context, selected, 'withdraw-lead')
        journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': 2,
            'action': canonical(selected), 'result': canonical(withdrawn)})
        assert project(owner, context, store, known)['credit'] == 0


def test_screening_uses_authenticated_original_disposition_not_bytes_or_repeats(tmp_path):
    from gene_annotation_episode.literature_required_grading import execute
    from gene_annotation_episode.literature_assay_grading_storage import LiteratureAssayGradingRepository
    with Store(tmp_path) as store:
        context, proposed, _, observation = question_fixture(store)
        source = store.get(observation['source_ref'])
        span = {key: observation['anchor'][key] for key in ('source_ref', 'artifact_ref', 'start', 'end')}
        context = commission(context, {'kind': 'source_answer', 'answer_kind': 'screening', 'examined': [span]},
            proposed, screening_schema())
        context = replace(context, received_record_refs=(source['id'], proposed))
        owner = binding(store, context)
        journal = Journal(store, context.run_id)
        assert project(owner, context, store, list(context.received_record_refs))['credit'] == 0
        selection = {'kind': 'reason', 'commit': {key: [] for key in store.reasoning_schema()['required']},
            'evidence_processing': {'kind': 'no_applicable_evidence', 'reason': 'Synthetic screening disposition',
                'examined': [{'source_ref': source['id'], 'representation': 'original',
                    'start': span['start'], 'end': span['end'], 'quote': observation['anchor']['quote']}]}}
        outcome = execute(context, selection, 'screen', LiteratureAssayGradingRepository(store, context.run_id),
            authorize_source_access=lambda *args: None)
        assert outcome['status'] in ('completed', 'partial')
        for index in range(2):
            journal.save('runtime_actions', {'episode_id': context.episode_id, 'decision_index': index,
                'action': canonical(selection), 'result': canonical(outcome)})
        result = project(owner, context, store, list(context.received_record_refs))
        assert result['credit'] == 7
        assert result['source_contributions'][0]['annotation_support'] == 'not_assessed'
        assert not store.db.execute("SELECT 1 FROM records WHERE record_type='assessment'").fetchone()
        assert owner.facts(context, {'committed_record_refs': []})[SCREENING] == result['source_contributions']
        from gene_annotation_episode.communication import ReportBoundaryError, validate_form
        with pytest.raises(ReportBoundaryError, match='reference is unavailable'):
            validate_form({'screening': result['source_contributions']}, obj({'screening': screening_schema()}),
                lambda ref, namespace: ref != span['artifact_ref'])


def test_lead_only_reason_with_existing_subject_enters_original_runtime_action(tmp_path):
    import asyncio
    import json
    from functools import partial
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.runtime import Workflow
    from gene_annotation_episode.tools import ToolRegistry
    from test_runtime import FixtureController, ScriptedProvider
    with Store(tmp_path / 'state') as store:
        context, proposed, subject, observation = question_fixture(store)
        known = [proposed, subject, observation['source_ref']]
        context = commission(context, {'kind': 'verified_source_leads'}, proposed, lead_return_schema())
        workflow = Workflow(store, ToolRegistry(store), ScriptedProvider([]), tmp_path / 'runtime', 'lead-runtime',
            lambda path, initial: FixtureController(str(path), initial, 1),
            ScientificFindingProgress(FindingProgressPolicy(1)), episode_record_receipts=True,
            initial_known_record_refs=known, episode_binding_factories=(partial(LiteratureEpisodes),))
        root = workflow.build('annotation', 'root', 'Find useful literature', store.validate_scope())
        unit = workflow.selected(root.source, {'kind': 'episode_child', 'role': 'literature',
            'assignment': plain(context.assignment), 'goal': 'Verify a useful source for the proposed annotation',
            'scope': store.validate_scope(), 'purpose': 'Use verified source leads',
            'schema_json': json.dumps(obj({'leads': lead_return_schema()})), 'initial_report_json': '{}'}, 0)
        child = unit.child.source
        selection = {'kind': 'reason', 'commit': {key: [] for key in store.reasoning_schema()['required']},
            'source_lead': {'proposed_annotation_ref': proposed, 'source_ref': observation['source_ref'],
                'subject_ref': subject, 'disposition': 'relevant', 'relevance_rationale': 'Synthetic verified source lead.',
                'witness': {**{key: observation['anchor'][key] for key in ('source_ref', 'start', 'end', 'quote')},
                    'representation': 'original'}}}
        accepted = child.apply_response({'selection': selection, 'report_update': {}}, 0,
            {'visible_record_refs': known}, workflow.action_schema(child))
        assert accepted is not None, child.feedback
        asyncio.run(child.execute(selection, 0))
        action = workflow.journal.row('runtime_actions', child.episode_id, 0)
        assert action['credit'] == 7
        assert json.loads(action['result'])['literature_source_lead']['subject_ref'] == subject
        assert not store.db.execute("SELECT 1 FROM records WHERE record_type='assessment'").fetchone()


def test_a105_experiment_needs_current_typed_assessment_and_correct_grader(tmp_path):
    from gene_annotation_episode.literature_assay_grading_storage import (
        LiteratureAssayGradingRepository, assay_grading_cells_schema,
    )
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        original, first, second = target_experiments(store)
        repo = LiteratureAssayGradingRepository(store, original.run_id)
        outcomes = [repo.populate(original, args, str(index)) for index, args in enumerate((first, second))]
        proposed = first['assertion_ref']
        context = commission(original, {'kind': 'a105_experiments', 'experiments': [
            {'experiment_ref': args['experiment_ref'], 'assay_type': args['assay_type']} for args in (first, second)]},
            proposed, assay_grading_cells_schema())
        owner = binding(store, context, rate_population=True, assay_grading_population=True)
        known = [*original.received_record_refs, *(ref for outcome in outcomes for ref in outcome['record_refs'])]
        assert project(owner, context, store, known)['credit'] == 0
        for args in (first, second):
            experiment = store.get(args['experiment_ref'])
            observation = store.put('observation', {'subject_refs': [args['experiment_ref']],
                'source_subject_refs': [args['experiment_ref']], 'kind': 'source_content',
                'source_ref': args['source_ref'], 'measurements': [], 'dependencies': [],
                'anchor': experiment['anchor']}, origin='extracted')
            assessment = put_finding(store, proposed, observation, args['experiment_ref'])
            known.append(assessment['id'])
        assert project(owner, context, store, known)['credit'] == 14
        again = repo.populate(original, first, 'same-experiment-revision')
        known.extend(again['record_refs'])
        assert project(owner, context, store, known)['credit'] == 14


def test_a105_assembly_is_one_answer_for_exact_roster_and_requested_metrics(tmp_path, monkeypatch):
    from gene_annotation_episode.literature_a105_aggregation_storage import (
        LiteratureA105AggregationRepository, aggregation_cells_schema,
    )
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        monkeypatch.setattr('test_literature_a105_aggregation_325.two_experiments', target_experiments)
        original, args, native, _ = parent_fixture(store)
        repo = LiteratureA105AggregationRepository(store, original.run_id,
            read_cells=lambda ctx, ref, components: native.fact_cells(ctx, [ref], components=components))
        task = {'kind': 'a105_assembly', 'experiment_refs': [item['experiment_ref'] for item in args['experiments']],
            'metrics': list(COMPONENTS)}
        context = commission(original, task, args['assertion_ref'], aggregation_cells_schema())
        owner = binding(store, context, rate_population=True, assay_grading_population=True)
        from gene_annotation_episode.literature_sheet_updates import current_sheet_refs
        scaffold_refs = current_sheet_refs(store, original)
        assert project(owner, context, store, [*original.received_record_refs, *scaffold_refs])['credit'] == 0
        outcome = repo.populate(original, args, 'assemble')
        known = [*original.received_record_refs, *outcome['record_refs']]
        assert project(owner, context, store, known)['credit'] == 7
        different = commission(context, {**task, 'experiment_refs': task['experiment_refs'][:1]},
            args['assertion_ref'], aggregation_cells_schema())
        assert project(owner, different, store, known)['credit'] == 0
        narrower = aggregation_cells_schema()
        narrower['items']['properties']['component']['enum'] = ['overall']
        with pytest.raises(ContractError, match='return_components_mismatch'):
            commissioned_task(commission(context, task, args['assertion_ref'], narrower))


@pytest.mark.parametrize('unreported_spread', [False, True])
def test_reported_quantity_answer_preserves_unknown_spread_and_counts_once(tmp_path, monkeypatch, unreported_spread):
    from gene_annotation_episode.literature_quantity_storage import LiteratureQuantityRepository, quantity_cells_schema
    from test_literature_quantity_integration import setup_store
    if unreported_spread:
        import test_literature_quantity_integration as fixture
        monkeypatch.setattr(fixture, 'SYNTHETIC', fixture.SYNTHETIC.replace(' ± 2', ''))
    store, original, selection = setup_store(tmp_path)
    with store:
        target = store.validate_scope()['subject_refs'][0]
        proposed = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'biological_role',
            'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}, origin='reasoning')['id']
        repo = LiteratureQuantityRepository(store, original.run_id)
        outcome = repo.populate(original, selection, 'measurement')
        task = {'kind': 'source_answer', 'answer_kind': 'measurement', 'selection': selection,
            'components': ['reported_value', 'reported_spread']}
        context = commission(original, task, proposed, quantity_cells_schema(),
            requested_quantity_components=task['components'])
        owner = binding(store, context, rate_population=True)
        owner.services.literature_quantity_repository = lambda: repo
        known = [*original.received_record_refs, proposed, *outcome['record_refs']]
        assert project(owner, context, store, known)['credit'] == 7
        outsider = replace(context, episode_id='other', path=(('literature', 'other'),))
        assert project(owner, outsider, store, known)['credit'] == 0
