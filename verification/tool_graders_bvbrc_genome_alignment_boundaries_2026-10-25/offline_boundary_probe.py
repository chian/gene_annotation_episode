"""Boundary evidence only: existing pure readers on retained official bytes.

Does not execute a native aligner, contact a service, or implement a grader.
The source bindings in separate_native-inputs.json are fixture declarations,
not a BV-BRC task receipt.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.xmfa_formats import parse_mauve_xmfa
from gene_annotation_episode.xmfa_sources import bind_xmfa_sources
from gene_annotation_episode.xmfa_calculators import xmfa_alignment_components, xmfa_interval_coverage


def read(name):
    path = ROOT / name
    raw = path.read_bytes()
    return raw, {"raw_artifact_ref": name, "source_ref": "source:" + name,
                 "sha256": hashlib.sha256(raw).hexdigest()}


def parse(name):
    raw, artifact = read(name)
    return parse_mauve_xmfa(raw, artifact=artifact, dialect="mauve1", alphabet="dna", encoding="ascii")


def selection(document):
    members = sorted({r['member_number']['value'] for b in document['blocks'] for r in b['records']})
    return {'population_id': 'all_retained_fixture_columns', 'document_id': document['document_id'],
            'member_numbers': members, 'block_columns': [
                {'block_index': b['block_index'], 'columns_0based': list(range(b['alignment_column_count']))}
                for b in document['blocks']], 'completeness': 'complete', 'evidence': []}


def values(record):
    return {k: v['value'] for k, v in record.items() if isinstance(v, dict) and 'unit' in v and 'value' in v}


base = 'verification/tool_graders_bvbrc_msa_xmfa_boundaries_2026-10-25/native_examples/'
source_name = 'verification/tool_graders_bvbrc_xmfa_sources_2026-10-25/saved_examples/separate_native-inputs.json'
supplied = json.loads((ROOT / source_name).read_text())
source_bytes_checks = []
for source in supplied['inputs']['files']:
    raw_source, retained_artifact = read(base + source['file_id'])
    assert retained_artifact['sha256'] == source['artifact']['sha256']
    lines = raw_source.decode('ascii').splitlines()
    assert len(source['records']) == 1 and lines[0] == '>' + source['records'][0]['header']
    assert ''.join(lines[1:]) == source['records'][0]['sequence']
    source_bytes_checks.append({'path': base + source['file_id'],
        'sha256': retained_artifact['sha256'], 'fixture_sequence_matches_retained_bytes': True})
parsed = parse(base + 'separate.xmfa')
document = parsed['value']
bound = bind_xmfa_sources(document, inputs=supplied['inputs'], source_comparison=supplied['source_comparison'])
chosen = selection(document)
components = xmfa_alignment_components(document, selection=chosen,
    selected_pairs=((1, 2), (1, 3), (2, 3)), case_policy='uppercase')
coverage = {basis: xmfa_interval_coverage(document, selection=chosen, bindings=bound, basis=basis)
            for basis in ('represented', 'multi_member_block', 'cooccupied_column')}
native = str(OUT.relative_to(ROOT)) + '/retained_sources/mauve/testdata/'
small = parse(native + 'small.alignment')
small_document = small['value']
small_components = xmfa_alignment_components(small_document, selection=selection(small_document),
    selected_pairs=((1, 2),), case_policy='uppercase')
legacy = parse(native + 'small.mauve')

script = r'''const fs=require('fs'); const reader=require(process.argv[1]);
const raw=fs.readFileSync(process.argv[2],'utf8'); const rows=reader.parse(raw);
let failure=null;try{for(const block of rows){for(const row of block){const name=row.name;
row.name=name.substr(name.lastIndexOf('/')+1);delete row.seq;}}}catch(e){failure={name:e.name,message:e.message};}
process.stdout.write(JSON.stringify({block_count:rows.length, first_record_keys:Object.keys(rows[0][0]), visualization_strip_failure:failure}));'''
parser_path = ROOT / 'verification/tool_graders_bvbrc_application_artifacts_2026-10-24/sources/p3_mauve/scripts/xmfa-parser.js'
js = subprocess.run(['node', '-e', script, str(parser_path), str(OUT / 'retained_sources/mauve/testdata/small.mauve')],
                    check=False, text=True, capture_output=True)

summary = {
    'scope': 'offline existing pure readers/calculators and upstream JS parser only; no scientific/native/API/HPC job',
    'fixture_binding_authority': 'fixture-declared invocation, not actual BV-BRC task evidence',
    'source_bytes_checks': source_bytes_checks,
    'separate_xmfa': {'parse_status': parsed['status'], 'binding_status': bound['status'],
        'widths': [b['alignment_column_count'] for b in document['blocks']],
        'source_lengths': [sum(len(r['sequence']) for r in f['records']) for f in supplied['inputs']['files']],
        'pairs': [{**{k:p[k] for k in ('member_a','member_b','state')},**values(p)} for p in components['blocks'][0]['pairs']],
        'coverage': {basis:[{'member_number':r['member_number'],**values(r)} for r in value['members']]
                     for basis,value in coverage.items()}},
    'small_xmfa': {'parse_status': small['status'], 'blocks':[
        {'index':b['block_index'],'width':b['alignment_column_count'],
         'rows':[{'member':r['member_number']['value'],'sequence_length':len(r['sequence']),
                  'nongaps':len(r['sequence'].replace('-','')),'gaps':r['sequence'].count('-')}
                 for r in b['records']]} for b in small_document['blocks']],
        'first_block_pair': {**values(small_components['blocks'][0]['pairs'][0])}},
    'legacy_as_xmfa': {'status':legacy['status'],'has_document':legacy['value'] is not None,
                       'diagnostic_codes':[r['code'] for r in legacy['diagnostics']]},
    'upstream_javascript_legacy_parse': {'exit_code':js.returncode,
        'result':json.loads(js.stdout) if js.returncode == 0 else None,'stderr':js.stderr},
}
assert parsed['status'] == bound['status'] == 'ok'
assert small['status'] == 'ok'
assert legacy['status'] == 'invalid' and legacy['value'] is None
assert js.returncode == 0 and summary['upstream_javascript_legacy_parse']['result']['visualization_strip_failure']['name'] == 'TypeError'
(OUT / 'OFFLINE_BOUNDARY_PROBE_001.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
