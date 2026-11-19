"""The A110 subtree on episode_runtime: home factory, literature bindings and the unit source's admission.

Real objects only: the shared Store with test-written records, A110 ToolRegistries built by the A110 home
factory, the runner's BindingRegistry/RunJournal/EpisodeRecorder/ProgressClock. No model is called and no
episode is run: a run needs a real model provider. The source is built with no provider (it is only read
when a decision is requested) and its admission is checked on test-written model responses.
"""
import json

import pytest
from jsonschema import ValidationError

from episode_runtime import BindingRegistry, BoundEpisode, EpisodeRecorder, Field, FormError, ProgressClock, RecordForm, RunJournal
from method_loop import EpisodeRef

from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.tools.biochemical_feasibility_evidence.tools import ToolRegistry
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.home import home_factory
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.published_evidence_assessment.literature_binding import (
    ACCESS_TOOLS, ACQUISITION_TOOLS, LiteratureBinding)
from gene_annotation_episode.episodic_workflow.root.a110.biochemical_feasibility_evidence.unit_source import UnitSource

HEAD = 'biochemical_feasibility_evidence'
LITERATURE = HEAD + '/published_evidence_assessment'
EXAMINATION = (LITERATURE + '/evidence_search_strategy_improvement/source_relevance_assessment/'
               'source_evidence_examination')
REMOTE = '/lus/flare/projects/BioReason-Aurora-Test/chian/runs'
HPC_RESOURCE = {'kind': 'pbs_ssh', 'workspace': REMOTE, 'ssh_argv': ['ssh', 'aurora'],
                'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
                'scheduler': {'kind': 'pbs'}}
MONITOR = {'information_unit': 1.0, 'yield_settings': {'kind': 'information_accumulation', 'cutoff': 0.25,
                                                       'uncertainty_alpha': 0.1}}


def local_job_operands(root):
    """The local job bindings' own local resource, workspaces and frozen launch instruction library."""
    from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LIBRARY_ROOT, LaunchInstructions
    for name in ('resource', 'coordinator'):
        (root / name).mkdir(parents=True, exist_ok=True)
    if not (root / 'launch').exists():
        LaunchInstructions.freeze(root / 'launch', source=LIBRARY_ROOT)
    return {'resource': {'kind': 'local', 'workspace': str(root / 'resource'),
                         'policy': {'memory_bytes': 1 << 30, 'scratch_bytes': 1 << 30}},
            'coordinator_workspace': root / 'coordinator', 'state_directory': root / 'practical',
            'launch_instruction_directory': root / 'launch'}


def hpc_job_settings(root):
    """The HPC job bindings' own pbs_ssh resource, coordinator directory and frozen launch instruction library."""
    from gene_annotation_episode.episodic_workflow.episode_support.instructions.launch_instructions import LIBRARY_ROOT, LaunchInstructions
    return {'resource': HPC_RESOURCE, 'directory': root / 'hpc',
            'launch_instructions': LaunchInstructions.freeze(root / 'hpc_launch', source=LIBRARY_ROOT)}


def compose(store):
    return BindingRegistry.compose([home_factory], {
        'store': store, 'a110': {'tool_registry': {}},
        'a110_local_job_execution': local_job_operands(store.path.parent / 'local_jobs'),
        'a110_hpc_job_execution': hpc_job_settings(store.path.parent / 'hpc_jobs'),
        'a110_progress_monitor': MONITOR})


def target_scope(store):
    target, = store.create_problem(raw_sequence='MARGKKIGYS', molecule='protein')['subject_refs']
    return store.validate_scope({'subject_refs': [target]})


def bound_for(tmp_path, binding, commission, *, report_form=None):
    journal = RunJournal(tmp_path / 'journal.sqlite3')
    path = ((binding.grain_name, 'entry'),)
    recorder = EpisodeRecorder(journal, 'run-a110', path)
    episode_id = EpisodeRef('run-a110', path).episode_id
    return BoundEpisode(run_id='run-a110', binding_path=binding.binding_path, path=path, key='entry',
                        episode_id=episode_id, request=commission.request, assignment=dict(commission.assignment),
                        recorder=recorder, progress=ProgressClock(recorder, run_id='run-a110', episode_id=episode_id),
                        report_form=report_form or binding.return_form)


def literature_commission(binding, scope, tools):
    return binding.entry_request({'objective': 'Find published reaction stoichiometry for the subject',
                                  'assignment': {'scope': scope, 'assignment': {'question': 'stoichiometry'},
                                                 'tools': tools}}, {}, parent_goal=None)


