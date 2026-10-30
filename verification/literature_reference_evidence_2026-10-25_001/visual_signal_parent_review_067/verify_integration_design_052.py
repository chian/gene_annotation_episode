"""Independent design-only contract checks; no source/Workflow/model execution."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
OWNED = HERE.parent / 'a105_ratio_episode_integration_077'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = json.loads((OWNED / 'DESIGN_MANIFEST_002.json').read_bytes())
for row in manifest['files']:
    assert sha(OWNED / row['path']) == row['sha256'], row['path']
from jsonschema import Draft202012Validator
from gene_annotation_episode.literature_episodes import LiteratureEpisodes, _population_catalog
from gene_annotation_episode.literature_ratio_source_storage import (
    ratio_source_population_schema, ratio_source_cells_schema, COMPONENTS)
from gene_annotation_episode.literature_reference_parent_prompt import REFERENCE_PARENT_TASK
from gene_annotation_episode.literature_experimental_prompt import EXPERIMENTAL_TASK

baseline = json.loads((OWNED / 'BASELINE_DEFAULT_CONTRACTS_001.json').read_bytes())
binding = LiteratureEpisodes(None, rate_population=True)
assert baseline['population_catalog'] == _population_catalog() and len(_population_catalog()) == 19
assert baseline['fact_sources'] == binding._rate_fact_sources() and len(binding._rate_fact_sources()) == 18
for role in binding.roles:
    assert baseline['assignment_schemas'][role] == binding.assignment_schema(role)
request = json.loads((OWNED / 'REQUEST_SCHEMA_001.json').read_bytes())
returned = json.loads((OWNED / 'RETURN_SCHEMA_001.json').read_bytes())
assert request == ratio_source_population_schema()
assert returned == ratio_source_cells_schema()
api = json.loads((OWNED / 'API_CONTRACT_001.json').read_bytes())
assert api['operation']['name'] == 'literature.ratio.source.populate'
assert api['namespace'] == 'literature_ratio_source_cells'
assert api['components'] == list(COMPONENTS)
enabled = json.loads((OWNED / 'ENABLED_ASSIGNMENT_SCHEMAS_002.json').read_bytes())
assert set(enabled) == set(binding.roles)
for role, value in enabled.items():
    expected = deepcopy(baseline['assignment_schemas'][role])
    expected['properties']['requested_ratio_source_components'] = {
        'type': 'array', 'uniqueItems': True, 'items': {'enum': list(COMPONENTS)}}
    assert value == expected
    Draft202012Validator.check_schema(value)
for value in (request, returned, api['internal_label_projection']):
    Draft202012Validator.check_schema(value)
child = (OWNED / 'DRAFT_CHILD_TASK_001.txt').read_text()
parent = (OWNED / 'DRAFT_PARENT_TASK_001.txt').read_text()
insert = (OWNED / 'DRAFT_SOURCE_RATIO_TASK_INSERT_001.txt').read_text().strip()
steering = (OWNED / 'DRAFT_PARENT_STEERING_001.txt').read_text()
assert child.count(insert) == 1 and EXPERIMENTAL_TASK in child
assert parent.count(REFERENCE_PARENT_TASK) == 1 and insert not in parent
assert '| reported_ratio |' in child and '| reported_ratio | 0.64 |' in steering
for hidden in ('difference_from_reference', 'log_reported_ratio', 'numerator 0.64', 'reference 1.00'):
    assert hidden not in steering
for essential in ('K426A', '1–253', '37 °C', 'pH 7.4'):
    assert essential in steering
receipt = {'scope': '077 design-only; implementation/connected execution unproven',
    'manifest_sha256': sha(OWNED / 'DESIGN_MANIFEST_002.json'),
    'design_payloads_checked': len(manifest['files']), 'default_operations': 19, 'default_namespaces': 18,
    'exact_existing_request_and_return_schemas': True,
    'all_enabled_assignment_schemas_add_only_requested_selector': len(enabled),
    'root_actual_complete_task_reads': {'child_characters': len(child), 'parent_characters': len(parent),
        'child_ranges': [[0,24000],[24000,48000],[48000,72000],[72000,len(child)]],
        'parent_ranges': [[0,16000],[16000,40000],[40000,len(parent)]]},
    'root_complete_design_reads': ['DESIGN_001.md','PROOF_PLAN_001.md','API_CONTRACT_001.json',
        'DRAFT_LABEL_RENDERING_001.md','DRAFT_SOURCE_RATIO_TASK_INSERT_001.txt','DRAFT_PARENT_STEERING_001.txt',
        'HANDOFF_001.md','build_design_artifacts_001.py'],
    'post_packet_reset': '077 correctly identified earlier retained YeaG reads; its full own reset is in progress before production release',
    'no_source_or_workflow_or_model_or_observations': True}
with (HERE / 'INTEGRATION_DESIGN_ROOT_RECEIPT_052.json').open('x') as stream:
    json.dump(receipt, stream, indent=2); stream.write('\n')
print(json.dumps(receipt))
