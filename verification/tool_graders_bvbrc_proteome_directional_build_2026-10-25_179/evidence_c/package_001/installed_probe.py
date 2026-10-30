import hashlib, json, pathlib, sys
sys.path.insert(0, sys.argv[1])
from gene_annotation_episode import bvbrc_proteome_directional_calculators as c
from gene_annotation_episode.bvbrc_proteome_directional import parse_genome_comparison_directional_report
from gene_annotation_episode.bvbrc_proteome_directional_sheet import build_directional_sheet
assert pathlib.Path(c.__file__).is_relative_to(pathlib.Path(sys.argv[1]))
data = pathlib.Path(sys.argv[2]).read_bytes()
source = {'content': {'source_ref': 'package-native-example', 'artifact_field': 'stdout_ref',
    'artifact_ref': 'package-retained-native', 'sha256': hashlib.sha256(data).hexdigest(),
    'byte_count': len(data)}, 'body_complete': True, 'object_complete': 'yes'}
parsed = parse_genome_comparison_directional_report(data, source=source,
    declared_format='ncbi_blastall_blastp_pairwise_text_v1', report_key='package-native-example')
observed = build_directional_sheet([parsed])['sheet']
result = c.calculate_directional_components(observed, parameters={
    'version': 'bvbrc_proteome_directional_parameters_v1',
    'formula_version': 'displayed_blastp_correspondence_v1',
    'amino_acid_alphabet': 'standard20', 'ratio_decimal_places': 18, 'rounding': 'half_even'})
subject = result['components']['reports'][0]['queries'][1]['subjects'][0]
coverage = subject['coverage']['query_trace_paired_union']['coverage']['value']
identity = subject['compatible_unique_pair_symbol_identity']['value']
assert (coverage['numerator'], coverage['denominator']) == (529, 600)
assert (identity['numerator'], identity['denominator']) == (468, 529)
print(json.dumps({'module': c.__file__, 'result_state': result['state'],
    'coverage': coverage, 'symbol_identity': identity,
    'unresolved_pair_count': subject['compatible_pair_counts']['unresolved_pairs']['value']}))
