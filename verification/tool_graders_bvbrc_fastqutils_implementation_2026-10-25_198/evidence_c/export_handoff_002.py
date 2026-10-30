"""Export actual pure-provider calls from the immutable C frozen source copy."""
from pathlib import Path
import hashlib
import importlib
import importlib.util
import inspect
import json
import sys

BASE = Path(__file__).resolve().parent
FROZEN = BASE / 'frozen_001/source'
sys.path.insert(0, str(FROZEN))
OUT = BASE / 'integration_handoff_002'
OUT.mkdir(exist_ok=False)
from gene_annotation_episode import bvbrc_fastqutils_bundle_adapter as provider
from gene_annotation_episode.bvbrc_fastqutils_contracts import canonical_json, json_sha256, validate_contract
from gene_annotation_episode.bvbrc_fastqutils_native import parse_fastqutils_artifact
from gene_annotation_episode.bvbrc_fastqutils_metadata import extract_fastqutils_metadata
from gene_annotation_episode.bvbrc_fastqutils_resolution import resolve_documents, resolve_calculation_inputs
from gene_annotation_episode.bvbrc_fastqutils_sheet import populate_fastqutils_sheet
from gene_annotation_episode.bvbrc_fastqutils_calculators import calculate_fastqutils
from gene_annotation_episode.bvbrc_fastqutils_saved_codec import validate_saved_projection

spec = importlib.util.spec_from_file_location('fixture_support', FROZEN / 'tests/fixtures/bvbrc_fastqutils/bundle/fixture_support.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
data, fields = f.seven_family_data()
bundle, raw, supplied, parameters = data
requested = f.schema(fields)
contexts, resolutions, requirements = resolve_documents(bundle, artifact_bytes=raw, parameters=parameters)
documents = [parse_fastqutils_artifact(raw[c['content']['artifact_ref']], context=c) for c in contexts]
metadata = extract_fastqutils_metadata(bundle['original_task'], analysis_id=parameters['analysis_id'], metadata_bindings=parameters['metadata_bindings'], supplied_values=supplied, documents=documents)
sheet = populate_fastqutils_sheet(documents, metadata=metadata, document_resolutions=resolutions)
calculation_parameters = resolve_calculation_inputs(sheet, requests=parameters['calculation_requests'])
components = calculate_fastqutils(sheet, parameters=calculation_parameters)
result = provider.consume_bundle(bundle, artifact_bytes=raw, supplied_values=supplied, requested_form=requested, parameters=parameters)
assert result['sheet'] == sheet and result['components']['calculations'] == components
validate_saved_projection(sheet, result['components'], facts=result['facts'], status=result['status'], missing_requirements=result['missing_requirements'], diagnostics=result['diagnostics'], requested_form=requested, parameters=parameters, original_task=bundle['original_task'], bundle=bundle)
assert set(r['selection']['target']['kind'] for r in result['facts'].values()) == {'measurement', 'component', 'category', 'population', 'association', 'requirements', 'request_status'}

def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')

for name, value in {'bundle': bundle, 'supplied_values': supplied, 'parameters': parameters, 'requested_schema': requested, 'parse_contexts': contexts, 'document_resolutions': resolutions, 'resolution_requirements': requirements, 'native_documents': documents, 'metadata': metadata, 'sheet': sheet, 'calculation_parameters': calculation_parameters, 'calculated_components': components, 'saved_components': result['components'], 'selected_facts': result['facts'], 'provider_result': result}.items():
    write(name + '.json', value)
for ident, body in raw.items():
    (OUT / (ident + '.native')).write_bytes(body)
# These exact bytes supply the selected metadata pointer values. They are
# synthetic fixture contents, not an authenticated custody claim.
metadata_raw = canonical_json({'declarations': [r['value'] for r in supplied]}).encode()
assert hashlib.sha256(metadata_raw).hexdigest() == supplied[0]['evidence']['content']['sha256']
(OUT / 'artifact_declarations.json').write_bytes(metadata_raw)
exports = {
    'native': ['parse_fastqutils_artifact', 'parse_unsupported_artifact'],
    'metadata': ['select_metadata', 'extract_fastqutils_metadata'],
    'sheet': ['populate_fastqutils_sheet'],
    'resolution': ['resolve_documents', 'resolve_calculation_inputs'],
    'calculators': ['calculate_fastqutils'],
    'bundle_adapter': ['FastqUtilsBundleAdapter', 'consume_bundle', 'implementation_sha256'],
    'projection': ['project_fastqutils_facts'],
    'saved_codec': ['encode_failures', 'encode_saved_components', 'decode_saved_components', 'validate_saved_projection'],
}
manifest = []
for suffix, names in exports.items():
    module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_' + suffix)
    for name in names:
        obj = getattr(module, name)
        manifest.append(dict(module=module.__name__, export=name, signature=str(inspect.signature(obj.consume_bundle if name == 'FastqUtilsBundleAdapter' else obj)), path=str(Path(module.__file__).relative_to(BASE)), sha256=hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()))
write('EXPORT_MANIFEST.json', manifest)
all_cells = {r['id']: r for r in sheet['measurements']}
audit = []
for c in components['components']:
    consumed = c['operand_measurement_refs']
    audit.append(dict(component_id=c['id'], calculation_id=c['calculation_id'], metric=c['metric'], value=c['value'], state=c['state'], numerator=c['numerator'], denominator=c['denominator'], operand_measurement_refs=consumed, consumed_metric_keys=[all_cells[r]['metric'] for r in consumed], retained_unused_measurement_refs=[r for r in all_cells if r not in consumed], population_refs=c['population_refs'], encoding_basis=c['encoding_basis'], lineage_basis=c['lineage_basis']))
write('NUMERICAL_AUDIT.json', audit)
summary = dict(adapter_id=provider.ADAPTER_ID, adapter_version=provider.ADAPTER_VERSION, implementation_sha256=provider.implementation_sha256(), scientific_dependency_count=len(provider._DEPENDENCIES), status=result['status'], selected_field_count=len(fields), fact_families=sorted({r['selection']['target']['kind'] for r in result['facts'].values()}), native_documents=len(documents), measurements=len(sheet['measurements']), components=len(components['components']), complete_sheet_sha256=json_sha256(sheet), calculator_parameters_sha256=json_sha256(calculation_parameters), provider_result_sha256=json_sha256(result), stages=[dict(recipe_ordinal=s['recipe_ordinal'], observed_state=s['observed_state']) for s in sheet['stages']], values={name:field['records'][0]['payload'] for name,field in result['facts'].items() if name in ('read_count','gc','errors','retained')}, verification='Pure parsers, metadata, sheet, calculators, provider, exact projection and saved validation executed against frozen source; all native bytes handcrafted for this fixture. No native executable or live service ran. Host custody and full ResultSelector validation are separate root work.')
write('SUMMARY.json', summary)
write('ARTIFACT_DIGESTS.json', [dict(path=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), byte_count=p.stat().st_size) for p in sorted(OUT.iterdir()) if p.is_file()])
print(json.dumps({k:v for k,v in summary.items() if k not in ('values','stages')}, indent=2))
