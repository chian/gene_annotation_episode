"""Canonical infrastructure with genuine private validators and saved receipts.

Journal/request rows are context fixtures, not commissioned scientific work.
No scientific result, model call, publication producer or authority is simulated.
"""
from dataclasses import replace
from importlib import import_module
import json
from types import SimpleNamespace

import pytest

from gene_annotation_episode.domain import canonical
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeGoal, EpisodeRequest
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.task_values import Record


PRIVATE = 'gene_annotation_episode.episodic_workflow.root.a105'
ROOT = 'gene_annotation_episode.episodic_workflow.root'
RUN = 'canonical-private-context-boundary'


@pytest.mark.parametrize('private_owner,name,canonical_owner', [
    ('domain', 'ContractError', 'gene_annotation_episode.domain'),
    ('communication', 'ReportBoundaryError', ROOT + '.communication'),
    ('episode_contract_information', 'ContractInformationError', ROOT + '.episode_contract_information'),
    ('episode_journal', 'WorkflowError', ROOT + '.episode_journal'),
    ('acquisition', 'AcquisitionError', 'gene_annotation_episode.acquisition'),
    ('providers', 'ModelCallError', ROOT + '.provider_errors'),
    ('runtime', 'ActionFailure', ROOT + '.task_action_units'),
    ('episode_bindings', 'BindingContext', ROOT + '.receiving_context'),
])
def test_real_private_producing_owners_use_canonical_types(private_owner, name, canonical_owner):
    assert getattr(import_module(PRIVATE + '.' + private_owner), name) is getattr(import_module(canonical_owner), name)


def test_private_report_validator_preserves_canonical_diagnostic():
    private = import_module(PRIVATE + '.communication')
    error_type = import_module(ROOT + '.communication').ReportBoundaryError
    with pytest.raises(error_type) as caught:
        private._finite({'measurement': [float('nan')]})
    assert type(caught.value) is error_type
    assert caught.value.diagnostic == {
        'category': 'report_format', 'code': 'nonfinite_number', 'field': 'report.measurement[0]'}


def test_error_payload_and_cause_are_not_rewritten():
    domain = import_module(PRIVATE + '.domain')
    info = import_module(PRIVATE + '.episode_contract_information')
    detail = {'returned_channel': ['unavailable']}
    original = domain.ContractError('missing_native_return_channel', detail=detail)
    assert original.detail is detail and original.args == ('missing_native_return_channel',)
    with pytest.raises(import_module(ROOT + '.episode_contract_information').ContractInformationError) as caught:
        try:
            raise original
        except import_module('gene_annotation_episode.domain').ContractError as error:
            raise info.ContractInformationError('operand_unavailable', 'native') from error
    assert caught.value.__cause__ is original
    assert caught.value.code == 'operand_unavailable' and caught.value.field == 'native'
    assert str(caught.value) == 'operand_unavailable:native'


def test_acquisition_failure_retains_original_operational_fields():
    error_type = import_module(PRIVATE + '.acquisition').AcquisitionError
    diagnostic, operational = {'phase': 'read'}, {'job': 'retained'}
    failure = error_type('read_failed', retry_after=2.5, job_ref='job:boundary',
        phase='download', submission_outcome='unavailable', diagnostic=diagnostic, operational=operational)
    assert type(failure) is import_module('gene_annotation_episode.acquisition').AcquisitionError
    assert failure.args == ('read_failed',) and failure.code == 'read_failed'
    assert failure.retry_after == 2.5 and failure.job_ref == 'job:boundary'
    assert failure.phase == 'download' and failure.submission_outcome == 'unavailable'
    assert failure.snapshot is None and failure.diagnostic is diagnostic and failure.operational is operational


def test_returned_action_failure_keeps_finite_feedback_and_workflow_base():
    error_type = import_module(PRIVATE + '.runtime').ActionFailure
    feedback = {'status': 'unavailable', 'values': [-3, 0, 2.5]}
    failure = error_type(feedback)
    assert isinstance(failure, import_module(ROOT + '.episode_journal').WorkflowError)
    assert failure.feedback is feedback and json.loads(str(failure)) == feedback
    with pytest.raises(ValueError):
        error_type({'measurement': float('inf')})


def test_model_failure_retains_args_and_diagnostic_without_transport():
    error_type = import_module(PRIVATE + '.providers').ModelCallError
    diagnostic = {'phase': 'decision', 'cause_code': 'provider_unavailable'}
    error = error_type('provider_unavailable', 'retained detail', diagnostic=diagnostic)
    assert type(error) is import_module(ROOT + '.provider_errors').ModelCallError
    assert error.args == ('provider_unavailable', 'retained detail') and error.diagnostic is diagnostic


@pytest.mark.parametrize('module,name', [('episode_commissions', 'CommissionError'), ('episode_admission', 'AdmissionError')])
def test_original_private_error_subclasses_keep_canonical_base(module, name):
    cls = getattr(import_module(PRIVATE + '.' + module), name)
    assert cls.__module__.startswith(PRIVATE + '.')
    assert issubclass(cls, import_module(ROOT + '.episode_journal').WorkflowError)
    assert cls is not import_module(ROOT + '.episode_journal').WorkflowError


