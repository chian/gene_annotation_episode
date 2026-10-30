"""Record actual current outputs and reads, without rerunning sealed writers."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
GOAL=Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,value):
    with (OUT/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')


assert digest(GOAL)=='ba5d7d751400cb8faeeda23ea7bbc8c177ec94e6b83ba4797a805b001f73d70e'
assert not (ROOT/'GOAL.md').exists()
authority=[
    'AGENTS.md','research/experimental_scoring_review_2026-10-23/AGENTS.md',
    'docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md','docs/TOOL_KNOWLEDGE.md',
    'docs/TASK_AND_STEERING.md','docs/AMENDMENTS/TASK_AND_STEERING_2026-10-23_001.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_REVIEW_2026-10-23_001.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_DIRECTION.md',
    'research/slotted_process_library/publications/2026-10-23-002/VERBATIM_RECOVERY_002.md',
    'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
    'verification/a105_three_parts_review_2026-10-23_001/scoring_sheet_numeric_review_002.md',
    'research/experimental_scoring_review_2026-10-23/a105_complete_deliverable_022/A105_NUMERICAL_SCORING_SHEET_001.md',
    'gene_annotation_episode/literature_optical_inputs.py','gene_annotation_episode/literature_optical_calculations.py',
    'gene_annotation_episode/literature_optical_validation.py','gene_annotation_episode/literature_experimental_contracts.py',
    'gene_annotation_episode/literature_rate_reader.py','gene_annotation_episode/literature_rate_calculations.py',
]
save('POST_PAPER_RESET_PROVENANCE.json',dict(
    meaning='Hash capture after actual displayed reads, not fabricated per-read timing; not a runtime gate',
    utc=datetime.now(timezone.utc).isoformat(),fixed_pasted_goal_sha256=digest(GOAL),
    paper_text_ranges_actually_read=[[1,160],[161,300],[301,403]],
    complete_post_paper_reads={name:digest(ROOT/name) for name in authority},
    additional_read='SOURCE_CORRECTIONS.md complete before reset; literature_assay_inputs.py lines90-280 for complete selected _Sources/helpers',
    latest_actual_user_instructions_read_last='Current conversation: fixed goal; delete GOAL.md/conflicts; ordinary statistics allowed; computational-biology suites exceptional; families differ from assay graders; overlapping assays retain value',
    historical_scope_excluded='Old A105 proposal target-correspondence/candidate/W05 sections were read as historical proposals, not adopted or implemented',
    root_GOAL_absent=True))
files=[ROOT/'gene_annotation_episode/literature_rate_bound_calculations.py',
       ROOT/'tests/test_literature_rate_bound_calculations.py',ROOT/'tests/test_literature_coupled_redox_primary.py']
files.extend(sorted(path for path in OUT.rglob('*') if path.is_file()))
save('CURRENT_MANIFEST.json',dict(files={str(path.relative_to(ROOT)):digest(path) for path in files},
    final_case_data='generation_002',initial_top_level_outputs='historical pre-projection repair'))
save('VERIFICATION.json',dict(
    actual_test_command='PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/test_literature_coupled_redox_primary.py tests/test_literature_rate_bound_calculations.py tests/test_literature_rate_reader.py tests/test_literature_rate_calculations.py tests/test_literature_rate_replicates.py',
    actual_completed_exec_session=88854,exit_code=0,passed=192,reported_seconds=1.19,
    actual_primary_run='read_and_populate.py generation_002',primary_run_exit_code=0,
    reported_rate_values=21,source_measurement_rows=20,assay_readouts=3,within_endpoint_comparisons=7,
    optical_reported_epsilon=6.2,raw_trace_rate=None,calibration_recovery=None,sampling_count=None,
    new_completed_assay_specific_graders=0,computational_biology_suites_executed=0,
    model_calls_for_this_case=0,native_episode_executed=False,typed_return_executed=False,
    controller_observations_added=0,full_fixed_goal_complete=False))
print('Case093 final generation002 and actual192-test receipt sealed; fixed goal unchanged and GOAL.md absent.')
