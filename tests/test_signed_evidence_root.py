"""Signed root custody and runtime use; scientific examples are synthetic."""
import asyncio
from copy import deepcopy
from dataclasses import replace
import json
import math

import pytest

from method_loop.identities import EpisodeRef
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_a106_subscore import REQUESTED, COMPONENTS, SCORE_COMPONENT
from gene_annotation_episode.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.runtime import run_workflow, controller_from_settings
from gene_annotation_episode.signed_evidence_root import SignedEvidenceRootSupport
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_literature_a106_subscore import final_arguments
from test_literature_intervention_storage import intervention_fixture
from test_runtime import ScriptedProvider


def supplied_owner_contributions(monkeypatch, callback, *, axes=('A105', 'A106', 'A107', 'A108', 'A110')):
    """Explicit composition fixture; native owner behavior is tested separately."""
    from gene_annotation_episode.root_axis_receipts import axis_contribution_readers
    from gene_annotation_episode.root_axis_scalars import bind_contribution
    def readers(store, run_id):
        bound = axis_contribution_readers(store, run_id)
        for axis in axes:
            def supplied(store, context, *, annotation, target, scope, _axis=axis, **options):
                result = callback(store, context, _axis, assertion_ref=annotation['id'],
                    target=target, annotation=annotation, scope=scope, **options)
                scalar, details = result if isinstance(result, tuple) else (result, [])
                transfer = {'status': 'established' if scalar['value'] is not None else 'unresolved',
                    'missing_inputs': scalar['missing_inputs'], 'needed_refs': [], 'link_refs': []}
                return bind_contribution(scalar, annotation=annotation, subject=target, scope=scope,
                    transfer=transfer), details
            bound[axis] = supplied
        return bound
    monkeypatch.setattr('gene_annotation_episode.signed_evidence_root.axis_contribution_readers', readers)


def registered_receiver(store, run_id, name, scope):
    path = (('annotation', name),)
    identity = EpisodeRef(run_id, path).episode_id
    request = {'message': {'scope': scope, 'episode_assignment': {}}}
    journal = Journal(store, run_id)
    journal.save('runtime_episodes', {'episode_id': identity, 'path': json.dumps(path),
        'request': json.dumps(request), 'initial_credit': 0, 'state': 'active',
        'completion': None, 'archive': None})
    from gene_annotation_episode.root_axis_receipts import receiver_context
    return receiver_context(store, run_id, identity, ())


def prepared_negative_target(store):
    target, = store.create_problem(raw_sequence='ATGGCT', molecule='dna')['subject_refs']
    context, args = intervention_fixture(store)
    # Explicit synthetic target/model association, not a biological transfer.
    for name in ('assertion_ref', 'comparison_ref'):
        original = store.get(args[name])
        data = {key: value for key, value in original.items() if key not in {'id', 'record_type', 'origin'}}
        data['subject_refs'] = [target]
        args[name] = store.put('hypothesis', data, origin='reasoning')['id']
    args['quantities']['assertion_prediction'], args['quantities']['alternative_prediction'] = (
        args['quantities']['alternative_prediction'], args['quantities']['assertion_prediction'])
    context = replace(context, received_record_refs=(*context.received_record_refs,
        target, args['assertion_ref'], args['comparison_ref']))
    native = LiteratureInterventionRepository(store, context.run_id)
    assessment = native.populate(context, args, 'negative-assessment')
    assessment_ref = assessment['result']['sheet_ref']
    context = replace(context, received_record_refs=(*context.received_record_refs, assessment_ref),
        assignment={**context.assignment, REQUESTED: list(COMPONENTS)})
    final_args = final_arguments(store, args, assessment_ref)
    repo = LiteratureA106SubscoreRepository(store, context.run_id)
    final = repo.populate(context, final_args, 'negative-final')
    return target, context, args, final_args, repo, final


