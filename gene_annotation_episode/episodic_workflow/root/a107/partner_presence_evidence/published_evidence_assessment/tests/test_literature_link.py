"""The seven A107 literature bindings linked through the generic runner over the shared Store.

Real pieces only: each literature binding built by its own constructor with its own
``A107ToolRegistry`` over the run's one ``Store``, a real ``RunJournal``, the standard
``ModelProvider`` constructed from a Codex app-server configuration, and A107's
finding-progress credit. No unit is run, so the model is never called: the test reads what
a linked literature episode presents for its first decision and opens its controller.
"""
import pytest

from episode_runtime import BindingRegistry, FormError, RunJournal, link
from method_loop import Episode
from yield_control import AccumulationYieldController

from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.tools.partner_presence_evidence.evidence_operations import A107ToolRegistry
from gene_annotation_episode.episodic_workflow.episode_support.acquisition.partner_presence_evidence.acquisition import PublicClients
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.episode import (
    DESCENDANT_PATHS, LITERATURE_PATH, _descendant)
from gene_annotation_episode.episodic_workflow.root.a107.partner_presence_evidence.published_evidence_assessment.\
    literature_cycle import LiteratureCycleSource

PATHS = tuple(path for path in DESCENDANT_PATHS if path.startswith(LITERATURE_PATH))
EXAMINATION = LITERATURE_PATH + ('/evidence_search_strategy_improvement/source_relevance_assessment/'
                                 'source_evidence_examination')
MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}


@pytest.fixture(autouse=True)
def _own_local_resources(tmp_path, monkeypatch):
    """Each test binds its registries to its own local-resource directory, not the machine-wide one."""
    monkeypatch.setenv('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY', str(tmp_path / 'local-resources'))


def _registry(tmp_path, store):
    from importlib import import_module
    base = 'gene_annotation_episode.episodic_workflow.root.a107.'
    return BindingRegistry(tuple(
        _descendant(import_module(base + path.replace('/', '.') + '.episode'))(
            tool_registry=A107ToolRegistry(store, a107_work_directory=str(tmp_path / 'a107_work'), a107_detection_bindings=[],
                clients=PublicClients(), cmsearch_executable=None, minimap2_executable=None,
                minimap2_cache_dir=tmp_path / 'minimap2-cache', pdfinfo_executable=None,
                pdftotext_executable=None, pdftoppm_executable=None))
        for path in PATHS))


def _link(tmp_path, store, registry, path, tools):
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
    continuation = {binding_path: {'cutoff': 0.5, 'parameters': {'uncertainty_alpha': 0.05}, 'finding_unit': 1}
                    for binding_path in PATHS}
    entry = {'objective': 'Which partners does the target require according to published omission experiments?',
             'scope': {'subject_refs': [target]}, 'tools': tools,
             'assignment': {'question': 'partner requirement of the target activity'}}
    return link(registry, path, entry, run_id='a107_literature_link', journal=RunJournal(tmp_path / 'journal.sqlite'),
                collaborators={'store': store, 'model_provider': provider, 'continuation': continuation})


def test_literature_episode_runs_its_own_source_and_continuation(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(tmp_path, store)
        binding = registry.binding(LITERATURE_PATH)
        tools = ['public.literature.search', 'source.read']
        run = _link(tmp_path, store, registry, LITERATURE_PATH, tools)
        assert isinstance(run.episode, Episode)
        source = run.episode.source
        assert type(source) is LiteratureCycleSource
        assert set(source.catalog()) == set(tools)
        assert binding.instruction in source.instructions()
        controller = run.episode.grain.controller(((binding.grain_name, run.episode.key),))
        assert isinstance(controller, AccumulationYieldController)
        assert isinstance(controller.state().stop, bool)
        source._restore(0)
        context = source.context(0, 0, controller.state())
        assert context['assignment'] == {'question': 'partner requirement of the target activity'}
        assert sorted(context['child_slots']) == sorted(binding.child_slots)
        assert set(context['tool_catalog']) == set(tools)
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()


def test_source_examination_offers_no_public_acquisition(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(tmp_path, store)
        assert not any(name.startswith('public.') for name in registry.binding(EXAMINATION).selectable_tools)
        with pytest.raises(FormError, match='not_an_offered_option'):
            _link(tmp_path, store, registry, EXAMINATION, ['public.literature.search'])
