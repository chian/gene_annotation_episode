"""The seven A104 literature bindings linked through the generic runner over the shared Store.

Real pieces only: each literature binding built by the class its home declares (as ``a104_home``
selects it) with its own A104 ``ToolRegistry`` over the run's one ``Store``, a real ``RunJournal``,
the standard ``ModelProvider`` constructed from a Codex app-server configuration, and A104's
evolutionary-history credit. No unit is run, so the model is never called: the test reads what a
linked literature episode presents and admits for its first decision and opens its controller.
"""
import pytest
from jsonschema import Draft202012Validator, ValidationError

from episode_runtime import BindingRegistry, FormError, RunJournal, grain_name_for, link
from method_loop import Episode
from yield_control import BoundedQualityYieldController

from gene_annotation_episode.model_provider import ModelProvider
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.tools.evolutionary_history_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.runtime_bindings import (
    EPISODES, LITERATURE_ROLES, _literature_class)
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.runtime_source import (
    EVIDENCE_REFS, form_schema, head_credit_projector)
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.published_evidence_assessment.\
    literature_binding import LiteratureBinding
from gene_annotation_episode.episodic_workflow.root.a104.evolutionary_history_evidence.published_evidence_assessment.\
    literature_source import LiteratureSource

MODEL_CONFIG = {'connection': {'command': ['codex', 'app-server']},
                'REASONING': {'model': 'configured-model', 'reasoning_effort': 'high'}}
PATHS = {role: path for path, role, _ in EPISODES}
LITERATURE, EXAMINATION = PATHS['literature'], PATHS['literature_page']


@pytest.fixture(autouse=True)
def _own_local_resources(tmp_path, monkeypatch):
    """Each test binds its registries to its own local-resource directory, not the machine-wide one."""
    monkeypatch.setenv('GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY', str(tmp_path / 'local-resources'))


def _registry(tmp_path, store):
    """The seven literature bindings, each built by its own class with its own registry over the run's store."""
    projector = head_credit_projector()
    continuation = {'kind': projector.yield_method, 'cutoff': 0.001, 'parameters': {'uncertainty_alpha': 0.05},
                    'credit_definition': projector.as_record()}
    children = {path: {} for path, _, _ in EPISODES}
    for path, role, parent in EPISODES[1:]:
        children[parent][role] = path
    roles_by_grain = {grain_name_for(path): role for path, role, _ in EPISODES}
    return BindingRegistry(tuple(
        _literature_class(path, role, parent)(child_slots=children[path], roles_by_grain=roles_by_grain, store=store,
                                              tool_registry=ToolRegistry(store), continuation=continuation)
        for path, role, parent in EPISODES if role in LITERATURE_ROLES))


def _link(tmp_path, store, registry, path, entry):
    provider = ModelProvider(MODEL_CONFIG, tmp_path / 'model_calls', tmp_path)
    return link(registry, path, entry, run_id='a104_literature_link', journal=RunJournal(tmp_path / 'journal.sqlite'),
                collaborators={'store': store, 'model_provider': provider})


def _target(store):
    target, = store.create_problem(raw_sequence='ACDEFGHIKL', molecule='protein')['subject_refs']
    return target


def test_every_literature_home_is_its_own_literature_binding():
    assert {role for _, role, _ in EPISODES if role.startswith('literature')} == set(LITERATURE_ROLES)


def test_literature_episode_runs_its_own_source_and_continuation(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(tmp_path, store)
        for role in LITERATURE_ROLES:
            assert isinstance(registry.binding(PATHS[role]), LiteratureBinding)
        binding = registry.binding(LITERATURE)
        target = _target(store)
        run = _link(tmp_path, store, registry, LITERATURE, {
            'scope': {'subject_refs': [target]}, 'tools': ['public.literature.search', 'source.read'],
            'role_assignment': {'question': 'Is the target family reported to have arisen by horizontal transfer?'}})
        assert isinstance(run.episode, Episode)
        source = run.episode.source
        assert type(source) is LiteratureSource
        schema = source.action_schema()
        options = schema['properties']['selection']['anyOf']
        kinds = [option['properties']['kind']['const'] for option in options]
        assert kinds.count('reason') == 1 and kinds.count('tool') == 2
        assert [option['properties']['role']['const'] for option in options
                if option['properties']['kind']['const'] == 'episode_child'] == list(binding.child_slots)
        assert source.credit_view()['credit'] == head_credit_projector()(
            store, source._scope, known_record_refs=[target])['credit']
        assert binding.instruction in source.instructions()
        controller = run.episode.grain.controller(((binding.grain_name, run.episode.key),))
        assert isinstance(controller, BoundedQualityYieldController)
        assert isinstance(controller.state().stop, bool)
        with pytest.raises(ValueError, match='a104_decision_response_must_be_exactly_selection'):
            source.admit({'choice': {}}, schema)
        slot, = binding.child_slots
        child = {'kind': 'episode_child', 'role': slot, 'objective': 'Plan the search', 'scope': source._scope,
                 'role_assignment': {'question': 'transfer'}, 'tools': ['public.literature.search']}
        assert source.admit({'selection': child}, schema) == child
        commission = source._commission(child)
        assert EVIDENCE_REFS in commission.report_form.fields
        # A child commission whose tools its own form does not offer is refused before acquisition.
        with pytest.raises(ValidationError):
            source.admit({'selection': {**child, 'tools': ['sequence.align']}}, schema)
        assert not (tmp_path / 'model_calls' / 'call-00001').exists()


def test_head_fills_the_literature_form_it_is_offered(tmp_path):
    """The head offers a literature child its declared form minus the held scope (runtime_source.form_schema)."""
    with Store(tmp_path / 'state') as store:
        binding = _registry(tmp_path, store).binding(LITERATURE)
        schema = form_schema(binding.assignment_form, held=('scope',))
        assert set(schema['properties']) == {'role_assignment', 'tools'}
        filled = {'role_assignment': {'question': 'transfer'}, 'tools': ['source.read']}
        Draft202012Validator(schema).validate(filled)
        with pytest.raises(ValidationError):
            Draft202012Validator(schema).validate({**filled, 'tools': ['sequence.align']})
        target = _target(store)
        assert binding.assignment_form.admit({'scope': {'subject_refs': [target]}, **filled}, 'head') == {
            'scope': {'subject_refs': [target]}, **filled}


def test_source_examination_offers_no_public_acquisition(tmp_path):
    with Store(tmp_path / 'state') as store:
        registry = _registry(tmp_path, store)
        assert not any(name.startswith('public.') for name in registry.binding(EXAMINATION).selectable_tools)
        with pytest.raises(FormError, match='not_an_offered_option'):
            _link(tmp_path, store, registry, EXAMINATION, {
                'scope': {'subject_refs': [_target(store)]}, 'tools': ['public.literature.search'],
                'role_assignment': {'question': 'transfer'}})
