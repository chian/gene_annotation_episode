"""Offline selected thread operands under the enclosing workflow CPU quota."""
from importlib import import_module

import pytest


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


def test_launch_schema_allows_positive_selected_threads_without_count_maximum(jobs):
    policy = module('local_jobs').LocalJobPolicy(1024, 1024)
    values = module('homology_service_setup').create_homology_bindings(
        jobs, parser_policy=policy, credit_projector=lambda *args, **kwargs: 0,
        credit_binding={'version': 'synthetic-operational'},
        monitoring_projector=lambda *args, **kwargs: 0,
        monitoring_binding={'version': 'synthetic-monitoring'})
    schemas = values['job_launch'].commission_schemas({'properties': {}})
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
