"""Scripted choices, real bounded native phmmer, original typed return path.

These are engineering fixtures; no configured model or production scientific
credit policy is invoked. Numerical quantities are carried by the parent's
requested source-qualified observation references, without raw sheet prompts.
"""
import json

from gene_annotation_episode.homology_results import NativePhmmerInput
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from test_homology_episode_runtime import ParentTools, Provider, action, commission, run
from test_homology_jobs import wait_terminal
from test_phmmer_grading_binding import values, assert_paired_aliases_equal_shared
from test_resource_episode_branches import resources as resource_fixture
from test_resource_episode_branches import test_nested_launch_real_local_job_checked_handoff_and_separate_results as run_nested


def test_nested_resource_local_child_returns_original_numerical_observation(tmp_path):
    generator = resource_fixture.__wrapped__(tmp_path)
    r = next(generator)
    try:
        # Existing nested launch -> local child -> native result -> results
        # child -> original constrained parent form and witness admission.
        run_nested(r)
        alignments = [row for row in r.store.list('observation') if row['kind'] == 'alignment']
        assert len(alignments) == 1
        observation = alignments[0]
        number = values(r.store, observation['id'])
        assert number['paired_positions'] == 253
        assert number['model_span_coverage'] == number['paired_model_coverage'] == 1
        assert number['sequence_identity_fraction'] == 1
        assert number['native_domain_bias_bits'] >= 0
        grading, = source_tool_gradings(r.store, observation['source_ref'])
        assert grading['sheet']['domains'][0]['associations'][0]['locator']['artifact_role'] == 'stdout'
        parent_returns = [json.loads(row[0]) for row in r.store.db.execute(
            "SELECT result FROM runtime_actions WHERE json_extract(action,'$.kind')='child' "
            "AND json_extract(action,'$.role')='results'")]
        assert len(parent_returns) == 1
        assert parent_returns[0]['result']['acquired'] == [observation['id']]
        assert_paired_aliases_equal_shared(r.store, parent_returns[0]['result']['acquired'][0])
        assert 'hmmer_search_sheet_v1' not in json.dumps(parent_returns)
        job, = [row[0] for row in r.jobs.db.execute('SELECT job_ref FROM orders')]
        native = NativePhmmerInput.from_job(r.jobs, r.jobs.handoff(job))
        assert native.domain_table == r.jobs._directory(job)/'domains.tbl'
        assert native.provenance['native_parameters']['command'] == r.jobs._handle(job).read()['command']
    finally:
        generator.close()


def test_workflow_return_admission_replay_adds_no_model_or_controller_action(tmp_path):
    generator = resource_fixture.__wrapped__(tmp_path)
    r = next(generator)
    tools = ParentTools(r.store)
    launch = commission(r.homology, 'job_launch', r.scope, query_ref=r.query, cpu=2)
    launch['selection']['search_mode'] = 'native_defaults'
    def results(context):
        handoff = context['child_reports'][-1]['job_handoff']
        wait_terminal(r.jobs, handoff['job_ref'])
        return commission(r.homology, 'job_results', r.scope, handoff=handoff)
    provider = Provider([launch, action('homology.environment'), action('homology.configure'),
        action('homology.stage'), action('homology.submit'), action('homology.check_handoff'),
        results, action('homology.extract', {'limit': 10})])
    # Resource fixture's explicit zero projector is used, not retired category credit.
    counts = {'annotation': 2, 'job_launch': 5, 'job_results': 1}
    try:
        summary = run(r.store, tools, provider, r.homology, tmp_path/'workflow', counts=counts)
        assert summary['completed_actions'] == 2
        assert len(provider.contexts) == 8 and tools.seen == []
        assert r.store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 8
        assert r.store.db.execute('SELECT count(*) FROM runtime_model_calls').fetchone()[0] == 8
        assert r.store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0] == 8
        actions = [tuple(row) for row in r.store.db.execute('SELECT * FROM runtime_actions ORDER BY rowid')]
        history = [tuple(row) for row in r.store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid')]
        sources = [tuple(row) for row in r.store.db.execute('SELECT * FROM records ORDER BY id')]
        no_more_calls = Provider([])
        replay = run(r.store, tools, no_more_calls, r.homology, resume=True, counts=counts)
        assert replay == summary and no_more_calls.contexts == []
        assert [tuple(row) for row in r.store.db.execute('SELECT * FROM runtime_actions ORDER BY rowid')] == actions
        assert [tuple(row) for row in r.store.db.execute('SELECT * FROM runtime_observations ORDER BY rowid')] == history
        assert [tuple(row) for row in r.store.db.execute('SELECT * FROM records ORDER BY id')] == sources
        for context in provider.contexts:
            assert 'hmmer_search_sheet_v1' not in json.dumps(context)
        forms = [json.loads(row[0]) for row in r.store.db.execute('SELECT form FROM runtime_report_attempts')]
        returned, = [form['comparisons'] for form in forms if 'comparisons' in form]
        assert len(returned) == 1
        numbers = values(r.store, returned[0])
        assert_paired_aliases_equal_shared(r.store, returned[0])
        assert numbers['paired_positions'] == 253 and numbers['sequence_identity_fraction'] == 1
        assert numbers['posterior_lower_mean'] <= numbers['posterior_upper_mean']
        parent_action = r.store.db.execute("SELECT result FROM runtime_actions "
            "WHERE json_extract(action,'$.role')='job_results'").fetchone()[0]
        assert json.loads(parent_action)['changed_record_refs'] == returned
    finally:
        generator.close()