def test_actual_received_negative_score_is_used_but_source_handle_cannot_grant_private_cells(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, child, args, _, repo, final = prepared_negative_target(store)
        assert final['result']['cells'][0]['value'] == pytest.approx(-7.5)
        known = tuple(dict.fromkeys((*child.received_record_refs, *repo.cell_record_refs(final['result']['cells']))))
        parent = registered_receiver(store, child.run_id, 'parent', {'subject_refs': [target]})
        parent = replace(parent, received_record_refs=known)
        scorer = SignedEvidenceRootSupport(args['assertion_ref'], args['comparison_ref'])
        before = scorer(store, parent.scope, known_record_refs=known,
            run_id=parent.run_id, episode_id=parent.episode_id)
        assert before['axis_components']['A106'] is None and before['credit'] == 0
        repo.receive_cells(parent, final['result']['cells'], 'verified-manual-delivery')
        after = scorer.read_details(store, parent.scope, known_record_refs=known,
            run_id=parent.run_id, episode_id=parent.episode_id, details_offset=0, details_limit=10)
        assert after['axis_components']['A106'] == pytest.approx(math.tanh(-7.5 / 2))
        assert after['credit'] < 0
        assert after['support'] == 0
        assert after['opposition'] == pytest.approx(-math.tanh(-7.5 / 2))
        assert after['target_sheets'][target]['axis_results']['A106']['native_inputs'] == final['result']['cells'][0]
        other = registered_receiver(store, child.run_id, 'other', {'subject_refs': [target]})
        unrelated = scorer(store, other.scope, known_record_refs=known,
            run_id=other.run_id, episode_id=other.episode_id)
        assert unrelated['axis_components']['A106'] is None
        assert repo.read(final['result']['sheet_ref'])['sheet']['cells']['experimental_subscore']['value'] == final['result']['cells'][0]['value']


def test_received_revision_retires_opposition_without_rewriting_original_receipt(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, child, args, final_args, repo, original = prepared_negative_target(store)
        parent = registered_receiver(store, child.run_id, 'parent', {'subject_refs': [target]})
        known = tuple(dict.fromkeys((*child.received_record_refs, *repo.cell_record_refs(original['result']['cells']))))
        parent = replace(parent, received_record_refs=known)
        repo.receive_cells(parent, original['result']['cells'], 'first-delivery')
        changed_args = deepcopy(args)
        changed_args['experiment_assessment'].update(
            revises_sheet_ref=final_args['experiments'][0]['sheet_ref'], revision_reason='Synthetic missing attribution')
        changed_args['interpretations']['attribution_supported'] = {'status': 'unknown', 'support_refs': []}
        native = LiteratureInterventionRepository(store, child.run_id)
        revised = native.populate(child, changed_args, 'revised-assessment')
        parent = replace(parent, received_record_refs=tuple(dict.fromkeys((*known,
            *native.cell_record_refs(revised['result']['cells'])))))
        native.receive_cells(parent, revised['result']['cells'], 'assessment-correction-delivery')
        scorer = SignedEvidenceRootSupport(args['assertion_ref'], args['comparison_ref'])
        before_new_final = scorer(store, parent.scope, known_record_refs=parent.received_record_refs,
            run_id=parent.run_id, episode_id=parent.episode_id)
        assert before_new_final['axis_components']['A106'] is None
        child = replace(child, received_record_refs=(*child.received_record_refs,
            original['result']['sheet_ref'], revised['result']['sheet_ref']))
        updated = deepcopy(final_args)
        updated['experiments'][0]['sheet_ref'] = revised['result']['sheet_ref']
        updated.update(revises_subscore_ref=original['result']['sheet_ref'], revision_reason='Use current experiment')
        from test_literature_a106_subscore import commissioned
        judging = commissioned(store, child, args['assertion_ref'])
        request, = repo.prepare_judgments(judging)
        new = repo.complete_judgment(judging, request['judgment_ref'],
            {'selection': updated, 'unresolved_reasons': []}, provenance={'provider': 'scripted-test'})
        assert new['result']['cells'][0]['value'] is None
        parent = replace(parent, received_record_refs=tuple(dict.fromkeys((*known, *repo.cell_record_refs(new['result']['cells'])))))
        repo.receive_cells(parent, new['result']['cells'], 'revised-delivery')
        view = scorer(store, parent.scope, known_record_refs=parent.received_record_refs,
            run_id=parent.run_id, episode_id=parent.episode_id)
        assert view['axis_components']['A106'] is None and view['credit'] == 0
        assert repo.read(original['result']['sheet_ref'])['sheet']['cells']['experimental_subscore']['value'] == original['result']['cells'][0]['value']


@pytest.mark.parametrize('axis_values,support,opposition', [
    ({}, 0, 0),
    ({'A105': .5, 'A106': -.5}, .5, .5),
    ({'A105': -.5, 'A106': -.5}, 0, 1.25),
])
def test_runtime_passes_actual_receiver_to_annotation_channel_and_preserves_progress(
        tmp_path, monkeypatch, axis_values, support, opposition):
    from gene_annotation_episode.root_axis_scalars import AXES, _result
    # Explicit scalar fixtures isolate ordinary context/summary propagation;
    # actual native receipt admission is exercised separately above.
    def supplied_scalar(store, context, axis, **arguments):
        return _result(axis, axis_values.get(axis), formula='synthetic_context_propagation', inputs={})
    supplied_owner_contributions(monkeypatch, supplied_scalar)
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'functional_family',
            'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}, origin='reasoning')['id']
        scorer = SignedEvidenceRootSupport(hypothesis)
        progress = ScientificFindingProgress(FindingProgressPolicy(1))
        settings = {'controller': {'cost': 1., 'uncertainty_alpha': .05}}
        seen = []
        def inspect(context):
            seen.append(context)
            assert context['annotation_score'] == support - opposition
            assert context['annotation_support'] == support
            assert context['annotation_opposition'] == opposition
            assert context['annotation_evidence_vector'] == dict.fromkeys(AXES, None) | axis_values
            commit = {name: [] for name in store.reasoning_schema()['required']}
            commit['hypotheses'] = [{'alias': 'retained_candidate', 'subject_refs': [target],
                'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
                'context_refs': []}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        result = asyncio.run(run_workflow(store, ToolRegistry(store), run_dir=tmp_path / 'workflow',
            provider=ScriptedProvider([inspect]), controller_factory=controller_from_settings(settings),
            project_credit=progress, project_annotation_score=scorer,
            binding_definitions={'credit': progress.as_record(), 'annotation_score': scorer.as_record(),
                'controller': {'kind': 'synthetic_zero_gain_native_yield_check', **settings['controller']}},
            initial_known_record_refs=[store.targets()[0]['source_ref'], hypothesis],
            episode_record_receipts=True))
        assert result['annotation_score'] == support - opposition
        assert result['annotation_support'] == support
        assert result['annotation_opposition'] == opposition
        assert result['credit'] == 0
        assert result['ended_by'] == 'yield_stop'
        assert len(seen) == 1
        action = store.db.execute('SELECT result FROM runtime_actions').fetchone()[0]
        outcome = json.loads(action)
        assert outcome['status'] == 'completed'
        assert len(seen[0]['annotation_evidence_vector']) == 9
        observation = json.loads(store.db.execute('SELECT observation FROM runtime_observations').fetchone()[0])
        assert observation['step']['marginal_credit'] == 0


def test_receipt_context_cannot_be_guessed_or_replaced(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MARGK', molecule='protein')['subject_refs']
        scorer = SignedEvidenceRootSupport('hypothesis_' + 'a' * 24)
        with pytest.raises(ValueError, match='saved_context_required'):
            scorer(store, {'subject_refs': [target]}, known_record_refs=[], run_id='unregistered', episode_id='guessed')


def test_standard_case_policy_binds_signed_support_without_changing_progress_or_task_costs():
    from gene_annotation_episode.investigation_policy import create_policy
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from types import SimpleNamespace
    from gene_annotation_episode.root_axis_scalars import VERSION
    parameters = {'scientific_progress': {'finding_unit': 3, 'initial_known_record_refs': [], 'loss_preview_size': 4},
        'operational': {'registry_ref': 'synthetic-registry', 'handoff_unit': 1, 'acquired_record_unit': 1},
        'monitoring': {'information_unit': 1},
        'controller': {'cost': .001, 'cost_by_task': {'A105:whole_axis_findings': {
            'cutoff': .023, 'credit_definition': ScientificFindingProgress(FindingProgressPolicy(3)).as_record()}},
            'uncertainty_alpha': .05}}
    original = create_policy(parameters, episode_roles=('literature',))
    assert original.project_annotation_score is None
    parameters['annotation_support'] = {'version': VERSION,
        'assertion_ref': 'hypothesis_' + 'a' * 24,
        'selections': {'A105': 'source_' + 'b' * 24}}
    signed = create_policy(parameters, episode_roles=('literature',))
    parameters['annotation_support']['selections']['A105'] = 'source_' + 'c' * 24
    assert isinstance(signed.project_annotation_score, SignedEvidenceRootSupport)
    assert signed.episode_record_receipts is True
    assert signed.project_task_credit.as_record() == original.project_task_credit.as_record()
    assert signed.controller_definition == original.controller_definition
    assert signed.controller_factory((('annotation', 'root'),), 0).cost == .001
    path = (('annotation', 'root'), ('scientific_process', 'child'))
    assert signed.controller_factory(path, 0, context=SimpleNamespace(path=path),
        task_key='A105:whole_axis_findings',
        credit_definition=ScientificFindingProgress(FindingProgressPolicy(3)).as_record()).cost == .023
    assert signed.project_annotation_score.as_record()['selections']['A105'] == 'source_' + 'b' * 24


def test_qualified_source_pointer_does_not_grant_an_unreceived_assessment_body():
    from types import SimpleNamespace
    from gene_annotation_episode.component_assessment_dependencies import qualification_annotation
    class PrivateStore:
        def get(self, reference):
            raise AssertionError('An unreceived private assessment must not be read')
    context = SimpleNamespace(received_record_refs=())
    pointer = {'source_function_finding': {'assessment_ref': 'assessment_' + 'd' * 24}}
    assert qualification_annotation(PrivateStore(), context, pointer) is None
    public = {'assessment_hypothesis_ref': 'hypothesis_' + 'e' * 24}
    assert qualification_annotation(PrivateStore(), context, public) == public['assessment_hypothesis_ref']


def test_signed_root_does_not_create_interaction_between_different_original_targets(tmp_path, monkeypatch):
    with Store(tmp_path / 'state') as store:
        fasta = tmp_path / 'two.faa'
        fasta.write_text('>first\nMARG\n>second\nMARGKKIG\n')
        first, second = store.create_problem(fasta, molecule='protein')['subject_refs']
        hypothesis = store.put('hypothesis', {'subject_refs': [first, second], 'predicate': 'functional_family',
            'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}, origin='reasoning')['id']
        scope = {'subject_refs': [first, second]}
        context = registered_receiver(store, 'signed-scope-test', 'root', scope)
        from gene_annotation_episode.root_axis_scalars import _result
        def native_fixture(store, context, axis, *, target, **kwargs):
            value = 1 if ((axis == 'A101' and target == first)
                or (axis == 'A102' and target == second)) else None
            return _result(axis, value, formula='synthetic_aggregation_only', inputs={}), []
        supplied_owner_contributions(monkeypatch, native_fixture, axes=('A101', 'A102', 'A103', 'A104'))
        result = SignedEvidenceRootSupport(hypothesis)(store, scope, known_record_refs=[hypothesis],
            run_id=context.run_id, episode_id=context.episode_id)
        assert result['credit'] == 1
        assert result['target_sheets'][first]['axis_components']['A101'] == 1
        assert result['target_sheets'][first]['axis_components']['A102'] is None
        assert result['target_sheets'][second]['axis_components']['A102'] == 1
        assert result['target_sheets'][second]['axis_components']['A101'] is None


def test_root_preserves_separate_totals_when_different_targets_have_conflicting_evidence(tmp_path, monkeypatch):
    from gene_annotation_episode.root_axis_scalars import _result
    with Store(tmp_path / 'state') as store:
        fasta = tmp_path / 'two.faa'
        fasta.write_text('>first\nMARG\n>second\nMARGKKIG\n')
        first, second = store.create_problem(fasta, molecule='protein')['subject_refs']
        annotation = store.put('hypothesis', {'subject_refs': [first, second], 'predicate': 'functional_family',
            'value': {'type': 'enum', 'value': 'unresolved'}, 'context_refs': []}, origin='reasoning')['id']
        scope = {'subject_refs': [first, second]}
        context = registered_receiver(store, 'split-scope-test', 'root', scope)
        def supplied_scalar(store, context, axis, *, target, **arguments):
            value = ({'A105': .5, 'A106': .5} if target == first else
                     {'A105': -.5, 'A106': -.5}).get(axis)
            return _result(axis, value, formula='synthetic_target_aggregation', inputs={})
        supplied_owner_contributions(monkeypatch, supplied_scalar)
        result = SignedEvidenceRootSupport(annotation)(store, scope, known_record_refs=[annotation],
            run_id=context.run_id, episode_id=context.episode_id)
        assert result['target_sheets'][first]['support'] == 1.25
        assert result['target_sheets'][first]['opposition'] == 0
        assert result['target_sheets'][second]['support'] == 0
        assert result['target_sheets'][second]['opposition'] == 1.25
        assert result['support'] == pytest.approx(1.25 / 3)
        assert result['opposition'] == pytest.approx(2.5 / 3)
        assert result['credit'] == pytest.approx(-1.25 / 3)
        assert result['minimum'] == -31 and result['maximum'] == 511


def proposed_annotation(store, target, value, *, contexts=(), predicate='functional_family'):
    term = store.put('term', {'namespace': 'synthetic_function', 'accession': value, 'label': value, 'term_type': 'family',
        'source_ref': store.targets()[0]['source_ref'], 'anchor': None}, origin='external')['id']
    return store.put('hypothesis', {'subject_refs': [target], 'predicate': predicate,
        'value': {'type': 'term_ref', 'ref': term}, 'context_refs': list(contexts)}, origin='reasoning')['id']


def assessed(store, proposal, observation, *, relation='strengthens', footprint=None, revision=0, **fields):
    return store.put('assessment', {'hypothesis_ref': proposal, 'observation_ref': observation,
        'relation': relation, 'applicability': 'scope_limited' if footprint is not None else 'direct',
        'condition_refs': [], 'assumption_refs': [],
        'extent_basis': 'inferred_extent' if footprint is not None else 'observed_extent',
        **({'target_footprint': footprint} if footprint is not None else {}),
        'expected_revision': revision, **fields}, origin='reasoning')['id']


def native_structure_observation(store, target, *, length=100, paired=90, scope=None):
    from gene_annotation_episode.a102_publication import publish_comparison
    from test_a102_scoring import native
    row = native(length=length, reference_length=length, paired=paired, scope=scope)
    row.update(target_ref=target, producer='synthetic_geometry_fixture')
    publication = publish_comparison(store, row)
    source = publication['source_ref']
    # A102 publishes an authenticated source, then the ordinary reasoning
    # interface extracts its observation. No fictitious native publisher.
    record = store.get(source)
    raw = store.get_artifact(record['text_ref'])
    start = raw.index(target.encode())
    payload = {name: [] for name in store.reasoning_schema()['required']}
    payload['observations'] = [{'alias': 'structural_measurement', 'subject_refs': [target],
        'source_subject_refs': [target], 'kind': 'alignment', 'source_ref': source,
        'anchor': {'source_ref': source, 'artifact_ref': record['text_ref'],
            'start': start, 'end': start + len(target)}, 'dependencies': [target], 'measurements': []}]
    extracted = store.commit_reasoning(payload, {'subject_refs': store.problem()['subject_refs']},
        'extract-' + source)
    assert extracted['status'] == 'completed', extracted
    return source, extracted['aliases']['structural_measurement']


def collection(store, context, known, *, scope=None, details_limit=20):
    return SignedEvidenceRootSupport().read_details(store, scope or context.scope,
        known_record_refs=known, run_id=context.run_id, episode_id=context.episode_id,
        details_limit=details_limit, details_offset=0)


def test_native_structure_is_separate_by_proposal_and_preserves_partial_denominator(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='M' + 'A' * 99, molecule='protein')['subject_refs']
        first, other = [proposed_annotation(store, target, value) for value in ('enzyme', 'binder')]
        source, observed = native_structure_observation(store, target)
        footprint = [{'target_ref': target, 'start': 0, 'end': 20, 'unit': 'aa'}]
        assessment = assessed(store, first, observed, footprint=footprint)
        context = registered_receiver(store, 'native-structure-proposals', 'root', {'subject_refs': [target]})
        known = [target, first, other, source, observed, assessment]
        result = collection(store, context, known)
        rows = {row['proposed_annotation_ref']: row for row in result['proposed_annotations']}
        assert rows[first]['axis_components']['A102'] == pytest.approx(.16)
        assert rows[first]['axis_transfer']['A102']['status'] == 'established'
        assert rows[first]['axis_transfer']['A102']['link_refs'] == [assessment]
        assert rows[other]['score'] is None
        assert rows[other]['axis_missing_inputs']['A102'] == ['no_received_applicable_supporting_assessment']
        assert result['comparisons'][0]['best_scored_refs'] == [first]
        assert result['comparisons'][0]['unscored_refs'] == [other]
        assert 'credit' not in result
        from gene_annotation_episode.a102_credit import A102StructuralCredit
        native_owner = A102StructuralCredit()
        for proposal, expected in ((first, .16), (other, 0.)):
            local = native_owner(store, {'subject_refs': [target]}, known_record_refs=known,
                assignment={'scope': {'subject_refs': [target]}, 'proposed_annotation_ref': proposal})
            assert local['credit'] == pytest.approx(expected)
        for missing in (observed, source, assessment):
            missing_result = collection(store, context, [ref for ref in known if ref != missing])
            assert all(row['score'] is None for row in missing_result['proposed_annotations'])
        # A received opposing/mixed assessment cannot turn unsigned geometry into support.
        changed = assessed(store, first, observed, relation='weakens', footprint=footprint, revision=1)
        revised = collection(store, context, [*known, changed])
        assert all(row['score'] is None for row in revised['proposed_annotations'])
        assert next(row for row in revised['proposed_annotations'] if row['proposed_annotation_ref'] == first)[
            'axis_transfer']['A102']['status'] == 'established'


def test_axis_owner_distinguishes_missing_invalid_and_withdrawn_annotation_links(tmp_path):
    from gene_annotation_episode.a102_credit import A102StructuralCredit
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='A' * 100, molecule='protein')['subject_refs']
        proposal = proposed_annotation(store, target, 'enzyme')
        source, observed = native_structure_observation(store, target)
        finding = {'source_claim': {'subject_refs': [target], 'predicate': 'functional_family',
                'value': store.get(proposal)['value'], 'context_refs': []},
            'qualification': {'kind': 'none', 'context_refs': [], 'assumption_refs': []},
            'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
            'same_source_claim_as_ref': None, 'replaces_refs': []}
        condition = store.get(proposal)['value']['ref']
        assessment = assessed(store, proposal, observed, condition_refs=[condition], investigation_finding=finding)
        context = registered_receiver(store, 'axis-transfer-states', 'root', {'subject_refs': [target]})
        scope = store.validate_scope({'subject_refs': [target]})
        known = [target, proposal, source, observed, assessment, condition]
        def read(received):
            return A102StructuralCredit().annotation_contribution(store,
                replace(context, received_record_refs=tuple(received)), target=target,
                annotation=store.get(proposal), scope=scope, details_limit=10)
        scalar, details = read(known)
        assert scalar['proposed_annotation_ref'] == proposal and scalar['subject_ref'] == target
        assert scalar['scope'] == scope and scalar['value'] > 0
        assert scalar['transfer']['status'] == 'established'
        assert details[0]['assessment_refs'] == [assessment]
        missing, _ = read([ref for ref in known if ref != condition])
        assert missing['value'] is None and missing['transfer']['status'] == 'unresolved'
        assert missing['transfer']['needed_refs'] == [condition]
        invalid = assessed(store, proposal, observed, applicability='incomparable', revision=1, condition_refs=[condition],
            investigation_finding=finding)
        scalar, _ = read([*known, invalid])
        assert scalar['value'] is None and scalar['transfer']['status'] == 'invalid'
        withdrawn = deepcopy(finding)
        withdrawn.update(status='withdrawn', withdrawal_reason='source_misread')
        revision = assessed(store, proposal, observed, revision=2, condition_refs=[condition], investigation_finding=withdrawn)
        scalar, _ = read([*known, invalid, revision])
        assert scalar['value'] is None and scalar['transfer']['status'] == 'withdrawn'
        assert scalar['transfer']['link_refs'] == [revision]


@pytest.mark.parametrize('field,value', [('proposed_annotation_ref', 'hypothesis_other'),
    ('subject_ref', 'input_other'), ('scope', {'subject_refs': []})])
def test_root_rejects_owner_contribution_for_a_different_annotation_subject_or_scope(tmp_path, monkeypatch, field, value):
    from gene_annotation_episode.root_axis_receipts import axis_contribution_readers
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='A' * 100, molecule='protein')['subject_refs']
        proposal = proposed_annotation(store, target, 'enzyme')
        context = registered_receiver(store, 'owner-identity', 'root', {'subject_refs': [target]})
        owners = axis_contribution_readers(store, context.run_id)
        original = owners['A102']
        def wrong(*args, **kwargs):
            scalar, details = original(*args, **kwargs)
            scalar[field] = value
            return scalar, details
        owners['A102'] = wrong
        monkeypatch.setattr('gene_annotation_episode.signed_evidence_root.axis_contribution_readers', lambda *_: owners)
        with pytest.raises(ValueError, match='axis_contribution_identity_mismatch'):
            collection(store, context, [target, proposal])


def test_dynamic_task_credit_keeps_scientific_support_separate_from_earned_work(tmp_path, monkeypatch):
    from gene_annotation_episode.root_axis_scalars import AXES
    monkeypatch.setattr('gene_annotation_episode.signed_evidence_root.received_axis_task_credit',
        lambda store, context: iter(()))
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='A' * 100, molecule='protein')['subject_refs']
        proposal = proposed_annotation(store, target, 'enzyme')
        other = proposed_annotation(store, target, 'binder')
        source, observation = native_structure_observation(store, target)
        assessment = assessed(store, proposal, observation)
        context = registered_receiver(store, 'collection-task-credit', 'root', {'subject_refs': [target]})
        scorer = SignedEvidenceRootSupport(task_credit=True)
        result = scorer(store, context.scope, known_record_refs=[target, proposal, other, source, observation, assessment],
            run_id=context.run_id, episode_id=context.episode_id)
        assert scorer.as_record()['task_credit'] is True
        assert result['credit']['mode'] == 'annotation_axis_credit'
        arms = {(row['proposed_annotation_ref'], row['axis']): row for row in result['credit']['arms']}
        assert len(arms) == 2 * len(AXES)
        scientific = next(row for row in result['proposed_annotations']
            if row['proposed_annotation_ref'] == proposal)
        assert scientific['axis_components']['A102'] is not None
        assert arms[proposal, 'A102']['credit'] == 0
        assert arms[proposal, 'A102']['transfer']['status'] == 'established'
        assert arms[other, 'A102']['credit'] == 0
        assert all(row['subject_ref'] == target for row in arms.values())
        with pytest.raises(ValueError, match='requires_dynamic_collection'):
            SignedEvidenceRootSupport(proposal, task_credit=True)


def test_opposing_axis_result_earns_returned_local_credit_once(tmp_path, monkeypatch):
    from gene_annotation_episode.domain import identity
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.root_axis_scalars import _result
    from gene_annotation_episode.scientific_process_records import scientific_invocation_ref
    from gene_annotation_episode.scientific_process_reports import project_process_result
    from test_scientific_process_return_records import _full_row, _libraries

    supplied_owner_contributions(monkeypatch, lambda store, context, axis, **options:
        _result(axis, -.4, formula='synthetic_opposing_evidence', inputs={}), axes=('A106',))
    library, tools = _libraries(tmp_path, monkeypatch)
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='A' * 100, molecule='protein')['subject_refs']
        proposal = proposed_annotation(store, target, 'enzyme')
        root = registered_receiver(store, 'returned-local-credit', 'root', {'subject_refs': [target]})
        initial = SignedEvidenceRootSupport()(store, root.scope,
            known_record_refs=[target, proposal], run_id=root.run_id, episode_id=root.episode_id)
        arm_scope, = (row['scope'] for row in initial['proposed_annotations'])
        child_path = (*root.path, ('scientific_process', 'child_0'))
        selection = _full_row(library, tools)['selection']
        original = _full_row(library, tools)
        original.update(invocation_ref=scientific_invocation_ref(root.run_id, child_path),
            parent_invocation_ref=scientific_invocation_ref(root.run_id, root.path),
            selection=selection, initial_credit=2., credit=3.5,
            credit_binding_ref=identity('scientific_credit_binding', {'task': 'A106_evidence'}))
        returned = project_process_result(original, library=library, tool_library=tools)
        returned['proposed_annotation_ref'] = proposal
        selection['evidence_axis']['option_id'] = 'A106'
        returned['selection']['evidence_axis']['option_id'] = 'A106'
        child = BindingContext(root.run_id, EpisodeRef(root.run_id, child_path).episode_id,
            'scientific_process', child_path, arm_scope,
            {'selection': selection, 'proposed_annotation_ref': proposal},
            {'message': {'scientific_invocation_ref': scientific_invocation_ref(root.run_id, child_path)}})
        form = {'results': [returned]}
        schema = {'properties': {'results': {'x-source': 'scientific_process_results'}}}
        monkeypatch.setattr('gene_annotation_episode.episode_return_records.EpisodeReturnRecords.received_attempts',
            lambda self, context: iter(((child, form, schema), (child, form, schema))))
        view = SignedEvidenceRootSupport(task_credit=True)(store, root.scope,
            known_record_refs=[target, proposal], run_id=root.run_id, episode_id=root.episode_id)
        scientific, = view['proposed_annotations']
        arm = next(row for row in view['credit']['arms'] if row['axis'] == 'A106')
        assert scientific['score'] < 0 and scientific['axis_components']['A106'] < 0
        assert arm['credit'] == 1.5
        assert arm['credit_binding_ref'] == returned['credit_binding_ref']

        changed = deepcopy(form)
        changed['results'][0]['credit'] = 4.5
        monkeypatch.setattr('gene_annotation_episode.episode_return_records.EpisodeReturnRecords.received_attempts',
            lambda self, context: iter(((child, form, schema), (child, changed, schema))))
        with pytest.raises(ValueError, match='root_axis_replayed_result_conflict'):
            SignedEvidenceRootSupport(task_credit=True)(store, root.scope,
                known_record_refs=[target, proposal], run_id=root.run_id, episode_id=root.episode_id)


def test_native_translated_protein_keeps_original_region_and_amino_acid_denominator(tmp_path):
    with Store(tmp_path / 'state') as store:
        genome, = store.create_problem(raw_sequence='GCT' * 100, molecule='dna')['subject_refs']
        outcome = ToolRegistry(store).execute('sequence.translate', {'subject_ref': genome, 'code': 11})
        assert outcome['status'] == 'completed'
        protein = outcome['result']['records'][0]['product_ref']
        proposal = proposed_annotation(store, protein, 'enzyme')
        source, observed = native_structure_observation(store, protein)
        extent = [{'target_ref': genome, 'start': 0, 'end': 60, 'unit': 'nt'}]
        assessment = assessed(store, proposal, observed, footprint=extent)
        context = registered_receiver(store, 'derived-proposal', 'root', {'subject_refs': [genome]})
        known = [genome, *outcome['record_refs'], proposal, source, observed, assessment]
        result = collection(store, context, known)
        row, = result['proposed_annotations']
        assert row['subject_ref'] == protein
        assert row['scope']['subject_refs'] == [genome]
        assert row['scope']['segments'] == [{'target_ref': genome, 'start': 0, 'end': 300, 'unit': 'nt'}]
        assert row['native_regions'] == [[0, 100]] and row['native_unit'] == 'aa'
        assert row['axis_components']['A102'] == pytest.approx(.16)
        partial = {'subject_refs': [genome], 'segments': extent}
        fixed = SignedEvidenceRootSupport(proposal)(store, partial, known_record_refs=known,
            run_id=context.run_id, episode_id=context.episode_id)
        assert fixed['target_sheets'][protein]['native_regions'] == [[0, 20]]
        assert fixed['credit'] > row['score']
        assert not collection(store, context, [ref for ref in known if ref != protein])['proposed_annotations']


def test_blast_shared_source_only_counts_the_assessed_native_hit(tmp_path):
    from gene_annotation_episode.blast_search import native_hsp_metadata, HSP_PROJECTION_VERSION
    from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading
    from test_blast_graders_integration import grade_json, native_document
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='ACDEFXXXXX', molecule='protein')['subject_refs']
        proposals = [proposed_annotation(store, target, value) for value in ('function_a', 'function_b', 'unassessed')]
        document = native_document()
        artifact = store.artifact(json.dumps(document), 'application/json')
        retained = retain_tool_grading(store, provider='ncbi_blast', native_artifact_ref=artifact,
            grading=grade_json(_retain_correspondence=True))
        source = store.put('source', {'provider': 'ncbi_blast', 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None,
            'retrieved_at': None, 'auxiliary_artifact_refs': [retained]}, origin='tool')['id']
        known = [target, *proposals, source]
        observed_refs = []
        for index, bits in enumerate((10, 9)):
            reference = store.put('reference', {'reference_type': 'protein', 'source_ref': source,
                'accession': ('SYN_A', 'SYN_B')[index], 'label': 'Synthetic native hit', 'sequence_ref': None,
                'molecule': 'protein', 'length': 10, 'term_refs': [], 'context_refs': []}, origin='tool')['id']
            hsp = document['BlastOutput2'][0]['report']['results']['search']['hits'][index]['hsps'][0]
            metadata = native_hsp_metadata(hsp, program='blastp', query_length=10, reference_length=10,
                hit_ordinal=index, hsp_ordinal=0)
            metadata['shared_projection'] = {'version': HSP_PROJECTION_VERSION, 'grading_artifact_ref': retained,
                'native_artifact_ref': artifact, 'hit_row': index, 'hsp_row': 0}
            observation = store.put('observation', {'subject_refs': [target], 'source_subject_refs': [reference],
                'kind': 'comparison', 'source_ref': source, 'anchor': None, 'dependencies': [target, reference],
                'measurements': [{'name': 'bitscore', 'value': {'type': 'number', 'value': bits, 'unit_ref': None}}],
                'operand_intervals': [{'role': role, 'subject_ref': ref, 'start': 0, 'end': 5,
                    'unit': 'aa', 'model_unit': 'aa'} for role, ref in [('query', target), ('reference', reference)]],
                'native_blast': metadata}, origin='tool')['id']
            known.extend([reference, observation, assessed(store, proposals[index], observation)])
            observed_refs.append(observation)
        context = registered_receiver(store, 'native-hits', 'root', {'subject_refs': [target]})
        result = collection(store, context, known)
        rows = {row['proposed_annotation_ref']: row for row in result['proposed_annotations']}
        assert rows[proposals[0]]['score'] == pytest.approx((1 - math.exp(-.025 * 10)) * .25)
        assert rows[proposals[1]]['score'] == pytest.approx((1 - math.exp(-.025 * 9)) * .25)
        assert rows[proposals[2]]['score'] is None
        assert len(result['source_contributions']) == 2
        from gene_annotation_episode.a101_credit import A101SequenceCredit
        for proposal in proposals:
            local = A101SequenceCredit()(store, {'subject_refs': [target]}, known_record_refs=known,
                assignment={'scope': {'subject_refs': [target]}, 'proposed_annotation_ref': proposal})
            assert local['credit'] == pytest.approx(rows[proposal]['score'] or 0.)


def test_collection_ranks_negative_scores_preserves_ties_unknowns_and_subject_groups(tmp_path, monkeypatch):
    from gene_annotation_episode.root_axis_scalars import _result
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
        proposals = [proposed_annotation(store, target, value) for value in ('negative', 'tie', 'unknown')]
        other_question = proposed_annotation(store, target, 'intact', predicate='sequence_integrity')
        def supplied(store, context, axis, *, assertion_ref, **kwargs):
            value = -.5 if axis == 'A106' and assertion_ref in proposals[:2] else None
            return _result(axis, value, formula='synthetic_comparison_fixture', inputs={})
        supplied_owner_contributions(monkeypatch, supplied)
        context = registered_receiver(store, 'compare', 'root', {'subject_refs': [target]})
        result = collection(store, context, [*proposals, other_question])
        assert len(result['comparisons']) == 2
        group = next(row for row in result['comparisons'] if row['predicate'] == 'functional_family')
        assert set(group['best_scored_refs']) == set(proposals[:2])
        assert group['best_score'] == -.5 and group['unscored_refs'] == proposals[2:]
        assert group['annotation_selected'] is False
        assert store.current_annotations() == []


def test_dynamic_selectors_are_not_reused_across_proposals():
    with pytest.raises(ValueError, match='not_global_selectors'):
        SignedEvidenceRootSupport(comparison_ref='hypothesis_' + 'a' * 24)
    with pytest.raises(ValueError, match='not_global_selectors'):
        SignedEvidenceRootSupport(selections=(('A105', 'source_' + 'b' * 24),))


def test_runtime_discovers_new_proposal_and_updates_score_on_later_decision(tmp_path):
    from test_runtime import FixtureController
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='M' + 'A' * 99, molecule='protein')['subject_refs']
        source, observed = native_structure_observation(store, target)
        scorer = SignedEvidenceRootSupport()
        progress = ScientificFindingProgress(FindingProgressPolicy(1))
        seen = []
        def decision(context):
            seen.append(context)
            assert 'annotation_score' not in context
            assert 'annotation_score' not in context['available_report_facts']
            assert context['available_report_facts']['proposed_annotations']['type'] == 'array'
            commit = {name: [] for name in store.reasoning_schema()['required']}
            if len(seen) == 1:
                assert context['proposed_annotations'] == []
                commit['hypotheses'] = [{'alias': 'candidate', 'subject_refs': [target],
                    'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
                    'context_refs': []}]
            elif len(seen) == 2:
                row, = context['proposed_annotations']
                assert row['score'] is None
                commit['assessments'] = [{'hypothesis_ref': row['proposed_annotation_ref'],
                    'alias': 'structure_application',
                    'observation_ref': observed, 'relation': 'strengthens', 'applicability': 'direct',
                    'extent_basis': 'observed_extent', 'condition_refs': [], 'assumption_refs': [],
                    'expected_revision': 0}]
            else:
                row, = context['proposed_annotations']
                assert row['score'] == pytest.approx(.72)
                commit['hypotheses'] = [{'alias': 'retained_candidate', 'subject_refs': [target],
                    'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
                    'context_refs': []}]
            return {'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}}
        result = asyncio.run(run_workflow(store, ToolRegistry(store), run_dir=tmp_path / 'workflow',
            provider=ScriptedProvider([decision] * 3),
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 3),
            project_credit=progress, project_annotation_score=scorer,
            binding_definitions={'credit': progress.as_record(), 'annotation_score': scorer.as_record()},
            initial_known_record_refs=[target, store.targets()[0]['source_ref'], source, observed],
            episode_record_receipts=True))
        assert len(seen) == 3
        assert 'annotation_score' not in result
        assert result['proposed_annotations'][0]['score'] == pytest.approx(.72)
        assert result['annotation_comparisons'][0]['best_score'] == pytest.approx(.72)
        assert result['ended_by'] == 'yield_stop' and result['completed_actions'] == 3
        # Restricted roots retain their existing action catalog. Inspect the
        # original detail port against this saved receiver without changing it.
        from types import SimpleNamespace
        from gene_annotation_episode.runtime import assemble_workflow
        episode_id = store.db.execute('SELECT episode_id FROM runtime_episodes').fetchone()[0]
        settings = json.loads(store.db.execute('SELECT settings FROM runtime_runs').fetchone()[0])
        workflow = assemble_workflow(store, ToolRegistry(store), ScriptedProvider([]), tmp_path / 'workflow',
            result['run_id'], settings, project_credit=progress, project_annotation_score=scorer,
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 3),
            initial_known_record_refs=[target, store.targets()[0]['source_ref'], source, observed],
            episode_record_receipts=True)
        details = workflow.annotation_score_read(SimpleNamespace(scope={'subject_refs': [target]},
            episode_id=episode_id), {'limit': 1, 'offset': 0})
        assert details['status'] == 'completed'
        assert details['result']['mode'] == 'proposed_annotation_collection'
        assert 'credit' not in details['result'] and 'annotation_score' not in details['result']
        assert details['result']['source_contribution_count'] == 1
        assert store.current_annotations() == []


