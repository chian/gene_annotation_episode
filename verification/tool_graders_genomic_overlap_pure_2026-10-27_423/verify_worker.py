"""Bounded pure verification. No native overlap command or network acquisition."""
from pathlib import Path
import json
import sys

import pytest

attempt, snapshot = map(Path, sys.argv[1:])
status = pytest.main(['-q','-p','no:cacheprovider','--basetemp',str(attempt / 'temporary/pytest'),
    '--rootdir',str(snapshot),'--junitxml',str(attempt / 'pytest.xml'),
    str(snapshot / 'tests/test_genomic_overlap_inputs.py'),
    str(snapshot / 'tests/test_genomic_overlap_calculations.py')])
if status:
    raise SystemExit(status)
from gene_annotation_episode.genomic_overlap_inputs import parse_region_set, parse_bedtools_intersect_wo, extract_overlap_reference_metadata, build_genomic_overlap_sheet
from gene_annotation_episode.genomic_overlap_calculations import calculate_genomic_overlap_components
worked = json.loads((snapshot / 'verification/tool_graders_genomic_overlap_contract_2026-10-27_418/WORKED_EXAMPLE.json').read_text())
raw = {r['key']:r['utf8_text'].encode() for r in worked['raw_artifacts']}
request = worked['request']
sets = [parse_region_set(raw[name],specification=spec,set_position=i) for i,(name,spec) in enumerate(zip(('input_a','input_b'),request['region_sets']))]
index = {s['set_key']:s for s in sets}
pair = parse_bedtools_intersect_wo(raw['native'],pair=request['comparisons'][0],sets=index,native=worked['supplied_output_metadata_example'])
refs = extract_overlap_reference_metadata(specifications=request['region_sets'],sets=index,comparisons=request['comparisons'])
sheet = build_genomic_overlap_sheet(request=request,sets=sets,native_pairs=[pair],reference_relations=refs)
components = calculate_genomic_overlap_components(sheet,parameters=worked['components']['parameters'])
example = {'evidence_label':'hand_worked_synthetic_supplied_data', 'native_execution_claim':False,
           'sheet':sheet,'components':components}
(attempt/'FILLED_EXAMPLE.json').write_text(json.dumps(example,indent=2)+'\n')
print(json.dumps({'example_pairwise_sum':components['pairs'][0]['unfiltered']['pairwise_overlap_bp_sum'],
    'example_shared_union':components['pairs'][0]['unfiltered']['intersection_union_bp'],
    'example_jaccard':components['pairs'][0]['unfiltered']['jaccard_bp'],
    'selected_pair_count':components['pairs'][0]['selected']['selected_pair_count']}))
