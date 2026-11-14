"""Real A103 registry and planning checks, without native execution or receipts."""
from gene_annotation_episode.episodic_workflow.root.a103.tests.hierarchy_paths import current_module_name as _a103_current_module_name
import hashlib
from importlib import import_module
import json
from pathlib import Path
import shutil
AXIS = __package__.rsplit('.tests', 1)[0]
FIXTURE = Path(__file__).parent / 'fixtures/homology_thread_operands_v2'

def module(name):
    return import_module(_a103_current_module_name(AXIS + '.' + name))

def check_saved_v2_registry(directory):
    """Replay an actual controlled v2 order without rewriting its configuration."""
    provenance = json.loads((FIXTURE / 'PROVENANCE.json').read_text())
    for name, recorded in provenance['assets'].items():
        assert hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest() == recorded['sha256']
    configuration_bytes = (FIXTURE / 'configuration.json').read_bytes()
    database_bytes = (FIXTURE / 'jobs.sqlite').read_bytes()
    configuration = json.loads(configuration_bytes)
    assert configuration['version'] == 'single_query_phmmer_jobs_v2'
    assert configuration['max_cpu'] == 1
    for key, name in (('executable', 'unexecuted-program'), ('reference_database', 'reference.faa')):
        assert hashlib.sha256((FIXTURE / name).read_bytes()).hexdigest() == configuration[key]['sha256']
    directory.mkdir()
    for name in ('configuration.json', 'jobs.sqlite'):
        shutil.copyfile(FIXTURE / name, directory / name)
    source = module('homology_jobs')
    registry = source.HomologyJobs(directory)
    try:
        rows = [dict(row) for row in registry.db.execute('SELECT * FROM orders')]
        assert rows == [provenance['original_order']]
        original, = rows
        operands = {key: original[key] for key in ('query_ref', 'query_fasta', 'cpu', 'operation_key')}
        assert registry.order(**operands) == original['job_ref']
        assert (directory / 'configuration.json').read_bytes() == configuration_bytes
        assert (directory / 'jobs.sqlite').read_bytes() == database_bytes
        assert registry.config == configuration
        assert registry.configured_cpu_forecasts == (1,)
        selected = registry.order(**{**operands, 'cpu': 4, 'operation_key': 'new-selected-thread-operand'})
        assert selected != original['job_ref']
        assert registry.order(**{**operands, 'cpu': 4, 'operation_key': 'new-selected-thread-operand'}) == selected
        selected_row = registry._row(selected)
        assert selected_row['cpu'] == 4
        assert registry._command(selected_row)[1:3] == ['--cpu', '4']
        assert registry.cpu_forecast_choices == (1, 4)
        assert not selected_row['staged'] and (not selected_row['submission_requested'])
        assert dict(registry.db.execute('SELECT * FROM orders WHERE job_ref=?', (original['job_ref'],)).fetchone()) == original
        assert registry.db.execute('SELECT count(*) FROM handoffs').fetchone()[0] == 0
        assert registry.db.execute('SELECT count(*) FROM samples').fetchone()[0] == 0
    finally:
        registry.close()
    reopened = source.HomologyJobs(directory)
    try:
        assert reopened.config == configuration
        assert reopened.config['registry_ref'] == configuration['registry_ref']
        assert reopened.order(**operands) == original['job_ref']
        assert reopened._row(selected)['cpu'] == 4
        assert reopened.cpu_forecast_choices == (1, 4)
        assert (directory / 'configuration.json').read_bytes() == configuration_bytes
    finally:
        reopened.close()
    assert (FIXTURE / 'configuration.json').read_bytes() == configuration_bytes
    assert (FIXTURE / 'jobs.sqlite').read_bytes() == database_bytes

def check_private_forecasts(jobs, statistics, expected_class, directory):
    """The six actual private planning owners retain actual selected counts."""
    policy = module('local_jobs').LocalJobPolicy(1024, 1024)
    families = module('homology_service_setup').create_homology_bindings(jobs, parser_policy=policy, credit_projector=lambda *args, **kwargs: 0, credit_binding={'version': 'synthetic-operational'}, monitoring_projector=lambda *args, **kwargs: 0, monitoring_binding={'version': 'synthetic-monitoring'}, statistics=statistics)
    homes = {'job_launch': 'homology_job_submission', 'job_monitor': 'homology_job_monitoring', 'job_results': 'homology_result_acquisition'}
    with module('state').Store(directory) as store:
        store.create_problem(raw_sequence='MA', molecule='protein')
        query, = store.targets()
        scope = store.validate_scope()
        selected = jobs.order(query_ref=query['id'], query_fasta='>query\nMA\n', cpu=4, operation_key='forecast-original-selection')
        before = [dict(row) for row in jobs.db.execute('SELECT * FROM orders ORDER BY job_ref')]
        for parent in ('legacy_annotation', 'legacy_improvement'):
            for role, home in homes.items():
                binding = families[parent][role]
                assert binding.binding_path == parent + '/' + home
                assert type(binding).__module__ == _a103_current_module_name(AXIS + '.' + parent + '.' + home + '.episode')
                assert binding.jobs is jobs and binding.statistics is statistics
                options = binding.prospective_execution_options(store, scope)
                assert {value['query_ref'] for value in options} == {query['id']}
                assert {value['cpu'] for value in options} == {1, 4}
                above, = [value for value in options if value['cpu'] == 4]
                assert above['execution_class'] == expected_class
                assert above['search_mode'] == 'native_defaults'
        assert [dict(row) for row in jobs.db.execute('SELECT * FROM orders ORDER BY job_ref')] == before
        assert jobs._row(selected)['submission_requested'] == 0
        assert not statistics.history_path.exists()
