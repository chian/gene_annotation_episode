"""The real world the A103 grading tests run in: a Store with a protein target, a proposed annotation of it, two
engineered GenBank genomes (the fixture of the library's own ``a103_test_support.genomic_file``: an anchor CDS and a
partner CDS on the same strand, 9 bp apart; genome B's anchor differs from the target at one residue) and a
definition source; the frozen option library of this episode's tests and a frozen tool library of the A103 context
operations; the entry input passing every record in custody; the settings of the head. Nothing is faked: the runner,
journal, Store, registry, native worker and model provider are the real ones."""
import importlib
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord

from episode_runtime import BindingRegistry, EpisodeBinding, RunJournal, link
from episode_runtime.estimate_table import EstimateTable
from episode_runtime.job_access import JobAccess
from episode_runtime.resource_adapters import ResourceAdapters
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.model_provider import ModelProvider, load_config
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.configuration.gene_context_evidence.process_options import (
    GeneContextEvidenceLibrary)
from gene_annotation_episode.episodic_workflow.episode_support.jobs.instruction_libraries import InstructionLibraries
from gene_annotation_episode.episodic_workflow.episode_support.jobs.native_events import NativeEvents
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import (
    A103ContextCredit)
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.construction_records import (
    SELECTION_VERSION)
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.evidence_operations import (
    NAMES, A103ToolRegistry)
from gene_annotation_episode.episodic_workflow.episode_support.tools.tool_catalog import ScientificToolLibrary

from ..episode import GeneContextEvidence

PATH = GeneContextEvidence.binding_path
LIBRARY_SOURCE = Path(__file__).resolve().parent / 'fixtures' / 'publication' / '2026-10-24-001'
CODONS = {'M': 'ATG', 'D': 'GAT', 'E': 'GAA', 'A': 'GCT', 'K': 'AAA', 'G': 'GGT', 'Q': 'CAA'}
TARGET = 'MDEAKG'


def genbank(identity, *, anchor):
    """An engineered GenBank record (the library's ``genomic_file`` fixture): anchor then partner, same strand."""
    data, features, start = list('A' * 400), [], 100
    for name, sequence in (('anchor', anchor), ('partner', 'MKQQ')):
        nucleotides = ''.join(CODONS[residue] for residue in sequence) + 'TAA'
        data[start:start + len(nucleotides)] = nucleotides
        features.append(SeqFeature(SimpleLocation(start, start + len(nucleotides), strand=1), type='CDS',
                                   qualifiers={'locus_tag': [name], 'protein_id': [identity + '.' + name],
                                               'translation': [sequence], 'transl_table': ['11']}))
        start += len(nucleotides) + 9
    record = SeqRecord(Seq(''.join(data)), id=identity, name=identity, description='Engineered A103 fixture')
    record.annotations.update(molecule_type='DNA', topology='linear', organism='Engineering fixture')
    record.features = features
    from io import StringIO
    text = StringIO()
    SeqIO.write(record, text, 'genbank')
    return text.getvalue()


def source(store, provider, text, accession):
    artifact = store.artifact(text, 'text/plain')
    return store.put('source', {'provider': provider, 'accession': accession, 'uri': None, 'artifact_ref': artifact,
                                'text_ref': artifact, 'request_ref': None, 'version': 'engineering_fixture',
                                'retrieved_at': None}, origin='caller')


def registry_settings(directory):
    return {'minimap2_cache_dir': str(directory / 'minimap2-cache'),
            'a103_work_directory': str(directory / 'a103-work'), 'target_genomic_sources': {}}


def frozen_libraries(directory, store):
    """The frozen option library of the head's tests, and a frozen tool library of the A103 context operations as
    the registry offers them; the selection of A103, its first thought pattern and those tools."""
    library = GeneContextEvidenceLibrary.freeze(directory / 'option-library', source=LIBRARY_SOURCE)
    thought = next(header['option_ref'] for header in library.headers()
                   if header['option_ref']['slot'] == 'thought_pattern')
    available = A103ToolRegistry(store, **registry_settings(directory)).catalog()
    tools = [{'name': name, **available[name]} for name in NAMES]
    tool_library = ScientificToolLibrary.freeze(directory / 'tool-library', catalog=tools)
    information = tool_library.resolve_tool_info([{'name': name, 'resources': 'local'} for name in NAMES])
    selection = {'version': SELECTION_VERSION, 'evidence_axis': library.reference('A103'), 'thought_pattern': thought,
                 'child_tool_info': information}
    return selection, library.directory, tool_library.directory


