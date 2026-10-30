"""Read-only source accounting for workload577; stdlib, no application imports."""
raise SystemExit('Historical direction/plan manifest generator retired; no grader uses its Markdown as a runtime specification.')
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ITEMS = []


def record(path, scope, kind):
    data = (ROOT / path).read_bytes()
    ITEMS.append(dict(path=path, inspection_scope=scope, kind=kind,
                      bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))


for name in """
infernal_search_grader.py infernal_search_inputs.py rfam_batch_grader.py
rfam_batch_report_grader.py rfam_batch_table_grader.py rfam_batch_contracts.py
rfam_batch_inputs.py rfam_batch_report.py rfam_batch_report_contracts.py
rfam_batch_table.py rfam_batch_views.py rfam_batch_table_views.py
rfam_batch_report_views.py rfam_batch_publication.py rfam_batch_returns.py
rfam_batch_alignment.py infernal_native_result_views.py
infernal_result_presentation.py native_infernal_result_publication.py
native_infernal_result_worker.py native_infernal_returns.py
native_infernal_results.py api_rfam.py rna_evidence.py
""".split():
    record('gene_annotation_episode/' + name, 'complete module', 'implementation_source')

for name, scope in {
    'tools.py': 'complete _publish_cmsearch function; relevant native-artifact helper and caller contexts',
    'state.py': 'cmsearch observation/native-result validation branch around lines1090-1178',
    'domain.py': 'complete CMSEARCH_MATCH declaration around lines216-243',
    'execution_progress.py': 'complete local Rfam extractor branch around lines798-863',
}.items():
    record('gene_annotation_episode/' + name, scope, 'consumer_context')

for name, scope in {
    'test_rfam_batch_grader.py': 'complete module',
    'test_rfam_saved_live_replay.py': 'complete module',
    'test_rfam_batch_inputs.py': 'lines1-86 and named native-field/identity cases',
    'test_rfam_batch_table.py': 'lines1-152 and native fixture references',
    'test_rfam_batch_report.py': 'lines1-135 and additional case names/source examples',
    'test_rfam_batch_table_views.py': 'saved numerical projection/identity cases',
}.items():
    record('tests/' + name, scope, 'existing_test_source_not_executed')

for path in [
    'verification/tool_graders_rfam_contract_2026-10-26_232/examples/official-single-result.json',
    'verification/tool_graders_rfam_contract_2026-10-26_232/examples/single-input-identity.json',
    'verification/tool_graders_rfam_transport_2026-10-26_234/live/multi/004-fetch-tblout/response.body',
    'verification/tool_graders_rfam_transport_2026-10-26_234/live/multi/005-fetch-out/response.body',
]:
    record(path, 'complete retained source artifact', 'retained_fixture')

for name in ['cmsearch_fmt3.hits.tbl', 'cmscan_fmt3.hits.tbl',
             'cmsearch_no_hits.hits.tbl', 'cmsearch_hmmonly.hits.tbl', 'PROVENANCE.md']:
    record('tests/fixtures/infernal_search_graders/' + name,
           'complete retained fixture/provenance', 'retained_fixture')

for path in [
    'tests/fixtures/native_infernal_result_worker/PROVENANCE.md',
    'tests/fixtures/native_infernal_publication/PROVENANCE.md',
    'verification/tool_graders_rfam_report_2026-10-26_242/HANDOFF.md',
    'verification/tool_graders_infernal_search_2026-10-26_219/WORKLOAD_001.md',
    'verification/tool_graders_infernal_search_2026-10-26_219/NATIVE_FINDINGS_AND_CELL_MEANINGS.md',
]:
    record(path, 'complete document', 'historical_implementation_evidence_not_goal_authority')

record('AGENTS.md', 'complete instruction file', 'instructions')
record('docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md',
       'complete direction record; current supplied goal supersedes historical sheet-per-tool language',
       'instructions')
goal = Path('/home/chia/.codex/attachments/6960b4a1-b2e0-46d4-8003-fcb7685a2232/pasted-text-1.txt')
manifest = dict(
    version='rfam_shared_scoring_boundary_review_v1',
    status='read_only_plan_no_implementation',
    goal_source=str(goal), goal_sha256=hashlib.sha256(goal.read_bytes()).hexdigest(),
    source_items=ITEMS,
    actions=dict(scientific_executions=0, network_requests=0, application_imports=0,
                 test_runs=0, production_edits=0),
    limitations=[
        'Existing test source was inspected as specified; tests were not run.',
        'No assertion of complete historical-test review or unrelated execution-module review.',
        'No new native or live-service result was produced.',
    ],
)
handoff = (OUT / 'HANDOFF.md').read_text()
missing = []
for name in ['rfam_batch_contracts.py', 'rfam_batch_report_contracts.py']:
    tree = ast.parse((ROOT / 'gene_annotation_episode' / name).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in {
                'RFAM_HIT_METRICS', 'RFAM_QUERY_STRAND_METRICS',
                'RFAM_TABLE_HIT_METRICS', 'RFAM_REPORT_HIT_METRICS',
            } for t in node.targets
        ):
            missing.extend(n.value for n in ast.walk(node.value)
                           if isinstance(n, ast.Constant) and isinstance(n.value, str)
                           and n.value not in handoff)
manifest['handoff_check'] = dict(
    all_declared_old_rfam_metric_names_documented=not missing,
    missing_metric_names=missing,
    meaning='static name coverage only; not implementation or numerical verification',
)
(OUT / 'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(dict(source_items=len(ITEMS), handoff_lines=len(handoff.splitlines()),
                      **manifest['handoff_check']), indent=2))
if missing:
    raise RuntimeError('missing metric mapping')
