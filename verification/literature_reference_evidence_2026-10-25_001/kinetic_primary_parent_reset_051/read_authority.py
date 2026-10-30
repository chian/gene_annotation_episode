"""Parent-owned post-packet reset. Acknowledge only fully observed chunks."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ACTIVE = Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
BASE = ROOT / 'verification/literature_reference_evidence_2026-10-25_001'
PATHS = [
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
]
FILES = [ACTIVE, *(ROOT / p for p in PATHS), ACTIVE,
    BASE / 'LATEST_HUMAN_DIRECTION_PARENT_039.txt',
    BASE / 'LITERATURE_GRADER_SELECTION_TARGET_040.md']

chunks, entries = [], []
for path in FILES:
    raw = path.read_bytes()
    lines = raw.decode().splitlines(keepends=True)
    entries.append({'path': str(path), 'bytes': len(raw),
        'sha256': hashlib.sha256(raw).hexdigest(), 'lines': len(lines)})
    buffer, start = '', 1
    for index, line in enumerate(lines, 1):
        if len((buffer + line).encode()) > 15000 and buffer:
            chunks.append({'path': str(path), 'start_line': start,
                'end_line': index - 1, 'text': buffer})
            buffer, start = '', index
        buffer += line
    if buffer:
        chunks.append({'path': str(path), 'start_line': start,
            'end_line': len(lines), 'text': buffer})

parser = argparse.ArgumentParser()
parser.add_argument('--read', type=int)
parser.add_argument('--count', type=int, default=1)
parser.add_argument('--ack', type=int, action='append')
args = parser.parse_args()
receipt = OUT / 'READ_RECEIPT.json'
record = json.loads(receipt.read_text()) if receipt.exists() else {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'documents': entries, 'chunks_total': len(chunks),
    'acknowledged_chunks': [], 'complete': False,
    'packet_read': 'Parent fully read051 PROPOSAL_001.md as one paper-specific retained038 CysQ case plan. No new original article, table image, supplement or raw fit data was read by parent. Complete own fresh authority/current-sheet/kinetic-contract reset precedes scientific adjudication and harness release.',
    'scientific_component_interpretation_before_reset': False,
}
assert record['documents'] == entries
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
