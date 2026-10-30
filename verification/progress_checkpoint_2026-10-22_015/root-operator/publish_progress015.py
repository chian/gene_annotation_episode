"""Add a new permanent record; never rewrite an earlier checklist or note."""
from pathlib import Path
import hashlib
import json
import os
import re
import stat

ROOT = Path('/home/chia/repos/gene_annotation_episode')
RUN = Path('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001')
OUT = ROOT / 'verification/progress_checkpoint_2026-10-22_015'
DOC = ROOT / 'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_015.md'
PREVIOUS = ROOT / 'docs/AMENDMENTS/SLOT_CORRECTION_2026-10-22_014.md'


def sha(body):
    return hashlib.sha256(body).hexdigest()


def save(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o444)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


assert sha(PREVIOUS.read_bytes()) == 'e0376b08d6da1e853e1103a301b67e5e4bd3c392a5f83c76fc5de66bb5c90a59'
assert not OUT.exists() and not DOC.exists()
previous = PREVIOUS.read_text()
checklist = previous[previous.index('## Retained correction checklist'):previous.index('## Completed model-context repair')]
assert len(re.findall(r'^- \[[ x]\] \*\*', checklist, re.M)) == 41
baseline = json.loads((RUN / 'caller-inputs/INITIAL_BASELINE_SNAPSHOT001.json').read_text())
assert baseline['initial_completed_own_turns'] == 0 and baseline['selected_inherited_refs'] == 200
assert baseline['initial_scientific_progress'] == 12.0 and baseline['initial_monitoring_information_credit'] == 0.0
publication = json.loads(Path('/tmp/configured-api-caller-root-publication-check-20261022-001/VERIFICATION_FINAL001.json').read_text())
assert publication['status'] == 'passed'
assert publication['manifest_sha256'] == 'd402530d46239223f6dc1e59b81169d4da1a623e5b66c1126c9532bfde08c8b4'

