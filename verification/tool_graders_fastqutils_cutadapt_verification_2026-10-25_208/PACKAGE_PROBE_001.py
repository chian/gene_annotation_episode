"""Inspect an extracted wheel using only its imports and retained specimen data."""
from copy import deepcopy
import base64
import hashlib
import importlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

installed, specimen = [Path(v).resolve() for v in sys.argv[1:]]
sys.dont_write_bytecode = True
sys.path.insert(0, str(installed))
from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode import bvbrc_fastqutils_calculators as calculators
from gene_annotation_episode.bvbrc_fastqutils_contracts import (
    FastqUtilsContractError, canonical_json, make_requested_schema, validate_requested_form,
)
from gene_annotation_episode.bvbrc_fastqutils_returns import (
    FACT_SOURCES, BVBRCFastqUtilsReturns, parent_form_schema, project_fastqutils_return_facts,
    encode_return_value, decode_return_value,
)
from gene_annotation_episode.bvbrc_fastqutils_saved_codec import validate_saved_projection
from gene_annotation_episode.bvbrc_fastqutils_fastqc_reader import _Report
from gene_annotation_episode.bvbrc_fastqutils_cutadapt_reader import append_cutadapt_report
from gene_annotation_episode.bvbrc_fastqutils_tool_info import fastqutils_tool_contracts
from gene_annotation_episode.bvbrc_fastqutils_identity import field_ref
from gene_annotation_episode.bvbrc_fastqutils_metric_specs import metric_spec
from gene_annotation_episode.bvbrc_fastqutils_cutadapt_specs import CUTADAPT_METRICS
from gene_annotation_episode.bvbrc_appservice_adapters import bind_adapters
from gene_annotation_episode.communication import validate_form


def read(name):
    return json.loads((specimen / name).read_text())


attempts = []


def forbidden(*args, **kwargs):
    attempts.append(True)
    raise AssertionError('Unexpected network, native execution, or forbidden scientific replay')


socket.socket.connect = forbidden
socket.create_connection = forbidden
urllib.request.OpenerDirector.open = forbidden
subprocess.run = forbidden
subprocess.Popen = forbidden

meta = read('meta.json')
cases = read('provider_cases.json')
direct = read('direct_native_cases.json')
legacy = {name: read('legacy/' + name + '.json') for name in ('requested_schema', 'provider_result', 'bundle', 'parameters')}
all_before = canonical_json([meta, cases, direct, legacy])
assert list(adapter._DEPENDENCIES) == meta['dependency_order']
dependency_hashes = {}
pin = hashlib.sha256()
for name in sorted(adapter._DEPENDENCIES):
    raw = (installed / 'gene_annotation_episode' / name).read_bytes()
    dependency_hashes[name] = hashlib.sha256(raw).hexdigest()
    pin.update(name.encode() + b'\0' + str(len(raw)).encode() + b'\0' + raw)
assert dependency_hashes == meta['dependency_hashes']
assert pin.hexdigest() == meta['provider_pin'] == adapter.implementation_sha256()
bound = bind_adapters([dict(adapter_id='bvbrc_fastqutils', adapter_version='2', implementation_sha256=pin.hexdigest())])
assert bound[('bvbrc_fastqutils', '2')] == (adapter, pin.hexdigest())
for name in adapter._DEPENDENCIES:
    if name.endswith('.py'):
        importlib.import_module('gene_annotation_episode.' + name[:-3])
tool = fastqutils_tool_contracts(resource_id='selected-api', assignment_schema={'type': 'object'})[0]
assert tool == meta['tool_info']
assert tool['name'] == 'bvbrc.fastqutils' and tool['resources'] == 'api'
for token in ('api.bvbrc_appservice.prepare', 'Cutadapt4.9', 'Trim Galore0.6.10',
              'calculation_requests', 'Deterministic calculators', 'requested typed'):
    assert token in tool['instructions'], token
assert len(CUTADAPT_METRICS) == 23
for metric, definition in CUTADAPT_METRICS.items():
    assert metric_spec(metric) == definition


def value(result, name):
    payload = result['facts'][name]['records'][0]['payload']
    return None if payload is None else payload['value']


actuals = {}
for name, case in cases.items():
    inputs = deepcopy(case['inputs'])
    raw = {k: base64.b64decode(v, validate=True) for k, v in inputs.pop('artifact_bytes_base64').items()}
    before = canonical_json(inputs)
    actual = adapter.consume_bundle(artifact_bytes=raw, **inputs)
    assert actual == case['expected'], name
    assert list(actual['facts']) == inputs['requested_form']['required'], name
    assert canonical_json(inputs) == before
    actuals[name] = actual
native = actuals['native']
native_numbers = {name: value(native, name) for name in (
    'cutadapt_input_reads', 'cutadapt_output_reads', 'cutadapt_output_bases', 'trimgalore_input_reads',
    'final_reads', 'final_bases', 'cutadapt_base_retention')}