@pytest.mark.parametrize('axis', ['A107', 'A110'])
def test_component_receipt_uses_public_native_subject_and_requires_region_coverage(tmp_path, monkeypatch, axis):
    # Qualified values are explicit fixtures of the existing receiving port;
    # this tests its subject/region binding, not upstream native calculations.
    from gene_annotation_episode.root_axis_receipts import axis_contribution_readers
    with Store(tmp_path / 'state') as store:
        genome, = store.create_problem(raw_sequence='GCT' * 100, molecule='dna')['subject_refs']
        translation = ToolRegistry(store).execute('sequence.translate', {'subject_ref': genome, 'code': 11})
        protein = translation['result']['records'][0]['product_ref']
        proposal = proposed_annotation(store, protein, 'enzyme')
        other = proposed_annotation(store, protein, 'other')
        context = registered_receiver(store, 'component-' + axis, 'root', {'subject_refs': [genome]})
        result = {'assessment_hypothesis_ref': proposal, 'missing': []}
        if axis == 'A107':
            result.update(source_subject_correspondence={'reference_subject_ref': protein},
                partner_components=[{'component': name, 'value': 1., 'status': 'populated',
                    'unit': 'dimensionless'} for name in ('partner_loss_fraction', 'restored_reference_fraction')])
            regions = [[0, 300]]
        else:
            result.update(component_correspondence={'reference_subject_ref': protein}, component_family='reaction',
                selected_components=[{'component': 'reaction_comparison', 'value': .5, 'status': 'populated',
                    'unit': 'dimensionless'}])
            regions = [{'target_ref': genome, 'start': 0, 'end': 300, 'unit': 'nt'}]
        body = {'target_ref': genome, 'target_regions': regions, 'scope': {'subject_refs': [genome]},
            'result': result, 'operation': 'partner.requirement_evidence', 'current': True}
        def publish(value):
            artifact = store.artifact(json.dumps(value), 'application/json')
            return store.put('source', {'provider': 'synthetic_qualified_receiving_fixture', 'accession': None,
                'uri': None, 'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
                'version': None, 'retrieved_at': None}, origin='tool')['id']
        row = {**body, 'source_ref': publish(body)}
        port = ('gene_annotation_episode.a107_qualification.received_qualifications' if axis == 'A107'
            else 'gene_annotation_episode.a110_qualification.received')
        monkeypatch.setattr(port, lambda *args, **kwargs: [row])
        context = replace(context, received_record_refs=(protein, proposal, row['source_ref']))
        scope = {'subject_refs': [genome], 'segments': store.coverage(protein)}
        reader = axis_contribution_readers(store, context.run_id)[axis]
        def contribution(target, proposal):
            return reader(store, context, target=target, annotation=store.get(proposal), scope=scope)[0]
        assert contribution(protein, proposal)['value'] == .5
        assert contribution(genome, proposal)['value'] is None
        assert contribution(protein, other)['value'] is None
        body['target_regions'] = [[0, 30]] if axis == 'A107' else [dict(regions[0], end=30)]
        row.update(body, source_ref=publish(body))
        partial = contribution(protein, proposal)
        assert partial['value'] is None
        assert 'received_axis_result_does_not_cover_requested_scope' in partial['missing_inputs']


