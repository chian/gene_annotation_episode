"""Genuine A105 constructor operands; no scientific assignment or acquisition."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.episode import SignedRootEpisodeBinding
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.root_assembly import create_signed_evidence_root_workflow
from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import ConstructorTools, InputOnlyProvider
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.episode import ScientificProcessEpisode
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.episode import create_binding_tree
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.episodic_workflow.root.a105.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process_provenance import ScientificProcessProvenance
from gene_annotation_episode.episodic_workflow.root.a105.scientific_tool_retrieval import ScientificToolRetriever

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]


def canonical_owner(value, module_name, relative):
    assert value.__module__ == module_name
    module = sys.modules[module_name]
    source = REPO / relative
    current = REPO
    for part in Path(relative).parts:
        current /= part
        assert not current.is_symlink()
    assert Path(module.__file__).resolve() == source.resolve()
    assert getattr(module, value.__name__) is value


def validate_library_input():
    entries = {}
    source = REPO / 'research/slotted_process_library/publications/2026-10-24-001'
    for line in (Path(__file__).parent / 'fixtures/private_constructor_library.sha256').read_text().splitlines():
        expected, relative = line.split('  ', 1)
        path = REPO / relative
        assert '..' not in Path(relative).parts and path.is_relative_to(source) and path.is_file()
        current = REPO
        for part in Path(relative).parts:
            current /= part
            assert not current.is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        assert relative not in entries
        entries[relative] = expected
    assert {str(p.relative_to(REPO)) for p in source.rglob('*') if p.is_file()} == set(entries)
    return source


@dataclass
class ActualPrivateRoot:
    store: Store
    workflow: object
    episode: object
    head: ScientificProcessEpisode
    children: tuple
    tools: ConstructorTools
    provider: InputOnlyProvider

    @property
    def context(self):
        value = self.workflow.binding_context(self.episode.source)
        assert type(value) is BindingContext
        return value


def actual_rows(root):
    return {table: [dict(row) for row in root.store.db.execute('SELECT * FROM ' + table + ' WHERE run_id=?', (root.workflow.run_id,))]
            for table in ('runtime_actions', 'runtime_observations', 'runtime_model_calls')}


@contextmanager
def actual_private_root(directory, *, initialize=True, retrieval=None):
    canonical_owner(Store, 'gene_annotation_episode.state', 'gene_annotation_episode/state.py')
    prefix = 'gene_annotation_episode.episodic_workflow.root'
    base = 'gene_annotation_episode/episodic_workflow/root/'
    for value, name in ((WorkflowServices, 'episode_services'), (Journal, 'episode_journal'), (BindingContext, 'receiving_context')):
        canonical_owner(value, prefix + '.' + name, base + name + '.py')
    for value, name in ((ScientificProcessEpisode, 'scientific_process.episode'),
                        (ScientificProcessLibrary, 'scientific_process_library'),
                        (ScientificToolLibrary, 'scientific_tool_library'),
                        (ScientificProcessProvenance, 'scientific_process_provenance'),
                        (ScientificToolRetriever, 'scientific_tool_retrieval')):
        canonical_owner(value, prefix + '.a105.' + name, base + 'a105/' + name.replace('.', '/') + '.py')
    library = ScientificProcessLibrary.freeze(directory / 'scientific_library', source=validate_library_input())
    tools, provider = ConstructorTools(), InputOnlyProvider()
    tool_library = ScientificToolLibrary.freeze(directory / 'tool_library', catalog=tools.catalog(), tool_info=True)
    raw = (Path(__file__).parent / 'fixtures/fresh_decision_binding.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '14abad6673f40e74f2494ed9dec06125d4883720d903a30596b47fcfe662b437'
    binding = SignedRootEpisodeBinding.from_record(json.loads(raw))
    captured = {}

    def head_factory(services):
        head = ScientificProcessEpisode(services, library=library, tool_library=tool_library,
            child_roles=('scientific_process', 'literature'), tool_retrieval=retrieval)
        children = tuple(create_binding_tree(services))
        assert len(children) == 7 and all(item.services is services for item in (head, *children))
        captured.update(head=head, children=children, services=services)
        return head

    def child_factory(index):
        def from_actual_tree(services):
            assert captured['services'] is services
            return captured['children'][index]
        return from_actual_tree

    with Store(directory / 'store') as store:
        if initialize:
            store.create_problem(raw_sequence='ATGAAATAG', molecule='dna', role='assembly')
        scope = store.validate_scope()
        try:
            workflow = create_signed_evidence_root_workflow(store, tools, provider, directory / 'workflow',
                'engineering-selected-private-setup', binding.yield_controller,
                initial_known_record_refs=binding.initial_known_record_refs, project_credit=binding.task_credit,
                credit_binding=binding.task_credit.as_record(), controller_binding=binding.controller_record(),
                episode_binding_factories=(head_factory, *(child_factory(index) for index in range(7))),
                annotation_child_roles=('scientific_process',))
            assert type(workflow.services) is WorkflowServices and type(workflow.journal) is Journal
            assert workflow.store is store and captured['services'] is workflow.services
            episode = workflow.build('annotation', 'root', 'Engineering private setup reader boundary', scope)
            yield ActualPrivateRoot(store, workflow, episode, captured['head'], captured['children'], tools, provider)
        finally:
            assert provider.requests == [] and tools.execution_calls == []