assert native_numbers == dict(cutadapt_input_reads=4, cutadapt_output_reads=4, cutadapt_output_bases=28,
    trimgalore_input_reads=4, final_reads=3, final_bases=24, cutadapt_base_retention=28/58)
trim = next(d for d in native['sheet']['documents'] if d['document_id'] == 'trim')
input_bases = [c for c in trim['cells'] if c['metric'] == 'cutadapt_processed_bases' and c['axis']['kind'] == 'none']
assert len(input_bases) == 1 and input_bases[0]['value'] == 58
assert trim['artifact']['producer_name'] == 'Trim Galore' and trim['artifact']['producer_version'] is None
assert [v['value'] for v in trim['labels'] if v['kind'] == 'producer_version'] == ['0.6.10', '4.9']
assert all(e['scope'] == 'artifact_local' and e['task_stage_ref'] is None for e in native['sheet']['native_lineage'])
assert all(s['observed_state'] == 'unknown' for s in native['sheet']['stages'])
assert all(p['association_ref'] is None for p in native['sheet']['populations'])
for name in ('partial', 'wrong_version'):
    result = actuals[name]
    assert result['status'] == 'partial'
    assert value(result, 'final_reads') == 3 and value(result, 'final_bases') == 24
    assert value(result, 'cutadapt_base_retention') is None
assert actuals['partial']['facts']['cutadapt_output_reads']['records'][0]['state'] == 'partial'
assert value(actuals['partial'], 'cutadapt_output_reads') == 4
assert actuals['wrong_version']['facts']['cutadapt_output_reads']['records'][0]['payload'] is None

direct_answers = {}
for row in direct:
    raw = base64.b64decode(row['raw_base64'], validate=True)
    assert row['original_receipt']['exit_code'] == 0 and row['original_receipt']['native_executable_run']
    assert row['original_receipt']['BV_BRC_service_run'] is False
    report = _Report(raw, row['context'], 'native_text', 'Cutadapt')
    append_cutadapt_report(report, raw, start=0, end=len(raw))
    doc = report.finish()
    assert doc == row['expected_document']
    assert doc['artifact']['producer_name'] == 'Cutadapt' and doc['artifact']['declared_format'] == 'native_text'
    if row['case'] == 'cutadapt_empty':
        assert len(doc['cells']) == 1 and doc['cells'][0]['metric'] == 'cutadapt_processed_count'
        assert doc['cells'][0]['value'] == 0 and not doc['native_lineage']
        direct_answers[row['case']] = dict(input_reads=0, retained_cell_count=1, base_counters_absent=True)

# Now prevent native parsing, metadata extraction, sheet population and providers.
for suffix in ('native', 'trim_reader', 'cutadapt_reader', 'fastq_reader', 'sam_reader', 'bam_reader',
               'fastqc_reader', 'pair_report_reader', 'hostile_reader', 'metadata', 'sheet', 'bundle_adapter'):
    module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
    for name, function in list(vars(module).items()):
        if callable(function) and (name.startswith(('parse_', 'populate_', 'extract_'))
                                  or name in ('append_cutadapt_report', 'consume_bundle')):
            setattr(module, name, forbidden)
for case, actual in actuals.items():
    saved = actual['components']['calculations']
    assert calculators.calculate_fastqutils(actual['sheet'], parameters=saved['parameters']) == saved, case
for row in direct:
    if 'sheet' not in row:
        continue
    result = calculators.calculate_fastqutils(row['sheet'], parameters=row['parameters'])
    assert result == row['components']
    parts = {r['metric']: r for r in result['components']}
    expected = {'cutadapt_single': (58, 28), 'cutadapt_filtered': (58, 24), 'zero_bases': (0, 0)}[row['case']]
    before, after = expected
    retention = parts['base_retention_fraction']
    assert (retention['numerator'], retention['denominator']) == expected[::-1]
    assert retention['value'] == (after / before if before else None)
    assert retention['state'] == ('available' if before else 'undefined')
    assert parts['removed_count']['value'] == before - after
    direct_answers[row['case']] = dict(before_bases=before, after_bases=after,
        fraction=retention['value'], state=retention['state'], removed_bases=parts['removed_count']['value'])
synthetic = actuals['seven_family_synthetic']
changed = deepcopy(synthetic['components']['calculations']['parameters'])
quality, = [job for job in changed['calculations'] if job['method'] == 'quality_phred_v1']
quality['quality_thresholds'] = [40, 41]
recalculated = calculators.calculate_fastqutils(synthetic['sheet'], parameters=changed)
fractions = {r['threshold']: r['value'] for r in recalculated['components'] if r['metric'] == 'q_ge_threshold_fraction'}
assert fractions == {40: 1, 41: 0}
assert recalculated['sheet_sha256'] == synthetic['components']['calculations']['sheet_sha256']
assert {r['parameter_sha256'] for r in recalculated['components']}.isdisjoint(
    {r['parameter_sha256'] for r in synthetic['components']['calculations']['components']})