from test_a103_context import context_case


def test_received_a103_native_attachment_is_assessed_for_only_one_proposal(context_case):
    from test_a103_context import grade
    from gene_annotation_episode.a103_publication import publish
    store, target, known, _, _, _, _, _, _, _, _, raw, _ = context_case
    measured = publish(store, raw, [target])
    known.add(measured)
    native, _ = grade(store, target, known)
    attachment = next(row for row in native['tool_attachments'] if row['measurement_ref'] == measured)
    observation = next(ref for ref in known if store.get(ref)['record_type'] == 'observation'
        and store.get(ref)['source_ref'] == attachment['source_ref'])
    first, other = [proposed_annotation(store, target, name) for name in ('context_a', 'context_b')]
    assessment = assessed(store, first, observation, footprint=store.coverage(target))
    known.update([first, other, assessment])
    context = registered_receiver(store, 'a103-proposals', 'root', {'subject_refs': [target]})
    result = collection(store, context, known)
    rows = {row['proposed_annotation_ref']: row for row in result['proposed_annotations']}
    assert rows[first]['axis_components']['A103'] == native['credit'] == .5
    assert rows[other]['score'] is None
    contribution, = result['source_contributions']
    assert contribution['assessment_refs'] == [assessment]
    changed = assessed(store, first, observation, relation='mixed', footprint=store.coverage(target), revision=1)
    assert all(row['score'] is None for row in collection(store, context, [*known, changed])['proposed_annotations'])


