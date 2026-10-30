"""Fresh parent post-paper reset; acknowledge only completely displayed chunks."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = OUT.parent
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
    'gene_annotation_episode/literature_binding_interaction_inputs.py',
    'verification/literature_reference_evidence_2026-10-25_001/a105_binding_native_design_052/RESULT_CONTRACT_003.md',
    'verification/literature_reference_evidence_2026-10-25_001/a105_binding_native_design_052/RESULT_CONTRACT_INTEGRATION_005.md',
]
FILES = [ACTIVE, *(ROOT / name for name in PATHS), ACTIVE,
    BASE / 'LATEST_HUMAN_DIRECTION_PARENT_039.txt',
    BASE / 'A105_GRADER_COUNT_CLARIFICATION_040.md',
    BASE / 'LITERATURE_GRADER_SELECTION_TARGET_040.md',
    BASE / 'LATEST_HUMAN_DIRECTION_PARENT_041.txt']
documents, chunks = [], []
for path in FILES:
    raw = path.read_bytes()
    lines = raw.decode().splitlines(keepends=True)
    documents.append({'path': str(path), 'bytes': len(raw), 'lines': len(lines),
                      'sha256': hashlib.sha256(raw).hexdigest()})
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
path = OUT / 'READ_RECEIPT.json'
record = json.loads(path.read_bytes()) if path.exists() else {
    'created_utc': datetime.now(timezone.utc).isoformat(), 'documents': documents,
    'chunks_total': len(chunks), 'acknowledged_chunks': [], 'complete': False,
    'paper_read_before_reset': 'Root fully read retained042 primary_text409lines and Table3 actual JPEG via view_image; full058sealed proposal/provenance/build_proposal and expected numerical packet, plus042provenance. One combined display truncated and affected primary281–409/proposal96–end were reread fully. No supplementary images/raw curves or other paper examined.',
    'scientific_conversion_before_reset': False,
    'contract_scope': 'Current696-line sheet, complete native003 source-reader contract/code, experimental contracts, full003 and005 declared result interfaces. Other previously read frozen calculators/storage/visual implementations are not claimed reread by this reset.'}
assert record['documents'] == documents
for index in args.ack or []:
    assert index == len(record['acknowledged_chunks']) < len(chunks)
    record['acknowledged_chunks'].append({k: v for k, v in chunks[index].items() if k != 'text'})
record['complete'] = len(record['acknowledged_chunks']) == len(chunks)
path.write_text(json.dumps(record, indent=2) + '\n')
if args.read is not None:
    assert args.read == len(record['acknowledged_chunks'])
    for index in range(args.read, min(args.read + args.count, len(chunks))):
        chunk = chunks[index]
        print(json.dumps({'chunk': index, 'total': len(chunks), **{k: v for k, v in chunk.items() if k != 'text'}}))
        print(chunk['text'], end='')
else:
    print(json.dumps({'acknowledged': len(record['acknowledged_chunks']),
                      'total': len(chunks), 'bytes': sum(r['bytes'] for r in documents), 'complete': record['complete']}))