def world(directory):
    """The Store and everything the head is handed."""
    store = Store(directory / 'store')
    target, = store.create_problem(raw_sequence=TARGET, molecule='protein')['subject_refs']
    hypothesis = store.put('hypothesis', {'subject_refs': [target], 'predicate': 'sequence_integrity',
                                          'value': {'type': 'enum', 'value': 'intact'}, 'context_refs': []},
                           origin='caller')['id']
    genome_a = source(store, 'engineering.genome', genbank('A.1', anchor=TARGET), 'A.1')
    genome_b = source(store, 'engineering.genome', genbank('B.1', anchor='MEEAKG'), 'B.1')
    definition = source(store, 'engineering.a103.definition',
                        canonical({'relationship': 'declared adjacent same-strand loci; no real function'}),
                        'definition')
    selection, option_directory, tool_directory = frozen_libraries(directory, store)
    evidence = [row[key] for row in (genome_a, genome_b, definition) for key in ('id', 'artifact_ref')]
    assignment = {'selection': selection, 'proposed_annotation_ref': [hypothesis], 'evidence_refs': evidence,
                  'constraints': {}, 'context': {'a103_task': {'name': 'gene_context'}},
                  'scope': {'subject_refs': [target]}, 'scope_refs': [target, store.get(target)['sequence_ref']]}
    projector = A103ContextCredit()
    settings = {'library_directory': str(option_directory), 'tool_library_directory': str(tool_directory),
                'tool_registry': registry_settings(directory),
                'yield_bindings': {'A103:gene_context': {'kind': 'bounded_quality', 'cutoff': 0.0,
                                                         'parameters': {'uncertainty_alpha': 0.1},
                                                         'credit_definition': projector.as_record()}},
                'child_values': {}}
    return {'store': store, 'target': target, 'hypothesis': hypothesis, 'genome_a': genome_a['id'],
            'genome_b': genome_b['id'], 'definition': definition['id'], 'assignment': assignment,
            'settings': settings, 'directory': directory}


def subtree():
    """Every binding of the head's subtree (its episode folders), as the registry needs them to link the head."""
    root = Path(__file__).resolve().parent.parent
    package = GeneContextEvidence.__module__.rsplit('.', 1)[0]
    bindings = []
    for path in sorted(root.rglob('episode.py')):
        relative = path.relative_to(root).parent.parts
        if 'tests' in relative:
            continue
        module = importlib.import_module('.'.join((package, *relative, 'episode')))
        bindings.extend(value() for value in vars(module).values()
                        if isinstance(value, type) and issubclass(value, EpisodeBinding) and value is not EpisodeBinding)
    return bindings


def services(directory):
    """The run's services the subtree declares, built from this world's configuration when first used: no job route,
    no resource, no instruction library is configured, so a job child commissioned here fails with the real
    service's own configuration error. The head itself declares none."""
    return {'job_access': lambda: JobAccess({}),
            'estimate_table': lambda: EstimateTable(directory / 'estimates.sqlite3'),
            'native_events': lambda: NativeEvents(directory / 'native-events'),
            'resource_adapter': lambda: ResourceAdapters([], {}),
            'instruction_libraries': lambda: InstructionLibraries(directory / 'launch-instructions',
                                                                  directory / 'tool-knowledge'),
            'resources': lambda: ResourceAdapters([], {})}


def linked(world, run_id, *, settings=None, journal=None):
    """The head linked as the entry of a new run, with its settings and the empty settings of every other binding
    of its subtree (they are built only when commissioned)."""
    bindings = subtree()
    continuation = {binding.binding_path: {} for binding in bindings}
    continuation[PATH] = settings or world['settings']
    collaborators = {'store': world['store'],
                     'model_provider': ModelProvider(load_config(), world['directory'] / 'model_calls',
                                                     world['directory']),
                     'continuation': continuation, 'services': services(world['directory'])}
    entry = {'assignment': world['assignment'], 'message': {'purpose': 'grade the gene context of the target'},
             'selection': ['committed_record_refs']}
    return link(BindingRegistry(bindings), PATH, entry, run_id=run_id,
                journal=journal or RunJournal(world['directory'] / 'journal.sqlite3'), collaborators=collaborators)
