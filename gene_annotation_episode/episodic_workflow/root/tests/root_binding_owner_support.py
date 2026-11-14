"""Engineering routing records, genuine Store/Journal and original private heads.

The descendant records below exercise custody/routing only. They are not accepted
private scientific assignments, completed actions, publications or earned credit.
The schema-required initial_credit=0 is inert fixture input. No private task runs.
"""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.episode import SignedRootEpisodeBinding
from gene_annotation_episode.episodic_workflow.root.episode_bindings import EpisodeBindingRegistry, EpisodeServices
from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.episode_services import WorkflowServices
from gene_annotation_episode.episodic_workflow.root.method_loop import EpisodeGoal, EpisodeRequest
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.root_assembly import create_signed_evidence_root_workflow
from gene_annotation_episode.episodic_workflow.root.scientific_process_records import validate_selection
from gene_annotation_episode.episodic_workflow.root.task_values import Record
from gene_annotation_episode.episodic_workflow.root.tests.fresh_decision_support import ConstructorTools, InputOnlyProvider
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.episode import ScientificProcessEpisode as A105Head
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process.published_evidence_assessment.episode import create_binding_tree as a105_tree
from gene_annotation_episode.episodic_workflow.root.a105.scientific_process_library import ScientificProcessLibrary as A105Library
from gene_annotation_episode.episodic_workflow.root.a105.scientific_tool_library import ScientificToolLibrary as A105Tools
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.episode import ScientificProcessEpisode as A108Head
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process.published_evidence_assessment.episode import create_binding_tree as a108_tree
from gene_annotation_episode.episodic_workflow.root.a108.scientific_process_library import ScientificProcessLibrary as A108Library
from gene_annotation_episode.episodic_workflow.root.a108.scientific_tool_library import ScientificToolLibrary as A108Tools

REPO = Path(__file__).resolve().parents[4]
OWNERS = ('A105', 'A108')
MEMBER = 'root_binding_selection'
CONFIGURATION = ((A105Head, a105_tree, A105Library, A105Tools),
                 (A108Head, a108_tree, A108Library, A108Tools))


def detached(value):
    return json.loads(json.dumps(value))


def canonical_owner(value):
    module = sys.modules[value.__module__]
    relative = Path(*value.__module__.split('.')).with_suffix('.py')
    expected = REPO / relative
    assert expected.is_file() and Path(module.__file__).resolve() == expected.resolve()
    current = REPO
    for part in relative.parts:
        current /= part
        assert not current.is_symlink()
    assert getattr(module, value.__name__) is value


def library_input():
    source = REPO / 'research/slotted_process_library/publications/2026-10-24-001'
    paths = set()
    for line in (Path(__file__).parent / 'fixtures/root_binding_owner_library.sha256').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        path = REPO / relative
        assert path.is_relative_to(source) and '..' not in Path(relative).parts
        current = REPO
        for part in Path(relative).parts:
            current /= part
            assert not current.is_symlink()
        assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest
        assert path not in paths
        paths.add(path)
    assert paths == {p for p in source.rglob('*') if p.is_file()}
    return source


@dataclass
class OwnerRoot:
    store: Store
    workflow: object
    episode: object
    groups: dict
    tools: ConstructorTools
    provider: InputOnlyProvider
    root_credit: object

    @property
    def records(self):
        return EpisodeReturnRecords(self.store, self.workflow.run_id, failure_prefix='root_binding_')

    @property
    def context(self):
        return self.records.context(self.episode.source.episode_id)

    def assert_no_execution(self):
        assert self.tools.execution_calls == [] and self.provider.requests == []
        for table in ('runtime_observations', 'runtime_model_calls', 'runtime_forms',
                      'runtime_report_attempts', 'runtime_timed_commissions'):
            assert list(self.store.db.execute('SELECT * FROM ' + table + ' WHERE run_id=?',
                                             (self.workflow.run_id,))) == []
        assert all(row['result'] is None and row['credit'] is None
                   for row in self.store.db.execute('SELECT result,credit FROM runtime_actions WHERE run_id=?',
                                                    (self.workflow.run_id,)))
        assert self.workflow.journal.row('runtime_episodes', self.episode.source.episode_id)['initial_credit'] == self.root_credit
        assert self.workflow._constructing_binding_requests == {}


