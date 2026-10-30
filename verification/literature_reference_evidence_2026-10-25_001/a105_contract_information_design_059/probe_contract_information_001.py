"""Proposal-only lossless contract presentation on actual current schemas.

This code is deliberately outside production. No provider, Store, source,
controller, episode or scientific operation is created or executed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_experimental_prompt import _task as child_task
from gene_annotation_episode.literature_reference_parent_prompt import _task as parent_task
from gene_annotation_episode.runtime import _action_generation_schema, _embedded_tool_schema
from gene_annotation_episode.communication import validate_closed_schema
from gene_annotation_episode.domain import obj
from gene_annotation_episode.scientific_process_prompt import _schema


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def fingerprint(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def save(name, value):
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    with (OUT / name).open('x') as stream:
        stream.write(text)


class NamedDefinitions:
    """Lossless JSON DAG for research; names are local grammar labels, not IDs."""
    def __init__(self, original):
        self.definitions = []
        self.index = {}
        self.root = self.intern(original)

    def intern(self, value):
        if not isinstance(value, (dict, list)):
            return {'literal': deepcopy(value)}
        key = canonical(value)
        if key in self.index:
            return {'definition': self.index[key]}
        name = 'Definition' + str(len(self.definitions) + 1)
        self.index[key] = name
        row = {'name': name, 'kind': 'object' if isinstance(value, dict) else 'array'}
        self.definitions.append(row)
        row['fields'] = [(key, self.intern(child)) for key, child in value.items()] if isinstance(value, dict) else [
            (index, self.intern(child)) for index, child in enumerate(value)]
        return {'definition': name}

    def reconstruct(self):
        records = {row['name']: row for row in self.definitions}
        def expand(value):
            if 'literal' in value:
                return deepcopy(value['literal'])
            record = records[value['definition']]
            values = [(key, expand(child)) for key, child in record['fields']]
            return dict(values) if record['kind'] == 'object' else [child for _, child in values]
        return expand(self.root)

    def text(self, title):
        def literal(value):
            if value is None:
                return 'null'
            if value is True:
                return 'true'
            if value is False:
                return 'false'
            return str(value).replace('|', '\\|').replace('\n', '<br>')
        lines = [title, '', 'Root: ' + self.root['definition'], '',
            'Each local Definition names one exact structure. Repeated references have the same complete meaning; '
            'array positions preserve order. All fields and constraints below are present; no definitions are omitted.']
        for row in self.definitions:
            lines.extend(['', row['name'] + ' — ' + row['kind'], '',
                '| Field or position | Declared value or structure |', '| --- | --- |'])
            if not row['fields']:
                lines.append('| (none) | empty ' + row['kind'] + ' |')
            for key, value in row['fields']:
                shown = value['definition'] if 'definition' in value else literal(value['literal'])
                lines.append('| ' + str(key).replace('|', '\\|') + ' | ' + shown + ' |')
        return '\n'.join(lines) + '\n'


def main():
    dependency_names = ['runtime.py', 'providers.py', 'composition_information.py', 'decision_exchanges.py',
        'decision_context.py', 'literature_episodes.py', 'literature_experimental_prompt.py',
        'literature_reference_parent_prompt.py', 'scientific_process_prompt.py', 'communication.py',
        'independent_execution.py', 'application_execution_binding.py', 'episode_bindings.py']
    before = {name: fingerprint(ROOT / 'gene_annotation_episode' / name) for name in dependency_names}
    populations = _population_catalog()
    facts = LiteratureEpisodes(None, rate_population=True)._rate_fact_sources()
    measurements = []
    for namespace, entries in [('operation', {row['name']: row['input_schema'] for row in populations}),
                               ('fact', {name: row['report_schema'] for name, row in facts.items()})]:
        for name, original in entries.items():
            graph = NamedDefinitions(original)
            assert graph.reconstruct() == original
            text = graph.text(name + ' complete declared contract')
            measurements.append({'kind': namespace, 'name': name, 'schema_json_bytes': len(canonical(original).encode()),
                'old_expanded_table_bytes': len(_schema(original, 'arguments' if namespace == 'operation' else 'return').encode()),
                'named_definition_text_bytes': len(text.encode()), 'unique_definitions': len(graph.definitions),
                'reconstructed_exactly': True})
            if name in ('literature.binding.interaction.populate', 'literature.kinetic.populate', 'literature_binding_interaction_cells'):
                safe = name.replace('.', '_')
                save(safe + '_NAMED_CONTRACT_001.txt', text)
                save(safe + '_GRAPH_001.json', {'root': graph.root, 'definitions': graph.definitions})
    catalog = [{key: row[key] for key in ('name', 'description')} for row in populations]
    state = {'goal': {'objective': 'SYNTHETIC INTERFACE QUESTION: evaluate supplied experimental evidence.'},
        'scope': {'subject_refs': ['gene001']}, 'tools': catalog,
        'literature_assignment': {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': []},
        'child_options': 'All currently permitted narrower literature investigations remain available.'}
    guidance = ('Full argument contracts are available through request_context, composition_information, '
        'episode.operation_contract, selecting the actual operation name. All listed operations remain available. '
        'A lookup supplies instructions within this same decision and creates no completed action or observation. '
        'You may invoke an operation directly; its original full host contract still validates the arguments.')
    child = child_task(state, guidance)
    save('SYNTHETIC_CHILD_INITIAL_TASK_001.txt', child)
    metadata = {name: {key: row[key] for key in ('type', 'meaning') if key in row} for name, row in facts.items()}
    descriptor = {'source_refs': ['source_SYNTHETIC_CUSTODY'], 'source_custody': [],
        'child_population_operations': catalog}
    parent_state = {**state, 'tools': [], 'available_report_facts': metadata}
    parent = parent_task(parent_state, guidance + '\nFor a permitted child\'s return contract, '
        'request episode.return_contract with the child role and fact source. Choose your own return field names '
        'and requested source meanings. A fact-schema reference expands to the exact declared closed type before commissioning.', descriptor)
    save('SYNTHETIC_PARENT_INITIAL_TASK_001.txt', parent)
    host_schema = obj({'selection': {'anyOf': [obj({'kind': {'const': 'tool'}, 'tool': {'const': row['name']},
        'arguments': _embedded_tool_schema(row['input_schema'])}) for row in populations]}, 'report_update': obj({})})
    before_schema = canonical(host_schema)
    old_generation = _action_generation_schema(host_schema)
    prospective_generation = deepcopy(old_generation)
    for branch in prospective_generation['properties']['selection']['anyOf']:
        branch['properties']['arguments'] = {'type': 'string', 'description':
            'JSON encoding of the exact argument object for this operation. Omitted fields and explicit nulls retain '
            'their meanings. Request the authoritative operation contract as information when needed. The original '
            'complete host contract validates the decoded object before execution.'}
    assert canonical(host_schema) == before_schema
    names = lambda schema: [branch['properties']['tool']['enum'][0] for branch in schema['properties']['selection']['anyOf']]
    assert names(old_generation) == names(prospective_generation) == [row['name'] for row in populations]
    save('PROSPECTIVE_PROVIDER_SCHEMA_001.json', prospective_generation)
    # Proposed pre-validation expansion only, outside production. A parent
    # explicitly selects the fact source and its own field name; no values exist.
    chosen = 'literature_kinetic_cells'
    compact_form = obj({'measured_comparison': {'$ref': 'episode-fact:' + chosen}})
    expanded_form = obj({'measured_comparison': deepcopy(facts[chosen]['report_schema'])})
    expanded_form['properties']['measured_comparison']['x-source'] = chosen
    assert validate_closed_schema(expanded_form) == expanded_form
    save('SYNTHETIC_COMPACT_FORM_001.json', compact_form)
    save('SYNTHETIC_EXPANDED_FORM_001.json', expanded_form)
    after = {name: fingerprint(ROOT / 'gene_annotation_episode' / name) for name in dependency_names}
    assert before == after
    save('INPUT_BASELINE_001.json', before)
    result = {'scope': 'Proposal-only actual-schema transforms; not installed, no model/provider/Store/episode/controller/source',
        'operation_contracts': len(populations), 'fact_contracts': len(facts), 'all_schema_graphs_roundtrip_exact': True,
        'actual_host_schema_unchanged': True, 'all_operation_names_retained': True,
        'population_only_provider_schema_old_bytes': len(canonical(old_generation).encode()),
        'population_only_provider_schema_prospective_bytes': len(canonical(prospective_generation).encode()),
        'prospective_child_initial_task_bytes': len(child.encode()), 'prospective_parent_initial_task_bytes': len(parent.encode()),
        'compact_parent_form_bytes': len(canonical(compact_form).encode()),
        'expanded_parent_form_bytes': len(canonical(expanded_form).encode()),
        'complete_measurements': measurements, 'model_calls': 0, 'completed_actions': 0,
        'controller_observations': 0, 'production_or_tests_changed': False, 'dependency_hashes_unchanged': True}
    save('PROBE_RECEIPT_001.json', result)
    print(json.dumps({key: value for key, value in result.items() if key != 'complete_measurements'}))


if __name__ == '__main__':
    main()