# Pure saved projection/communication must also work without calculators.
for suffix in ('calculators', 'composition', 'quality', 'mapping', 'retention', 'consistency', 'bundle_adapter'):
    module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
    for name, function in list(vars(module).items()):
        if callable(function) and name.startswith('calculate_'):
            setattr(module, name, forbidden)
orders = {}
family_for_kind = dict(zip(('measurement', 'component', 'category', 'population', 'association', 'requirements', 'request_status'), FACT_SOURCES))
for name, case in cases.items():
    actual = actuals[name]
    facts = project_fastqutils_return_facts(case['saved_publication'], requested_sources=FACT_SOURCES,
        sheet=actual['sheet'], components=actual['components'])
    assert facts == case['communication'], name
    form = validate_requested_form(case['inputs']['requested_form'])
    assert [r['field'] for r in form['fields']] == case['inputs']['requested_form']['required']
    schema = parent_form_schema(form)
    returned = {name: facts[node['x-source']] for name, node in schema['properties'].items()}
    validate_form(returned, schema, lambda reference, namespace=None: BVBRCFastqUtilsReturns._has_reference(facts, reference, namespace))
    for kind, source_name in family_for_kind.items():
        expected_fields = [row['field'] for row in form['fields'] if row['selection']['target']['kind'] == kind]
        assert [r['field'] for r in facts[source_name]] == [field_ref(actual['sheet']['analysis_id'], f) for f in expected_fields]
    for fact in actual['facts'].values():
        kind = fact['selection']['target']['kind']
        assert decode_return_value(kind, encode_return_value(kind, fact)) == fact
    orders[name] = [r['field'] for r in form['fields']]
    if name == 'seven_family_synthetic':
        assert len(facts) == 7 and all(facts.values())
    if name == 'native':
        assert [decode_return_value('measurement', r['value'])['records'][0]['payload']['value']
                for r in facts['bvbrc_fastqutils_measurements']] == [4, 4, 28, 4, 3, 24]
old = legacy['requested_schema']
form = validate_requested_form(old)
assert [r['field'] for r in form['fields']] == old['required']
current = make_requested_schema(form)
assert current != old and validate_requested_form(current) == form
rejected = []
for damage in ('open_object', 'missing_field', 'extra_keyword', 'altered_definition', 'mixed_generation', 'new_metric_smuggling'):
    broken = deepcopy(old)
    if damage == 'open_object': broken['additionalProperties'] = True
    elif damage == 'missing_field': broken['required'].pop()
    elif damage == 'extra_keyword': broken['title'] = 'foreign'
    elif damage == 'altered_definition': broken['$defs']['ProjectedField']['additionalProperties'] = True
    elif damage == 'mixed_generation':
        changed_defs = [n for n in old['$defs'] if old['$defs'][n] != current['$defs'][n]]
        assert len(changed_defs) > 1
        broken['$defs'][changed_defs[0]] = deepcopy(current['$defs'][changed_defs[0]])
    else:
        selector = broken['properties']['read_count']['x-bvbrc-fastqutils']['target']['selector']
        selector.update(metric='cutadapt_processed_count', section_key='cutadapt_summary')
    try:
        validate_requested_form(broken)
    except FastqUtilsContractError as error:
        assert error.code == 'requested_form_invalid'
        rejected.append(damage)
    else:
        raise AssertionError('Invalid legacy form accepted: ' + damage)
saved = legacy['provider_result']
validate_saved_projection(saved['sheet'], saved['components'], **{k: saved[k] for k in
    ('facts', 'status', 'missing_requirements', 'diagnostics')}, requested_form=old,
    parameters=legacy['parameters'], original_task=legacy['bundle']['original_task'], bundle=legacy['bundle'])
legacy_numbers = {name: value(saved, name) for name in ('read_count', 'gc', 'errors', 'retained')}
assert legacy_numbers == dict(read_count=2, gc=5/9, errors=.001, retained=.75)
assert all_before == canonical_json([meta, cases, direct, legacy]) and not attempts
origins = {}
for name, module in sorted(sys.modules.items()):
    if name.split('.')[0] in ('gene_annotation_episode', 'method_loop'):
        path = Path(module.__file__).resolve()
        assert path.is_relative_to(installed / name.split('.')[0]), (name, path)
        origins[name] = str(path)
print(json.dumps(dict(provider_pin=pin.hexdigest(), dependency_count=len(dependency_hashes), dependency_hashes=dependency_hashes,
    native_numbers=native_numbers, native_input_bases=58, direct_native_answers=direct_answers,
    changed_quality_threshold_fractions=fractions, legacy_numbers=legacy_numbers,
    rejected_legacy_forms=rejected, requested_orders=orders, legacy_requested_order=old['required'],
    same_parameter_saved_recalculation=True, changed_parameters_preserve_original=True,
    saved_communication_without_science=True, legacy_saved_replay_without_science=True,
    forbidden_call_count=len(attempts), isolated_origins=origins, provider_case_count=len(cases),
    scientific_metric_count=len(CUTADAPT_METRICS), substantive_tool_information_verified=True,
    host_custody_verified=False, live_service_execution_verified=False)))
