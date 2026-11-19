"""A103's commissioned report forms (C5) and the head's received-file reader, over real bindings and a real Store.

The A103 home factory builds the head over the run's shared Store; each Episode below
is a real ``BoundEpisode`` journaled in a real ``RunJournal``. The received-file reader
reads a test-written GenBank file the episode received as a Store Source. No model,
network or HPC job is used (the head's ``ModelProvider`` is constructed and never called).
"""
from dataclasses import replace
import json

import pytest

from episode_runtime import Field, RecordForm, RunJournal
from episode_runtime.journal import EpisodeRecorder
from episode_runtime.progress import ProgressClock
from episode_runtime.runner import BoundEpisode
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import ContractError, canonical
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence import home
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning import hpc_runtime
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning.episode import \
    HPCEpisode as PlanningEpisode
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning \
    .hpc_allocation_execution import allocation_runtime
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.hpc_work_planning \
    .hpc_allocation_execution.episode import HPCEpisode as AllocationEpisode
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.runtime_source import (
    HEAD_REPORT_FIELDS, A103Invocation, GeneContextEvidenceSource)
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.tests.test_head_runtime import (
    RUN, bound_head, services)
from gene_annotation_episode.episodic_workflow.episode_support.readers.gene_context_evidence.received_inputs import ReceivedFiles
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.tests.a103_test_support import genomic_file
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from method_loop import EpisodeRef

MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}


def _form(return_form, **added):
    return RecordForm({**return_form.fields, **added})


def _head(store, tmp_path):
    target, = store.create_problem(raw_sequence='MDEAKG', molecule='protein')['subject_refs']
    head = home.factory(services(store, tmp_path))[0]
    entry = {'scope': {'subject_refs': [target]}, 'thought_pattern': sorted(head.thought_patterns)[0],
             'tools': ['context.compare_neighborhoods'], 'evidence_refs': []}
    return target, head, bound_head(head, RunJournal(tmp_path / 'journal.sqlite'), entry)


def _descendant(binding, tmp_path, name, scope, report_form):
    """A real journaled BoundEpisode of an A103 descendant binding, admitted against ``report_form``."""
    journal = RunJournal(tmp_path / (name + '.sqlite'))
    commission = binding.entry_request({'scope': scope, 'role_assignment': {}}, {}, parent_goal=None)
    path = ((binding.grain_name, 'k'),)
    journal.open_run(RUN, {'entry_path': binding.binding_path})
    journal.open_episode(RUN, path, binding.binding_path, commission.as_record())
    recorder = EpisodeRecorder(journal, RUN, path)
    episode_id = EpisodeRef(RUN, path).episode_id
    return BoundEpisode(run_id=RUN, binding_path=binding.binding_path, path=path, key='k', episode_id=episode_id,
                        request=commission.request,
                        assignment=binding.assignment_form.admit(commission.assignment, 'assignment'),
                        recorder=recorder, progress=ProgressClock(recorder, run_id=RUN, episode_id=episode_id),
                        report_form=report_form)


# -- head (C5) ---------------------------------------------------------------------------------------

def test_head_commissioned_report_form_adds_its_held_finding_fields(tmp_path):
    with Store(tmp_path / 'state') as store:
        _, head, bound = _head(store, tmp_path)
        provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
        form = _form(head.return_form, evidence_refs=Field('list', 'The records the findings rest on'),
                     units=Field('integer', 'Units consumed', required=False))
        source = GeneContextEvidenceSource(head, replace(bound, report_form=form),
                                           {'store': store, 'model_provider': provider}, {})
        assert source._report_fields == ('evidence_refs', 'units')
        assert set(HEAD_REPORT_FIELDS) >= set(source._report_fields)


def test_head_commissioned_report_field_it_does_not_hold_raises(tmp_path):
    with Store(tmp_path / 'state') as store:
        _, head, bound = _head(store, tmp_path)
        provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
        form = _form(head.return_form, summary=Field('text', 'A narrative summary the head never records'))
        with pytest.raises(ContractError, match='a103_head_commissioned_report_field_not_held:gene_context_evidence:'
                                                'summary'):
            GeneContextEvidenceSource(head, replace(bound, report_form=form),
                                      {'store': store, 'model_provider': provider}, {})


# -- HPC planning and allocation execution (C5) ------------------------------------------------------

@pytest.mark.parametrize('binding, held', [(PlanningEpisode(), hpc_runtime.PLANNING_REPORT_FIELDS),
                                           (AllocationEpisode(), allocation_runtime.EXECUTION_REPORT_FIELDS)])
def test_hpc_commissioned_report_form_adds_only_held_finding_fields(binding, held, tmp_path):
    with Store(tmp_path / 'state') as store:
        target, = store.create_problem(raw_sequence='ATGGCT', molecule='dna')['subject_refs']
        scope = {'subject_refs': [target]}
        own = _descendant(binding, tmp_path, 'own', scope, binding.return_form)
        assert hpc_runtime.commissioned_report_fields(binding, own, held) == ()
        form = _form(binding.return_form, hpc_ledger=Field('text', 'The ledger path'),
                     units=Field('integer', 'Units consumed'))
        bound = _descendant(binding, tmp_path, 'added', scope, form)
        assert hpc_runtime.commissioned_report_fields(binding, bound, held) == ('hpc_ledger', 'units')
        wrong = _descendant(binding, tmp_path, 'wrong', scope,
                            _form(binding.return_form, summary=Field('text', 'Never recorded')))
        with pytest.raises(hpc_runtime.HPCRuntimeError,
                           match='a103_hpc_commissioned_report_field_not_held:' + binding.binding_path + ':summary'):
            hpc_runtime.commissioned_report_fields(binding, wrong, held)


