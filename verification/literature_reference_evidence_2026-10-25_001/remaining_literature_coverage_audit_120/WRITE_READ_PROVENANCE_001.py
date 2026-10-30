import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
report = HERE/'REPORT_001.md'
report.write_text(report.read_text().replace('read_native_partner_inputs', 'read_partner_native_inputs'))
full = [
 'AGENTS.md',
 'docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md',
 'research/experimental_scoring_review_2026-10-23/AGENTS.md',
 *['gene_annotation_episode/'+p+'.py' for p in (
 'literature_context_inputs','literature_context_calculations','literature_context_storage','literature_context_prompt',
 'literature_reaction_inputs','literature_reaction_calculations','literature_reaction_storage','literature_reaction_prompt',
 'literature_partner_inputs','literature_partner_calculations','literature_partner_storage','literature_partner_prompt',
 'literature_partner_native_inputs','literature_partner_defined_units','literature_partner_source_fields','literature_partner_operand_information')],
 'tests/test_literature_partner_native_inputs.py',
 'tests/test_literature_context_integration.py',
 'tests/test_literature_reaction_integration.py',
 'tests/test_literature_partner_integration.py',
]
partial = {
 'gene_annotation_episode/literature_rate_storage.py': [[1,154],[404,434],[570,793]],
 'gene_annotation_episode/literature_episodes.py': [[1,758],[921,1280]],
 'gene_annotation_episode/episode_services.py': [[1,100],[184,233]],
 'gene_annotation_episode/literature_experimental_prompt.py': [[290,355],[390,485],[532,565],[847,902]],
 'tests/test_literature_partner_native_storage.py': [[1,142]],
 'tests/test_literature_context_storage.py': [[1,110]],
 'tests/test_literature_reaction_storage.py': [[1,85]],
}
goal = Path('/home/chia/.codex/attachments/ccb637ea-d3ca-4bc5-a5e0-7fbf53192c54/pasted-text-1.txt')
def row(path):
 p = Path(path)
 if not p.is_absolute(): p=ROOT/p
 raw=p.read_bytes()
 return {'path': str(p),'sha256_at_finalization':hashlib.sha256(raw).hexdigest(),'lines_at_finalization':len(raw.splitlines())}
provenance={
 'agent':'/root/remaining_literature_coverage_audit_120',
 'finalized_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Bounded engineering source/test audit of A108, A110 and experimental partners; no production changes.',
 'fixed_goal':{**row(goal),'fully_read':True,'expected_sha256':'ba5d7d751400cb8faeeda23ea7bbc8c177ec94e6b83ba4797a805b001f73d70e'},
 'full_reads':[row(p) for p in full],
 'partial_reads':[{**row(p),'read_line_ranges':ranges} for p,ranges in partial.items()],
 'provenance_qualifications':[
 'Full-read entries were read in untruncated chunks; truncated calls were repaired by narrower reads.',
 'Partial entries identify relevant complete methods/sections, not a claim to have read the entire file.',
 'Line ranges document inspected source during this workload. Current hashes were captured at finalization; shared integration files may be edited concurrently, so fingerprints are not an atomic historical read snapshot.',
 'Source-specific labels in integration test code were examined as engineering assertions only. No original primary source or retained paper-specific packet was opened or run.',
 'No independent scientific validation of primary assertions and no actual model-backed literature execution occurred in this workload.',
 'Constructed counterexample uses the existing synthetic native fixture and a new isolated Store beneath the exclusive audit directory.',
 'No GOAL.md read or modification, new amendment, production/test edit, old receipt/pin edit, model call or live DB write.',
 'A shell probe with python failed because that alias was absent; subsequent probes used .venv/bin/python. Collection only successfully listed27integration tests.',
 ],
 'test_receipt':'CONSTRUCTED_CHECKS_001.json',
 'counterexample_receipt':'CONSTRUCTED_MEANING_PROBE_001.json',
}
assert provenance['fixed_goal']['sha256_at_finalization']==provenance['fixed_goal']['expected_sha256']
(HERE/'READ_PROVENANCE_001.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps({'goal_hash_verified':True,'complete_files':len(full),'partial_files':len(partial)},indent=2))