def test_home_factory_builds_the_whole_subtree_with_own_registries_over_the_shared_store(tmp_path):
    with Store(tmp_path / 'workspace') as store:
        registry = compose(store)
        bindings = registry.subtree(HEAD)
        assert len(bindings) == 26
        # The head and the seven literature bindings (the result acquisitions, monitors and HPC job routes also
        # hold their own registries now that they are ported; they are not these eight).
        model_driven = [binding for binding in bindings.values()
                        if binding.binding_path == HEAD or isinstance(binding, LiteratureBinding)]
        assert len(model_driven) == 8
        registries = [binding.tool_registry for binding in model_driven]
        # Each model-driven binding has its own A110 ToolRegistry, all over the run's one shared Store.
        assert len({id(tools) for tools in registries}) == 8
        assert all(type(tools) is ToolRegistry and tools.store is store for tools in registries)
        for binding in model_driven:
            assert binding.required_collaborators == ('model_provider', 'store', 'continuation')
        with pytest.raises(KeyError, match='a110_home_operands_must_be_exactly_tool_registry'):
            BindingRegistry.compose([home_factory], {'store': store, 'a110': {'tool_registry': {}, 'hpc': {}}})
        with pytest.raises(TypeError, match='a110_home_store_must_be_the_shared_store'):
            BindingRegistry.compose([home_factory], {'store': object(), 'a110': {'tool_registry': {}}})


def test_literature_bindings_offer_their_own_operations(tmp_path):
    with Store(tmp_path / 'workspace') as store:
        registry = compose(store)
        literature = [binding for binding in registry.subtree(HEAD).values() if isinstance(binding, LiteratureBinding)]
        assert len(literature) == 7
        for binding in literature:
            offered = set(binding.assignment_form.fields['tools'].options)
            expected = set(ACCESS_TOOLS) | (set(ACQUISITION_TOOLS) if binding.acquisition else set())
            assert offered == expected
            assert offered <= set(binding.tool_registry.catalog(None))
            assert binding.instruction in binding.instructions()
        assert registry.binding(LITERATURE).acquisition is True
        assert registry.binding(EXAMINATION).acquisition is False
        # The commissioner chooses a subset of the offered operations (C6); anything else is refused.
        scope = target_scope(store)
        examination = registry.binding(EXAMINATION)
        with pytest.raises(FormError, match='not_an_offered_option'):
            literature_commission(examination, scope, ['public.literature.search'])
        with pytest.raises(FormError, match='repeats_an_option'):
            literature_commission(examination, scope, ['source.read', 'source.read'])


def test_unit_source_offers_only_the_commissioned_operations_and_admits_selections(tmp_path):
    with Store(tmp_path / 'workspace') as store:
        binding = compose(store).binding(EXAMINATION)
        scope = target_scope(store)
        commission = literature_commission(binding, scope, ['source.locate', 'source.read'])
        bound = bound_for(tmp_path, binding, commission)
        source = UnitSource(binding, bound, {'store': store, 'model_provider': None}, {})
        catalog = source.catalog()
        assert sorted(catalog) == ['source.locate', 'source.read']
        assert source.commission == {'assignment': {'question': 'stoichiometry'}}
        schema = source.response_schema(catalog)
        tool_branch = schema['properties']['selection']['anyOf'][0]
        assert tool_branch['properties']['tool']['enum'] == ['source.locate', 'source.read']
        selected = {'finding': 'Nothing read yet', 'selection': {
            'kind': 'tool', 'tool': 'source.read',
            'arguments_json': json.dumps({'source_ref': 'source_' + '0' * 24, 'offset': 0, 'limit': 64})}}
        assert callable(source.admit(0, selected, schema, catalog, []))
        # An operation the commission did not select, or arguments its schema refuses, create no unit.
        with pytest.raises(ValidationError):
            source.admit(0, {**selected, 'selection': {**selected['selection'], 'tool': 'state.query'}},
                         schema, catalog, [])
        with pytest.raises(ValidationError):
            source.admit(0, {**selected, 'selection': {**selected['selection'],
                                                       'arguments_json': json.dumps({'offset': 0})}},
                         schema, catalog, [])
        with pytest.raises(ContractError, match='empty_reasoning_commit'):
            source.admit(0, {'finding': 'x', 'selection': {'kind': 'reason', 'commit_json': json.dumps(
                {name: [] for name in store.reasoning_schema()['properties']})}}, schema, catalog, [])


def test_unit_source_refuses_another_store_and_commissioned_report_fields(tmp_path):
    with Store(tmp_path / 'workspace') as store, Store(tmp_path / 'other') as other:
        binding = compose(store).binding(LITERATURE)
        commission = literature_commission(binding, target_scope(store), ['source.read'])
        with pytest.raises(ContractError, match='a110_tool_registry_must_use_the_run_store'):
            UnitSource(binding, bound_for(tmp_path, binding, commission), {'store': other, 'model_provider': None}, {})
        extended = RecordForm({**binding.return_form.fields, 'extra': Field('text', 'A field no A110 decision fills')})
        with pytest.raises(ContractError, match='a110_cannot_fill_commissioned_report_fields:.*:extra'):
            UnitSource(binding, bound_for(tmp_path, binding, commission, report_form=extended),
                       {'store': store, 'model_provider': None}, {})
