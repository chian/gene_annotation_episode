"""Exact failure associations from retained native cases and explicit corruptions."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import validate_closed_schema, validate_form
from gene_annotation_episode.infernal_preparation_result_views import preparation_fact_sources
from gene_annotation_episode.native_infernal_preparation_failure_views import preparation_failure_facts


ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / ('verification/tool_graders_infernal_preparation_2026-10-26_247/'
    'workflow_remaining_003/temporary/pytest/test_partial_acquisition_retur1')


def retained():
    body = json.loads((CASE / 'CASE.json').read_text())['outcomes'][0]['result']
    digest = body['capture']['bundle_artifact_ref'].removeprefix('artifact_')
    bundle = json.loads((CASE / 'state/artifacts' / digest[:2] / digest).read_bytes())
    return body, bundle


def test_original_changed_stdout_has_exact_role_and_requested_closed_form(monkeypatch):
    body, bundle = retained()
    original = deepcopy(body)
    def forbidden(*args, **kwargs):
        raise AssertionError('Failure projection did new work')
    for target in ('builtins.open', 'socket.socket', 'subprocess.Popen',
            'gene_annotation_episode.native_infernal_preparation_worker.grade_infernal_preparation'):
        monkeypatch.setattr(target, forbidden)
    rows = preparation_failure_facts(body, bundle=bundle)
    mismatch = [r for r in rows if r['code'] == 'native_infernal_preparation_sealed_artifact_digest_mismatch']
    assert len(mismatch) == 1
    row, = mismatch
    assert row['affected'] == {'direction': 'output', 'role': 'stdout', 'ordinal': 0}
    assert row['stage'] == 'capture' and row['source_ref'] == body['source_ref']
    assert row['handoff_ref'] == body['assignment']['handoff_ref']
    schema = validate_closed_schema({'type': 'object', 'additionalProperties': False,
        'properties': {'failures': preparation_fact_sources()['execution_infernal_preparation_failures']['report_schema']},
        'required': ['failures']})
    assert validate_form({'failures': rows}, schema, lambda *_: True) == {'failures': rows}
    assert body == original


def test_unknown_error_prose_stays_out_of_failure_form_and_source_less_attempts_stay_distinct():
    body, _ = retained()
    body.update(source_ref=None, prepared=None, capture=None, failures=[
        {'stage': 'grading', 'code': 'Unexpected sentence with private path /somewhere.', 'record_key': None}])
    original = deepcopy(body)
    first, = preparation_failure_facts(body)
    assert first['code'] == 'native_infernal_preparation_unclassified_error'
    assert first['source_ref'] is None and first['affected'] is None
    assert body == original
    body['assignment']['handoff_ref'] = 'source_other_original_handoff'
    second, = preparation_failure_facts(body)
    assert first != second


def test_known_issue_stages_and_exact_failed_record_occurrence_are_preserved():
    body, bundle = retained()
    occurrence = body['prepared']['occurrences'][0]
    key = occurrence['occurrence_ref'] + '#key_request/0'
    body['failures'] = [{'stage': stage, 'code': 'artifact_key_request_unsatisfied', 'record_key': key}
        for stage in ('format', 'association', 'validation')]
    rows = preparation_failure_facts(body, bundle=bundle)
    assert [row['stage'] for row in rows] == ['format', 'association', 'validation']
    assert all(row['record_key'] == key and row['affected'] == {k: occurrence[k]
        for k in ('direction', 'role', 'ordinal')} for row in rows)


@pytest.mark.parametrize('corruption', ['role', 'ordinal', 'path'])
def test_capture_failure_cannot_claim_a_different_file(corruption):
    body, bundle = retained()
    problem = next(r for r in body['failures'] if 'sealed_artifact_digest_mismatch:' in r['code'])
    parts = problem['code'].split(':', 4)
    parts[{'role': 2, 'ordinal': 3, 'path': 4}[corruption]] = 'not_the_original'
    problem['code'] = ':'.join(parts)
    with pytest.raises(ValueError, match='failure_file_association_conflict'):
        preparation_failure_facts(body, bundle=bundle)
