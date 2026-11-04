"""Actual fixed-gene Store/shared runtime, scripted decisions and fixture policy.

No live models, native search or scientific annotation is claimed by this harness.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch

import pytest

from gene_annotation_episode.case_execution import prepare_case_run, run_prepared_case
from gene_annotation_episode.homology_jobs import HomologyJobs, digest
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_homology_jobs import PROGRAM, PROJECT, QUERY
from test_homology_episode_runtime import Provider, action


POLICY = '''from gene_annotation_episode.case_execution import PolicyBindings
from gene_annotation_episode.numerical import YieldController, YieldEstimate, NumericBand

def create_policy(parameters):
    def task_credit(store, scope):
        return parameters['score']
    def scientific_child_credit(store, scope, **kwargs):
        return parameters['score']
    def job_credit(store, **kwargs):
        return parameters['score']
    def fixture_estimate(history, settings, contexts):
        return YieldEstimate(len(history), NumericBand.exact(0 if len(history) >= parameters.get('stop_after', 1) else 1), settings,
            {'kind':'fixture_only_not_production'})
    def controller(path, initial):
        return YieldController(str(path), initial, parameters['cost'], parameters['numerical'],
            estimate_with_context=fixture_estimate)
    return PolicyBindings(task_credit, scientific_child_credit, job_credit, job_credit, controller,
        {'kind':'fixture_constant','score':parameters['score']},
        {'kind':'fixture_constant','score':parameters['score']},
        {'kind':'fixture_constant','score':parameters['score']},
        {'kind':'fixture_constant','score':parameters['score']},
        {'kind':'fixture_estimator','cost':parameters['cost'],'numerical':parameters['numerical']})
'''


PARAMETERS = {'score': 0, 'cost': 0, 'numerical': {
    'window_size': 8, 'subsample_size': 4, 'uncertainty_alpha': .05}}


def prepared(tmp_path, *, with_protein=True):
    case = tmp_path/'case'
    case.mkdir()
    (case/'target.fna').write_bytes((PROJECT/'cases/gene_001/target.fna').read_bytes())
    workspace = case/'workspace'
    with Store(workspace) as store:
        problem = store.create_problem(case/'target.fna', molecule='dna', role='gene')
        target = problem['subject_refs'][0]
        product = None
        if with_protein:
            translated = ToolRegistry(store).execute('sequence.translate', {'subject_ref': target, 'code': 11, 'cds': True},
                scope={'subject_refs': [target]})
            product = translated['result']['records'][0]['product_ref']
        artifact = store.artifact('{"kind":"explicit_case_harness_fixture"}', 'application/json')
        source = store.put('source', {'provider': 'fixture.input_context', 'accession': None, 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': 'fixture',
            'retrieved_at': None, 'parent_source_refs': [], 'operand_refs': [target]}, origin='tool')
    (case/'case.json').write_text(json.dumps({'case_ref': 'fixture_gene', 'target_kind': 'single_gene',
        'target_ref': target, 'problem_ref': problem['id'],
        'target_files': {'target.fna': digest(case/'target.fna')},
        'scientific_question': 'Fixture runtime inspection; no biological inference.'}))
    (case/'evidence-refs.json').write_text(json.dumps({'target_ref': target, 'product_ref': product,
        'source_refs': {'context': source['id'], 'missing': 'fixture_missing_source'}, 'comparison_refs': []}))
    reference = case/'references.faa'
    reference.write_text(QUERY)
    import tomllib
    from gene_annotation_episode.providers import default_config_path
    defaults = tomllib.loads(default_config_path().read_text())
    configuration = {'workspace': 'workspace', 'history': 'global.sqlite', 'resource_id': 'fixture-host',
        'max_cpu': 1, 'reference_records': 1, 'reference_residues': 253,
        'executable': {'path': str(PROGRAM), 'sha256': digest(PROGRAM)},
        'reference_database': {'path': 'references.faa', 'sha256': digest(reference)},
        'local_jobs': {'memory_bytes': 128*1024**2, 'scratch_bytes': 4*1024**2},
        'models': defaults['models'], 'restoration': defaults['restoration']}
    policy = case/'explicit_fixture_policy.py'
    policy.write_text(POLICY)
    return case, configuration, policy


def inspect_sources():
    return action('state.query', {'kind': 'source', 'offset': 0, 'limit': 2})


def test_scientific_focus_is_caller_owned_recorded_and_preserved_on_resume(tmp_path, capsys):
    from gene_annotation_episode.case_execution import main
    case, configuration, policy = prepared(tmp_path, with_protein=False)
    run = tmp_path/'focused_run'
    focus = 'Coordinate iterative synthetic sub-investigations; choose useful questions from results.'
    focus_file = tmp_path/'focus.txt'
    focus_file.write_text(focus)
    # CLI configuration accepts TOML, while the Python API shares its parsed
    # configuration. Read the exact focus file through the real CLI boundary.
    with patch('gene_annotation_episode.case_execution.tomllib.loads', return_value=configuration), \
         patch('subprocess.Popen', side_effect=AssertionError('Preparation cannot launch work')):
        config_file = tmp_path/'configuration.toml'
        config_file.write_text('# configuration supplied by this explicit fixture')
        main(['prepare', '--case-dir', str(case), '--run-dir', str(run),
              '--config', str(config_file), '--focus-file', str(focus_file)])
    assert json.loads(capsys.readouterr().out)['state'] == 'prepared'
    manifest = json.loads((run/'case-launch.json').read_text())
    assert manifest['focus'] == focus and focus in manifest['goal']
    assert 'Fixture runtime inspection' in manifest['goal']
    assert manifest['target_ref'] in manifest['goal']
    assert prepare_case_run(case, run, configuration) == manifest
    assert prepare_case_run(case, run, configuration, focus=focus) == manifest
    with pytest.raises(ValueError, match='scientific_focus_conflict'):
        prepare_case_run(case, run, configuration, focus='Different investigation')
    focus_file.unlink()
    provider = Provider([inspect_sources()])
    summary = asyncio.run(run_prepared_case(run, policy_file=policy,
        parameters=PARAMETERS, provider=provider))
    assert focus in provider.contexts[0]['goal']['objective']
    assert json.loads((run/'run.json').read_text())['goal'] == manifest['goal']
    assert asyncio.run(run_prepared_case(run, resume=True, provider=Provider([]))) == summary


def test_case_preparation_launch_and_replay_use_fixed_material_and_explicit_policy(tmp_path):
    case, configuration, policy = prepared(tmp_path)
    run = tmp_path/'run'
    with patch('subprocess.Popen', side_effect=AssertionError('Preparation cannot start models or jobs')):
        manifest = prepare_case_run(case, run, configuration)
        assert prepare_case_run(case, run, configuration) == manifest
    with Store(case/'workspace') as store:
        source = store.get(manifest['context_source_ref'])
        inventory = json.loads(store.get_artifact(source['artifact_ref']))
        assert inventory['target_ref'] == manifest['target_ref']
        assert 'context' in inventory['baseline_source_refs'] and 'missing' not in inventory['baseline_source_refs']
        assert inventory['unavailable_input_references'] == [{'input_key':'missing', 'requested_ref':'fixture_missing_source'}]
        assert store.count('annotation') == store.count('assessment') == 0
    jobs = HomologyJobs(run/'native-jobs')
    assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    jobs.close()
    provider = Provider([inspect_sources()])
    summary = asyncio.run(run_prepared_case(run, policy_file=policy, parameters=PARAMETERS, provider=provider))
    assert summary['completed_actions'] == 1 and summary['scientific_completion'] == 'not_established_by_termination'
    settings = json.loads((run/'run.json').read_text())
    assert settings['credit_policy'] is settings['controller'] is None
    assert settings['initial_tool_resources']['local_jobs'] == manifest['configuration']['local_jobs']
    assert settings['job_episodes']['statistics']['history_path'] == str(case/'global.sqlite')
    assert settings['execution_expectations']['homology']['registry_directory'] == str(run/'native-jobs')
    assert provider.contexts[0]['credit_binding']['definition']['definition']['kind'] == 'fixture_constant'
    assert settings['execution_expectations']['homology']['planning_roles'] == ['annotation', 'improvement']
    assert provider.contexts[0]['execution_expectations']['execution_classes'][0]['query_residues'] == 253
    forecast, = provider.contexts[0]['resource_tool_estimates']
    assert forecast['job_ref'] is None and forecast['cpu_threads'] == 1
    assert forecast['status'] == 'no_matching_history' and forecast['expected_total_seconds'] is None
    # Original staging files and source code are no longer dependencies of a
    # committed case. Resume uses its immutable Store target and policy copy.
    (case/'target.fna').unlink()
    policy.write_text('raise AssertionError("Do not use this changed original policy on resume")')
    assert asyncio.run(run_prepared_case(run, resume=True, provider=Provider([]))) == summary
    with pytest.raises(ValueError, match='policy_parameters'):
        asyncio.run(run_prepared_case(run, resume=True, parameters={**PARAMETERS, 'score': 1}, provider=Provider([])))
    with pytest.raises(ValueError, match='policy_source'):
        asyncio.run(run_prepared_case(run, resume=True, policy_file=policy, provider=Provider([])))
    with Store(case/'workspace') as store:
        assert store.count('annotation') == store.count('assessment') == 0


def test_case_refreshes_empty_planning_context_after_actual_protein_acquisition(tmp_path):
    case, configuration, policy = prepared(tmp_path, with_protein=False)
    run = tmp_path/'run'
    manifest = prepare_case_run(case, run, configuration)
    def translate(context):
        assert context['execution_expectations']['execution_classes'] == []
        assert context['resource_tool_estimates'] == []
        return action('sequence.translate', {'subject_ref': manifest['target_ref'], 'code': 11, 'cds': True})
    def inspect(context):
        assert context['last_local_outcome']['status'] == 'completed'
        forecast, = context['resource_tool_estimates']
        assert forecast['job_ref'] is None and forecast['cpu_threads'] == 1
        assert context['execution_expectations']['execution_classes'][0]['query_residues'] == 253
        return inspect_sources()
    provider = Provider([translate, inspect])
    result = asyncio.run(run_prepared_case(run, policy_file=policy, parameters={**PARAMETERS, 'stop_after': 2},
        provider=provider))
    assert result['completed_actions'] == 2
    jobs = HomologyJobs(run/'native-jobs')
    try:
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close()


def test_preparation_preserves_unrelated_history_and_missing_native_assets_are_not_scientific_gates(tmp_path):
    case, configuration, policy = prepared(tmp_path)
    path = case/'global.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE unrelated(value INTEGER)')
    before = path.read_bytes()
    configuration['executable'] = {'path': str(case/'unavailable_binary'), 'sha256': 'a'*64}
    manifest = prepare_case_run(case, tmp_path/'run', configuration)
    assert path.read_bytes() == before
    assert manifest['configuration']['executable']['path'] == str(case/'unavailable_binary')
    summary = asyncio.run(run_prepared_case(tmp_path/'run', policy_file=policy, parameters=PARAMETERS,
                                            provider=Provider([inspect_sources()])))
    assert summary['completed_actions'] == 1
    assert path.read_bytes() == before


def test_missing_policy_does_not_fall_back_to_default_scientific_or_job_scores(tmp_path):
    case, configuration, _ = prepared(tmp_path)
    run = tmp_path/'run'
    prepare_case_run(case, run, configuration)
    provider = Provider([])
    with pytest.raises(ValueError, match='explicit_policy_source_and_parameters'):
        asyncio.run(run_prepared_case(run, provider=provider))
    assert provider.contexts == [] and not (run/'run.json').exists()


def test_interrupted_case_restores_policy_snapshot_and_completed_action_history(tmp_path):
    case, configuration, policy = prepared(tmp_path)
    run = tmp_path/'run'
    prepare_case_run(case, run, configuration)
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(run_prepared_case(run, policy_file=policy, parameters=PARAMETERS,
                                      provider=Provider([KeyboardInterrupt()])))
    (case/'target.fna').unlink()
    policy.unlink()
    summary = asyncio.run(run_prepared_case(run, resume=True, provider=Provider([inspect_sources()])))
    assert summary['completed_actions'] == 1
    with Store(case/'workspace') as store:
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1


def test_case_preserves_actual_scientific_projection_across_policy_snapshot_and_resume(tmp_path):
    """Real scientific adapter through the case entry point; synthetic evidence only."""
    from gene_annotation_episode.credit import CreditPolicy, project_credit
    from gene_annotation_episode.scientific_credit import ScientificEvidenceCredit
    from test_scientific_hypervolume_runtime import evidence, assessment, annotation, commit

    case, configuration, policy_file = prepared(tmp_path)
    run = tmp_path/'run'
    manifest = prepare_case_run(case, run, configuration)
    target = manifest['target_ref']
    scope = {'subject_refs': [target]}
    # This factory is explicit engineering scaffolding, not the production case
    # policy. Only the scientific projectors use the actual evidence projection.
    policy_file.write_text(POLICY.replace(
        '    return PolicyBindings(task_credit, scientific_child_credit, job_credit, job_credit, controller,\n'
        "        {'kind':'fixture_constant','score':parameters['score']},\n"
        "        {'kind':'fixture_constant','score':parameters['score']},",
        '    from gene_annotation_episode.credit import CreditPolicy\n'
        '    from gene_annotation_episode.scientific_credit import ScientificEvidenceCredit\n'
        "    scientific = ScientificEvidenceCredit(CreditPolicy.from_record(parameters['scientific']))\n"
        '    return PolicyBindings(scientific, scientific, job_credit, job_credit, controller,\n'
        '        scientific.as_record(), scientific.as_record(),'))
    credit_policy = CreditPolicy(scale=137, epsilon=.4, unresolved_factor=.7)
    parameters = {**PARAMETERS, 'stop_after': 2, 'scientific': credit_policy.as_record()}
    with Store(case/'workspace') as store:
        observations = [evidence(store, target, kind) for kind in ('alignment', 'mechanism')]
        hypothesis = store.put('hypothesis', {'subject_refs': [target],
            'predicate': 'functional_family', 'value': {'type': 'enum', 'value': 'unresolved'},
            'context_refs': []}, origin='reasoning')['id']

    def revise(index):
        def decision(context):
            with Store(case/'workspace') as store:
                current = project_credit(store, scope, credit_policy)
                assert context['current_credit'] == pytest.approx(current.credit)
                assert context['credit_binding']['definition']['definition'] == ScientificEvidenceCredit(credit_policy).as_record()
                current_annotations = store.current_annotations(scope)
                previous = current_annotations[0] if current_annotations else None
                previous_refs = ([] if previous is None else
                    previous['coherent_sets'][0]['interpretations'][0]['assessment_refs'])
                return commit(store,
                    assessments=[assessment(hypothesis, observations[index]['id'], 'direct', alias='a')],
                    annotation_update=annotation(target, hypothesis, previous_refs+['@a'],
                        0 if previous is None else previous['revision'], alias='n'), report={})
        return decision

    with pytest.raises(KeyboardInterrupt):
        asyncio.run(run_prepared_case(run, policy_file=policy_file, parameters=parameters,
            provider=Provider([revise(0), KeyboardInterrupt()])))
    with Store(case/'workspace') as store:
        first = project_credit(store, scope, credit_policy).credit
        assert first > 0
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 1
    policy_file.write_text('raise AssertionError("Resume must use the recorded policy")')
    summary = asyncio.run(run_prepared_case(run, resume=True, provider=Provider([revise(1)])))
    with Store(case/'workspace') as store:
        final = project_credit(store, scope, credit_policy).credit
        assert final > first
        assert summary['credit'] == pytest.approx(final)
        assert summary['completed_actions'] == 2
        assert store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0] == 2
    recorded = json.loads((run/'policy-binding.json').read_text())
    assert recorded['parameters']['scientific'] == credit_policy.as_record()
    assert recorded['definitions']['credit'] == ScientificEvidenceCredit(credit_policy).as_record()
    assert recorded['definitions']['scientific_child_credit'] == recorded['definitions']['credit']


def test_module_cli_uses_the_same_policy_binding_class_as_imported_factories(tmp_path, monkeypatch, capsys):
    import runpy
    import sys
    from gene_annotation_episode import case_execution
    case, configuration, policy_file = prepared(tmp_path)
    run = tmp_path/'run'
    prepare_case_run(case, run, configuration)
    parameters_file = tmp_path/'parameters.json'
    parameters_file.write_text(json.dumps(PARAMETERS))

    async def inspect_policy(run_dir, *, policy_file, parameters, resume):
        policy, _ = case_execution._load_policy(run_dir, policy_file, parameters, resume=resume)
        assert type(policy) is case_execution.PolicyBindings
        return {'policy_loaded': True, 'model_calls': 0}

    monkeypatch.setattr(case_execution, 'run_prepared_case', inspect_policy)
    monkeypatch.setattr(sys, 'argv', ['case_execution', 'run', '--run-dir', str(run),
        '--policy', str(policy_file), '--parameters', str(parameters_file)])
    with patch('subprocess.Popen', side_effect=AssertionError('CLI identity check cannot launch models or jobs')):
        with pytest.warns(RuntimeWarning, match='found in sys.modules'):
            runpy.run_module('gene_annotation_episode.case_execution', run_name='__main__')
    assert json.loads(capsys.readouterr().out) == {'policy_loaded': True, 'model_calls': 0}


def test_child_binding_provenance_does_not_repeat_root_parameters_and_resume_keeps_full_configuration(tmp_path):
    from gene_annotation_episode.domain import canonical
    from test_runtime import obj
    case, configuration, policy_file = prepared(tmp_path)
    run = tmp_path/'run'
    manifest = prepare_case_run(case, run, configuration)
    query = json.loads((case/'evidence-refs.json').read_text())['product_ref']
    # Explicit fixture metadata tests configuration provenance, not biological
    # records or an actual episode knowledge baseline.
    parameters = {**PARAMETERS, 'stop_after': 2,
        'root_provenance_fixture': ['root-only-metadata-'+str(i) for i in range(750)]}
    expected_digest = hashlib.sha256(canonical(parameters).encode()).hexdigest()

    def commission_launch(context):
        facts = context['job_episode_options']['job_launch']['report_facts']
        form = obj({key: facts[key]['report_schema'] for key in ('job_ref', 'job_handoff_state')})
        return {'selection': {'kind': 'job_child', 'role': 'job_launch',
            'query_ref': query, 'cpu': 1, 'scope': {'subject_refs': [manifest['target_ref']]},
            'goal': 'Inspect and establish the assigned execution environment.',
            'purpose': 'Use the returned preparation and handoff state in the next decision.',
            'schema_json': json.dumps(form), 'initial_report_json': '{}'}, 'report_update': {}}

    def use_returned(context):
        assert context['child_reports'][-1]['job_handoff_state'] == 'unavailable'
        return inspect_sources()

    provider = Provider([commission_launch, action('homology.environment'),
        action('homology.configure'), use_returned])
    summary = asyncio.run(run_prepared_case(run, policy_file=policy_file,
        parameters=parameters, provider=provider))
    assert summary['credit'] == 0 and summary['completed_actions'] == 2
    assert summary['episode_count'] == 2
    for context in provider.contexts:
        assert 'root-only-metadata-' not in json.dumps(context)
        for name in ('credit_binding', 'controller_binding'):
            binding = context[name]
            if 'policy_parameters_sha256' not in binding:
                binding = binding['definition']
            assert binding['policy_parameters_sha256'] == expected_digest
            assert 'parameters' not in binding
        assert context['controller_binding']['definition']['definition']['cost'] == parameters['cost']
        assert context['current_credit'] == parameters['score']
    recorded = json.loads((run/'policy-binding.json').read_text())
    assert recorded['parameters'] == parameters
    with Store(case/'workspace') as store:
        actions = store.db.execute('SELECT * FROM runtime_actions').fetchall()
        observations = store.db.execute('SELECT * FROM runtime_observations').fetchall()
    assert asyncio.run(run_prepared_case(run, resume=True, provider=Provider([]))) == summary
    with Store(case/'workspace') as store:
        assert store.db.execute('SELECT * FROM runtime_actions').fetchall() == actions
        assert store.db.execute('SELECT * FROM runtime_observations').fetchall() == observations
    jobs = HomologyJobs(run/'native-jobs')
    try:
        assert jobs.db.execute('SELECT count(*) FROM orders').fetchone()[0] == 1
        assert jobs.db.execute('SELECT sum(submission_requested) FROM orders').fetchone()[0] == 0
    finally:
        jobs.close()
