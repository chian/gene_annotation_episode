"""Offline interface sizes. Synthetic metadata only; no model/scientific action."""
from functools import partial
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_kinetic_storage import COMPONENTS, kinetic_cells_schema
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow, _action_generation_schema, DECISION_EXCHANGE_PROTOCOL
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

OUT = Path(__file__).resolve().parent

def encode(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False)

def metrics(value):
    text = value if isinstance(value, str) else encode(value)
    raw = text.encode()
    return {'characters': len(text), 'utf8_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)

class ForbiddenProvider:
    async def complete(self, *_args, **_kwargs):
        raise AssertionError('No model calls authorized in offline measurement')

def controller(*_args):
    raise AssertionError('No controller/episode execution authorized in measurement')

def main():
    destination = OUT / 'synthetic_measurement_001'
    destination.mkdir(exist_ok=False)
    all_populations = _population_catalog()
    result = {'meaning': 'Synthetic metadata / interface measurement only; no source science or model launch',
        'serialization': 'json.dumps ensure_ascii=True default separators, matching provider RPC _send',
        'population_operation_count': len(all_populations),
        'populations': [{'name': row['name'], 'input_schema': metrics(row['input_schema']),
            'schema_nodes': sum(1 for _ in nodes(row['input_schema'])),
            'schema_properties': sum(len(n.get('properties', {})) for n in nodes(row['input_schema']))}
            for row in all_populations]}
    with Store(destination / 'synthetic_state') as store:
        # Non-scientific placeholder material establishes the host scope only.
        store.create_problem(raw_sequence='ATG', molecule='dna')
        tools = ToolRegistry(store)
        progress = ScientificFindingProgress(FindingProgressPolicy(1))
        workflow = Workflow(store, tools, ForbiddenProvider(), destination, 'synthetic-interface-only',
            controller, progress, project_child_credit=progress, initial_known_record_refs=[],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            annotation_child_roles=('literature',), decision_protocol=DECISION_EXCHANGE_PROTOCOL)
        scope = plain(store.validate_scope())
        assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
            'source_refs': [], 'requested_kinetic_components': list(COMPONENTS)}
        episode = workflow.build('literature', 'synthetic-root', 'SYNTHETIC METADATA ONLY: inspect interface shapes.',
            scope, episode_assignment=assignment)
        source = episode.source
        catalog = workflow.catalog(scope, source=source)
        host_schema = workflow.action_schema(source)
        exchange_schema = source.exchange_schema(host_schema)
        generated = _action_generation_schema(exchange_schema)
        binding = workflow.specialist(source)
        form = obj({'numbers': kinetic_cells_schema()})
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
                'aspect': 'source_experimental_evidence'},
            'goal': {'objective': 'SYNTHETIC METADATA ONLY: inspect interface shapes.'},
            'scope': scope, 'literature_assignment': assignment,
            'literature_source_custody': [], 'tools': catalog, 'requested_form': form,
            'available_report_facts': binding.fact_sources('literature')}
        instructions = source.instructions(state)
        text = render_literature_experimental_prompt(state, instructions)
        # _presentation is pure when constructed without its transport initializer.
        connection = _SessionConnection.__new__(_SessionConnection)
        connection.scientific_prompt_states = {}
        presented, developer = connection._presentation('synthetic-only', 'REASONING', instructions, state)
        assert presented == text
        request = {'threadId': 'SYNTHETIC-NOT-STARTED', 'model': 'SYNTHETIC-NOT-SELECTED',
            'effort': 'SYNTHETIC-NOT-SELECTED', 'input': [{'type': 'text', 'text': presented}],
            'outputSchema': generated}
        result['literature_child'] = {'catalog_count': len(catalog), 'catalog_names': [r['name'] for r in catalog],
            'catalog': metrics(catalog), 'host_action_schema': metrics(host_schema),
            'exchange_schema': metrics(exchange_schema), 'provider_output_schema': metrics(generated),
            'provider_schema_properties': sum(len(n.get('properties', {})) for n in nodes(generated)),
            'provider_schema_max_depth_unmeasured': True,
            'synthetic_context_json': metrics(state), 'recurring_model_text': metrics(presented),
            'recurring_task': metrics(presented.split('\n\nSTEERING', 1)[0]),
            'recurring_steering': metrics(presented.split('\n\nSTEERING', 1)[1]),
            'developer_instructions': metrics(developer), 'turn_start_params': metrics(request),
            'requested_form': metrics(form), 'available_fact_projection_schemas': metrics(binding.fact_sources('literature'))}
        result['population_transport_branches'] = []
        for branch in generated['properties']['response']['anyOf'][1]['properties']['selection']['anyOf']:
            properties = branch.get('properties', {})
            name = properties.get('tool', {}).get('enum', [None])[0]
            if name and name.startswith('literature.'):
                result['population_transport_branches'].append({'name': name, 'schema': metrics(branch),
                    'arguments_type': properties['arguments'].get('type'),
                    'description_characters': len(properties['arguments'].get('description', ''))})
        # Requested return components do not change catalog/action schemas.
        second = {**assignment, 'requested_kinetic_components': ['parameter_ratio'],
            'requested_binding_interaction_components': []}
        context = BindingContext(workflow.run_id, 'synthetic-contract', 'literature',
            (('literature', 'synthetic-contract'),), scope, second, {}, ())
        assert binding.catalog(context) == binding.catalog(workflow.binding_context(source))
        result['component_selection_leaves_catalog_equal'] = True
        result['runtime_counts'] = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in ('runtime_model_calls', 'runtime_actions', 'runtime_observations')}
        result['model_calls'] = 0
        result['scientific_sources'] = 0
        result['runtime_episodes_prepared_only'] = store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0]
        for name, value in [('catalog.json', catalog), ('provider_output_schema.json', generated)]:
            (destination / name).write_text(encode(value) + '\n')
        (destination / 'model_text.txt').write_text(text)
    (OUT / 'SCHEMA_MEASUREMENTS_001.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
