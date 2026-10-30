from copy import deepcopy
import json
from pathlib import Path

from gene_annotation_episode.blast_vdb_function_inputs import validate_blast_vdb_function_sheet

root = Path(__file__).resolve().parents[2]
packet = Path(__file__).parent
fixture = root / 'verification/tool_graders_blast_vdb_function_inputs_2026-10-26_342/fixtures_001/whole_sequence.json'
original = json.loads(fixture.read_text())
changed = deepcopy(original)
before = [r['sample_key'] for r in changed['base_components']['sample_groups']['groups']]
for row in changed['base_components']['sample_groups']['groups']:
    row['sample_key'] = 'invented-shared-sample'
for row in changed['entities']:
    if row['origin_sample_keys']:
        row['origin_sample_keys'] = ['invented-shared-sample']
try:
    returned = validate_blast_vdb_function_sheet(changed)
except ValueError as error:
    result = dict(rejected=True, error=str(error), original_sample_keys=before)
else:
    result = dict(rejected=False, returned_value_identical=returned == changed,
                  original_sample_keys=before,
                  changed_sample_keys=[r['sample_key'] for r in returned['base_components']['sample_groups']['groups']],
                  original_member_dataset_records_unchanged=(original['base_sheet'] == returned['base_sheet']))
(packet / 'probe_result_001.json').write_text(json.dumps(result, indent=2) + '\n')
(packet / 'probe_original_001.json').write_text(json.dumps(original, indent=2) + '\n')
(packet / 'probe_changed_001.json').write_text(json.dumps(changed, indent=2) + '\n')
print(json.dumps(result, sort_keys=True))
