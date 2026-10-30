"""Retain the numerical example and reread it with all acquisition disabled."""
from contextlib import ExitStack
import hashlib
import importlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

root = Path(__file__).resolve().parent
candidate = root / 'candidate'
sys.path[:0] = [str(candidate), str(candidate/'tests')]
from gene_annotation_episode.bvbrc_fastqutils_bundle_adapter import implementation_sha256
from gene_annotation_episode.bvbrc_fastqutils_contracts import validate_requested_form
from gene_annotation_episode.bvbrc_fastqutils_sra_specs import SRA_FIELDS
from gene_annotation_episode.bvbrc_fastqutils_returns import (
    FACT_SOURCES, BVBRCFastqUtilsReturns, project_fastqutils_return_facts,
    decode_return_value, parent_form_schema,
)
from gene_annotation_episode.communication import validate_form
from test_bvbrc_fastqutils_returns import saved_fixture
from test_bvbrc_fastqutils_provider import f

out = root/'numerical_example_001'
out.mkdir(exist_ok=False)
raw = (candidate/'tests/fixtures/bvbrc_fastqutils/sra/native_selected_run.json').read_bytes()
data = f.build({'sra':(raw,'sra_metadata')})
data[0]['original_task']['submitted_parameters'].update(
    paired_end_libs=[], single_end_libs=[], srr_libs=[{'srr_accession':'SRR6263255'}])
fields = {name:f.selection('measurement',f.measurement('sra',metric,'sra_run'),
    availability='available_value') for name,(metric,*_) in SRA_FIELDS.items()}
fields['requirements'] = f.selection('requirements')
body,sheet,components = saved_fixture(data,fields)
expected = project_fastqutils_return_facts(body,requested_sources=FACT_SOURCES,
    sheet=sheet,components=components)
artifacts = dict(publication=body,sheet=sheet,components=components,typed_facts=expected,
    parameters=data[3],requested_schema=body['publication_inputs']['selector']['requested_schema'])
for name,value in artifacts.items():
    (out/(name+'.json')).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
(out/'native_metadata.json').write_bytes(raw)
loaded = {name:json.loads((out/(name+'.json')).read_text()) for name in artifacts}
attempts = []
def forbidden(*args,**kwargs):
    attempts.append(True)
    raise AssertionError('saved communication attempted acquisition or scientific work')
with ExitStack() as stack:
    for suffix in ('native','sra_native','metadata','sheet','calculators','bundle_adapter'):
        module = importlib.import_module('gene_annotation_episode.bvbrc_fastqutils_'+suffix)
        for name,value in vars(module).copy().items():
            if callable(value) and name.startswith(('parse_','extract_','populate_','calculate_','consume_')):
                stack.enter_context(patch.object(module,name,forbidden))
    for name in ('socket.socket.connect','socket.create_connection','urllib.request.OpenerDirector.open','subprocess.Popen'):
        stack.enter_context(patch(name,forbidden))
    actual = project_fastqutils_return_facts(loaded['publication'],requested_sources=FACT_SOURCES,
        sheet=loaded['sheet'],components=loaded['components'])
    assert actual == loaded['typed_facts'] and not attempts
    schema = parent_form_schema(validate_requested_form(loaded['requested_schema']))
    returned = {name:actual[node['x-source']] for name,node in schema['properties'].items()}
    validate_form(returned,schema,
        lambda reference,namespace=None:BVBRCFastqUtilsReturns._has_reference(actual,reference,namespace))
numbers = [decode_return_value('measurement',r['value'])['records'][0]['payload']['value']
    for r in actual['bvbrc_fastqutils_measurements']]
assert numbers == [2673129532,35172757,937094000,76.0,1]
assert all(p['association_ref'] is None for p in sheet['populations'])
receipt = dict(passed=True,provider_pin=implementation_sha256(),values=numbers,
    independent_from_native_execution=True,forbidden_attempts=len(attempts),
    original_srr_request='SRR6263255',automatic_library_association=False,
    metadata_origin='actual p3-sra source run on retained live NCBI XML',
    provider_envelope='controlled test fixture, not host execution',
    host_custody_verified=False,method_loop_verified=False,live_BV_BRC_job=False,
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
