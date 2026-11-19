"""The A110 head binding on episode_runtime: registration, its own tool registry, credit and controller.

Real objects only: the shared Store with test-written records, the A110 ToolRegistry, the runner's
RunJournal/EpisodeRecorder/ProgressClock and the head's own YieldController. No model is called; the
head's decisions need a real model provider, so no head run is driven here.
"""
import math

import pytest

from episode_runtime import BindingRegistry, BoundEpisode, EpisodeRecorder, FormError, ProgressClock, RunJournal
from method_loop import EpisodeRef

from gene_annotation_episode.domain import ContractError, identity
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.tools.biochemical_feasibility_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.episode import (
    BiochemicalFeasibilityEvidenceEpisode)
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.head_episode import (
    head_credit, instructions)
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.runtime_contract import (
    RuntimeRecord)

TEXT = 'ConstructX grows. The measured ConstructX grows under this condition.'


def target_question(store):
    target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'biological_role',
                                          'value': {'type': 'enum', 'value': 'unresolved'},
                                          'context_refs': []}, origin='reasoning')['id']
    return target, hypothesis


def quoted_observation(store, accession):
    artifact = store.artifact(TEXT)
    source = store.put('source', {'provider': 'synthetic_fixture', 'accession': accession, 'uri': None,
                                  'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
                                  'version': accession, 'retrieved_at': None,
                                  'publication_identifiers': [{'namespace': 'doi', 'value': '10.1234/synthetic'}]},
                       origin='external')
    anchor = {'source_ref': source['id'], 'artifact_ref': artifact, 'start': 0, 'end': 17, 'quote': TEXT[0:17]}
    subject = {'reference_type': 'construct', 'source_ref': source['id'], 'label': 'ConstructX', 'anchor': anchor,
               'sequence_ref': None, 'length': None, 'molecule': None, 'term_refs': [], 'context_refs': []}
    subject['accession'] = identity('source_entity', {key: subject[key] for key in ('source_ref', 'label', 'anchor')})
    subject_ref = store.put('reference', subject, origin='extracted')['id']
    observation = store.put('observation', {'subject_refs': [subject_ref], 'source_subject_refs': [subject_ref],
                                            'kind': 'source_content', 'source_ref': source['id'],
                                            'measurements': [], 'dependencies': [], 'anchor': anchor},
                            origin='extracted')
    return subject_ref, observation['id']


def put_finding(store, hypothesis, observation, subject, *, value, qualification='none', revision=0):
    return store.put('assessment', {
        'hypothesis_ref': hypothesis, 'observation_ref': observation, 'relation': 'does_not_discriminate',
        'applicability': 'incomparable', 'extent_basis': 'observed_extent', 'condition_refs': [],
        'assumption_refs': [], 'expected_revision': revision,
        'investigation_finding': {
            'source_claim': {'subject_refs': [subject], 'predicate': 'growth_capability',
                             'value': {'type': 'enum', 'value': value}, 'context_refs': []},
            'qualification': {'kind': qualification, 'context_refs': [], 'assumption_refs': []},
            'status': 'retained', 'withdrawal_reason': 'not_withdrawn',
            'same_source_claim_as_ref': None, 'replaces_refs': []}}, origin='reasoning')['id']


def test_head_registers_with_its_contract_forms(tmp_path):
    with Store(tmp_path / 'workspace') as store:
        head = BiochemicalFeasibilityEvidenceEpisode(ToolRegistry(store))
        registry = BindingRegistry([head])
        assert registry.binding('biochemical_feasibility_evidence') is head
        assert head.required_collaborators == ('model_provider', 'store', 'continuation')
        record = {'credit': 3.0, 'finding': 'Two findings retained', 'assessment_refs': ['assessment_a']}
        assert head.return_form.admit(record, 'result') == record
        with pytest.raises(FormError):
            head.return_form.admit({'credit': 3.0, 'finding': 'missing references'}, 'result')
        assert 'Investigate whether a possible reaction or pathway is chemically sustainable' in instructions()


