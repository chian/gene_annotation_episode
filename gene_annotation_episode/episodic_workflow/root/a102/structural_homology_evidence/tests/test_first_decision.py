"""The A102 head stepped offline to its first decision in a real world (no model): ``link`` and
``EpisodeRun.next_decision`` with a real Store, journal and job services. Entering the Episode computes ``credit`` of
the initial summary and ``internal_summary``, whose credit view reads the finding progress through the custody reader
(``findings/structural_homology_evidence/investigation_progress.py``: ``project_finding_progress`` on the
``RecordReader``); ``decide`` then builds the request the model would be sent.

World: a caller FASTA with one protein (the target of the scope), a proposed hypothesis about it, the published
process library, a selection that names no library tool and no named ``a102_task`` (so the credit is the finding
progress), and the accumulation yield binding of that credit."""
import asyncio
import importlib
from pathlib import Path

from episode_runtime import BindingRegistry, EpisodeBinding, ModelRequest, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.records.structural_homology_evidence.construction_records import (
    SELECTION_VERSION)

from .. import credit as credit_file, task
from ..episode import StructuralHomologyEvidence

PATH = StructuralHomologyEvidence.binding_path
LIBRARY_SOURCE = Path(__file__).resolve().parents[6] / 'research' / 'slotted_process_library' / 'publications' / \
    '2026-10-24-001'
TARGET = 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVV'


def subtree():
    root = Path(__file__).resolve().parent.parent
    package = StructuralHomologyEvidence.__module__.rsplit('.', 1)[0]
    bindings = []
    for path in sorted(root.rglob('episode.py')):
        relative = path.relative_to(root).parent.parts
        if 'tests' in relative:
            continue
        module = importlib.import_module('.'.join((package, *relative, 'episode')))
        bindings.extend(value() for value in vars(module).values()
                        if isinstance(value, type) and issubclass(value, EpisodeBinding) and value is not EpisodeBinding)
    return bindings


def services(directory, bindings):
    real = job_services({
        'local': {'local': {'workspace': str(directory / 'jobs'), 'cpu_threads': 1,
                            'policy': {'memory_bytes': 256 * 1024 ** 2, 'scratch_bytes': 64 * 1024 ** 2}}},
        'pbs': {}, 'capabilities': [], 'event_ledger_directory': str(directory / 'events'),
        'estimate_table_path': str(directory / 'estimates' / 'table.sqlite3'),
        'launch_instructions_directory': str(directory / 'no_launch_instructions'),
        'tool_knowledge_directory': str(directory / 'no_tool_knowledge')})

    def missing(name):
        def build():
            raise LookupError('service_not_implemented:' + name)
        return build
    names = {name for binding in bindings for name in binding.services}
    return {name: real[name] if name in real else missing(name) for name in names}


def test_the_head_reaches_its_first_decision_with_the_finding_progress_read_through_custody(tmp_path):
    store = Store(tmp_path / 'store')
    fasta = tmp_path / 'protein.fasta'
    fasta.write_text('>target\n' + TARGET + '\n')
    target, = store.create_problem(str(fasta), molecule='protein')['subject_refs']
    hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
                                          'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                           origin='caller')['id']
    library = task.StructuralHomologyEvidenceLibrary.freeze(tmp_path / 'option-library', source=LIBRARY_SOURCE)
    thought = next(header['option_ref'] for header in library.headers()
                   if header['option_ref']['slot'] == 'thought_pattern')
    # no library tool is selected: the head's own tools and its children are what the first decision offers
    selection = {'version': SELECTION_VERSION, 'evidence_axis': library.reference('A102'),
                 'thought_pattern': thought, 'child_tool_info': []}
    scope = {'subject_refs': [target]}
    assignment = {'selection': selection, 'proposed_annotation_ref': [hypothesis], 'evidence_refs': [],
                  'constraints': {}, 'context': {}, 'scope': scope,
                  'scope_refs': [target, store.get(target)['sequence_ref']]}
    # no named a102_task: the credit is the received retained findings (``ScientificFindingProgress``)
    definition = credit_file.projector(None).as_record()
    settings = {'process_library_directory': str(library.directory),
                'yield_bindings': {'A102:' + definition['kind']: {
                    'kind': 'accumulation', 'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.1},
                    'credit_definition': definition}}}
    bindings = subtree()
    continuation = {binding.binding_path: {} for binding in bindings}
    continuation[PATH] = settings
    run = link(BindingRegistry(bindings), PATH,
               {'assignment': assignment, 'message': {'purpose': 'structural homology evidence for the target'},
                'selection': []},
               run_id='a102-first-decision', journal=RunJournal(tmp_path / 'journal.sqlite3'),
               collaborators={'store': store, 'continuation': continuation, 'services': services(tmp_path, bindings),
                              'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)})
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest)
    assert request.context['investigation_progress']['retained_finding_count'] == 0
    assert request.context['current_credit'] == 0.0
    summary = StructuralHomologyEvidence.internal_summary(run.view)
    assert summary['credit_view']['policy'] == definition['policy']
    assert StructuralHomologyEvidence.credit(summary, run.view.records) == 0.0
    assert not list((tmp_path / 'model_calls').glob('call-*'))
    store.close()