@pytest.mark.parametrize('axis', ['A103', 'A104'])
def test_received_attachment_association_masks_native_regions_and_retains_measured_zero(tmp_path, monkeypatch, axis):
    # Explicit received-attachment seam: native A103 calculation is exercised
    # above; this isolates both existing projectors' interval/status handling.
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='A' * 100, molecule='protein')['subject_refs']
        first, other = [proposed_annotation(store, target, name) for name in ('function_a', 'function_b')]
        source, observation = native_structure_observation(store, target)
        attachment = {'source_ref': source, 'measurement_ref': source, 'target_ref': target,
            'grading_artifact_ref': 'synthetic-received-port', 'target_regions': [[0, 20]],
            'score': .7, 'raw_value': .7, 'missing': [], 'qualification_dependencies': [source],
            'policy': 'phylogeny.measure_placement_original_native_operands_v1' if axis == 'A104' else 'native_context',
            'state': 'attributed', 'producer_operation': 'synthetic'}
        module = 'a103' if axis == 'A103' else 'a104'
        monkeypatch.setattr('gene_annotation_episode.' + module + '_attachments.received_attachments',
            lambda *_: [deepcopy(attachment)])
        monkeypatch.setattr('gene_annotation_episode.' + module + '_credit.received_attachments',
            lambda *_: [deepcopy(attachment)])
        extent = [{'target_ref': target, 'start': 50, 'end': 70, 'unit': 'aa'}]
        assessment = assessed(store, first, observation, footprint=extent)
        context = registered_receiver(store, 'region-' + axis, 'root', {'subject_refs': [target]})
        known = [target, first, other, source, observation, assessment]
        result = collection(store, context, known)
        row = next(row for row in result['proposed_annotations'] if row['proposed_annotation_ref'] == first)
        assert row['axis_components'][axis] is None
        attachment['target_regions'] = [[50, 70]]
        attachment['score'] = 0.
        result = collection(store, context, known)
        rows = {row['proposed_annotation_ref']: row for row in result['proposed_annotations']}
        assert rows[first]['axis_components'][axis] == 0.
        assert rows[other]['axis_components'][axis] is None
        from gene_annotation_episode.a103_credit import A103ContextCredit
        from gene_annotation_episode.a104_credit import A104EvolutionaryCredit
        attachment['score'] = .7
        owner = A103ContextCredit() if axis == 'A103' else A104EvolutionaryCredit()
        local = {proposal: owner(store, {'subject_refs': [target]}, known_record_refs=known,
            assignment={'scope': {'subject_refs': [target]}, 'proposed_annotation_ref': proposal})
            for proposal in (first, other)}
        assert local[first]['credit'] == pytest.approx(.14 if axis == 'A103' else .14 / 7)
        assert local[other]['credit'] == 0.
        changed = assessed(store, first, observation, relation='weakens', footprint=extent, revision=1)
        result = collection(store, context, [*known, changed])
        assert all(row['axis_components'][axis] is None for row in result['proposed_annotations'])