body = '''# Separate permanent progress record015

This additive record follows unchanged014, SHA256 e0376b08d6da1e853e1103a301b67e5e4bd3c392a5f83c76fc5de66bb5c90a59. The same41 IDs, order, checked states and historical descriptions follow verbatim. Later evidence is recorded after them. No whole-goal item is closed by this increment.

''' + checklist + '''## Completed006 engineering and publication

The final frozen implementation is /tmp/gene-annotation-configured-caller-20261022-006:136 runtime files,218 tests, source pin209ff0d8ca80a6ee2a592f997933115e2f688f8ccc90e6db35e40146dabb613f. All348 previous source/test files,319 assets and eight normative inputs retain their original bytes. The only two added runtime modules are scientific_checkpoint_fork.py166d459b38295ab4003ebe39babd22184a96482dba5146b3b2479291ebd423ab and api_planning_case_policy.py4474422fa09ac5247b1957e7d1bce4a57ac811f39f1cc9356666a7c4d4ea276f. No original implementation file was changed.

The [engineering report](../CONFIGURED_API_CALLER_VERIFICATION_2026-10-22_001.md), SHA256 ea5a0189636307b67182f22a759d7567356ff625a8fa8d36621b0396ef029702, points to the permanent5538-file capsule. Its manifest is d402530d46239223f6dc1e59b81169d4da1a623e5b66c1126c9532bfde08c8b4. Root independently ran the fully read byte/membership/mode/source/baseline/copy-control/XML checker:5537 members plus manifest,156738399 member bytes,1486 directories,37 internal aliases and5532 unchanged original copy controls. No application, database or test was run by this publication checker.

Evidence stays separated by actual source version: P57 component cases; R8 caller-only cases at the135-file pin; historical C56 at cce993/d115; two reproduced late C failures; corrected C5 affected cases at the final pin; one first joined fixture failure and one corrected passing joined node; and the final136 detached-worker repetition of an already counted R node. These are not additive unique coverage. The late C fix refuses unequal final source database/sidecar witnesses instead of publishing source_files_equal:true. The joined fixture correction supplied the actual complete provider connection/routing configuration. Original failures, fixture revisions, source pins and raw-custody limits remain explicit. All these engineering checks use scripted/synthetic fixtures rather than configured-model science.

## Actual custody, preparation and configured launch

Root separately used [actual scope001](../CONFIGURED_API_CALLER_ACTUAL_SCOPE_2026-10-22_001.md). The actual stopped source configured_development_002 remains under its original implementation and pending-request hashes. C published a NEW workspace at /home/chia/gene_annotation_episode_runs/configured_api_prechoice_001/workspace. Actual receipt0badb45cb17c60648891ff5b2cff7ea6f0b6b567148483b28a5685e3cc572167 records the exact immutable checkpoint21922c544ebc17da977f7c0e064c8d95cd290efa3e6ba48c58d67be69069f4d8,211947520bytes, and truthful historical working-publication hash. Original179actions,175observations,180model-call rows and pending request remain unchanged. No original Store or old run was resumed.

The actual200-reference inherited selection contains193 committed input/record IDs, four resolvable original artifacts, one original material member and two newly registered lineage sources. Independent review verified all144 old artifact files/4201310bytes, nine authority copies,175 exact raw observation rows and index, four native receipts, and preserved revisions. The24 revision records are13 assessments and11 annotations; the13 current-revision keys are12 assessments and one annotation. They must not be described as24 annotation revisions. This review opened only the NEW immutable checkpoint through two explicitly closed readonly/query_only connections; it opened neither the original nor active working database. Its sealed manifest is8fac89adb1f7279e05fb5a47b4dbe1ab2a3e9143521cb0f6c416297cdfa0dcd4.

Actual prepare_case_run completed with zero model/native jobs, fresh native registry execution_registry_ecee82cc3ead4f79a5e087e8fbc7bfe7 and empty orders/handoffs/samples. The actual client descriptor matched7c3113045c9b8bd9d0613e12a5fd16eddbddb06fcb6b748b75f68d51dc1f2eb9 without HTTP. The reviewed parameter derivation filled only the200-reference inherited list and actual fresh registry ID. Static scientific/controller/monitoring operands, FAST luna/none, REASONING sol/medium,20GiB RAM,4GiB scratch, null wall time and HTTP90 remain unchanged. The exact config/focus/parameters/derivation/launch command are preserved in this record's capsule.

The ordinary new configured-model run started as run_23b029a976e343e2bf3957dcc5d0d2ac, root episode episode_3f296d8c6dbd96a740157d29eceda747dd4cc7b19d97b4763735999fe99b1979, with final source pin209ff0d8ca80a6ee2a592f997933115e2f688f8ccc90e6db35e40146dabb613f. It uses the actual connection, without --resume or a transport shim. Its saved first model presentation has268812 input characters. Its initial scientific progress is12, monitoring information is0, own completed turns0 and controller scores[]. Old175 observations were not imported into its local estimator. This is actual configured execution, not evidence yet of useful child influence or complete scientific behavior.

The initial receipt index contains339 dependency-expanded references. It includes all193 committed references, all four old native receipts and199 of200 explicitly selected references. The remaining member_e3d5ca64bb22d80dade693b1 is intentionally served through the existing paged collection-member interface; its collection/material/source parents are initially received. An early operator assertion incorrectly required every selected member in runtime_record_receipts and failed before writing a proof. The corrected snapshot records this existing distinction; no runtime change was made and no200-receipt claim is made.

The first three actual decisions selected source.xlsx.sheets on a JSON caller inventory and failed with xlsx_source_or_selection_invalid/BadZipFile/File is not a zip file. These were three distinct selected native XLSX worker attempts, not phmmer work or an automatic retry. Each exact failure reached the next model-facing context; both source.read and explicitly XLSX schemas were present. The episode then chose source.read successfully. Failed actions had NULL credit and no completed own observations. P's read-only trace found no proven feedback, presentation or catalog omission and proposed no code change. These attempts are operational evidence, not scientific progress. The fixed initial snapshot records nine selected action rows, six own observations and no commissions at its capture; subsequent live state can differ.

## Remaining goal work and human choices

The same three human decisions remain unresolved: support/scoring adoption after reviewing concrete evidence routes and current arithmetic; the wait-forecast horizon and compatible numerical model; and the intended actual HPC environment. A request for the HPC host/service/scheduler/instructions has been resurfaced while independent work continues. No answer, numerical law, support entry or environment is inferred. Active scientific library remains A0/P19, with variable actual-tool retrieval. Literature retains its separate existing hierarchy.

Actual useful scientific child receipt and subsequent parent decisions, composed scientific children, pending-aware numerical continuation, intended HPC execution, configured nested literature/monitoring and complete connected scientific/lifecycle evidence remain open. The new run continues under its own controller; this record introduces no itinerary, turn cap, cadence, retry, cancellation or supervisor. The immutable overall goal remains active and incomplete. The permanent [progress capsule](../../verification/progress_checkpoint_2026-10-22_015/MANIFEST.json) preserves this note and exact selected evidence; earlier notes and publications remain unchanged.
'''
assert body[body.index('## Retained correction checklist'):body.index('## Completed006 engineering')] == checklist
OUT.mkdir(mode=0o700)
copies = {}


def copy(source, relative):
    source = Path(source)
    assert source.is_file() and not source.is_symlink()
    before = source.stat()
    raw = source.read_bytes()
    save(OUT / relative, raw)
    after = source.stat()
    assert (before.st_size, before.st_mtime_ns, stat.S_IMODE(before.st_mode)) == (after.st_size, after.st_mtime_ns, stat.S_IMODE(after.st_mode))
    assert source.read_bytes() == raw
    copies[relative] = {'source': str(source), 'bytes': len(raw), 'sha256': sha(raw),
                        'source_mode': f'{stat.S_IMODE(before.st_mode):04o}',
                        'source_mtime_ns': before.st_mtime_ns, 'source_unchanged': True}


