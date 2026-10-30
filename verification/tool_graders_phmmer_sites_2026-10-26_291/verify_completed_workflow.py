"""Verify the already completed check002 run without another phmmer submission."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from gene_annotation_episode.communication import ReportBoundaryError
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.execution_recording import HomologyStatistics
from gene_annotation_episode.homology_episodes import HomologyEpisodes
from gene_annotation_episode.homology_jobs import HomologyJobs
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_alignment_site_workflow import (
    _context, _controller, _descriptor, _redeliver_frozen, _snapshot, _assert_no_private_sheet,
)
from test_homology_episode_runtime import Provider
from test_resource_episode_branches import no_scientific_credit
from test_sequence_views_integration import LocalOnly
from test_tool_grading_child_returns import zero_fixture_credit


ORIGINAL = Path(__file__).parent / 'check002/temporary/test_tiny_real_phmmer_results_0'


def test_original_completed_run_parent_admission_and_replay(monkeypatch):
    with Store(ORIGINAL / 'workspace') as store:
        jobs = HomologyJobs(ORIGINAL / 'jobs')
        try:
            policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
            homology = HomologyEpisodes(jobs, parser_policy=policy,
                credit_projector=no_scientific_credit, credit_binding={'kind': 'engineering_fixture_zero'},
                monitoring_projector=no_scientific_credit, monitoring_binding={'kind': 'engineering_fixture_zero'},
                statistics=HomologyStatistics(ORIGINAL / 'history.sqlite', 'resource-fixture-host', 1, 253))
            root, = store.db.execute('SELECT * FROM runtime_episodes WHERE json_array_length(path)=1').fetchall()
            request = json.loads(root['request'])
            scope = request['message']['scope']
            tools = ToolRegistry(store, clients=LocalOnly())
            directory = ORIGINAL / 'workflow'
            descriptor, _ = _descriptor(directory, tools)
            decisions = Provider([])
            workflow = Workflow(store, tools, decisions, directory, 'phmmer-site-workflow-291',
                _controller({'annotation': 3, 'job_launch': 5, 'job_results': 1, 'scientific_process': 1}),
                zero_fixture_credit, job_episodes=homology, episode_binding_descriptors=[descriptor],
                annotation_child_roles=('job_launch', 'job_results', 'scientific_process'),
                episode_record_receipts=True, initial_known_record_refs=[])
            parent = workflow.build('annotation', 'root', 'Compare selected protein correspondence', scope)
            child, = store.db.execute("SELECT * FROM runtime_episodes WHERE "
                "json_extract(path,'$[#-1][0]')='scientific_process'").fetchall()
            child_id = child['episode_id']
            schema = json.loads(child['request'])['report_contract']['measurements']['schema']
            returned = json.loads(workflow.journal.row('runtime_forms', child_id)['form'])
            attempt, = store.db.execute('SELECT * FROM runtime_report_attempts '
                'WHERE parent_episode_id=? AND child_episode_id=?',
                (parent.source.episode_id, child_id)).fetchall()
            assert json.loads(attempt['form']) == returned
            for row in store.db.execute('SELECT request FROM runtime_model_calls'):
                current = json.loads(row['request'])['context']
                _assert_no_private_sheet(current.get('child_reports', []))
                assert 'hmmer_search_sheet_v1' not in json.dumps(current)
                assert 'reference_site_comparison_sheet_v1' not in json.dumps(current)
            before = _snapshot(store)
            operation, = store.db.execute("SELECT * FROM tool_operations WHERE name='sequence.sites'").fetchall()
            result = json.loads(operation['result'])
            assert tools.execute('sequence.sites', json.loads(operation['arguments']), scope=scope,
                                 operation_key=operation['operation_key']) == result
            workflow.receive_form(parent.source, returned, schema, attempt['decision_index'], redelivery=True)
            assert _snapshot(store) == before
            def forbidden(*args, **kwargs):
                pytest.fail('Closed return accessed live grading or own-action data')
            monkeypatch.setattr(WorkflowServices, 'alignment_site_own_action_results', forbidden)
            import gene_annotation_episode.alignment_site_calculators as calculators
            monkeypatch.setattr(calculators, 'calculate_reference_site_components', forbidden)
            context = _context(workflow, child_id)
            workflow.scientific_process_binding.validate_report(context, returned, schema)
            _redeliver_frozen(workflow, parent, child_id, schema, returned, 3)
            altered = deepcopy(returned)
            altered['selected'][0]['components']['paired_positions'] += 1
            with pytest.raises(ReportBoundaryError):
                workflow.scientific_process_binding.validate_report(context, altered, schema)
            assert _snapshot(store) == before and decisions.contexts == []
            assert jobs.db.execute('SELECT count(*),sum(submission_requested) FROM orders').fetchone()[:] == (1, 1)
        finally:
            jobs.close()