def test_a108_pooled_multi_subject_score_is_not_copied_to_individual_subjects(tmp_path, monkeypatch):
    from gene_annotation_episode.literature_a108_aggregation_storage import LiteratureA108AggregationRepository
    with Store(tmp_path / 'state') as store:
        fasta = tmp_path / 'two.faa'
        fasta.write_text('>one\nMARG\n>two\nMAGG\n')
        first, second = store.create_problem(fasta, molecule='protein')['subject_refs']
        single = proposed_annotation(store, first, 'context')
        single_record = store.get(single)
        multi = store.put('hypothesis', {key: value for key, value in single_record.items()
            if key not in {'id', 'origin', 'record_type', 'subject_refs'}} | {'subject_refs': [first, second]}, origin='reasoning')['id']
        scope = {'subject_refs': [first, second]}
        request = store.artifact(json.dumps({'scope': scope}), 'application/json')
        source = store.put('source', {'provider': 'synthetic_received_a108', 'accession': None,
            'uri': None, 'artifact_ref': request, 'text_ref': None, 'request_ref': request,
            'version': None, 'retrieved_at': None}, origin='tool')['id']
        cell = {'component': 'overall', 'assertion_ref': multi, 'sheet_ref': source,
            'status': 'complete', 'observation_sets': {'support': ['original-1'], 'conflict': [], 'unresolved': []},
            'evidence_amount': 1, 'net_support': 1, 'support_count': 1, 'conflict_count': 0}
        monkeypatch.setattr(LiteratureA108AggregationRepository, 'current_annotation_cells', lambda *args: [cell])
        context = registered_receiver(store, 'a108-pooled', 'root', {'subject_refs': [first, second]})
        owner = LiteratureA108AggregationRepository(store, context.run_id)
        def contribution(target, proposal):
            return owner.annotation_contribution(store, context, target=target,
                annotation=store.get(proposal), scope=store.validate_scope({'subject_refs': [target]}))[0]
        for target in (first, second):
            scalar = contribution(target, multi)
            assert scalar['value'] is None
            assert 'pooled_context_score_has_no_individual_subject_attribution' in scalar['missing_inputs']
        cell['assertion_ref'] = single
        assert contribution(first, single)['value'] == .5
        assert contribution(first, single)['transfer']['status'] == 'established'
        assert contribution(second, single)['value'] is None
        assert contribution(second, single)['transfer']['status'] == 'invalid'


