"""051 read provenance; ack only after the preceding complete display was read."""
raise SystemExit("Historical agent-note reader retired.")

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = OUT.parent
ACTIVE = Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
SOURCE = BASE / 'a105_specificity_case_038'
SOURCE_PATHS = [SOURCE / name for name in (
    'source/PMC2711008.bioc.txt', 'source/Table1.decoded.xml',
    'FINDINGS.md', 'HANDOFF.md', 'PROVENANCE.md', 'SOURCE_MANIFEST.json')]
AUTHORITY = [
    'AGENTS.md', 'GOAL.md', 'docs/EPISODE_STRUCTURE.md',
    'docs/TIME_AWARE_ESTIMATION.md', 'docs/TOOL_KNOWLEDGE.md',
    'docs/TASK_AND_STEERING.md',
    'docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
    'verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md',
    'research/experimental_scoring_review_2026-10-23/AGENTS.md',
    'research/experimental_scoring_review_2026-10-23/SOURCE_CORRECTIONS.md',
    'research/experimental_scoring_review_2026-10-23/a105_complete_deliverable_022/A105_NUMERICAL_SCORING_SHEET_001.md',
    'gene_annotation_episode/literature_kinetic_calculations.py',
    'gene_annotation_episode/literature_kinetic_inputs.py',
    'gene_annotation_episode/literature_kinetic_storage.py',
    'gene_annotation_episode/literature_kinetic_validation.py',
    'gene_annotation_episode/literature_experimental_contracts.py',
    'gene_annotation_episode/literature_episodes.py',
    'gene_annotation_episode/episode_services.py',
    'gene_annotation_episode/literature_experimental_prompt.py',
    'tests/test_literature_kinetic_integration.py',
]
RESET_PATHS = [ACTIVE, *(ROOT / p for p in AUTHORITY),
    BASE / 'a105_kinetic_integration_047/FINAL_HANDOFF_006.md', ACTIVE,
    BASE / 'LATEST_HUMAN_DIRECTION_PARENT_039.txt',
    BASE / 'LITERATURE_GRADER_SELECTION_TARGET_040.md']

parser = argparse.ArgumentParser()
parser.add_argument('phase', choices=('source', 'reset', 'reset006'))
parser.add_argument('--read', type=int)
parser.add_argument('--count', type=int, default=1)
parser.add_argument('--ack', type=int, action='append')
args = parser.parse_args()
paths = SOURCE_PATHS if args.phase == 'source' else RESET_PATHS
if args.phase == 'reset006':
    paths = [(BASE / 'a105_kinetic_integration_047/snapshot_006/gene_annotation_episode/literature_episodes.py')
             if p == ROOT / 'gene_annotation_episode/literature_episodes.py' else p for p in paths]
chunks, entries = [], []
for path in paths:
    raw = path.read_bytes()
    lines = raw.decode().splitlines(keepends=True)
    entries.append({'path': str(path), 'bytes': len(raw),
        'sha256': hashlib.sha256(raw).hexdigest(), 'lines': len(lines)})
    buffer, start = '', 1
    for number, line in enumerate(lines, 1):
        if len((buffer + line).encode()) > 13000 and buffer:
            chunks.append({'path': str(path), 'start_line': start,
                'end_line': number - 1, 'text': buffer})
            buffer, start = '', number
        buffer += line
    if buffer:
        chunks.append({'path': str(path), 'start_line': start,
            'end_line': len(lines), 'text': buffer})
receipt = OUT / (args.phase.upper() + '_READ_RECEIPT.json')
record = json.loads(receipt.read_text()) if receipt.exists() else {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'documents': entries, 'chunks_total': len(chunks),
    'acknowledged_chunks': [], 'complete': False,
    'agent': '/root/a105_kinetic_primary_example_051',
    'scientific_interpretation_before_post_paper_reset': False,
}
if args.phase == 'reset006' and not receipt.exists():
    previous_path = OUT / 'RESET_READ_RECEIPT.json'
    previous = json.loads(previous_path.read_bytes())
    assert len(previous['documents']) == len(entries)
    for old, new in zip(previous['documents'], entries):
        assert all(old[k] == new[k] for k in ('bytes', 'sha256', 'lines'))
    record['continued_exact_partial_receipt'] = {
        'path': str(previous_path), 'sha256': hashlib.sha256(previous_path.read_bytes()).hexdigest(),
        'reason': '050 now owns current C7 operand-information metadata; root directed exact immutable047006 contract binding',
        'scientific_interpretation_repeated': False,
    }
    for index, acknowledged in enumerate(previous['acknowledged_chunks']):
        assert acknowledged['start_line'] == chunks[index]['start_line']
        assert acknowledged['end_line'] == chunks[index]['end_line']
        record['acknowledged_chunks'].append({k: v for k, v in chunks[index].items() if k != 'text'})
assert record['documents'] == entries
if args.phase != 'source':
    assert json.loads((OUT / 'SOURCE_READ_RECEIPT.json').read_text())['complete']
for acknowledged in args.ack or []:
    assert acknowledged == len(record['acknowledged_chunks']) < len(chunks)
    record['acknowledged_chunks'].append({k: v for k, v in chunks[acknowledged].items() if k != 'text'})
record['complete'] = len(record['acknowledged_chunks']) == len(chunks)
receipt.write_text(json.dumps(record, indent=2) + '\n')
if args.read is not None:
    assert args.read == len(record['acknowledged_chunks'])
    for index in range(args.read, min(args.read + args.count, len(chunks))):
        chunk = chunks[index]
        print(json.dumps({'chunk': index, 'total': len(chunks),
            **{k: v for k, v in chunk.items() if k != 'text'}}))
        print(chunk['text'], end='')
else:
    print(json.dumps({'acknowledged': len(record['acknowledged_chunks']),
        'total': len(chunks), 'complete': record['complete']}))
