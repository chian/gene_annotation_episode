"""The real world the A104 head tests run in: a Store with a protein target and a proposed annotation of it; the frozen
option library (the published ``2026-10-24-001`` slotted process library, frozen into the test's directory) and a
frozen tool library of the A104 phylogeny operations; the entry input passing every record in custody; the settings of
the head; the services the head's subtree declares. Nothing is faked: the runner, journal, Store and model provider are
the real ones."""
import importlib
from pathlib import Path

from episode_runtime import BindingRegistry, EpisodeBinding, RunJournal, link
from episode_runtime.estimate_table import EstimateTable
from episode_runtime.job_access import JobAccess
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.grading.evolutionary_history_evidence.credit import (
    A104EvolutionaryCredit)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.evolutionary_history_evidence.process_options import (
    EvolutionaryHistoryEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.episode_support.records.evolutionary_history_evidence.construction_records import (
    SELECTION_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary

from ..episode import EvolutionaryHistoryEvidence
from ..task import PHYLOGENY_TOOLS

PATH = EvolutionaryHistoryEvidence.binding_path
LIBRARY_SOURCE = Path(__file__).resolve().parents[6] / 'research' / 'slotted_process_library' / 'publications' / \
    '2026-10-24-001'
TARGET = 'MDEAKGQKLV'


def frozen_libraries(directory):
    """The frozen option library and a frozen tool library of the A104 phylogeny operations; the selection of A104,
    its first thought pattern and those tools."""
    library = EvolutionaryHistoryEvidenceLibrary.freeze(directory / 'option-library', source=LIBRARY_SOURCE)
    thought = next(header['option_ref'] for header in library.headers()
                   if header['option_ref']['slot'] == 'thought_pattern')
    tools = [{'name': name, 'description': description, 'input_schema': schema, 'resources': 'local'}
             for name, description, schema in PHYLOGENY_TOOLS.values()]
    tool_library = ScientificToolLibrary.freeze(directory / 'tool-library', catalog=tools)
    information = tool_library.resolve_tool_info([{'name': tool['name'], 'resources': 'local'} for tool in tools])
    selection = {'version': SELECTION_VERSION, 'evidence_axis': library.reference('A104'), 'thought_pattern': thought,
                 'child_tool_info': information}
    return selection, library.directory, tool_library.directory


def world(directory):
    store = Store(directory / 'store')
    target, = store.create_problem(raw_sequence=TARGET, molecule='protein')['subject_refs']
    hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
                                          'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                           origin='caller')['id']
    selection, option_directory, tool_directory = frozen_libraries(directory)
    assignment = {'selection': selection, 'proposed_annotation_ref': hypothesis, 'evidence_refs': [],
                  'constraints': {}, 'context': {}, 'scope': {'subject_refs': [target]},
                  'record_refs': [hypothesis, target, store.get(target)['sequence_ref']]}
    projector = A104EvolutionaryCredit()
    settings = {'process_library_directory': str(option_directory), 'tool_library_directory': str(tool_directory),
                'tool_registry': {'minimap2_cache_dir': str(directory / 'minimap2-cache')},
                'yield_bindings': {'A104:a104_evolutionary_history': {
                    'kind': 'bounded_quality', 'cutoff': 0.0, 'parameters': {'uncertainty_alpha': 0.1},
                    'credit_definition': projector.as_record()}}}
    return {'store': store, 'target': target, 'hypothesis': hypothesis, 'assignment': assignment,
            'settings': settings, 'directory': directory}


def subtree():
    """Every binding of the head's subtree (its episode folders), as the registry needs them to link the head."""
    root = Path(__file__).resolve().parent.parent
    package = EvolutionaryHistoryEvidence.__module__.rsplit('.', 1)[0]
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
    """A factory for every service the subtree declares. The two with a real implementation are built from this
    world (no job route, so a job child fails with the real service's own configuration error); a declared service
    nothing implements yet fails with its name when built. The head itself declares none."""
    real = {'job_access': lambda: JobAccess({}),
            'estimate_table': lambda: EstimateTable(directory / 'estimates.sqlite3')}

    def missing(name):
        def build():
            raise LookupError('service_not_implemented:' + name)
        return build
    names = {name for binding in bindings for name in binding.services}
    return {name: real[name] if name in real else missing(name) for name in names}


def linked(world, run_id, *, journal=None):
    """The head linked as the entry of a new run, with its settings and the empty settings of every other binding of
    its subtree (they are built only when commissioned)."""
    bindings = subtree()
    continuation = {binding.binding_path: {} for binding in bindings}
    continuation[PATH] = world['settings']
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), world['directory'] / 'model_calls',
                                                     world['directory']),
                     'continuation': continuation, 'services': services(world['directory'], bindings)}
    entry = {'assignment': world['assignment'],
             'message': {'purpose': 'measure the evolutionary history of the target', 'initial_report': {}},
             'selection': ['committed_record_refs']}
    return link(BindingRegistry(bindings), PATH, entry, run_id=run_id,
                journal=journal or RunJournal(world['directory'] / 'journal.sqlite3'), collaborators=collaborators)