def test_a108_assessment_publication_updates_evidence_credit_without_a_scoring_episode(tmp_path):
    from gene_annotation_episode.literature_a108_grading import COMPONENTS, CRITERIA_BY_TYPE
    from gene_annotation_episode.literature_a108_grading_storage import LiteratureA108GradingRepository, REQUESTED
    from gene_annotation_episode.literature_a108_aggregation_storage import LiteratureA108AggregationRepository
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='MARG', molecule='protein')['subject_refs']
        proposal = proposed_annotation(store, target, 'synthetic_thermal_role')
        text = 'Synthetic sample grows at 20 C; this is an engineering fixture, not biological evidence.'
        artifact = store.artifact(text, 'text/plain')
        source = store.put('source', {'provider': 'synthetic_context_fixture', 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
            'version': None, 'retrieved_at': None}, origin='caller')['id']
        sample = store.put('context', {'context_type': 'sample', 'name': 'Synthetic sample',
            'source_ref': source, 'attributes': [], 'related_refs': [target]}, origin='caller')['id']
        observed = store.put('reference', {'reference_type': 'literature_result', 'source_ref': source,
            'accession': 'synthetic-observation', 'label': 'Synthetic thermal observation',
            'sequence_ref': None, 'molecule': None, 'length': None, 'term_refs': [], 'context_refs': [sample],
            'anchor': {'source_ref': source, 'artifact_ref': artifact, 'start': 0, 'end': len(text), 'quote': text}},
            origin='caller')['id']
        witness = {'source_ref': source, 'representation': 'original', 'start': 0, 'end': len(text), 'quote': text}
        arguments = {'assertion_ref': proposal, 'source_ref': source, 'target_context_ref': sample,
            'target_identity': {'status': 'supported', 'support_refs': [sample]}, 'target_identity_evidence': [],
            'grader_type': 'environment_temperature', 'observations': [{
                'original_observation_ref': observed, 'context_claim_ref': proposal,
                'source_subject_ref': target, 'source_context_ref': sample,
                'origin': 'recorded_sample_condition', 'target_relationship': 'direct', 'relation': 'support',
                'criteria': {name: {'status': 'supported', 'support_refs': [observed]}
                    for name in CRITERIA_BY_TYPE['environment_temperature']},
                'qualifications': ['Synthetic applicability is stipulated.'],
                'evidence': [{'kind': 'literature_passage', 'witness': witness}], 'origin_link_evidence': []}]}
        context = registered_receiver(store, 'a108-automatic', 'owner', {'subject_refs': [target]})
        context = replace(context, assignment={REQUESTED: list(COMPONENTS)},
            received_record_refs=(target, proposal, source, sample, observed))
        native = LiteratureA108GradingRepository(store, context.run_id)
        first = native.populate(context, arguments, 'first-context-assessment')
        main = LiteratureA108AggregationRepository(store, context.run_id)
        first_cell, = main.current_annotation_cells(context)
        assert first_cell['sheet_ref'] in first['record_refs']
        assert first_cell['support_count'] == 1 and first_cell['conflict_count'] == 0
        private_parent = registered_receiver(store, context.run_id, 'parent', {'subject_refs': [target]})
        private_parent = replace(private_parent, received_record_refs=(*context.received_record_refs, *first['record_refs']))
        assert main.current_annotation_cells(private_parent) == []
        changed = deepcopy(arguments)
        changed['observations'][0]['relation'] = 'conflict'
        second = native.populate(context, changed, 'corrected-context-assessment')
        current, = main.current_annotation_cells(context)
        assert current['sheet_ref'] in second['record_refs']
        assert current['support_count'] == 0 and current['conflict_count'] == 1
        scalar, _ = main.annotation_contribution(store, context, target=target,
            annotation=store.get(proposal), scope=store.validate_scope({'subject_refs': [target]}))
        assert scalar['value'] == -.5
        assert main.read(first_cell['sheet_ref'])['sheet']['cells']['overall']['support_count'] == 1
        private_parent = replace(private_parent,
            received_record_refs=(*private_parent.received_record_refs, *main.cell_record_refs([current])))
        main.receive_cells(private_parent, [current], 'actual-current-score-delivery')
        assert main.current_annotation_cells(private_parent) == [current]
        assert store.db.execute('SELECT COUNT(*) FROM runtime_episodes').fetchone()[0] == 2
        assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0


