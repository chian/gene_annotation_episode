"""Retain complete examples and reproduce saved calculations with I/O disabled.

Verification source IDs below are fixture identities, not authenticated C4
publications, tasks, service receipts, or evidence of a live scientific job.
"""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path('/home/chia/repos/gene_annotation_episode')
BASE = ROOT / 'verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24'
STAGING = BASE / 'staging'
OUT = BASE / 'provider-common-verification'
sys.path.insert(0, str(STAGING / 'tests'))
import test_bvbrc_phylogeny_common as f
from gene_annotation_episode import bvbrc_phylogeny_common_inputs as inputs
from gene_annotation_episode import bvbrc_phylogeny_common_contracts as contracts
from gene_annotation_episode import bvbrc_phylogeny_common_grader as grader

assert all(Path(m.__file__).resolve().parent == STAGING / 'gene_annotation_episode' for m in (inputs, contracts, grader))
(OUT / 'raw').mkdir(exist_ok=True)
raw = []
examples = []


def retained(path, reader, **spec):
    data = path.read_bytes()
    destination = OUT / 'raw' / path.name
    destination.write_bytes(data)
    raw.append({'original_path': str(path), 'retained_path': str(destination), 'byte_count': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    return f.read(data, 'retained-example/' + path.name, reader, **spec)


def export(name, args, p, evidence_type, limits):
    original = deepcopy(args)
    with f.guard_io():
        result, sheet = f.extracted(args)
        components = grader.calculate_common_components(sheet, provider=args['provider'], parameters=p)
        payload = json.loads(json.dumps({'extraction_inputs': args, 'extraction_result': result, 'sheet': sheet, 'parameters': p, 'components': components}, allow_nan=False))
        repeated_read = inputs.extract_common_fields(**payload['extraction_inputs'])
        replay = grader.calculate_common_components(payload['sheet'], provider=args['provider'], parameters=payload['parameters'])
        assert repeated_read == payload['extraction_result']
        assert replay == payload['components'] and args == original
        contracts.validate_shared_fields(payload['sheet'], provider=args['provider'])
    data = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    destination = OUT / (name + '.json.gz')
    with destination.open('wb') as target:
        with gzip.GzipFile(filename='', fileobj=target, mode='wb', mtime=0) as compressed:
            compressed.write(data)
    summary = {'name': name, 'evidence_type': evidence_type, 'path': str(destination), 'uncompressed_bytes': len(data),
        'compressed_bytes': destination.stat().st_size, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        'extraction_status': result['status'], 'offline_saved_replay': True, 'complete_input_and_output': True,
        'limitations': limits, 'numerical_examples': {}}
    if components['alignments']:
        row = components['alignments'][0]
        summary['numerical_examples']['alignment'] = {k: row[k]['value'] for k in ('member_count', 'site_count', 'cell_count', 'gap_cells', 'gap_fraction', 'canonical_cells', 'ambiguity_cells')}
    if components['trees']:
        row = components['trees'][0]
        summary['numerical_examples']['tree'] = {'tip_count': row['tip_count']['value'], 'branch_length_sum': row['branch_length_sum']['value'], 'unit': row['branch_length_sum']['unit']}
    if components['composition']:
        summary['numerical_examples']['composition'] = components['composition'][0]['rows']
    examples.append(summary)
    print(json.dumps({k: summary[k] for k in ('name', 'evidence_type', 'compressed_bytes', 'extraction_status', 'offline_saved_replay')}, sort_keys=True))


args = f.fixture(); subjects = f.add_members(args)
for i, function in enumerate(('A', 'A', 'B')):
    args['joins']['functions'].append({'assignment_id': f'function/{i}', 'subject': subjects[i], 'function_key': function, 'function_label': function, 'source_record_id': subjects[i]['source_record_id'], 'evidence': []})
    args['joins']['taxa'].append({'subject': subjects[i], 'taxon_id': ('X', 'X', 'Y')[i], 'rank': 'species', 'lineage': [], 'source_record_id': subjects[i]['source_record_id'], 'evidence': []})
for kind, selected in (('composition', subjects), ('taxonomy', subjects[:3])):
    args['assembly']['caller_populations'][kind].append({'population_id': kind, 'unit': 'sequence_member', 'member_subjects': selected, 'assignment_completeness': 'unknown', 'membership_completeness': 'complete', 'evidence': []})
_, sheet = f.extracted(args); p = f.parameters(sheet)
p.update(composition_population_ids=['composition'], taxon_requests=[{'population_id': 'taxonomy', 'rank': 'species'}], original_coverage_population_ids=[p['alignment_requests'][0]['population_id']])
export('synthetic_hand', args, p, 'synthetic_hand_calculation', 'Explicit fixture evidence only; original maps unavailable; native branch/support methods unknown; no C4 authentication or scientific execution.')

args = f.fixture(matrix=b'>a\nAAA\n>b\nAA\n'); _, sheet = f.extracted(args); p = f.parameters(sheet); p['alignment_requests'][0]['pairs'] = []
export('synthetic_partial_alignment', args, p, 'synthetic_failure_case', 'Malformed matrix keeps unavailable dimensions; independent four-tip tree retained. No repaired/padded rows.')

args = f.fixture(); tid = args['documents']['parsed']['analyses'][0]['raw_tree_id']; args['observed_run']['settings'] = []
args['assembly']['caller_populations']['bootstraps'] = [{'population_id': 'unknown-replicates', 'tree_ids': [], 'expected_replicates': None, 'completeness': 'unknown', 'expected_count_evidence': []}]
_, sheet = f.extracted(args); p = f.parameters(sheet); p['tree_requests'][0]['branch_unit'] = 'expected_substitutions_per_model_site'
p['bootstrap_requests'] = [{'reference_tree_id': tid, 'replicate_population_id': 'unknown-replicates', 'tip_join': {'reference_tree_id': tid, 'mappings': []}, 'method': 'rapid_bootstrap'}]
export('synthetic_missing_interpretations', args, p, 'synthetic_missing_metadata', 'Unproved alphabet is unknown; named branch unit unavailable; unsupported bootstrap omitted with exact requirements, independent counts retained.')

native_dir = f.NATIVE / 'official_example/test9_genome_dir'
matrix_path = next(native_dir.glob('*.phy')); tree_path = next(native_dir.glob('RAxML_bestTree.*'))
matrix = retained(matrix_path, 'relaxed_phylip', layout='interleaved', continuation_ids='absent')
tree = retained(tree_path, 'newick', dialect='newick', allow_multiple=False)
args = f.fixture(matrix=None, tree=None, provider='codon_tree'); args['documents']['reads'] = [matrix, tree]
args['documents']['parsed']['store']['alignments'] = [matrix['result']['value']]; args['documents']['parsed']['store']['tree_documents'] = [tree['result']['value']]
analysis = args['documents']['parsed']['analyses'][0]; analysis['final_alignment_id'] = matrix['result']['value']['alignment_id']; analysis['raw_tree_id'] = tree['result']['value']['trees'][0]['tree_id']
_, sheet = f.extracted(args); p = f.parameters(sheet); p['alignment_requests'][0].update(alphabet='unknown', pairs=[])
export('retained_codon_matrix_tree', args, p, 'retained_official_native_output', 'Complete retained repository example bytes; no original service/task custody. Mixed alphabet remains unknown for the whole matrix; original maps and run units remain unknown.')

for index, path in enumerate(sorted((f.NATIVE / 'additional_sources/bvbrc_gene_tree/tests').glob('*.xml'))):
    xml = retained(path, 'phyloxml')
    args = f.fixture(matrix=None, tree=None); args['documents']['reads'] = [xml]; args['documents']['parsed']['store']['phyloxml'] = [xml['result']['value']]
    args['documents']['parsed']['analyses'][0]['phyloxml_tree_id'] = xml['result']['value']['trees'][0]['tree']['tree_id']
    _, sheet = f.extracted(args)
    export('retained_gene_xml_' + str(index + 1), args, f.parameters(sheet), 'retained_official_native_output', 'Complete native XML derivative; generic support method/unit remain unknown, XML inserted-zero/lost-zero-support qualifications retained. No original raw tree or service/task custody.')

invalid_args = f.fixture(); f.add_members(invalid_args); invalid_args['joins']['input_rows'][0]['member_id'] = 'absent'
with f.guard_io():
    invalid_result = inputs.extract_common_fields(**invalid_args)
assert invalid_result['status'] == 'invalid' and invalid_result['value'] is None
(OUT / 'invalid_association.json').write_text(json.dumps({'evidence_type': 'synthetic_wrong_member', 'input': invalid_args, 'output': invalid_result}, indent=2, allow_nan=False) + '\n')

code_paths = [STAGING / 'gene_annotation_episode' / ('bvbrc_phylogeny_common_' + suffix + '.py') for suffix in ('inputs', 'contracts', 'grader')] + [STAGING / 'tests/test_bvbrc_phylogeny_common.py']
manifest = {'version': 1, 'scope': 'S pure common provider only', 'examples': examples, 'raw_artifacts': raw,
    'implementation': [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size} for path in code_paths],
    'guard': ['builtins.open', 'io.open', 'pathlib.Path.open', 'socket.socket', 'socket.create_connection', 'subprocess.run', 'subprocess.Popen'],
    'not_verified': ['C4 Store authentication/byte custody', 'production installation/registries', 'selected child execution binding', 'typed episode communication', 'live service execution', 'PhyML/FastTree native log acquisition', 'W05/annotation scoring']}
(OUT / 'EXAMPLES_MANIFEST.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
print(json.dumps({'examples': len(examples), 'all_json_replays_equal_with_io_disabled': True, 'native_bytes_retained': sum(r['byte_count'] for r in raw)}, sort_keys=True))
