"""Actual opt-in discovery/selection with constructed decisions, no inference."""
import asyncio
from functools import partial
import json

from gene_annotation_episode.communication import plain
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.domain import obj
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_reaction_inputs import reaction_population_schema
from gene_annotation_episode.literature_reaction_native_storage import native_observations_schema, NAMESPACE
from gene_annotation_episode.literature_reaction_prompt import REACTION_TASK
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.tools import ToolRegistry
from test_contract_information_runtime_059 import PresentedProvider, information
from test_runtime_decision_exchanges import select
from test_runtime import FixtureController
from test_literature_reaction_native_integration_129 import setup_case


def test_selected_operation_and_new_native_contract_are_discovered_without_extra_observations(tmp_path, record_property):
    store, seed, args = setup_case(tmp_path / 'state')
    provider = PresentedProvider([])
    value = Workflow(store, ToolRegistry(store), provider, tmp_path / 'run', seed.run_id,
        lambda path, initial: FixtureController(str(path), initial, 2 if len(path) == 1 else 1),
        ScientificFindingProgress(FindingProgressPolicy(1)),
        initial_known_record_refs=list(seed.received_record_refs),
        episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
            reference_parent_sources=[args['source_ref']], contract_information_profile=CONTRACT_INFORMATION_PROFILE),),
        decision_protocol='decision_exchange_v1')
    root = value.build('annotation', 'root', 'Evaluate the constructed source reaction evidence', plain(seed.scope))
    compact = obj({'score': {'$ref': 'episode-fact:literature_reaction_semantic_cells'},
        'native': {'$ref': 'episode-fact:' + NAMESPACE}})
    commission = select({'selection': {'kind': 'episode_child', 'role': 'literature',
        'assignment': plain(seed.assignment), 'goal': 'Extract the source ratio and preserve its repetition basis',
        'scope': plain(seed.scope), 'purpose': 'Return only the requested component and native observation',
        'schema_json': json.dumps(compact), 'initial_report_json': '{}'}, 'report_update': {}})
    population = select({'selection': {'kind': 'tool', 'tool': 'literature.reaction.populate',
        'arguments': json.dumps(args)}, 'report_update': {}})
    paper = store.get(args['source_ref'])
    commit = {name: [] for name in store.reasoning_schema()['required']}
    commit['source_subjects'] = [{'alias': 'synthetic_profile_subject', 'reference_type': 'assay',
        'source_ref': paper['id'], 'label': 'SyntheticProtein', 'anchor': {
            'source_ref': paper['id'], 'artifact_ref': paper['artifact_ref'], 'start': 0,
            'end': len('SyntheticProtein'), 'quote': 'SyntheticProtein'}}]
    provider.script = iter([
        information('episode.return_contract', role='literature', source=NAMESPACE),
        information('episode.return_contract', role='literature', source='literature_reaction_semantic_cells'),
        commission,
        information('episode.operation_contract', operation='literature.reaction.populate'),
        population,
        select({'selection': {'kind': 'reason', 'commit': commit}, 'report_update': {}})])
    try:
        result = asyncio.run(root.run_async(value.context))
        assert result.units_consumed == 2
        assert store.db.execute('select count(*) from runtime_actions').fetchone()[0] == 3
        assert store.db.execute('select count(*) from runtime_observations').fetchone()[0] == 3
        assert store.db.execute('select count(*) from literature_reaction_operations').fetchone()[0] == 1
        assert store.db.execute('select count(*) from literature_reaction_native_observations_received').fetchone()[0] == 1
        child = store.db.execute('select * from runtime_episodes where json_array_length(path)=2').fetchone()
        requested = json.loads(child['request'])
        assert requested['report_contract']['measurements']['schema']['properties']['native'] == native_observations_schema()
        assert len(requested['message']['report_contract_declaration']['fact_references']) == 2
        returned = json.loads(store.db.execute('select form from runtime_forms').fetchone()[0])
        assert returned['native'][0]['reported_count'] == 4
        assert returned['native'][0]['independent_n'] is None
        assert returned['native'][0]['count_basis'] == 'technical_repeat'
        assert returned['score'][0]['value'] is None
        parent_tasks, child_tasks, operation_schemas, native_schemas = [], [], [], []
        for context, rendered in zip(provider.contexts, provider.rendered):
            task, steering = rendered.split('\n\nSTEERING\n', 1)
            if REFERENCE_PARENT_TASK in task:
                assert REFERENCE_PARENT_TASK in task
                parent_tasks.append(len(task))
            else:
                assert REACTION_TASK in task
                child_tasks.append(len(task))
            for outcome in context.get('pending_contract_information', ()):
                item = outcome['result']
                if item.get('operation') == 'literature.reaction.populate':
                    assert item['input_schema'] == reaction_population_schema(include_assessment=True)
                    operation_schemas.append(item['input_schema'])
                    assert 'Requested operation/return information: literature.reaction.populate' in task
                if item.get('source') == NAMESPACE:
                    assert item['report_schema'] == native_observations_schema()
                    native_schemas.append(item['report_schema'])
                    assert 'observation_position' in task and 'reported_count' in task
            assert 'Complete requested contract' not in steering
        assert operation_schemas and native_schemas and parent_tasks and child_tasks
        measurements = {'profile': CONTRACT_INFORMATION_PROFILE, 'parent_task_chars': parent_tasks,
            'child_task_chars': child_tasks, 'provider_calls': len(provider.contexts),
            'metadata_lookups': 3, 'completed_actions': 3, 'observations': 3,
            'full_parent_task_retained': True, 'full_reaction_task_retained': True,
            'model_backed': False}
        record_property('native129_contract_information', json.dumps(measurements, sort_keys=True))
        assert not store.list('observation') and not store.list('assessment')
    finally:
        store.close()