def test_a105_every_selected_experiment_needs_current_target_and_extent_binding(tmp_path):
    from gene_annotation_episode.literature_a105_aggregation_storage import direct_target_application
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='A' * 100, molecule='protein')['subject_refs']
        proposal = proposed_annotation(store, target, 'enzyme')
        source, observed = native_structure_observation(store, target)
        # This receiving-port control identifies the two original experimental
        # records explicitly; it does not fabricate a numerical experiment.
        experiments = [store.put('reference', {'reference_type': 'assay', 'source_ref': source,
            'accession': name, 'label': name, 'sequence_ref': None, 'molecule': None, 'length': None,
            'term_refs': [], 'context_refs': []}, origin='tool')['id'] for name in ('first', 'second')]
        original = store.get(observed)
        observed = store.put('observation', {key: value for key, value in original.items()
            if key not in {'id', 'origin', 'record_type', 'dependencies'}} | {'dependencies': [target, experiments[0]]},
            origin='extracted')['id']
        finding = {'source_claim': {'subject_refs': [target], 'predicate': 'functional_family',
                'value': store.get(proposal)['value'], 'context_refs': []},
            'qualification': {'kind': 'none', 'context_refs': [], 'assumption_refs': []},
            'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
            'same_source_claim_as_ref': None, 'replaces_refs': []}
        assessment = assessed(store, proposal, observed, footprint=store.coverage(target), investigation_finding=finding)
        context = registered_receiver(store, 'a105-binding', 'root', {'subject_refs': [target]})
        context = replace(context, received_record_refs=(target, proposal, source, observed, assessment, *experiments))
        cell = {'assertion_ref': proposal, 'selected_experiment_refs': experiments}
        assert direct_target_application(store, context, cell, target, context.scope)['status'] == 'unresolved'
        cell['selected_experiment_refs'] = experiments[:1]
        linked = direct_target_application(store, context, cell, target, context.scope)
        assert linked['status'] == 'established' and linked['missing_inputs'] == []
        assert linked['link_refs'] == [assessment]
        small = [{'target_ref': target, 'start': 0, 'end': 20, 'unit': 'aa'}]
        revised = assessed(store, proposal, observed, footprint=small, revision=1, investigation_finding=finding)
        context = replace(context, received_record_refs=(*context.received_record_refs, revised))
        assert direct_target_application(store, context, cell, target, context.scope)['status'] == 'unresolved'
