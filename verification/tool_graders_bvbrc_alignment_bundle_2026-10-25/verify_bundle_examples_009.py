"""Save full pure adapter operands/results, then replay without scientific work.

Retained native files are reused unchanged. All AppService/custody identities
are explicit synthetic fixtures; this is not live transport or episode proof.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
sys.path.insert(0, str(ROOT))

from pytest import MonkeyPatch
from test_bvbrc_alignment_associations import forbid_io
from test_bvbrc_alignment_bundle_resolution import (
    COUNT_FIELD, basic_fixture, msa_native_fixture, meta_native_fixture,
    xmfa_native_fixture, cross_family_fixture, optional_missing_fixture, slot,
)
from gene_annotation_episode import bvbrc_alignment_bundle_contracts as contracts
from gene_annotation_episode import bvbrc_alignment_bundle_resolution as resolver
from gene_annotation_episode import bvbrc_msa_bundle_adapter as msa
from gene_annotation_episode.bvbrc_alignment_bundle_projection import project_requested_facts, validate_projected_facts

OUT = Path(__file__).resolve().parent / (sys.argv[1] if len(sys.argv) > 1 else 'EXAMPLES_009')
OUT.mkdir(exist_ok=False)
(OUT / 'bytes').mkdir(exist_ok=True)


def save(path, value):
    raw = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False).encode() + b'\n'
    path.write_bytes(raw)
    return {'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw)}


msa_fields = {
    'native_score': {'kind':'native_measurement','analysis_id':'analysis','table':slot('analysis','frequency'),'row_index':1,'field':{'kind':'score'}},
    'entropy': {'kind':'measurement','analysis_id':'analysis','request_id':'entropy','metric':'literal_entropy_bits','selector':{'column_0based':1}},
    'sites': {'kind':'msa_sites','analysis_id':'analysis','request_id':'entropy','columns_0based':[1,2]},
}
meta_fields = {
    'native_p': {'kind':'native_measurement','analysis_id':'analysis','table':slot('analysis','raw_omnibus'),'row_index':1,'field':{'kind':'p_value'}},
    'biological_counts': {'kind':'group_counts','analysis_id':'analysis','request_id':'biological:counts','columns_0based':[1],
        'group_ids':['metacats_group:comparison/A','metacats_group:comparison/B'],'symbols':['A','C']},
    'native_test': {'kind':'statistical_tests','analysis_id':'analysis','request_id':'native:stats','tests':[
        {'category_id':'comparison','column_0based':1,'kind':'omnibus','group_ids':['metacats_group:comparison/A','metacats_group:comparison/B']}]},
}
xmfa_fields = {
    'cell': {'kind':'xmfa_coordinates','analysis_id':'analysis','request_id':'coordinates','cells':[{'block_index':0,'record_index':0,'column_0based':0}]},
    'metric': {'kind':'xmfa_alignment_measurements','analysis_id':'analysis','request_id':'metrics','measurements':[{'metric':'identical_canonical','block_index':0,'member_a':1,'member_b':3}]},
    'coverage': {'kind':'xmfa_coverage','analysis_id':'analysis','request_id':'represented','member_numbers':[1,2,3],'include_intervals':True,'include_original_coverage':False},
    'inverse': {'kind':'xmfa_source_positions','analysis_id':'analysis','request_id':'inverse','queries':[{'member_number':1,'position_0based':48}]},
}
family_fields = {'adjusted': {'kind':'multiplicity','analysis_id':None,'request_id':None,'family_request_id':'both','selection':'all_family','tests':[]}}
missing = basic_fixture(); missing.bundle['artifacts'] = []; missing.raw = {}
cases = [
    ('msa_dna', msa_native_fixture(), msa_fields),
    ('msa_protein', msa_native_fixture('protein'), msa_fields),
    ('metacats_native', meta_native_fixture(), meta_fields),
    ('two_analyses_same_category', cross_family_fixture(), family_fields),
    ('full_xmfa', xmfa_native_fixture(), xmfa_fields),
    ('xmfa_missing_source', xmfa_native_fixture(False), xmfa_fields),
    ('unrequested_missing_analysis', optional_missing_fixture(), COUNT_FIELD),
    ('requested_missing_alignment', missing, COUNT_FIELD),
]
receipts, replays = [], []
for name, fixture, fields in cases:
    form = contracts.requested_form_schema(fields, provider=fixture.provider)
    result = fixture.consume(fields)
    files = {}
    for reference, data in fixture.raw.items():
        sha = hashlib.sha256(data).hexdigest(); path = OUT / 'bytes' / (sha + '.bin')
        path.write_bytes(data)
        files[reference] = {'path': str(path.relative_to(ROOT)), 'sha256': sha, 'byte_count': len(data)}
    operands = {'provider':fixture.provider,'bundle':fixture.bundle,'parameters':fixture.parameters,
        'supplied_values':fixture.values,'requested_form':form,'artifact_files':files,
        'provenance':'retained native bytes or explicitly synthetic small input; synthetic AppService and custody fixtures; no live job'}
    operands_record = save(OUT / (name + '.operands.json'), operands)
    result_record = save(OUT / (name + '.result.json'), result)
    args = {'sheet_set':deepcopy(result['sheet']),'component_set':deepcopy(result['components']),
        'missing_requirements':tuple(result['missing_requirements']),'diagnostics':tuple(result['diagnostics']),
        'requested_form':form,'parameters':fixture.parameters,'provider':fixture.provider}
    replays.append((name, args, deepcopy(result['facts'])))
    receipts.append({'example':name,'status':result['status'],'operands':operands_record,'result':result_record,
        'artifact_count':len(files),'analysis_count':len(fixture.parameters['analyses']),
        'saved_requirements':len(result['missing_requirements']),'facts':deepcopy(result['facts'])})


def forbidden(*args, **kwargs):
    raise AssertionError('Saved projection invoked parsing, calculation, acquisition or I/O')


with MonkeyPatch.context() as monkeypatch:
    for name in ('_parse','extract_msa_sheet','extract_metacats_sheet','calculate_msa','calculate_metacats','verify_xmfa_source_inputs'):
        monkeypatch.setattr(resolver, name, forbidden)
    forbid_io(monkeypatch)
    for name, args, facts in replays:
        assert project_requested_facts(**args) == facts, name
        assert validate_projected_facts(facts, **args) == facts, name

source_files = ['gene_annotation_episode/' + name for name in msa._DEPENDENCIES]
source_files += ['tests/test_bvbrc_alignment_bundle_resolution.py','tests/test_bvbrc_alignment_bundle_projection.py']
source_hashes = {name:hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_files}
save(OUT / 'RECEIPT.json', {'adapter_pin':msa.implementation_sha256(),'examples':receipts,
    'projection_replays_without_scientific_work_or_io':len(replays),'source_hashes':source_hashes,
    'limitations':['No live BV-BRC task or transport','No scientific parent/child episode path in this script',
        'Synthetic custody is not proof of original host possession','No GenBank/DNAstar source extractor binding',
        'No prealigned launch bypass or deployed engine-version proof']})
print(json.dumps({'examples':len(receipts),'projection_replays':len(replays),
    'statuses':{row['example']:row['status'] for row in receipts},'adapter_pin':msa.implementation_sha256()}, sort_keys=True))
