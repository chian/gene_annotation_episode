"""Rerender the actual completed controlled MSA context without running work."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.scientific_process_prompt import render_scientific_process_prompt

HERE = Path(__file__).resolve().parent
RUN = ROOT / 'verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/runs/msa_dna-_7cous9_'
SOURCE = 'source_88af3848dbab8e698365e66e'
db = sqlite3.connect((RUN / 'state/state.sqlite3').as_uri() + '?mode=ro', uri=True)
db.execute('pragma query_only=on')
originals = {str(path.relative_to(RUN)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in RUN.glob('scientific-presentation-*.txt')}
checked = []
for episode, call, raw in db.execute('select episode_id,call_index,request from runtime_model_calls '
        'where request like ? order by call_index', ('%' + SOURCE + '%',)):
    request = json.loads(raw)
    context = request['context']
    state = context.get('fields', context)
    if not state.get('scientific_process') or not state.get('child_reports'):
        continue
    before = deepcopy(state)
    old = (RUN / f'scientific-presentation-{call}.txt').read_text()
    instructions = old.split('\n\nAssigned work\n\n', 1)[0].removeprefix('TASK\n\n')
    text = render_scientific_process_prompt(state, instructions)
    assert SOURCE not in text
    assert 'artifact_ref |' not in text.split('\n\nSTEERING\n')[1]
    for value in ('0.9182958340544896', '0.21428571428571427', '92.0',
            'alignment_deployed_version_unproven', 'hundredths_of_bit', 'selected_row_count'):
        assert value in text, value
    old = (RUN / f'scientific-presentation-{call}.txt').read_text()
    assert text.split('\n\nSTEERING\n')[0] == old.split('\n\nSTEERING\n')[0]
    assert state == before
    path = HERE / f'rendered-scientific-{call}-002.txt'
    path.write_text(text)
    checked.append({'call': call, 'episode': episode,
        'original_characters': len(old), 'rendered_characters': len(text),
        'full_task_unchanged': True, 'original_state_unchanged': True,
        'requested_numbers_units_qualifications_retained': True,
        'publication_source_id_absent': True, 'rendered_file': str(path.relative_to(ROOT))})
assert len(checked) == 6
assert originals == {str(path.relative_to(RUN)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in RUN.glob('scientific-presentation-*.txt')}
result = {'recorded_at': datetime.now(timezone.utc).isoformat(),
    'scope': 'read-only re-render of saved MSA Workflow009 contexts; no Workflow or model execution',
    'checked': checked, 'original_presentations_unchanged': True,
    'source_hashes': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        'gene_annotation_episode/alignment_result_presentation.py',
        'gene_annotation_episode/scientific_process_prompt.py')}}
(HERE / 'RETAINED_CONTEXT_002.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'contexts_checked': len(checked), 'originals_unchanged': True,
    'first_characters_before_after': [checked[0]['original_characters'], checked[0]['rendered_characters']]}))
