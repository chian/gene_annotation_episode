"""Additive synthetic parent/render contribution and source-code baseline sizes."""
from functools import partial
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.communication import plain
from gene_annotation_episode.composition_information import child_options
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.providers import _SessionConnection
from gene_annotation_episode.runtime import Workflow, _action_generation_schema, DECISION_EXCHANGE_PROTOCOL
from gene_annotation_episode.scientific_process_prompt import _schema
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from measure_synthetic_001 import metrics, ForbiddenProvider, controller, encode, nodes

OUT = Path(__file__).resolve().parent

def baseline():
    files = []
    for package in ('gene_annotation_episode', 'method_loop'):
        files.extend(p for p in (ROOT / package).rglob('*') if p.is_file()
            and '__pycache__' not in p.parts and p.suffix != '.pyc')
    return {str(p.relative_to(ROOT)): {'bytes': p.stat().st_size,
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(files)}

def main():
    start = baseline()
    first = json.loads((OUT / 'SCHEMA_MEASUREMENTS_001.json').read_bytes())
    populations = _population_catalog()
    assert [(r['name'], metrics(r['input_schema'])) for r in populations] == [
        (r['name'], r['input_schema']) for r in first['populations']]
    destination = OUT / 'synthetic_measurement_002'
    destination.mkdir(exist_ok=False)
    result = {'meaning': 'Synthetic parent metadata only; current code unchanged during measurement',
        'operation_render_contributions': [{'name': r['name'], 'rendered_input_schema': metrics(_schema(r['input_schema'], 'arguments'))}
            for r in populations]}
    with Store(destination / 'synthetic_state') as store:
        store.create_problem(raw_sequence='ATG', molecule='dna')
        progress = ScientificFindingProgress(FindingProgressPolicy(1))
        workflow = Workflow(store, ToolRegistry(store), ForbiddenProvider(), destination,
            'synthetic-parent-only', controller, progress, project_child_credit=progress,
            initial_known_record_refs=[], episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True),),
            annotation_child_roles=('literature',), decision_protocol=DECISION_EXCHANGE_PROTOCOL)
        scope = plain(store.validate_scope())
        parent = workflow.build('annotation', 'root', 'SYNTHETIC METADATA ONLY: inspect interface shapes.', scope)
        source = parent.source
        binding = workflow.episode_bindings.for_role('literature')
        schema = _action_generation_schema(source.exchange_schema(workflow.action_schema(source)))
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1',
                'aspect': 'reference_evidence_parent'},
            'reference_evidence_parent': {'version': 'reference_evidence_parent_v1',
                'source_refs': ['source_SYNTHETIC_METADATA_ONLY'], 'source_custody': [],
                'child_population_operations': [{k: r[k] for k in ('name', 'description')} for r in populations]},
            'goal': {'objective': 'SYNTHETIC METADATA ONLY: inspect interface shapes.'},
            'scope': scope, 'tools': workflow.catalog(scope, source=source),
            'available_report_facts': workflow.report_sources('annotation'),
            'child_options': child_options(workflow, source)['text']}
        instructions = source.instructions(state)
        presented = render_literature_experimental_prompt(state, instructions)
        connection = _SessionConnection.__new__(_SessionConnection)
        connection.scientific_prompt_states = {}
        assert connection._presentation('synthetic', 'REASONING', instructions, state)[0] == presented
        result['parent'] = {'available_own_tool_count': len(state['tools']),
            'allowed_child_roles': list(workflow.available_child_roles(source)),
            'provider_output_schema': metrics(schema), 'provider_schema_properties': sum(len(n.get('properties', {})) for n in nodes(schema)),
            'synthetic_state_json': metrics(state), 'recurring_model_text': metrics(presented),
            'available_report_facts': metrics(state['available_report_facts'])}
        result['runtime_counts'] = {name: store.db.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for name in ('runtime_model_calls', 'runtime_actions', 'runtime_observations')}
        result['model_calls'] = 0
        (destination / 'parent_model_text.txt').write_text(presented)
        (destination / 'parent_provider_output_schema.json').write_text(encode(schema) + '\n')
    end = baseline()
    assert start == end
    (OUT / 'CURRENT_CODE_BASELINE_001.json').write_text(json.dumps(start, indent=2) + '\n')
    result['current_code_baseline_file_count'] = len(start)
    result['baseline_unchanged_during_measurement'] = True
    result['population_schema_fingerprints_equal_measurement001'] = True
    (OUT / 'SCHEMA_MEASUREMENTS_002.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
