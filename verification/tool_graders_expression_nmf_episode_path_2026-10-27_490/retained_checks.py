"""Targeted verification against an already closed actual Workflow case.

This reads the original result and control records. It cannot fit, launch,
poll, reacquire or make a model decision. It completes verification of
test-only corrections without replacing the earlier frozen test outcome.
"""
from importlib import import_module, util
import hashlib
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from gene_annotation_episode.expression_nmf_common import canonical
from gene_annotation_episode.state import Store

F = import_module('verification.tool_graders_expression_nmf_episode_path_2026-10-27_490.fixture_helpers')


def run(attempt, directory):
    spec = util.spec_from_file_location('nmf490_current_test',
        attempt / 'source_snapshot/tests/test_expression_nmf_episode_path.py')
    test = util.module_from_spec(spec)
    sys.modules[spec.name] = test
    spec.loader.exec_module(test)
    configuration = json.loads((directory / 'fixture-configuration.json').read_bytes())
    saved_case = json.loads((directory / 'CASE.json').read_bytes())
    evidence = json.loads((directory / 'SAVED_CHECK.json').read_bytes())

    class NoNewDecisions:
        async def complete(self, *args, **kwargs):
            raise AssertionError('retained verification requested a model decision')

        async def release(self, episode_id):
            pass

    with pytest.MonkeyPatch.context() as patch, Store(directory / 'state') as store:
        for name in ('prepare_job', 'start_prepared', 'resume_start', 'status', 'wait_job', 'collect'):
            patch.setattr('gene_annotation_episode.native_lifecycle.' + name, test.deny)
        for name in ('capture_expression_nmf_native_files', 'prepare_expression_nmf_result_worker'):
            patch.setattr('gene_annotation_episode.native_expression_nmf_results.' + name, test.deny)
        patch.setattr('socket.create_connection', test.deny)
        patch.setattr('socket.socket.connect', test.deny)
        patch.setattr('socket.socket.connect_ex', test.deny)
        before = {table: F.rows(store, table) for table in F.TABLES}
        flow, tools = F.assemble(store, directory, NoNewDecisions(), configuration)
        owner = flow.episode_bindings.for_role('results')
        patch.setattr(type(owner.job_progress_provider.targets), 'observe_target', test.deny)
        archive = saved_case['archive']
        records = list(F.walk(archive))
        contexts = {row['episode_id']: owner.native_expression_nmf_returns.context(row['episode_id'])
            for row in records}
        by_role = {}
        for row in records:
            by_role.setdefault(contexts[row['episode_id']].role, []).append(row)
        result_contexts = [contexts[row['episode_id']] for row in by_role['results']]
        outcomes = [json.loads(flow.journal.row('runtime_actions', context.episode_id, 0)['result'])
            for context in result_contexts]
        returned = [json.loads(flow.journal.row('runtime_forms', context.episode_id)['form'])
            for context in result_contexts]
        assert returned == saved_case['returned']
        scientific, = [contexts[row['episode_id']] for row in by_role['scientific_process']]
        root = contexts[archive['episode_id']]
        original = evidence['original_receipt']
        native = original['native']
        retained_plan = store.get_artifact(native['plan_file']['artifact_ref'])
        assert json.loads(retained_plan) == native['original_plan']
        plan_path = Path(original['intent']['target']['execution_id']).parent / 'expression-nmf-plan.json'
        # Original native serialization is fixed by immutable_json; the content
        # comes from the prior authenticated captured control, not today's file.
        evidence['native_plans'] = {str(plan_path): canonical(json.loads(retained_plan)) + b'\n'}
        evidence['sheet_bytes'] = store.get_artifact(evidence['sheet_file']['artifact_ref'])
        assert hashlib.sha256(evidence['sheet_bytes']).hexdigest() == evidence['sheet_file']['sha256']
        case = SimpleNamespace(store=store, directory=directory, workspace=Path(original['intent']['target']['assignment']['workspace']),
            flow=flow, tools=tools, owner=owner, saved_evidence=evidence, outcomes=outcomes, returned=returned,
            scientific_context=scientific, root_context=root,
            provider=SimpleNamespace(target=original['intent']['target']))
        # Re-execute the complete corrected test, including all checks that
        # follow the formerly overbroad deleted-path assertion.
        test.test_saved_sheet_alone_preserves_authority_and_has_zero_new_acquisition(case)

        sheet = json.loads(evidence['sheet_bytes'])
        calculated_file = outcomes[1]['result']['qualified_files']['calculations']
        assert calculated_file == original['qualified_files']['calculations']
        calculation = json.loads(store.get_artifact(calculated_file['artifact_ref']))
        X, W, H = sheet['fit_matrix'], sheet['W'], sheet['H']
        predicted = [[sum(W[g][k] * H[k][s] for k in range(2)) for s in range(3)] for g in range(3)]
        residual = [[X[g][s] - predicted[g][s] for s in range(3)] for g in range(3)]
        sse = sum(value * value for row in residual for value in row)
        assert calculation['sse'] == pytest.approx(sse, rel=1e-12, abs=1e-20)
        assert calculation['frobenius_residual'] == pytest.approx(math.sqrt(sse), rel=1e-12)
        assert calculation['rmse'] == pytest.approx(math.sqrt(sse / 9), rel=1e-12)
        assert sheet['outcome'] == evidence['original_worker']['capture']['result']['native_outcome']
        native_execution = json.loads((directory / 'native-lifecycle.json').read_bytes())
        assert native_execution['returncode'] == 0
        assert native_execution['metadata']['verified_cgroup'] == {'memory_max': 21474836480,
            'memory_swap_max': 0, 'runtime_max': 'infinity', 'kill_mode': 'control-group', 'oom_policy': 'kill'}
        F.write(attempt / 'NUMERICAL_EXAMPLE.json', {'input': X, 'W': W, 'H': H,
            'independently_reconstructed': predicted, 'independent_residuals': residual,
            'independent_sse': sse, 'independent_frobenius_residual': math.sqrt(sse),
            'native_reconstruction_error': calculation['native_reconstruction_error'],
            'calculated_frobenius_residual': calculation['frobenius_residual'],
            'native_outcome': sheet['outcome'], 'returned': returned, 'forwarded': saved_case['forwarded']})
        assert {table: F.rows(store, table) for table in F.TABLES} == before
        F.write(attempt / 'retained_checks.json', {'original_case': str(directory),
            'corrected_saved_sheet_test': 'passed', 'independent_numerical_example': 'passed',
            'original_native_allocation': 'passed', 'new_model_calls': 0, 'new_native_work': 0,
            'original_histories_unchanged': True,
            'recreated_derived_artifacts': [row for row in evidence['removed'] if Path(row['path']).exists()]})
        print('Corrected saved-sheet test and retained numerical/allocation checks passed; no new model/native work.', flush=True)
