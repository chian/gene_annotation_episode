"""The A101 head's ported credit and continuation (``build_controller``) on episode_runtime objects.

Real pieces only: the head binding built by its own constructor from the repository's
slotted process library, a real A101 Store, a real ``RunJournal``/``EpisodeRecorder``,
A101's native BLAST grader over a test-written synthetic BLAST document, and the head's
real ``A101SequenceCredit`` projection. No model, network or workflow run.

The ``BoundEpisode`` is assembled here from the runner's own journal objects exactly as
``episode_runtime.runner`` assembles it, so the controller is observed without a model
deciding any unit (``test_runtime_head_link`` links the head through the runner).
"""
import json
import math
from pathlib import Path

import pytest
from episode_runtime import RunJournal
from episode_runtime.journal import EpisodeRecorder
from episode_runtime.progress import ProgressClock
from episode_runtime.runner import BoundEpisode
from method_loop import Controller, EpisodeRef

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.blast_search import HSP_PROJECTION_VERSION, native_hsp_metadata
from yield_control import BoundedQualityYieldController
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.episode import SequenceHomologyEvidenceEpisode
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.native_correspondence_credit import A101SequenceCredit
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.runtime_credit import INITIAL_CREDIT_DECISION, head_credit_view, open_head_receipts
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.yield_estimator import HEAD_TASK
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sequence_homology_evidence.process_options import SequenceHomologyEvidenceLibrary
from gene_annotation_episode.episodic_workflow.episode_support.grading.similarity_search.sequence_homology_evidence.tests.test_blast_graders_integration import grade_json, native_document
from gene_annotation_episode.episodic_workflow.episode_support.grading.sequence_homology_evidence.tool_grading_artifacts import retain_tool_grading
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import ToolRegistry

REPOSITORY = Path(__file__).resolve().parents[6]
LIBRARY_SOURCE = REPOSITORY / 'research' / 'slotted_process_library' / 'publications' / '2026-10-24-001'
RUN_ID = 'a101_head_controller_run'
YIELD_BINDINGS = {HEAD_TASK: {'kind': 'bounded_quality', 'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05},
                              'credit_definition': A101SequenceCredit().as_record()}}


def _head(tmp_path, store, yield_bindings):
    """The head built by its own constructor with its own A101 tool registry over the run's Store."""
    library = SequenceHomologyEvidenceLibrary.freeze(tmp_path / 'library', source=LIBRARY_SOURCE)
    return SequenceHomologyEvidenceEpisode(library=library, tool_registry=ToolRegistry(store),
                                           yield_bindings=yield_bindings)


def _collaborators(store):
    return {'store': store}


def _bound(head, journal, target, key='head'):
    choices = {'thought_pattern': sorted(head.thought_patterns)[0], 'tools': list(head.selectable_tools[:1])}
    commission = head.entry_request({'scope': {'subject_refs': [target]}, **choices}, {}, parent_goal=None)
    path = ((head.grain_name, key),)
    journal.open_run(RUN_ID, {'entry_path': head.binding_path, 'key': key})
    journal.open_episode(RUN_ID, path, head.binding_path, commission.as_record())
    recorder = EpisodeRecorder(journal, RUN_ID, path)
    episode_id = EpisodeRef(RUN_ID, path).episode_id
    return BoundEpisode(RUN_ID, head.binding_path, path, key, episode_id, commission.request,
                        head.assignment_form.admit(commission.assignment, 'assignment'), recorder,
                        ProgressClock(recorder, run_id=RUN_ID, episode_id=episode_id), head.return_form)


