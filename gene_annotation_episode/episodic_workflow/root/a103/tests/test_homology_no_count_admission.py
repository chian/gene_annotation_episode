"""Offline selected thread operands under the enclosing workflow CPU quota."""
from importlib import import_module

import pytest

from .homology_thread_operand_checks import check_saved_v2_registry, check_private_forecasts


AXIS = __package__.rsplit('.tests', 1)[0]


def module(name):
    return import_module(AXIS + '.' + name)


@pytest.fixture
def jobs(tmp_path):
    source = module('homology_jobs')
    executable = tmp_path / 'unexecuted-fixture'
    executable.write_text('Synthetic executable identity; never executed.\n')
    executable.chmod(0o700)
    database = tmp_path / 'reference.faa'
    database.write_text('>synthetic\nMA\n')
    value = source.HomologyJobs.create(
        tmp_path / 'jobs',
        executable=source.FileAsset(executable, source.digest(executable)),
        reference_database=source.FileAsset(database, source.digest(database)),
        policy=module('local_jobs').LocalJobPolicy(1024, 1024),
        max_cpu=1,
    )
    try:
        yield value
    finally:
        value.close()


def test_selected_threads_exceed_historical_count_without_changing_identity(jobs):
    operands = dict(query_ref='subject_synthetic', query_fasta='>query\nMA\n',
                    cpu=4, operation_key='original-selection')
    original_configuration = dict(jobs.config)
    selected = jobs.order(**operands)
    assert jobs.order(**operands) == selected
    row = jobs._row(selected)
    assert row['cpu'] == 4
    command = jobs._command(row)
    assert command[command.index('--cpu') + 1] == '4'
    assert jobs.configure(selected, 4)['configured_cpu'] == 4
    with pytest.raises(ValueError, match='selected_job_cpu_is_immutable'):
        jobs.configure(selected, 5)
    assert jobs.config == original_configuration
    assert jobs.configured_cpu_forecasts == (1,)
    assert jobs.config['version'] == 'single_query_phmmer_jobs_v3'
    assert jobs.config['historical_forecast_configuration'] == {'max_cpu': 1}
    assert jobs.cpu_forecast_choices == (1, 4)
    assert not row['submission_requested']
    check_saved_v2_registry(jobs.directory.parent / 'retained-v2-registry')


def test_execution_class_preserves_selected_threads_above_historical_count(jobs, tmp_path):
    statistics = module('execution_recording').HomologyStatistics(
        tmp_path / 'unopened-history.sqlite', 'local:synthetic', 1, 2)
    selected = statistics.execution_class_for_query(
        jobs, query_fasta='>query\nMA\n', cpu=4)
    other = statistics.execution_class_for_query(
        jobs, query_fasta='>query\nMA\n', cpu=5)
    assert selected.cpu_threads == 4
    assert selected.ref != other.ref
    assert not (tmp_path / 'unopened-history.sqlite').exists()
    check_private_forecasts(jobs, statistics, selected, tmp_path / 'forecast-store')


def test_launch_schema_allows_positive_selected_threads_without_count_maximum(jobs):
    policy = module('local_jobs').LocalJobPolicy(1024, 1024)
    values = module('homology_service_setup').create_homology_bindings(
        jobs, parser_policy=policy, credit_projector=lambda *args, **kwargs: 0,
        credit_binding={'version': 'synthetic-operational'},
        monitoring_projector=lambda *args, **kwargs: 0,
        monitoring_binding={'version': 'synthetic-monitoring'})
    for parent in ('legacy_annotation', 'legacy_improvement'):
        binding = values[parent]['job_launch']
        assert binding.binding_path == parent + '/homology_job_submission'
        schemas = binding.commission_schemas({'properties': {}})
        cpu = next(schema['properties']['cpu'] for schema in schemas
                   if 'cpu' in schema['properties'])
        assert cpu['type'] == 'integer'
        assert cpu['minimum'] == 1
        assert 'maximum' not in cpu and 'enum' not in cpu


@pytest.mark.parametrize('cpu', [0, -1, True])
def test_selected_threads_still_require_a_positive_integer(jobs, cpu):
    with pytest.raises(ValueError):
        jobs.order(query_ref='subject_synthetic', query_fasta='>query\nMA\n',
                   cpu=cpu, operation_key='invalid-selection')
    assert jobs.db.execute('SELECT COUNT(*) FROM orders').fetchone()[0] == 0