def test_head_requires_a_conforming_tool_registry(tmp_path):
    with Store(tmp_path / 'workspace') as store:
        assert BiochemicalFeasibilityEvidenceEpisode(ToolRegistry(store)).tool_registry.store is store
    with pytest.raises(ContractError, match='a110_binding_requires_its_own_a110_tool_registry'):
        BiochemicalFeasibilityEvidenceEpisode(object())


def test_head_credit_counts_distinct_known_retained_findings_without_a_bound(tmp_path):
    with Store(tmp_path / 'workspace') as store:
        target, hypothesis = target_question(store)
        scope = store.validate_scope({'subject_refs': [target]})
        subject_a, observation_a = quoted_observation(store, 'first')
        subject_b, observation_b = quoted_observation(store, 'second')
        subject_c, observation_c = quoted_observation(store, 'third')
        positive = put_finding(store, hypothesis, observation_a, subject_a, value='positive')
        negative = put_finding(store, hypothesis, observation_b, subject_b, value='negative')
        qualified = put_finding(store, hypothesis, observation_c, subject_c, value='negative',
                                qualification='measurement_does_not_establish_claim')
        # Records in the shared store that this episode has not received earn nothing.
        assert head_credit(store, scope, []) == (0, 0)
        assert head_credit(store, scope, [positive]) == (1, 1)
        # Distinct retained findings each add one unit; the scale is not bounded to [0, 1].
        assert head_credit(store, scope, [positive, negative, qualified]) == (3, 3)
        # Receiving the same assessment twice adds nothing.
        assert head_credit(store, scope, [positive, positive]) == (1, 1)


def test_head_controller_observes_its_credit_with_recorded_progress_receipts(tmp_path):
    with Store(tmp_path / 'workspace') as store:
        target, _ = target_question(store)
        head = BiochemicalFeasibilityEvidenceEpisode(ToolRegistry(store))
        commission = head.entry_request(
            {'objective': 'Assess the reaction feasibility of the supplied protein',
             'assignment': {'scope': store.validate_scope({'subject_refs': [target]}),
                            'evidence_task': head.assignment_form.declared['evidence_task'],
                            'tools': ['source.read', 'public.rhea.search']}},
            {}, parent_goal=None)
        journal = RunJournal(tmp_path / 'journal.sqlite3')
        path = (('biochemical_feasibility_evidence', 'head'),)
        recorder = EpisodeRecorder(journal, 'run-a110', path)
        episode_id = EpisodeRef('run-a110', path).episode_id
        bound = BoundEpisode(run_id='run-a110', binding_path=head.binding_path, path=path, key='head',
                             episode_id=episode_id, request=commission.request,
                             assignment=dict(commission.assignment), recorder=recorder,
                             progress=ProgressClock(recorder, run_id='run-a110', episode_id=episode_id),
                             report_form=head.return_form)
        settings = {'continuation': {head.binding_path: {'cutoff': 0.25, 'parameters': {'uncertainty_alpha': 0.05}}}}
        controller = head.build_controller(bound, settings)
        assert type(controller.state().stop) is bool
        observed = []
        for position, credit in enumerate((2.0, 5.0)):
            value = RuntimeRecord({'unit': 'reason:' + str(position), 'kind': 'reason', 'status': 'completed',
                                   'credit': credit,
                                   'estimation_context': {'progress_time': bound.progress.receipt(position)}})
            step = controller.observe(value.as_record()['unit'], value)
            observed.append(value.as_record())
            assert type(step.stop) is bool and type(step.requests_transition) is bool
        assert controller.state().current_credit == 5.0 and controller.state().history == (2.0, 3.0)
        # The recorded receipt is read back, not measured again.
        assert bound.progress.receipt(1) == observed[1]['estimation_context']['progress_time']
        replayed = head.build_controller(bound, settings)
        for record in observed:
            replayed.observe(record['unit'], head.restore_controller_input(record))
        assert replayed.state().as_record() == controller.state().as_record()
        assert math.isfinite(replayed.state().current_credit)
        with pytest.raises(ContractError, match='a110_continuation_settings_missing'):
            head.build_controller(bound, {'continuation': {}})