@contextmanager
def actual_owner_root(directory, *, initialize=True):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for value in (Store, Journal, WorkflowServices, BindingContext, EpisodeRef, EpisodeGoal,
                  EpisodeRequest, Record, EpisodeBindingRegistry):
        canonical_owner(value)
    source = library_input()
    tools, provider = ConstructorTools(), InputOnlyProvider()
    libraries = {}
    for owner, (head_type, tree_factory, library_type, tool_type) in zip(OWNERS, CONFIGURATION):
        for value in (head_type, tree_factory, library_type, tool_type):
            canonical_owner(value)
        libraries[owner] = (library_type.freeze(directory / owner / 'library', source=source),
                            tool_type.freeze(directory / owner / 'tools', catalog=tools.catalog(), tool_info=True))
    raw = (Path(__file__).parent / 'fixtures/fresh_decision_binding.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '14abad6673f40e74f2494ed9dec06125d4883720d903a30596b47fcfe662b437'
    signed = SignedRootEpisodeBinding.from_record(json.loads(raw))
    groups = {}

    def head_factory(owner, head_type, tree_factory):
        def construct(services):
            library, tool_library = libraries[owner]
            head = head_type(services, library=library, tool_library=tool_library,
                             child_roles=('scientific_process', 'literature'))
            children = tuple(tree_factory(services))
            assert len(children) == 7
            groups[owner] = (head, *children)
            assert all(item.services is services for item in groups[owner])
            return head
        return construct

    def child_factory(owner, index):
        def supplied_original(services):
            child = groups[owner][index]
            assert child.services is services
            return child
        return supplied_original

    factories, owners = [], []
    for owner, (head_type, tree_factory, _, _) in zip(OWNERS, CONFIGURATION):
        factories.append(head_factory(owner, head_type, tree_factory))
        factories.extend(child_factory(owner, index) for index in range(1, 8))
        owners.extend([owner] * 8)
    with Store(directory / 'store') as store:
        if initialize:
            store.create_problem(raw_sequence='ATGAAATAG', molecule='dna', role='assembly')
        workflow = create_signed_evidence_root_workflow(store, tools, provider, directory / 'workflow',
            'engineering-root-owner-routing', signed.yield_controller,
            initial_known_record_refs=signed.initial_known_record_refs, project_credit=signed.task_credit,
            credit_binding=signed.task_credit.as_record(), controller_binding=signed.controller_record(),
            episode_binding_factories=tuple(factories), episode_binding_owners=tuple(owners),
            annotation_child_roles=('scientific_process',))
        assert type(workflow.services) is WorkflowServices and isinstance(workflow.services, EpisodeServices)
        assert workflow.store is store and type(workflow.journal) is Journal
        episode = workflow.build('annotation', 'root', 'Engineering owner-routing boundary', store.validate_scope())
        root = OwnerRoot(store, workflow, episode, groups, tools, provider,
                         workflow.journal.row('runtime_episodes', episode.source.episode_id)['initial_credit'])
        try:
            yield root
        finally:
            root.assert_no_execution()


def engineering_edge(root, parent, *, owner='A105', role='scientific_process', index=0, save=True):
    """Use real typed requests/Journals; deliberately do not call private prepare."""
    assert type(parent) is BindingContext
    workflow = root.workflow
    binding = workflow.episode_bindings.for_child(parent.path, role, owner=owner)
    scope = root.store.validate_scope(parent.as_record()['scope'])
    process = validate_selection({'version': 'scientific_process_selection_v3',
        'evidence_axis': root.groups[owner][0].library.reference(owner),
        'thought_pattern': root.groups[owner][0].library.reference('P01'), 'child_tool_info': []})
    action = {'kind': 'episode_child', 'role': role, 'scope': scope,
              'goal': 'Engineering routing fixture; no private assignment acceptance',
              'purpose': 'Owner-routing boundary only', 'assignment': {'selection': process}}
    workflow.journal.save('runtime_actions', {'episode_id': parent.episode_id, 'decision_index': index,
                         'action': json.dumps(action), 'result': None, 'credit': None})
    selected = (workflow.binding_selection_for_child(root.episode.source, role, action, index)
                if parent.path == root.context.path else
                {'binding': workflow.episode_bindings.private_selection(owner, binding.binding_path),
                 'parent_episode_id': parent.episode_id, 'decision_index': index})
    path = (*parent.path, (role, 'child_' + str(index)))
    goal = EpisodeGoal.child(EpisodeGoal.from_record(parent.as_record()['request']['goal']),
                             objective=action['goal'], result_contract={'engineering_fixture': 'owner_routing'})
    request = EpisodeRequest(goal, Record({'scope': scope, 'initial_report': {},
        'engineering_fixture': 'routing_only_not_private_assignment', MEMBER: selected}))
    identity = EpisodeRef(workflow.run_id, path)
    context = BindingContext(workflow.run_id, identity.episode_id, role, path, scope, {}, request.as_record())
    if save:
        workflow.journal.save('runtime_episodes', {'episode_id': identity.episode_id, 'path': json.dumps(path),
            'request': json.dumps(request.as_record()), 'initial_credit': 0, 'state': 'active',
            'completion': None, 'archive': None})
        context = root.records.context(identity.episode_id)
    return context, request, selected


def rewrite_request(root, context, change):
    row = root.workflow.journal.row('runtime_episodes', context.episode_id)
    request = json.loads(row['request'])
    change(request)
    row['request'] = json.dumps(request)
    root.workflow.journal.save('runtime_episodes', row)


def rewrite_action(root, parent, index, change):
    row = root.workflow.journal.row('runtime_actions', parent.episode_id, index)
    action = json.loads(row['action'])
    change(action)
    row['action'] = json.dumps(action)
    root.workflow.journal.save('runtime_actions', row)


def narrower_scope(root):
    segment = dict(root.store.scope_coverage(root.context.as_record()['scope'])[0])
    segment['end'] -= 1
    return root.store.validate_scope({'subject_refs': list(root.context.scope['subject_refs']),
                                      'segments': [segment]}, root.context.as_record()['scope'])