@pytest.fixture
def saved_contexts(tmp_path):
    journal_type = import_module(PRIVATE + '.episode_journal').Journal
    receipts_type = import_module(PRIVATE + '.episode_receipts').EpisodeReceipts
    reader_type = import_module(PRIVATE + '.episode_return_records').EpisodeReturnRecords
    with Store(tmp_path / 'store') as store:
        journal, receipts = journal_type(store, RUN), receipts_type(store, RUN)
        reader = reader_type(store, RUN, failure_prefix='boundary_')

        def capture(path, parent=None):
            reference = EpisodeRef(RUN, path)
            manifest = receipts.bind(reference.episode_id, None if parent is None else parent.episode_id)
            options = {'objective': 'Saved context identity only', 'result_contract': {'role': path[-1][0]}}
            goal = (EpisodeGoal.root(**options) if parent is None else
                EpisodeGoal.child(EpisodeGoal.from_record(parent.as_record()['request']['goal']), **options))
            message = {'scope': {'subject_refs': []}, 'episode_assignment': {'nested': {'values': [1, 2]}},
                'initial_report': {}, 'knowledge_inheritance': manifest}
            request = EpisodeRequest(goal, Record(message)).as_record()
            with store.transaction():
                journal.save('runtime_episodes', {'episode_id': reference.episode_id, 'path': canonical(path),
                    'request': canonical(request), 'initial_credit': 0, 'state': 'active', 'completion': None, 'archive': None})
            return reader.context(reference.episode_id)

        context = capture((('annotation', 'root'),))
        yield store, reader, receipts, context, capture


def test_saved_private_context_is_exact_canonical_detached_immutable_type(saved_contexts):
    _, reader, _, context, _ = saved_contexts
    assert type(context) is BindingContext and reader.authenticate(context) is context
    detached = context.as_record()
    detached['assignment']['nested']['values'].append(9)
    assert context.assignment['nested']['values'] == (1, 2)
    with pytest.raises(TypeError):
        context.assignment['nested']['values'][0] = 4
    assert reader.context(context.episode_id).as_record() == context.as_record()


@pytest.mark.parametrize('field', ['run_id', 'episode_id', 'path', 'scope', 'assignment', 'request'])
def test_original_private_saved_reader_rejects_identity_or_request_changes(saved_contexts, field):
    _, reader, _, context, _ = saved_contexts
    changes = {'run_id': 'foreign-run', 'episode_id': 'foreign-episode',
        'path': (('annotation', 'foreign'),), 'scope': {'subject_refs': ['foreign']},
        'assignment': {'different': True}}
    if field == 'request':
        value = context.as_record()['request']
        value['message']['initial_report'] = {'unrecorded': True}
    else:
        value = changes[field]
    with pytest.raises(ValueError, match='boundary_(context_conflict|original_context_conflict)'):
        reader.authenticate(replace(context, **{field: value}))


def test_real_receipt_prefix_stays_frozen_and_does_not_create_work(saved_contexts):
    store, reader, receipts, parent, capture = saved_contexts
    earlier = store.artifact(b'earlier received bytes', 'text/plain')
    later = store.artifact(b'later received bytes', 'text/plain')
    receipts.receive(parent.episode_id, [earlier], kind='initial')
    child = capture(parent.path + (('literature', 'fixture-child'),), parent)
    receipts.receive(parent.episode_id, [later], kind='initial')
    assert set(receipts.known(child.episode_id)) == {earlier}
    assert set(receipts.known(parent.episode_id)) == {earlier, later}
    assert reader.authenticate(child) is child and type(child) is BindingContext
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0] == 0
    assert store.db.execute('SELECT COUNT(*) FROM runtime_observations').fetchone()[0] == 0


def test_context_eligibility_remains_exact_and_cache_bypass_is_separate(saved_contexts):
    _, reader, _, context, _ = saved_contexts
    bindings = import_module(PRIVATE + '.episode_bindings')
    cache = import_module(PRIVATE + '.form_reference_validation')
    # Counterfeit shape is solely a rejected negative; it supplies no authority
    # result and does not stand in for another axis's application type.
    foreign = SimpleNamespace(**context.as_record())
    class Subclass(BindingContext):
        pass
    subclass = Subclass(**context.as_record())
    assert bindings.BindingContext is BindingContext and type(foreign) is not BindingContext
    key = cache._binding_key(context)
    assert isinstance(key, str) and isinstance(hash(key), int)
    assert key == cache._binding_key(reader.context(context.episode_id))
    assert cache._binding_key(subclass) != cache._binding_key(subclass)
    assert cache._binding_key(foreign) != cache._binding_key(foreign)
    # The selected-native port originally uses isinstance, unlike the cache's
    # exact-type optimization. Preserve that distinction without executing work.
    assert bindings.native_observation_options('selected-operation', context)['observation_context'] is context
    assert bindings.native_observation_options('selected-operation', subclass)['observation_context'] is subclass
    with pytest.raises(import_module('gene_annotation_episode.domain').ContractError,
                       match='progress_observation_context_required'):
        bindings.native_observation_options('selected-operation', foreign)
    with pytest.raises(import_module('gene_annotation_episode.domain').ContractError,
                       match='progress_observation_context_requires_native_operation'):
        bindings.native_observation_options(None, context)