for path in sorted((RUN / 'caller-inputs').iterdir()):
    if path.is_file():
        copy(path, 'actual-caller-inputs/' + path.name)
for name in ('case-launch.json', 'policy-binding.json', 'episode-execution-binding.json', 'run.json'):
    copy(RUN / name, 'actual-run-binding/' + name)
copy(RUN / 'workspace/scientific-checkpoint-fork.json', 'actual-custody-receipt.json')
copy(ROOT / 'docs/CONFIGURED_API_CALLER_ACTUAL_SCOPE_2026-10-22_001.md', 'ACTUAL_SCOPE001.md')
for name in ('derive_parameters003.py', 'DERIVER_REVISION003.json', 'prepare_actual_custody001.py',
             'capture_initial_baseline001.py', 'publish_progress015.py',
             'actual_custody001.stdout.log', 'actual_custody001.stderr.log'):
    copy(Path(__file__).parent / name, 'root-operator/' + name)
for path in sorted(Path('/tmp/configured-api-caller-root-publication-check-20261022-001').iterdir()):
    if path.is_file():
        copy(path, 'engineering-publication-check/' + path.name)
for directory, prefix in (
    ('/tmp/actual-checkpoint-custody-review-20261022-b5de4mvi', 'independent-actual-custody'),
    ('/tmp/configured-api-caller-p-launch-readiness-ov314yc_', 'caller-launch-readiness'),
    ('/tmp/configured-api-live-failure-p-trace-md8fj14q', 'actual-failure-feedback-trace'),
):
    for path in sorted(Path(directory).rglob('*')):
        if path.is_file() and not path.is_symlink():
            copy(path, prefix + '/' + path.relative_to(directory).as_posix())
save(OUT / 'EXTERNAL_REFERENCES.json', json_bytes({
    'previous_record': {'path': str(PREVIOUS), 'sha256': sha(PREVIOUS.read_bytes())},
    'engineering_manifest': {'path': str(ROOT / 'verification/configured_api_caller_2026-10-22_001/MANIFEST.json'), 'sha256': 'd402530d46239223f6dc1e59b81169d4da1a623e5b66c1126c9532bfde08c8b4'},
    'engineering_report': {'path': str(ROOT / 'docs/CONFIGURED_API_CALLER_VERIFICATION_2026-10-22_001.md'), 'sha256': 'ea5a0189636307b67182f22a759d7567356ff625a8fa8d36621b0396ef029702'},
    'immutable_goal': {'path': '/home/chia/.codex/attachments/6c61440f-d223-4bea-91e3-6e4f7b2c5013/pasted-text-1.txt', 'sha256': '3a5d965c4dc76f6be6bf6c509d019eeabfff854b009f31c40e98de4ff73f096f'},
    'actual_working_workspace': str(RUN / 'workspace'),
    'actual_state_extent': 'Selected immutable initial inputs/bindings and public proof only. No live DB, checkpoint DB, runtime stderr/stdout or private provider events are copied.'}))
save(OUT / 'COPY_CONTROLS.json', json_bytes(copies))
save(DOC, body.encode())
save(OUT / 'PROGRESS.md', body.encode())
members = {}
for path in sorted(OUT.rglob('*')):
    if path.is_file():
        raw = path.read_bytes()
        members[path.relative_to(OUT).as_posix()] = {'sha256': sha(raw), 'bytes': len(raw), 'mode': '0444'}
manifest = {'version': 'permanent_progress_checkpoint_v1', 'members': members,
            'report_path': str(DOC), 'report_sha256': sha(body.encode()),
            'fixed41_same_ids_order_states_descriptions_verbatim': True,
            'goal_status': 'active_incomplete', 'old_records_replaced': 0,
            'live_databases_or_private_provider_events_copied': 0}
save(OUT / 'MANIFEST.json', json_bytes(manifest))
for path in sorted((p for p in OUT.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
    path.chmod(0o555)
OUT.chmod(0o555)
for rel, expected in members.items():
    raw = (OUT / rel).read_bytes()
    assert sha(raw) == expected['sha256'] and len(raw) == expected['bytes']
assert PREVIOUS.read_text() == previous
assert DOC.read_bytes() == (OUT / 'PROGRESS.md').read_bytes()
print(json.dumps({'record': str(DOC), 'record_sha256': sha(DOC.read_bytes()),
                  'capsule': str(OUT), 'manifest_sha256': sha((OUT / 'MANIFEST.json').read_bytes()),
                  'member_files': len(members), 'fixed41_verbatim': True,
                  'actual_run_id': baseline['run_id'], 'goal_status': 'active_incomplete'}, sort_keys=True))
