"""Replay the exact rejected A105 parent frame through current presentation.

Run through tools/one_workflow.sh. This calls the provider's presentation method
only: no provider process, model request, source read or scientific action.
"""
import argparse
from collections.abc import Mapping
from copy import deepcopy
from functools import cache
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.decision_context import state_frame
from gene_annotation_episode.literature_work_report import completed_work
from gene_annotation_episode.providers import _SessionConnection


FIXTURE = Path(__file__).parent / 'fixtures/work_reports/a105-parent-input-too-large.json.gz'
WORK_RECEIPTS = Path(__file__).parent / 'fixtures/work_reports/a105-parent-completed-work-receipts.json.gz'


@cache
def retained_input():
    return json.loads(gzip.decompress(FIXTURE.read_bytes()))


@cache
def retained_work_receipts():
    return json.loads(gzip.decompress(WORK_RECEIPTS.read_bytes()))


def recomputed_completed_work():
    """Read the actual parent receipts through the current production projector."""
    receipts = retained_work_receipts()
    with sqlite3.connect(':memory:') as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA temp_store=MEMORY')
        for table in ('runtime_actions', 'runtime_observations', 'runtime_report_attempts'):
            db.execute(receipts['schemas'][table])
            for row in receipts['tables'][table]:
                columns = ','.join(row)
                parameters = ','.join('?' for _ in row)
                db.execute(f'INSERT INTO {table} ({columns}) VALUES ({parameters})', tuple(row.values()))
        db.commit()
        db.execute('PRAGMA query_only=ON')
        original_changes = db.total_changes
        rows = completed_work(SimpleNamespace(db=db), SimpleNamespace(
            run_id=receipts['run_id'], episode_id=receipts['episode_id']))
        assert db.total_changes == original_changes
        return rows


def replay_input(trace=None, *, refresh_completed_work=True):
    """Present the retained state with only its parent-work projection refreshed."""
    trace = retained_input() if trace is None else trace
    state = deepcopy(trace['state'])
    if refresh_completed_work:
        state['literature_completed_work'] = recomputed_completed_work()
        context = state_frame(state)
    else:
        context = deepcopy(trace['context'])
    before = deepcopy(context)
    connection = object.__new__(_SessionConnection)
    connection.scientific_prompt_states = {}
    prompt, instructions = connection._presentation(
        trace['episode_id'], trace['role'], trace['instructions'], context)
    assert context == before
    assert connection.scientific_prompt_states[trace['episode_id'], trace['role']] == state
    return prompt, instructions


def scientific_inventory(trace):
    state = trace['state']
    main = {sheet['sheet_ref']: sheet for sheet in state['literature_current_scoring_sheets']}
    subscoring = {sheet['sheet_ref']: sheet for main_sheet in main.values()
                  for sheet in main_sheet.get('subscoring_sheets', [])}
    findings = {row['id']: row for row in state['working_state']['assessments']
                if isinstance(row.get('investigation_finding'), Mapping)}
    return main, subscoring, findings


def validate_scientific_presentation(prompt, trace):
    """Require scientific values and exact usable handles in the actual wire."""
    main, subscoring, findings = scientific_inventory(trace)
    normalized = prompt.replace('_', ' ')
    for reference in [*main, *subscoring, *findings]:
        assert reference in prompt, reference
    for sheet in [*main.values(), *subscoring.values()]:
        for cell in sheet.get('cells', []):
            value = cell.get('value')
            if value is not None:
                assert str(value) in prompt, (cell['component'], value)
            for field in ('status', 'unit'):
                if cell.get(field) is not None:
                    assert str(cell[field]).replace('_', ' ') in normalized
            for missing in cell.get('missing_inputs', []):
                if missing.get('reason'):
                    assert missing['reason'].replace('_', ' ') in normalized
    for record in findings.values():
        finding = record['investigation_finding']
        assert finding['qualification']['kind'].replace('_', ' ') in normalized
        for replaced in finding.get('replaces_refs', []):
            assert replaced in prompt
    return {'current_main_sheets': len(main), 'current_subscoring_sheets': len(subscoring),
            'received_typed_findings': len(findings),
            'all_current_sheet_handles_present': True,
            'all_received_finding_handles_present': True,
            'saved_values_units_statuses_and_missing_reasons_present': True,
            'source_qualifications_and_replacements_present': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path)
    args = parser.parse_args()
    from gene_annotation_episode.workflow_budget import active_budget
    root = Path(active_budget()['run_directory']).resolve()
    output = root if args.output_directory is None else args.output_directory.resolve()
    if output != root and root not in output.parents:
        raise ValueError('output_directory_must_belong_to_this_run')
    output.mkdir(parents=True, exist_ok=True)
    trace = retained_input()
    before = deepcopy(trace)
    prompt, instructions = replay_input(trace)
    invariants = validate_scientific_presentation(prompt, trace)
    assert trace == before
    original = trace['sent_text']
    assert trace['original_input_matches_sent']
    assert len(original) == trace['transport_failure']['input_chars']
    summary = {'kind': 'a105_original_rejected_parent_input_replay',
        'fixture_sha256': hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        'parent_work_receipts_sha256': hashlib.sha256(WORK_RECEIPTS.read_bytes()).hexdigest(),
        'parent_work_projection_recomputed_from_original_receipts': True,
        'original_characters': len(original), 'rendered_characters': len(prompt),
        'reduction_characters': len(original) - len(prompt),
        'original_child_forms': len(trace['state']['child_reports']),
        'recorded_provider_maximum': trace['transport_failure']['provider_max_chars'],
        'below_recorded_provider_maximum': len(prompt) <= trace['transport_failure']['provider_max_chars'],
        'original_source_context_unchanged': True,
        'cached_state_changes_only_completed_work_projection': True,
        'model_or_workflow_started': False, **invariants}
    (output / 'parent-prompt.txt').write_text(prompt)
    (output / 'parent-instructions.txt').write_text(instructions)
    (output / 'parent-prompt-review.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
