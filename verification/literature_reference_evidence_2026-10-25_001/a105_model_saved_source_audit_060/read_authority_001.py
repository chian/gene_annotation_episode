"""Own060 post-paper reset. Acknowledge only fully displayed bounded chunks."""
raise SystemExit("Historical agent-note reader retired.")

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ACTIVE = Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
PATHS = [
    'AGENTS.md', 'GOAL.md', 'docs/EPISODE_STRUCTURE.md', 'docs/TIME_AWARE_ESTIMATION.md',
    'docs/TOOL_KNOWLEDGE.md', 'docs/TASK_AND_STEERING.md',
    'docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
    'verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md',
    'research/experimental_scoring_review_2026-10-23/AGENTS.md',
    'research/experimental_scoring_review_2026-10-23/SOURCE_CORRECTIONS.md',
    'research/experimental_scoring_review_2026-10-23/a105_complete_deliverable_022/A105_NUMERICAL_SCORING_SHEET_001.md',
    'gene_annotation_episode/literature_experimental_contracts.py',
    'gene_annotation_episode/literature_rate_native_inputs.py',
    'gene_annotation_episode/literature_rate_calculations.py',
]
FILES = [ACTIVE, *(ROOT / p for p in PATHS), ACTIVE,
         BASE / 'LATEST_HUMAN_DIRECTION_PARENT_039.txt',
         BASE / 'A105_GRADER_COUNT_CLARIFICATION_040.md',
         BASE / 'LITERATURE_GRADER_SELECTION_TARGET_040.md',
         BASE / 'LATEST_HUMAN_DIRECTION_PARENT_041.txt', HERE / 'LATEST_HUMAN_060.txt']
documents, chunks = [], []
for path in FILES:
    raw = path.read_bytes()
    lines = raw.decode().splitlines(keepends=True)
    documents.append({'path': str(path), 'bytes': len(raw), 'lines': len(lines), 'sha256': hashlib.sha256(raw).hexdigest()})
    buffer, first = '', 1
    for index, line in enumerate(lines, 1):
        if len((buffer + line).encode()) > 9000 and buffer:
            chunks.append({'path': str(path), 'start': first, 'end': index - 1, 'text': buffer})
            buffer, first = '', index
        buffer += line
    if buffer:
        chunks.append({'path': str(path), 'start': first, 'end': len(lines), 'text': buffer})
parser = argparse.ArgumentParser()
parser.add_argument('--read', type=int)
parser.add_argument('--count', type=int, default=1)
parser.add_argument('--ack', action='append', type=int)
args = parser.parse_args()
receipt = HERE / 'RESET_READ_RECEIPT_001.json'
record = json.loads(receipt.read_bytes()) if receipt.exists() else {
    'created_utc': datetime.now(timezone.utc).isoformat(), 'documents': documents,
    'chunks_total': len(chunks), 'acknowledged_chunks': [], 'complete': False,
    'paper_read_before_reset': 'Own060 captured original030 selected decisions29/31 and their single source PMC2223550; fully read retained primary text403lines plus actual original HTML Table2 and all selected numerical/meaning/unit-definition witnesses. No other paper, figure pixels or supplement read.',
    'scientific_conversion_before_reset': False,
    'contract_scope': 'Full current696-line A105 proposal, complete current experimental contracts, native two-arm reader and rate calculator. Historical sheet transfer/pooling/candidate policies are not adopted.'}
assert record['documents'] == documents
for index in args.ack or []:
    assert index == len(record['acknowledged_chunks']) < len(chunks)
    record['acknowledged_chunks'].append({k:v for k,v in chunks[index].items() if k != 'text'})
record['complete'] = len(record['acknowledged_chunks']) == len(chunks)
receipt.write_text(json.dumps(record, indent=2) + '\n')
if args.read is not None:
    assert args.read == len(record['acknowledged_chunks'])
    for index in range(args.read, min(args.read + args.count, len(chunks))):
        chunk = chunks[index]
        print(json.dumps({'chunk': index, 'total': len(chunks), **{k:v for k,v in chunk.items() if k != 'text'}}))
        print(chunk['text'], end='')
else:
    print(json.dumps({'acknowledged': len(record['acknowledged_chunks']), 'total': len(chunks),
                      'bytes': sum(r['bytes'] for r in documents), 'complete': record['complete']}))
