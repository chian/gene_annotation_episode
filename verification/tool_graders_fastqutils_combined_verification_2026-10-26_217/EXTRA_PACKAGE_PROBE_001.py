"""Exercise installed SRA/SAMstat provider, then saved calculations with I/O denied."""
from copy import deepcopy
import base64
import builtins
import hashlib
import importlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import urllib.request

installed, specimen = map(lambda p: Path(p).resolve(), sys.argv[1:])
sys.path.insert(0, str(installed))
from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as adapter
from gene_annotation_episode import bvbrc_fastqutils_calculators as calculators
from gene_annotation_episode.bvbrc_fastqutils_contracts import canonical_json, validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_resolution import resolve_calculation_inputs
from gene_annotation_episode.bvbrc_fastqutils_returns import (
    FACT_SOURCES, BVBRCFastqUtilsReturns, parent_form_schema, project_fastqutils_return_facts,
    encode_return_value, decode_return_value,
)
from gene_annotation_episode.bvbrc_fastqutils_saved_codec import validate_saved_projection
from gene_annotation_episode.bvbrc_fastqutils_sra_specs import SRA_FIELDS
from gene_annotation_episode.bvbrc_fastqutils_tool_info import fastqutils_tool_contracts
from gene_annotation_episode.communication import validate_form

cases = json.loads((specimen / 'extra_provider_cases.json').read_text())
old208 = json.loads((specimen / 'historical208_native.json').read_text())
original = canonical_json([cases, old208])
pin = adapter.implementation_sha256()
attempts = []


def denied(*args, **kwargs):
    attempts.append('forbidden invocation')
    raise AssertionError('Forbidden network, source access, parser, native execution or scientific replay')


socket.socket.connect = denied
socket.create_connection = denied
urllib.request.OpenerDirector.open = denied
subprocess.Popen = denied
subprocess.run = denied
assert len(adapter._DEPENDENCIES) == 36
for filename in adapter._DEPENDENCIES:
    if filename.endswith('.py'):
        importlib.import_module('gene_annotation_episode.' + filename[:-3])
tool = fastqutils_tool_contracts(resource_id='selected-api', assignment_schema={'type': 'object'})[0]
assert all(token in tool['instructions'] for token in ('SAMstat 2.2.3', '2.5.0', 'p3-sra', 'samstat_report_mapping_v1'))


def run(case):
    inputs = deepcopy(case['inputs'])
    raw = {name: base64.b64decode(value, validate=True) for name, value in inputs.pop('artifact_bytes_base64').items()}
    result = adapter.consume_bundle(artifact_bytes=raw, **inputs)
    assert result == case['expected']
    assert result['status'] == 'ok'
    return result


results = {name: run(case) for name, case in cases.items()}
historical208 = run(old208)
historical_form = validate_requested_form(old208['inputs']['requested_form'])
assert historical_form['fields']
historical208_values = [historical208['facts'][name]['records'][0]['payload']['value'] for name in (
    'cutadapt_input_reads', 'cutadapt_output_reads', 'cutadapt_output_bases', 'trimgalore_input_reads',
    'final_reads', 'final_bases', 'cutadapt_base_retention')]
assert historical208_values == [4, 4, 28, 4, 3, 24, 28 / 58]
numerical = {}
for family in ('legacy', 'current'):
    result = results[family]
    calculated = result['components']['calculations']
    cells = {c['id']: c for c in result['sheet']['measurements']}
    rows = calculated['components']
    expected = cases[family]['independent_expected_numerator_denominator']
    assert [[r['numerator'], r['denominator']] for r in rows] == expected
    assert [r['value'] for r in rows] == [n / d for n, d in expected]
    for row in rows:
        assert row['state'] == 'available' and row['meaning'] == 'native_report_derived'
        assert row['uncertainty'] == 'not_estimated' and row['unit'] == 'fraction'
        assert {'samstat_input_scope_unproven', 'samstat_report_population_only',
                'samstat_mapq255_merged'} <= set(row['diagnostic_codes'])
    numerical[family] = dict(components=rows, operands=[cells[ref] for ref in rows[0]['operand_measurement_refs']],
        artifact=result['sheet']['documents'][0]['artifact'],
        populations=[p for p in result['sheet']['populations'] if p['id'] in rows[0]['population_refs']])
