"""Apply only the reviewed delta after direct component/package/loop checks."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / 'candidate_003'
CHECK = ROOT / 'verification/tool_graders_fastqutils_combined_verification_2026-10-26_217'
FLOW = ROOT / 'verification/tool_graders_bvbrc_fastqutils_episode_path_2026-10-25_202/final_208_001'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def passed(path, count):
    cases = list(ET.parse(path).iter('testcase'))
    assert len(cases) == count
    assert all(c.find(k) is None for c in cases for k in ('failure', 'error', 'skipped'))


if __name__ == '__main__':
    assert not (HERE / 'PRODUCTION_APPLICATION_001.json').exists()
    plan = read(HERE / 'APPLICATION_PLAN_001.json')
    manifest = read(HERE / 'combined_source_before_003.json')
    assert plan['source_manifest_sha256'] == sha(HERE / 'combined_source_before_003.json')
    assert manifest == read(CHECK / 'source_before.json') == read(CHECK / 'source_after_suite.json')
    suite, package, workflow = (read(path) for path in (
        CHECK / 'suite_receipt.json', CHECK / 'package_verification_001/receipt.json', FLOW / 'receipt.json'))
    assert suite['passed'] and suite['exit_code'] == 0 and not suite['deselections']
    assert suite['test_files'] == 20 and not any(suite['changed'].values())
    assert package['passed'] and package['dependency_count'] == 36
    assert not any(package['changed'].values()) and package['forbidden_call_count'] == 0
    assert sha(Path(package['wheel_path'])) == package['wheel_sha256']
    assert workflow['exit_code'] == 0 and not workflow['frozen_source_changes']
    assert not workflow['dependency_changes'] and not workflow['supplementary_input_changes']
    passed(CHECK / 'suite_results.xml', 562)
    passed(FLOW / 'junit.xml', 14)
    for filename, expected in manifest.items():
        assert sha(CANDIDATE / filename) == expected, filename
        assert sha(CHECK / 'candidate' / filename) == expected, filename
    # The five runtime integration modules are exactly the tested208 path.
    # pyproject adds the new schema package asset and is verified by217's wheel.
    for filename in plan['shared_existing_paths']:
        if filename != 'pyproject.toml':
            assert (FLOW / 'source' / filename).read_bytes() == (CANDIDATE / filename).read_bytes(), filename
    for item in plan['files']:
        target = ROOT / item['path']
        current = sha(target) if target.exists() else None
        assert current == item['before_sha256'], ('concurrent_edit', item['path'])
        assert sha(CANDIDATE / item['path']) == item['after_sha256'], item['path']
    started = datetime.now(timezone.utc).isoformat()
    for item in plan['files']:
        target = ROOT / item['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((CANDIDATE / item['path']).read_bytes())
    assert all(sha(ROOT / item['path']) == item['after_sha256'] for item in plan['files'])
    evidence_paths = [CHECK / 'suite_receipt.json', CHECK / 'suite_results.xml',
        CHECK / 'package_verification_001/receipt.json', FLOW / 'receipt.json', FLOW / 'junit.xml']
    record = dict(status='applied_exact_tested_source_post_application_checks_pending',
        started_at=started, completed_at=datetime.now(timezone.utc).isoformat(),
        plan_sha256=sha(HERE / 'APPLICATION_PLAN_001.json'),
        source_manifest_sha256=plan['source_manifest_sha256'],
        changed_paths=len(plan['files']), applied_files=plan['files'],
        provider_pin=package['provider_pin'], production_changed=True,
        new_samstat_full_episode_verification='218_still_running_not_claimed',
        baseline_full_Workflow='202_frozen208_passed_actual_shared_loop_with_controlled_choices_and_transport',
        evidence=[dict(path=str(p.relative_to(ROOT)), sha256=sha(p)) for p in evidence_paths],
        live_service_verified=False, whole_goal_complete=False,
        method_loop_changed=False, annotation_score_changed=False,
        historical_records_changed=False)
    with (HERE / 'PRODUCTION_APPLICATION_001.json').open('x') as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(dict(applied=True, changed_paths=record['changed_paths'],
        provider_pin=record['provider_pin'], whole_goal_complete=False,
        new_samstat_full_episode_verification=record['new_samstat_full_episode_verification'])))
