"""The seven A103 literature bindings linked through the generic runner over the shared Store.

Real pieces only: each literature binding built by its own constructor with its own
``A103ToolRegistry`` over the run's one ``Store``, a real ``RunJournal``, the standard
``ModelProvider`` constructed from a Codex app-server configuration, and A103's
measured-context credit. No unit is run, so the model is never called: the test reads what
a linked literature episode presents and admits for its first decision and opens its
controller.
"""
from importlib import import_module

import pytest
from jsonschema import ValidationError

from episode_runtime import BindingRegistry, FormError, RunJournal, link
from method_loop import Episode
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.credit import A103ContextCredit
from gene_annotation_episode.episodic_workflow.episode_support.tools.gene_context_evidence.evidence_operations import A103ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.home import LITERATURE_HOMES, PACKAGE
from gene_annotation_episode.episodic_workflow.root.a103.gene_context_evidence.published_evidence_assessment.\
    literature_source import LiteratureSource

YIELD_BINDINGS = {'A103:a103_context_credit': {'kind': 'bounded_quality', 'cutoff': 0.01,
                                               'parameters': {'uncertainty_alpha': 0.1},
                                               'credit_definition': A103ContextCredit().as_record()}}
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
LITERATURE = 'gene_context_evidence/' + LITERATURE_HOMES[0]
EXAMINATION = 'gene_context_evidence/' + LITERATURE_HOMES[3]


@pytest.fixture(autouse=True)
def _own_local_resources(tmp_path, monkeypatch):
    """Each test binds its registries to its own local-resource directory, not the machine-wide one."""
    monkeypatch.setenv('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY', str(tmp_path / 'local-resources'))


def _registry(tmp_path, store):
    return BindingRegistry(tuple(
        getattr(import_module(PACKAGE + home.replace('/', '.') + '.episode'), 'LiteratureEpisode')(
            tool_registry=A103ToolRegistry(store, a103_work_directory=tmp_path / 'runs' / 'a103',
                                           target_genomic_sources={}),
            yield_bindings=YIELD_BINDINGS)
        for home in LITERATURE_HOMES))


def _link(tmp_path, store, registry, path, tools):
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
    entry = {'scope': {'subject_refs': [target]}, 'tools': tools, 'evidence_refs': [],
             'role_assignment': {'question': 'Is the target reported in a conserved operon with its partners?'}}
    return link(registry, path, entry, run_id='a103_literature_link', journal=RunJournal(tmp_path / 'journal.sqlite'),
                collaborators={'store': store, 'model_provider': provider})


def test_literature_episode_runs_its_own_source_and_continuation(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(tmp_path, store)
        binding = registry.binding(LITERATURE)
        tools = ['public.literature.search', 'source.read']
        run = _link(tmp_path, store, registry, LITERATURE, tools)
        assert isinstance(run.episode, Episode)
        source = run.episode.source
        assert type(source) is LiteratureSource
        schema = source.action_schema()
        options = schema['properties']['selection']['anyOf']
        kinds = [option['properties']['kind']['const'] for option in options]
        assert kinds.count('reason') == 1 and kinds.count('tool') == 2
        assert [option['properties']['role']['const'] for option in options
                if option['properties']['kind']['const'] == 'episode_child'] == list(binding.child_slots)
        assert source.credit_view()['credit'] == 0
        assert binding.instruction in source.instructions()
        controller = run.episode.grain.controller(((binding.grain_name, run.episode.key),))
        assert isinstance(controller, BoundedQualityYieldController)
        assert isinstance(controller.state().stop, bool)
        with pytest.raises(ValueError, match='a103_decision_response_must_be_exactly_selection'):
            source.admit({'choice': {}}, schema)
        # A child commission whose tools its own form does not offer is refused before acquisition.
        slot, = binding.child_slots
        target = run.episode.source._scope
        with pytest.raises(ValidationError):
            source.admit({'selection': {'kind': 'episode_child', 'role': slot, 'objective': 'Plan the search',
                                        'scope': target, 'role_assignment': {'question': 'operon'},
                                        'tools': ['context.fusion']}}, schema)
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()


def test_source_examination_offers_no_public_acquisition(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(tmp_path, store)
        assert not any(name.startswith('public.') for name in registry.binding(EXAMINATION).selectable_tools)
        with pytest.raises(FormError, match='not_an_offered_option'):
            _link(tmp_path, store, registry, EXAMINATION, ['public.literature.search'])
