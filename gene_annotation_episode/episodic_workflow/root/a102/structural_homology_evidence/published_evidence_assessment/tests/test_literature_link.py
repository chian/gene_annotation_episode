"""The seven A102 literature bindings linked through the generic runner over the shared Store.

Real pieces only: each literature binding built by its own constructor with its own A102
``ToolRegistry`` over the run's one ``Store``, a real ``RunJournal``, the standard
``ModelProvider`` constructed from a Codex app-server configuration, and A102's native structural
correspondence credit. No unit is run, so the model is never called: the test reads what a linked
literature episode presents and admits for its first decision and opens its controller.
"""
from importlib import import_module

import pytest
from jsonschema import ValidationError

from episode_runtime import BindingRegistry, FormError, RunJournal, link
from method_loop import Episode
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.grading.structural_homology_evidence.credit import A102StructuralCredit
from gene_annotation_episode.episodic_workflow.episode_support.tools.structural_homology_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.contract_binding import (
    LITERATURE_KINDS, PATHS)
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.runtime_continuation import \
    A102Continuation
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.published_evidence_assessment.\
    literature_binding import LiteratureBinding, literature_continuation
from gene_annotation_episode.episodic_workflow.root.a102.structural_homology_evidence.published_evidence_assessment.\
    literature_source import LiteratureSource

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a102.'
CONTINUATION = {'kind': 'bounded_quality', 'cutoff': 0.01, 'parameters': {'uncertainty_alpha': 0.1},
                'credit_definition': A102StructuralCredit().as_record()}
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
LITERATURE_PATHS = tuple(path for path in PATHS if path.rsplit('/', 1)[-1] in LITERATURE_KINDS)
LITERATURE = LITERATURE_PATHS[0]
EXAMINATION = next(path for path in LITERATURE_PATHS if path.endswith('/source_evidence_examination'))


@pytest.fixture(autouse=True)
def _own_local_resources(tmp_path, monkeypatch):
    """Each test binds its registries to its own local-resource directory, not the machine-wide one."""
    monkeypatch.setenv('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY', str(tmp_path / 'local-resources'))


def _binding_class(path):
    module = import_module(PACKAGE + path.replace('/', '.') + '.episode')
    classes = [value for value in vars(module).values() if isinstance(value, type)
               and issubclass(value, LiteratureBinding) and value is not LiteratureBinding]
    assert len(classes) == 1
    return classes[0]


def _registry(store):
    return BindingRegistry(tuple(_binding_class(path)(tool_registry=ToolRegistry(store), continuation=CONTINUATION)
                                 for path in LITERATURE_PATHS))


def _link(tmp_path, store, registry, path, tools):
    target, = store.create_problem(raw_sequence='M' + 'A' * 99, molecule='protein')['subject_refs']
    provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
    entry = {'scope': {'subject_refs': [target]}, 'tools': tools,
             'question': {'question': 'Which deposited structures of homologs resolve the active-site geometry?'}}
    return link(registry, path, entry, run_id='a102_literature_link', journal=RunJournal(tmp_path / 'journal.sqlite'),
                collaborators={'store': store, 'model_provider': provider})


def test_seven_literature_bindings_are_declared():
    assert len(LITERATURE_PATHS) == 7


def test_literature_episode_runs_its_own_source_and_continuation(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(store)
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
        assert [option['properties']['slot']['const'] for option in options
                if option['properties']['kind']['const'] == 'episode_child'] == list(binding.child_slots)
        credit, _ = source.credit_view()
        assert credit == 0
        assert binding.instruction in source.instructions()
        controller = run.episode.grain.controller(((binding.grain_name, run.episode.key),))
        assert isinstance(controller, A102Continuation)
        assert isinstance(controller.controller, BoundedQualityYieldController)
        assert isinstance(controller.state().stop, bool)
        with pytest.raises(ValueError, match='a102_decision_response_must_be_exactly_selection'):
            source.admit({'choice': {}}, schema)
        # A child commission whose tools its own form does not offer is refused before acquisition.
        slot, = binding.child_slots
        child = {'kind': 'episode_child', 'slot': slot, 'objective': 'Plan the structure search',
                 'scope': source._scope, 'assignment': {'question': {'question': 'search'},
                                                        'tools': ['public.literature.search']}}
        assert source.admit({'selection': child}, schema) == child
        with pytest.raises(ValidationError):
            source.admit({'selection': {**child, 'assignment': {'question': {'question': 'search'},
                                                                'tools': ['sequence.align']}}}, schema)
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()


def test_source_examination_offers_no_public_acquisition(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(store)
        assert not any(name.startswith('public.') for name in registry.binding(EXAMINATION).selectable_tools)
        with pytest.raises(FormError, match='not_an_offered_option'):
            _link(tmp_path, store, registry, EXAMINATION, ['public.literature.search'])


def test_continuation_declaration_must_be_the_literature_credit():
    with pytest.raises(ContractError, match='credit_definition_mismatch'):
        literature_continuation({**CONTINUATION, 'credit_definition': {'kind': 'another'}})
    with pytest.raises(ContractError, match='method_credit_mismatch'):
        literature_continuation({**CONTINUATION, 'kind': 'accumulation'})