sra = results['sra']
sra_rows = {name: sra['facts'][name]['records'][0]['payload'] for name in SRA_FIELDS}
assert [sra_rows[name]['value'] for name in SRA_FIELDS] == [2673129532, 35172757, 937094000, 76.0, 1]
assert not sra['components']['calculations']['components']
assert all(p['scope'] == 'unknown' and p['association_ref'] is None for p in sra['sheet']['populations'])
assert sra['sheet']['documents'][0]['artifact']['producer_version'] is None
numerical['sra'] = dict(measurements=sra_rows, labels=sra['sheet']['documents'][0]['labels'],
                        artifact=sra['sheet']['documents'][0]['artifact'])

# Load every parser dependency before I/O is forbidden. Saved-only arithmetic
# receives saved data and explicit parameters, without a checkout or fixtures.
for suffix in ('native', 'samstat_native', 'samstat_svg', 'samstat_legacy', 'sra_native', 'metadata',
               'sheet', 'bundle_adapter'):
    module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
    for name, function in list(vars(module).items()):
        if callable(function) and (name.startswith(('parse_', 'populate_', 'extract_')) or name == 'consume_bundle'):
            setattr(module, name, denied)
before_results = canonical_json(results)
original_open, path_open = builtins.open, Path.open
builtins.open = denied
Path.open = denied
socket.socket = denied
try:
    for name, result in results.items():
        saved = result['components']['calculations']
        assert calculators.calculate_fastqutils(result['sheet'], parameters=saved['parameters']) == saved, name
    current = results['current']
    old_calculated = current['components']['calculations']
    request = deepcopy(cases['current']['inputs']['parameters']['calculation_requests'][0])
    request['populations'][0]['population_ordinal'] = 1
    parameters = resolve_calculation_inputs(current['sheet'], requests=[request])
    changed = calculators.calculate_fastqutils(current['sheet'], parameters=parameters)
    assert [[r['numerator'], r['denominator']] for r in changed['components']] == [[8, 9], [4, 9]]
    assert [r['value'] for r in changed['components']] == [8 / 9, 4 / 9]
    assert changed['sheet_sha256'] == old_calculated['sheet_sha256']
    assert {r['parameter_sha256'] for r in changed['components']}.isdisjoint(
        r['parameter_sha256'] for r in old_calculated['components'])
    assert before_results == canonical_json(results)
    # Typed saved return is also independent of calculator invocation.
    for suffix in ('calculators', 'samstat_mapping', 'bundle_adapter'):
        module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
        for name, function in list(vars(module).items()):
            if callable(function) and name.startswith('calculate_'):
                setattr(module, name, denied)
    orders = {}
    for name, case in {**cases, 'historical208': old208}.items():
        result = historical208 if name == 'historical208' else results[name]
        facts = project_fastqutils_return_facts(case['saved_publication'], requested_sources=FACT_SOURCES,
            sheet=result['sheet'], components=result['components'])
        assert facts == case['communication'], name
        form = validate_requested_form(case['inputs']['requested_form'])
        schema = parent_form_schema(form)
        returned = {field: facts[node['x-source']] for field, node in schema['properties'].items()}
        validate_form(returned, schema, lambda reference, namespace=None:
            BVBRCFastqUtilsReturns._has_reference(facts, reference, namespace))
        for fact in result['facts'].values():
            kind = fact['selection']['target']['kind']
            assert decode_return_value(kind, encode_return_value(kind, fact)) == fact
        orders[name] = [field['field'] for field in form['fields']]
        inputs = case['inputs']
        validate_saved_projection(result['sheet'], result['components'],
            **{key: result[key] for key in ('facts', 'status', 'missing_requirements', 'diagnostics')},
            requested_form=inputs['requested_form'], parameters=inputs['parameters'],
            original_task=inputs['bundle']['original_task'], bundle=inputs['bundle'])
    assert original == canonical_json([cases, old208]) and before_results == canonical_json(results)
finally:
    builtins.open, Path.open = original_open, path_open
origins = {}
for name, module in sorted(sys.modules.items()):
    if name.split('.')[0] in ('gene_annotation_episode', 'method_loop'):
        origin = Path(module.__file__).resolve()
        assert origin.is_relative_to(installed / name.split('.')[0]), (name, origin)
        origins[name] = str(origin)
assert not attempts
numerical['changed_R1'] = dict(components=changed['components'], parameters=parameters,
    original_components=old_calculated['components'], unchanged_original=True)
print(json.dumps(dict(provider_pin=pin, dependency_count=len(adapter._DEPENDENCIES),
    numerical=numerical, historical208_values=historical208_values, requested_orders=orders,
    saved_recalculation_with_io_and_parsers_forbidden=True, saved_returns_without_calculators=True,
    forbidden_call_count=len(attempts), isolated_origins=origins,
    host_or_Workflow_verified=False, live_acquisition=False, native_producer_executed=False)))