def _received_blast_observation(store, target):
    """A real A101 BLAST grading of a synthetic native document, attached to its observation."""
    document = native_document()
    native = document['BlastOutput2'][0]['report']['results']['search']['hits'][0]['hsps'][0]
    artifact = store.artifact(json.dumps(document).encode(), 'application/json')
    retained = retain_tool_grading(store, provider='ncbi_blast', native_artifact_ref=artifact,
                                   grading=grade_json(_retain_correspondence=True))
    source = store.put('source', {'provider': 'ncbi_blast', 'accession': None, 'uri': None, 'artifact_ref': artifact,
                                  'text_ref': None, 'request_ref': None, 'version': None, 'retrieved_at': None,
                                  'auxiliary_artifact_refs': [retained]}, origin='tool')['id']
    reference = store.put('reference', {'reference_type': 'protein', 'source_ref': source, 'accession': 'SYN_A',
                                        'label': 'Synthetic native fixture', 'sequence_ref': None, 'molecule': 'protein',
                                        'length': 10, 'term_refs': [], 'context_refs': []}, origin='tool')['id']
    metadata = native_hsp_metadata(native, program='blastp', query_length=10, reference_length=10, hit_ordinal=0,
                                   hsp_ordinal=0)
    metadata['shared_projection'] = {'version': HSP_PROJECTION_VERSION, 'grading_artifact_ref': retained,
                                     'native_artifact_ref': artifact, 'hit_row': 0, 'hsp_row': 0}
    return store.put('observation', {
        'subject_refs': [target], 'source_subject_refs': [reference], 'kind': 'comparison', 'source_ref': source,
        'anchor': None, 'dependencies': [target, reference],
        'measurements': [{'name': 'bitscore', 'value': {'type': 'number', 'value': 10, 'unit_ref': None}}],
        'operand_intervals': [{'role': role, 'subject_ref': ref, 'start': 0, 'end': 5, 'unit': 'aa', 'model_unit': 'aa'}
                              for role, ref in [('query', target), ('reference', reference)]],
        'native_blast': metadata}, origin='tool')['id']


def test_head_controller_opens_on_recorded_credit_and_observes_received_native_correspondence(tmp_path):
    with Store(tmp_path / 'state') as store:
        head = _head(tmp_path, store, YIELD_BINDINGS)
        target, = store.create_problem(raw_sequence='ACDEFXXXXX', molecule='protein')['subject_refs']
        bound = _bound(head, RunJournal(tmp_path / 'journal.sqlite'), target)
        collaborators = _collaborators(store)
        controller = head.build_controller(bound, collaborators)
        assert isinstance(controller, Controller) and type(controller) is BoundedQualityYieldController
        assert controller.epoch == bound.episode_id
        opened = controller.state()
        assert opened.stop is False and opened.initial_credit == 0 and opened.current_credit == 0
        assert bound.recorder.recall(INITIAL_CREDIT_DECISION) == 0
        receipts = EpisodeReceipts(store, RUN_ID)
        initial = set(receipts.known(bound.episode_id))
        assert target in initial  # with the records the subject itself references

        observed = _received_blast_observation(store, target)
        receipts.receive(bound.episode_id, [observed], kind='own_action', source_index=0)
        credit = head_credit_view(bound, store, receipts)['credit']
        assert credit == pytest.approx((1 - math.exp(-0.025 * 10)) * 0.5 * 0.5)
        step = controller.observe('tool:0', {'credit': credit}, is_root=False)
        assert step.credit == credit and step.marginal_credit == credit
        assert type(step.stop) is bool and step.requests_transition is False
        assert controller.state().current_credit == credit and type(controller.state().stop) is bool

        # A rebuilt controller (resume) opens with the credit recorded when the episode first opened,
        # not with the credit its receipts now project.
        reopened = head.build_controller(bound, collaborators)
        assert reopened.state().initial_credit == 0
        assert open_head_receipts(bound, store).manifest(bound.episode_id)['parent_episode_id'] is None


def test_head_without_a_configured_yield_binding_cannot_be_constructed(tmp_path):
    with Store(tmp_path / 'state') as store:
        with pytest.raises(ContractError, match='a101_head_yield_bindings_must_declare_exactly'):
            _head(tmp_path, store, {})


def test_head_yield_binding_must_declare_the_head_credit_definition(tmp_path):
    changed = {HEAD_TASK: {**YIELD_BINDINGS[HEAD_TASK],
                           'credit_definition': {**A101SequenceCredit().as_record(), 'version': 'other'}}}
    with Store(tmp_path / 'state') as store:
        head = _head(tmp_path, store, changed)
        target, = store.create_problem(raw_sequence='ACDEFXXXXX', molecule='protein')['subject_refs']
        bound = _bound(head, RunJournal(tmp_path / 'journal.sqlite'), target)
        with pytest.raises(ContractError, match='a101_head_yield_credit_definition_mismatch'):
            head.build_controller(bound, _collaborators(store))
