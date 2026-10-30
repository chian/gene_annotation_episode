"""Native bytes through provider, saved numerical replay and typed return.

The host bundle/publication envelope is synthetic. This is component integration
evidence, not Workspace acquisition, native execution or method_loop evidence.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import resource
import sys
from unittest.mock import patch
import uuid

EVIDENCE = Path(__file__).resolve().parent
REPOSITORY = EVIDENCE.parents[1]
CANDIDATE = REPOSITORY / 'verification/tool_graders_fastqutils_samstat_implementation_2026-10-25_212/candidate'
sys.path.insert(0, str(CANDIDATE))
resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
spec = importlib.util.spec_from_file_location('native_mapping_verification', CANDIDATE / 'tests/test_bvbrc_fastqutils_samstat_mapping.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
from gene_annotation_episode.execution_contracts import canonical, digest

def save(name, value):
    path = EVIDENCE / name
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    return dict(path=str(path.relative_to(REPOSITORY)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), byte_count=path.stat().st_size)

examples = []
for family in ('legacy', 'current'):
    data = t.fixture_data(family)
    result = t.f.run(data, t.fields())
    t.validate_saved(result, data, t.fields())
    saved = save('NATIVE_' + family.upper() + '_PROVIDER_002.json', result)
    job = result['components']['calculations']['parameters']['calculations'][0]
    index = {c['id']: c for c in result['sheet']['measurements']}
    examples.append(dict(family=family, retained_provider_result=saved,
        input_sha256=hashlib.sha256(data[1]['artifact_report']).hexdigest(),
        original_parameters=data[3], bound_operands=[index[ref] for ref in job['operand_measurement_refs']],
        components=t.components(result)))
    if family == 'current':
        current_data, current_result = data, result

# The typed return wrapper is local synthetic custody, built after the actual
# native parser/sheet/calculator/provider above has produced every scientific row.
def content(value, source=None):
    sha = digest(value)
    return dict(source_ref=source or 'source_' + sha[:24], artifact_field='artifact_ref',
                artifact_ref='artifact_' + sha, sha256=sha, byte_count=len(canonical(value).encode()))

data, result = current_data, current_result
selector = t.f.oracle('RESULT_SELECTOR_PRE_DOWNLOAD_002.json')
selector.update(requested_schema=t.f.schema(t.fields()), adapter=dict(adapter_id='bvbrc_fastqutils', adapter_version='2', parameters=data[3]))
data[0]['requested_selector_sha256'] = digest(selector)
for member in data[0]['artifacts']:
    ident = str(uuid.uuid5(uuid.NAMESPACE_URL, member['workspace_object']['path']))
    member['workspace_object']['uuid'] = member['task_association']['output_uuid'] = ident
saved_result = {k: deepcopy(result[k]) for k in ('adapter_id', 'adapter_version', 'status', 'facts', 'missing_requirements', 'diagnostics')}
saved_result.update(sheet_content=content(result['sheet']), components_content=content(result['components']))
source = 'source_' + digest(data[0])[:24]
body = dict(version=t.RESULT_VERSION, source_ref=source, reference=source, record_refs=[source], assignment=dict(selector=selector),
    publication_inputs=dict(selector=selector, adapter=selector['adapter'], adapter_implementation_sha256=t.adapter.implementation_sha256()),
    bundle=data[0], publication=dict(bundle_content=content(data[0], source), result_record_refs=[source], adapter_result=saved_result))
typed = t.project_fastqutils_return_facts(body, requested_sources=('bvbrc_fastqutils_components',), sheet=result['sheet'], components=result['components'])
schema = t.parent_form_schema(t.validate_requested_form(selector['requested_schema']))
t.validate_form({key: typed[node['x-source']] for key, node in schema['properties'].items()}, schema, lambda *_: True)
original = canonical(result)
restored = json.loads(canonical(result['sheet']))
old_parameters = deepcopy(result['components']['calculations']['parameters'])

def forbid(*args, **kwargs):
    raise AssertionError('saved numerical/return replay attempted parsing, I/O or acquisition')

targets = ['builtins.open', 'pathlib.Path.open', 'socket.socket', 'subprocess.Popen',
    'gene_annotation_episode.bvbrc_fastqutils_bundle_adapter.parse_fastqutils_artifact',
    'gene_annotation_episode.bvbrc_fastqutils_bundle_adapter.populate_fastqutils_sheet',
    'gene_annotation_episode.bvbrc_fastqutils_bundle_adapter.consume_bundle',
    'gene_annotation_episode.bvbrc_fastqutils_native.parse_fastqutils_artifact',
    'gene_annotation_episode.bvbrc_fastqutils_samstat_native.parse_samstat_html',
    'gene_annotation_episode.bvbrc_fastqutils_samstat_svg.parse_samstat_html_2_5_0',
    'gene_annotation_episode.bvbrc_fastqutils_samstat_legacy.parse_samstat_html_2_2_3']
# Import all targets before disabling file access.
for module in ('bvbrc_fastqutils_native', 'bvbrc_fastqutils_samstat_native', 'bvbrc_fastqutils_samstat_svg', 'bvbrc_fastqutils_samstat_legacy'):
    __import__('gene_annotation_episode.' + module)
from contextlib import ExitStack
with ExitStack() as stack:
    for target in targets:
        stack.enter_context(patch(target, forbid))
    old_replay = t.calculate_fastqutils(restored, parameters=old_parameters)
    later = t.calculate(restored, t.request((1,)))
    assert old_replay['components'] == t.components(result)
    assert [r['value'] for r in later['components']] == [8/9, 4/9]
    assert canonical(result) == original
    stack.enter_context(patch('gene_annotation_episode.bvbrc_fastqutils_calculators.calculate_fastqutils', forbid))
    assert t.project_fastqutils_return_facts(body, requested_sources=('bvbrc_fastqutils_components',), sheet=result['sheet'], components=result['components']) == typed

replay = save('SAVED_RECALCULATION_002.json', dict(original_parameters=old_parameters,
    old_replay=old_replay, changed_stratum_request=t.request((1,)), changed_stratum_result=later,
    forbidden_calls=targets, original_unchanged=True, typed_return_replay_unchanged=True))
returned = save('TYPED_RETURN_002.json', dict(scope='synthetic host custody, native scientific provider result',
    parent_form_schema=schema, returned_facts=typed, publication_envelope=body))
summary = save('NUMERICAL_EVIDENCE_002.json', dict(recorded_at=datetime.now(timezone.utc).isoformat(),
    source_candidate=str(CANDIDATE.relative_to(REPOSITORY)), native_examples=examples,
    saved_recalculation=replay, typed_return=returned,
    limits=dict(address_space_bytes=20*1024**3, per_file_bytes=4*1024**3, wall_time_cap=None),
    not_claimed=['new SAMstat native execution', 'live BV-BRC', 'Workspace custody', 'full selected-tool Workflow',
                'method_loop episode communication', 'production application', 'complete provider dependency closure']))
print(json.dumps(summary))