def test_hpc_result_record_lifts_added_fields_and_leaves_unknown_ones_absent():
    finding = {'hpc_ledger': '/ledger', 'hpc_job_id': None, 'units': 3}
    record = hpc_runtime.result_record(1.5, finding, ('hpc_ledger', 'hpc_job_id')).as_record()
    assert record == {'credit': 1.5, 'finding': finding, 'hpc_ledger': '/ledger'}


# -- the head's received-file reader ------------------------------------------------------------------

def _received_source(store, tmp_path):
    path = genomic_file(tmp_path / 'A.1.gb', 'A.1')
    raw = store.artifact(path.read_bytes(), 'text/plain')
    source = store.put('source', {'provider': 'engineering.genome', 'accession': 'A.1', 'uri': None,
                                  'artifact_ref': raw, 'text_ref': raw, 'request_ref': None,
                                  'version': 'engineering_fixture', 'retrieved_at': None}, origin='external')['id']
    return path, raw, source


def _invocation(bound, scope, received):
    return A103Invocation(bound.run_id, bound.episode_id, tuple(bound.path), 'gene_context_evidence', scope,
                          tuple(received))


def test_reader_returns_the_received_source_file_with_its_store_producer(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, head, bound = _head(store, tmp_path)
        path, raw, source = _received_source(store, tmp_path)
        scope = {'subject_refs': [target]}
        context = _invocation(bound, scope, [target, source])
        delivery, retained = ReceivedFiles(store, context, bound.recorder, 0)(context, source, 'source',
                                                                               file_format='genbank_text')
        assert delivery['failure'] is None
        assert retained.read_bytes() == path.read_bytes()
        assert delivery['input']['file']['artifact_ref'] == raw
        assert delivery['input']['file']['size_bytes'] == path.stat().st_size
        producer = delivery['input']['producer']
        assert producer['kind'] == 'store_record' and producer['origin'] == 'external'
        assert producer['operations'] == []


def test_reader_refuses_a_source_the_episode_did_not_receive(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, head, bound = _head(store, tmp_path)
        _, _, source = _received_source(store, tmp_path)
        context = _invocation(bound, {'subject_refs': [target]}, [target])
        delivery, retained = ReceivedFiles(store, context, bound.recorder, 0)(context, source, 'source',
                                                                               file_format='genbank_text')
        assert retained is None and delivery['input'] is None
        assert delivery['failure'] == {'stage': 'authority', 'code': 'reference_not_received'}


def test_reader_reports_retained_bytes_that_no_longer_match_their_identity(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, head, bound = _head(store, tmp_path)
        _, raw, source = _received_source(store, tmp_path)
        digest = store.get(raw)['sha256']
        (store.path / 'artifacts' / digest[:2] / digest).write_bytes(b'altered')
        context = _invocation(bound, {'subject_refs': [target]}, [target, source])
        delivery, retained = ReceivedFiles(store, context, bound.recorder, 0)(context, source, 'source',
                                                                               file_format='genbank_text')
        assert retained is None
        assert delivery['failure'] == {'stage': 'bytes', 'code': 'artifact_identity_conflict'}


def test_reader_takes_the_producer_from_the_episodes_own_recorded_tool_outcome(tmp_path):
    with Store(tmp_path / 'state') as store:
        target, head, bound = _head(store, tmp_path)
        _, _, source = _received_source(store, tmp_path)
        result = {'status': 'completed', 'operation_ref': None, 'record_refs': [source], 'changed_record_refs': [],
                  'result': None}
        bound.recorder.recorded('outcome.0', lambda: {'kind': 'reason', 'status': 'completed', 'record_refs': [],
                                                      'result': {'status': 'completed', 'record_refs': []}})
        bound.recorder.recorded('outcome.1', lambda: {'kind': 'tool', 'status': 'completed',
                                                      'record_refs': [source], 'result': result})
        operation_key = bound.run_id + ':' + bound.episode_id + ':1'
        context = _invocation(bound, {'subject_refs': [target]}, [target, source])
        reader = ReceivedFiles(store, context, bound.recorder, 2)
        with pytest.raises(ContractError, match='a103_received_file_producer_operation_unrecorded:' + operation_key):
            reader(context, source, 'source', file_format='genbank_text')
        store.db.execute('INSERT INTO a103_operations VALUES(?,?,?)',
                         (operation_key, canonical({'name': 'context.bind_locus'}), canonical(result)))
        delivery, retained = reader(context, source, 'source', file_format='genbank_text')
        assert delivery['failure'] is None and retained is not None
        assert delivery['input']['producer'] == {
            'kind': 'recorded_tool_outcome', 'run_id': bound.run_id, 'episode_id': bound.episode_id, 'position': 1,
            'operation_key': operation_key, 'operation_ref': None, 'status': 'completed'}
        store.db.execute('UPDATE a103_operations SET result=? WHERE operation_key=?',
                         (json.dumps({**result, 'record_refs': []}), operation_key))
        with pytest.raises(ContractError, match='a103_received_file_producer_operation_conflict:' + operation_key):
            reader(context, source, 'source', file_format='genbank_text')
