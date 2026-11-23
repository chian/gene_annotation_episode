"""The A108 head stepped offline to its first model decision in a real world (no model): ``link``,
``EpisodeRun.next_decision`` and ``EpisodeRun.run_unit`` with a real Store, journal and job services. Entering the
Episode computes ``credit`` of the initial summary and ``internal_summary``, which read the finding progress through
the custody reader (``findings/sample_context_evidence/investigation_progress.py``: ``project_finding_progress`` on
the ``RecordReader``). The head's first unit is its own lookup of the selection (a ``ToolCall`` decided by code);
after it ``decide`` builds the request the model would be sent.

World: a caller FASTA with one protein (the target of the scope), a proposed hypothesis about it, the published
process library, a frozen tool library of the head's access tools as the selected tools, and the whole-axis finding
task with credit unit 1."""
import asyncio
import importlib
from pathlib import Path

from episode_runtime import BindingRegistry, EpisodeBinding, ModelRequest, RunJournal, ToolCall, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.records.sample_context_evidence.construction_records import (
    SELECTION_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary

from .. import task
from ..episode import SampleContextEvidence

PATH = SampleContextEvidence.binding_path
LIBRARY_SOURCE = Path(__file__).resolve().parents[6] / 'research' / 'slotted_process_library' / 'publications' / \
    '2026-10-24-001'
TARGET = 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVV'


def subtree():
    root = Path(__file__).resolve().parent.parent
    package = SampleContextEvidence.__module__.rsplit('.', 1)[0]
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
    library = task.SampleContextEvidenceLibrary.freeze(tmp_path / 'option-library', source=LIBRARY_SOURCE)
    thought = next(header['option_ref'] for header in library.headers()
                   if header['option_ref']['slot'] == 'thought_pattern')
    rows = [{'name': name, 'resources': 'local', 'description': name, 'input_schema': schema}
            for name, schema in task.INPUT_SCHEMAS.items()]
    tools = ScientificToolLibrary.freeze(tmp_path / 'tool-library', catalog=rows)
    selection = {'version': SELECTION_VERSION, 'evidence_axis': library.reference('A108'),
                 'thought_pattern': thought,
                 'child_tool_info': [{'name': row['name'], 'resources': 'local'} for row in rows]}
    scope = {'subject_refs': [target]}
    held = [target, store.get(target)['sequence_ref'], hypothesis]
    assignment = {'selection': selection, 'proposed_annotation_ref': hypothesis, 'evidence_refs': [],
                  'constraints': {}, 'scope': scope, 'received_record_refs': held,
                  'context': {'evidence_task': {'version': 'evidence_axis_task', 'kind': 'whole_axis_findings',
                                                'evidence_axis': 'A108', 'credit_unit': 1.0}}}
    settings = {'process_library_directory': str(library.directory), 'tool_library_directory': str(tools.directory)}
    bindings = subtree()
    continuation = {binding.binding_path: {} for binding in bindings}
    continuation[PATH] = settings
    run = link(BindingRegistry(bindings), PATH,
               {'assignment': assignment, 'message': {'purpose': 'sample context evidence for the target'},
                'selection': []},
               run_id='a108-first-decision', journal=RunJournal(tmp_path / 'journal.sqlite3'),
               collaborators={'store': store, 'continuation': continuation, 'services': services(tmp_path, bindings),
                              'model_provider': ModelProvider(load_config(), tmp_path / 'model_calls', tmp_path)})
    # the first decision is the head's own lookup of what its selection names (decided by code)
    first = asyncio.run(run.next_decision())
    assert isinstance(first, ToolCall) and first.name == 'process_selection'
    looked_up = asyncio.run(run.run_unit(first))
    assert looked_up['outcome']['status'] == 'completed', looked_up['outcome']
    # the decision after it is the request the model would be sent, with the finding progress read through custody
    request = asyncio.run(run.next_decision())
    assert isinstance(request, ModelRequest)
    assert request.context['investigation_progress']['retained_finding_count'] == 0
    assert request.context['current_credit'] == 0.0
    summary = SampleContextEvidence.internal_summary(run.view)
    assert SampleContextEvidence.credit(summary, run.view.records) == 0.0
    assert not list((tmp_path / 'model_calls').glob('call-*'))
    store.close()
