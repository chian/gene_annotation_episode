"""Freeze actual repository/tests/runtime/assets; no scientific state copy."""
raise SystemExit("Historical note-governed artifact generator retired.")

from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[3]
output=Path(__file__).resolve().parent
pin=output/'pin_003'
paths=[]
for package in ('gene_annotation_episode','method_loop'):
 paths.extend(p for p in (root/package).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'))
paths.extend(root/'tests'/f'test_literature_ratio_source_{part}.py' for part in ('inputs','calculations','validation','storage','readonly'))
paths.append(root/'pyproject.toml')
for directory in ('visual_signal_parent_review_067/text_locator_declarations_008','a105_visual_signal_reader_070/normative'):
 paths.extend(p for p in (root/'verification/literature_reference_evidence_2026-10-25_001'/directory).rglob('*') if p.is_file() and p.suffix in ('.json','.md','.py'))
paths.extend(output/name for name in ('verify_joined_003.py','freeze_pin_003.py'))
paths.append(output/'ACTIVE_ATTACHMENT_003.txt')
paths.extend(root/name for name in ('AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md',
 'docs/TIME_AWARE_ESTIMATION.md','docs/TOOL_KNOWLEDGE.md','docs/TASK_AND_STEERING.md',
 'docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md',
 'docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md',
 'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
 'research/experimental_scoring_review_2026-10-23/AGENTS.md',
 'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md',
 'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md',
 'verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md'))
release=root/'verification/literature_reference_evidence_2026-10-25_001/visual_signal_parent_review_067'
paths.extend(release/name for name in ('NATIVE_REPOSITORY_RELEASE_071.md',
 'NATIVE_REPOSITORY_ORIGIN_ADDENDUM_071.md','PURE_IMPLEMENTATION_RELEASE_070.md',
 'SOURCE_TEXT_LOCATOR_ADDENDUM_008.md','CALCULATOR_IDENTITY_ADDENDUM_009.md'))
repair=root/'verification/literature_reference_evidence_2026-10-25_001/pure_reader_parent_review_070'
paths.extend(repair/name for name in ('DEPENDENCY_ORDER_REPAIR_RELEASE_074.md',
 'REPOSITORY_ROUNDTRIP_REPAIR_RELEASE_075.md','DEPENDENCY_ORDER_COUNTEREXAMPLE_001.json',
 'probe_dependency_order_001.py'))
paths=list(dict.fromkeys(paths))
def sha(data):return hashlib.sha256(data).hexdigest()
before={str(p.relative_to(root)):sha(p.read_bytes()) for p in paths}
if pin.exists():raise SystemExit('never overwrite frozen pin')
for p in paths:
 target=pin/p.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
after={str(p.relative_to(root)):sha(p.read_bytes()) for p in paths}
frozen={name:sha((pin/name).read_bytes()) for name in before}
result={'evidence_class':'code/assets only; no live/private database copied','file_count':len(paths),'before':before,'after':after,'frozen':frozen,'coherent':before==after==frozen}
(output/'PIN_MANIFEST_003.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['coherent']
print(json.dumps({'pin':str(pin),'files':len(paths),'coherent':True}))
