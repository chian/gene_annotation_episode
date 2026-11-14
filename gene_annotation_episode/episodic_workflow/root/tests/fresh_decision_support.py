"""Genuine Store/root construction operands for engineering boundary tests."""
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.episode import SignedRootEpisodeBinding
from gene_annotation_episode.episodic_workflow.root.root_assembly import create_signed_evidence_root_workflow


class ProviderUnavailable(RuntimeError):
    pass


class ConstructorTools:
    def __init__(self):
        self.execution_calls = []

    def catalog(self, *, scope=None):
        return []

    def execute(self, *args, **kwargs):
        self.execution_calls.append((args, kwargs))
        raise RuntimeError('engineering_fixture_has_no_acquisition_capability')


class InputOnlyProvider:
    def __init__(self):
        self.requests = []

    async def complete(self, episode_id, purpose, instructions, context, output_schema):
        self.requests.append(json.loads(json.dumps({'episode_id': episode_id, 'purpose': purpose,
            'instructions': instructions, 'context': context, 'output_schema': output_schema})))
        raise ProviderUnavailable('no_provider_transport_or_response_supplied')


@dataclass
class ActualRoot:
    store: Store
    binding: SignedRootEpisodeBinding
    workflow: object
    episode: object
    tools: ConstructorTools
    provider: InputOnlyProvider
    scope: dict

    @property
    def source(self):
        return self.episode.source


@contextmanager
def actual_root(directory, *, initialize=True):
    raw = (Path(__file__).parent / 'fixtures/fresh_decision_binding.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '14abad6673f40e74f2494ed9dec06125d4883720d903a30596b47fcfe662b437'
    binding = SignedRootEpisodeBinding.from_record(json.loads(raw))
    tools, provider = ConstructorTools(), InputOnlyProvider()
    with Store(directory / 'store') as store:
        if initialize:
            store.create_problem(raw_sequence='ATGAAATAG', molecule='dna', role='assembly')
        scope = store.validate_scope()
        workflow = create_signed_evidence_root_workflow(store, tools, provider, directory / 'workflow',
            'engineering-fresh-decision-helper-tests', binding.yield_controller,
            initial_known_record_refs=binding.initial_known_record_refs, project_credit=binding.task_credit,
            credit_binding=binding.task_credit.as_record(), controller_binding=binding.controller_record(),
            episode_binding_factories=(), annotation_child_roles=())
        episode = workflow.build('annotation', 'root', 'Engineering root decision helper connection', scope)
        yield ActualRoot(store, binding, workflow, episode, tools, provider, scope)


@contextmanager
def initial_view(root):
    scope = root.workflow.context.enter(root.episode.grain, root.episode.key)
    try:
        root.source.bind_execution_context(root.workflow.context)
        yield root.episode._view(root.workflow.context, scope, [])
    finally:
        root.workflow.context.leave(scope)


def action_rows(root):
    return {name: [dict(row) for row in root.store.db.execute('SELECT * FROM ' + name)]
            for name in ('runtime_actions', 'runtime_observations', 'runtime_model_calls')}
