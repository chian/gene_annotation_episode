"""The real world the A101 head's local-tool branch runs in: a Store holding a protein target (the first record of a
caller FASTA), a held reference protein (the second record, created as the run's caller, outside the assigned scope as a
comparison operand) and a proposed annotation of the target; the frozen option library; a frozen tool library of the
local tools the branch offers; the entry input passing the records in custody; the head's settings. Nothing is
faked: the runner, journal, Store, tool registry and model provider are the real ones."""
import importlib
from pathlib import Path

from episode_runtime import BindingRegistry, EpisodeBinding, RunJournal, link
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.configuration.sequence_homology_evidence.process_options import (
    SequenceHomologyEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.job_services import job_services
from gene_annotation_episode.episodic_workflow.episode_support.records.sequence_homology_evidence.construction_records import (
    SELECTION_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.tools.sequence_homology_evidence.tools import (
    ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary

from ..credit import A101SequenceCredit
from ..episode import SequenceHomologyEvidence

PATH = SequenceHomologyEvidence.binding_path
LIBRARY_SOURCE = Path(__file__).resolve().parents[6] / 'research' / 'slotted_process_library' / 'publications' / \
    '2026-10-24-001'
TARGET = 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVV'
REFERENCE = 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQGPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVV'
BLAST_BIN = Path(__file__).resolve().parents[6] / 'resources' / 'software' / 'ncbi-blast-2.17.0+' / 'bin'
TASK = 'Measure how similar the target protein is to the held reference protein and report what the measurement shows.'


def tool_registry_settings(directory):
    return {'minimap2_cache_dir': str(directory / 'minimap2-cache')}


def frozen_libraries(directory, store, tool_names):
    library = SequenceHomologyEvidenceLibrary.freeze(directory / 'option-library', source=LIBRARY_SOURCE)
    thought = next(header['option_ref'] for header in library.headers()
                   if header['option_ref']['slot'] == 'thought_pattern')
    available = ToolRegistry(store, **tool_registry_settings(directory)).catalog()
    tools = [{'name': name, 'resources': 'local', **available[name]} for name in tool_names]
    tool_library = ScientificToolLibrary.freeze(directory / 'tool-library', catalog=tools)
    information = tool_library.resolve_tool_info([{'name': name, 'resources': 'local'} for name in tool_names])
    selection = {'version': SELECTION_VERSION, 'evidence_axis': library.reference('A101'), 'thought_pattern': thought,
                 'child_tool_info': information}
    return selection, library.directory, tool_library.directory


def world(directory, tool_names, *, instruction=TASK):
    store = Store(directory / 'store')
    fasta = directory / 'proteins.fasta'
    fasta.write_text('>target\n' + TARGET + '\n>reference\n' + REFERENCE + '\n')
    created = store.create_problem(str(fasta), molecule='protein')
    target, reference = created['subject_refs']
    hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
                                          'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                           origin='caller')['id']
    selection, option_directory, tool_directory = frozen_libraries(directory, store, tool_names)
    assignment = {'selection': selection, 'proposed_annotation_ref': hypothesis,
                  'evidence_refs': [reference, store.get(reference)['sequence_ref']],
                  'constraints': {'instruction': instruction}, 'context': {},
                  'scope': {'subject_refs': [target]},
                  'scope_refs': [target, store.get(target)['sequence_ref'], hypothesis],
                  'child_credit_units': {'handoff_unit': 1.0, 'acquired_record_unit': 1.0, 'information_unit': 1.0,
                                         'completion_target': 1.0}}
    projector = A101SequenceCredit()
    settings = {'process_library_directory': str(option_directory), 'tool_library_directory': str(tool_directory),
                'tool_registry': tool_registry_settings(directory),
                'yield_bindings': {'A101:a101_native_sequence_correspondence': {
                    'kind': 'bounded_quality', 'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.1},
                    'credit_definition': projector.as_record()}}}
    return {'store': store, 'target': target, 'reference': reference, 'hypothesis': hypothesis,
            'assignment': assignment, 'settings': settings, 'directory': directory}


def subtree():
    root = Path(__file__).resolve().parent.parent
    package = SequenceHomologyEvidence.__module__.rsplit('.', 1)[0]
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
    """The run's services: the real job services with one local resource bound (the head reads the bound resources
    at every decision and offers a pairwise comparison on the local one)."""
    real = job_services({
        'local': {'local': {'workspace': str(directory / 'jobs'), 'cpu_threads': 1,
                            'policy': {'memory_bytes': 1024 ** 3, 'scratch_bytes': 64 * 1024 ** 2}}},
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


def collaborators(world, bindings, model_calls='model_calls'):
    """The head's settings and those of the child it can commission: a pairwise BLAST's cost, uncertainty
    parameter and the directory of the BLAST programs."""
    pairwise = {'cost': 0.2, 'parameters': {'uncertainty_alpha': 0.05}, 'blast_executable_directory': str(BLAST_BIN)}
    continuation = {binding.binding_path: {} for binding in bindings}
    continuation[PATH] = world['settings']
    continuation[PATH + '/pairwise_blast'] = pairwise
    return {'store': world['store'],
            'model_provider': ModelProvider(load_config(), world['directory'] / model_calls, world['directory']),
            'continuation': continuation, 'services': services(world['directory'], bindings)}


def linked(world, run_id, *, journal=None):
    bindings = subtree()
    entry = {'assignment': world['assignment'],
             'message': {'purpose': 'sequence-homology evidence for the target'},
             'selection': ['committed_record_refs']}
    return link(BindingRegistry(bindings), PATH, entry, run_id=run_id,
                journal=journal or RunJournal(world['directory'] / 'journal.sqlite3'),
                collaborators=collaborators(world, bindings))


def report_children(journal, run_id):
    """Print what each Episode below the head did with its commission, read from the journal: the first request its
    model was sent (the size of the instructions, their first words, the commission and the context keys), then
    each unit in order (the tool with the model's arguments and the outcome's status, or the child with its
    objective and return) with the credit the controller was given. Returns the printed rows per Episode."""
    rows = {}
    for episode in journal.episodes(run_id):
        path = tuple(tuple(step) for step in episode['path'])
        if len(path) < 2:
            continue
        name = '/'.join(key for _, key in path[1:])
        calls = journal.model_calls(run_id, path)
        if calls:
            request = calls[0]['request']
            print('CHILD_REQUEST', name, 'instructions', len(request['instructions']), 'first',
                  repr(request['instructions'][:90]), 'commission', request['context'].get('commission'),
                  'context_keys', sorted(request['context']))
        rows[name] = []
        for index, (label, controller_input, outcome, _) in enumerate(journal.units(run_id, path)):
            if outcome['kind'] == 'tool':
                arguments = outcome['arguments']
                shown = arguments['arguments'] if 'arguments' in arguments else arguments
                row = (index, outcome['tool'], shown, outcome['outcome'].get('status'))
            else:
                row = (index, 'child:' + outcome['slot'], outcome['message']['message'], outcome['report'])
            rows[name].append(row)
            print('CHILD_UNIT', name, *row, 'credit', controller_input['credit'])
        print('CHILD_END', name, 'model_calls', len(calls), 'completion', episode['completion'])
    return rows
