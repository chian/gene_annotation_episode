"""Own A104 Homology registry/type boundaries; required original-source fixture.

No native worker, provider transport, descriptor import or scientific score.
The original class below is a test reference with one authenticated declaration
import relocation to the actual own-axis owner. It is not a production restore path.
"""
import ast
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import ModuleType

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a104'
ROLES = ('job_launch', 'job_monitor', 'job_results')
HOMES = ('homology_job_submission', 'homology_job_monitoring', 'homology_result_acquisition')
ORIGINAL_SHA = '0970c0fa12d811a059ec339c8250fe1e2280645959acb1c6fc921f9d2ab246ae'
ORIGINAL_COMMIT = 'fb1e4d9bac279edcae98e8f2b3324b73c1679e51'
MONITORING_SOURCE_SHA = '5d9f7103461302d65bba629e3a111472c1441bc195aebc892133836b7296b5f6'
OBSERVATION_OWNER_SHA = '5ecfcaca47a5d86ac8b92e3305d251bfe39527af5dcec9278b746e3e64c3a4f0'


def own(name):
    return import_module(PACKAGE + '.' + name)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def original_family_type():
    fixture = Path(__file__).parent / 'fixtures/homology_family/original_homology_episodes.py.txt'
    raw = fixture.read_bytes()
    assert sha(raw) == ORIGINAL_SHA
    schema_original = fixture.with_name('original_monitoring_credit.py.txt').read_bytes()
    schema_owner = (Path(__file__).parents[1] / 'homology_observation_schema.py').read_bytes()
    assert sha(schema_original) == MONITORING_SOURCE_SHA and sha(schema_owner) == OBSERVATION_OWNER_SHA
    def declarations(source):
        tree = ast.parse(source)
        function, = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_object']
        schema, = [node for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'EXECUTION_OBSERVATION_SCHEMA' for target in node.targets)]
        return [ast.dump(node, include_attributes=False) for node in (function, schema)]
    assert declarations(schema_original) == declarations(schema_owner)
    old_import = b'from .monitoring_credit import EXECUTION_OBSERVATION_SCHEMA\n'
    new_import = b'from .homology_observation_schema import EXECUTION_OBSERVATION_SCHEMA\n'
    assert raw.count(old_import) == 1 and new_import not in raw
    relocated = raw.replace(old_import, new_import)
    assert relocated.replace(new_import, old_import) == raw
    module = ModuleType(PACKAGE + '.tests.original_homology_family_reference')
    module.__file__ = str(fixture)
    module.__package__ = PACKAGE
    # Fixed original bodies plus one exact declaration-owner import, never a
    # descriptor-selected import or a generic schema/value fallback.
    exec(compile(relocated, str(fixture), 'exec'), module.__dict__)
    assert module.ROLES == ROLES and module.HomologyEpisodes.roles == ROLES
    return module.HomologyEpisodes


def operational_credit(store, *, role, assignment, episode_id, run_id):
    """Explicit test zero; no operational or scientific completion claim."""
    return 0.


def monitoring_credit(store, *, role, assignment, episode_id, run_id):
    """Distinct original caller identity; explicit zero observation."""
    return 0.


def task_credit(*args, **kwargs):
    """Explicit root fixture projection, not inferred from a saved name."""
    return 0.


def controller_factory(path, initial_credit):
    return own('numerical').YieldController('homology-family-boundary', initial_credit, .5)


def install_resource_inventory_guard(monkeypatch, memory_path, failure_message):
    """Allow the original read-only native inventory, never dispatch or transport."""
    import re
    import socket
    import subprocess
    original_popen = subprocess.Popen
    listing = ['systemctl', '--user', 'list-units', '--all', '--type=service',
        '--plain', '--no-legend', '--no-pager', 'gene-local-job-*.service']
    properties = ['--property=' + name for name in ('LoadState', 'ActiveState',
        'SubState', 'MemoryMax', 'MemorySwapMax', 'KillMode', 'OOMPolicy',
        'ControlGroup', 'Slice', 'BindsTo')]

    def forbidden(*args, **kwargs):
        raise AssertionError(failure_message)

    def inventory_popen(arguments, *args, **kwargs):
        literal_listing = type(arguments) is list and arguments == listing
        native_properties = (type(arguments) is list and len(arguments) == 14
            and arguments[:3] == ['systemctl', '--user', 'show']
            and type(arguments[3]) is str
            and re.fullmatch(r'gene-local-job-[0-9a-f]{32}\.service', arguments[3]) is not None
            and arguments[4:] == properties)
        if (literal_listing or native_properties) and not args and kwargs == {
                'stdout': subprocess.PIPE, 'stderr': subprocess.DEVNULL, 'text': True}:
            return original_popen(arguments, **kwargs)
        return forbidden(arguments, *args, **kwargs)

    # This existing configuration input creates fresh operational observations
    # under this test's output; no default or historical memory store is opened.
    monkeypatch.setenv('GENE_EPISODE_EXECUTION_MEMORY', str(memory_path))
    monkeypatch.setattr(subprocess, 'Popen', inventory_popen)
    monkeypatch.setattr(socket, 'create_connection', forbidden)


class ContinuationObserved(KeyboardInterrupt):
    """Explicit interruption at the real provider; no selected unit has returned."""


class Provider:
    def __init__(self):
        self.calls = []

    def has_session(self, *args):
        return False

    async def complete(self, episode_id, purpose, instructions, context, schema):
        self.calls.append({'episode_id': episode_id, 'purpose': purpose,
            'instructions': instructions, 'context': deepcopy(context), 'schema': deepcopy(schema)})
        raise ContinuationObserved('actual_original_continuation_boundary')


def options(policy):
    return {'parser_policy': policy, 'credit_projector': operational_credit,
        'credit_binding': {'version': 'explicit_homology_family_operational_fixture_v1', 'claimed_credit': 0},
        'monitoring_projector': monitoring_credit,
        'monitoring_binding': {'version': 'explicit_homology_family_monitor_fixture_v1', 'claimed_credit': 0},
        'statistics': None}


def registry_files(directory):
    return {name: sha((directory / name).read_bytes()) for name in ('configuration.json', 'jobs.sqlite')}


def registry_rows(jobs):
    tables = [row[0] for row in jobs.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {name: [list(row) for row in jobs.db.execute('SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid')]
        for name in tables}


@contextmanager
def registry(directory):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    jobs_module = own('homology_jobs')
    policy = own('local_jobs').LocalJobPolicy.from_config()
    executable = directory / 'inert-executable-identity'
    reference = directory / 'reference.faa'
    executable.write_bytes(b'Explicit inert identity; no execute bit and never submitted.\n')
    reference.write_bytes(b'>original_reference\nMACDEFGH\n')
    jobs = jobs_module.HomologyJobs.create(directory / 'registry',
        executable=jobs_module.FileAsset(executable, sha(executable.read_bytes())),
        reference_database=jobs_module.FileAsset(reference, sha(reference.read_bytes())), policy=policy, max_cpu=1)
    try:
        with own('state').Store(directory / 'workspace') as store:
            scope = {'subject_refs': store.create_problem(raw_sequence='MACDEFGH', molecule='protein')['subject_refs']}
            query = scope['subject_refs'][0]
            job_ref = jobs.order(query_ref=query, query_fasta='>query\nMACDEFGH\n', cpu=1,
                operation_key='original-unsubmitted-family-order')
            yield store, jobs, policy, scope, job_ref
    finally:
        jobs.close()


def actual_descriptor_boundary(jobs, policy):
    original_type = original_family_type()
    original = original_type(jobs, **options(policy))
    private = own('homology_service_setup').create_homology_bindings(jobs, **options(policy))
    assert set(private) == set(ROLES)
    descriptor = original.as_record()
    assert descriptor['version'] == 'homology_episode_bindings_v4' and 'binding_id' not in descriptor
    for role, home in zip(ROLES, HOMES):
        leaf = private[role]
        assert type(leaf) is own(home + '.episode').HomologyEpisode
        assert leaf.roles == (role,)
        assert leaf.jobs is jobs and leaf.parser_policy is policy
        assert leaf._job_credit_calculator is operational_credit and leaf.monitoring_projector is monitoring_credit
        # A source comparison, never a serialized migration or field deletion.
        assert leaf.as_record() == {'binding_id': home, **descriptor}
    return {'original_fixture_commit': ORIGINAL_COMMIT, 'original_fixture_sha256': ORIGINAL_SHA,
        'original_observation_source_sha256': MONITORING_SOURCE_SHA,
        'current_observation_owner_sha256': OBSERVATION_OWNER_SHA,
        'reference_import_transition': 'monitoring_credit.EXECUTION_OBSERVATION_SCHEMA -> homology_observation_schema.EXECUTION_OBSERVATION_SCHEMA',
        'original_reference_class': original_type.__module__ + '.' + original_type.__qualname__,
        'original_roles': list(original.roles), 'original_descriptor': descriptor,
        'private_descriptors': {role: leaf.as_record() for role, leaf in private.items()},
        'factory_return_type': type(private).__name__, 'saved_descriptor_rewritten': False}


def actual_registry_close_reopen(jobs, policy):
    expected_type = own('homology_jobs').HomologyJobs
    before = own('homology_service_setup').create_homology_bindings(jobs, **options(policy))
    old_descriptor = {role: value.as_record() for role, value in before.items()}
    old_configuration = deepcopy(jobs.config)
    old_rows = registry_rows(jobs)
    directory = jobs.directory
    jobs.close()
    old_files = registry_files(directory)
    reopened = expected_type(directory)
    try:
        assert type(reopened) is expected_type and reopened.directory == directory
        assert reopened.config == old_configuration and registry_rows(reopened) == old_rows
        after = own('homology_service_setup').create_homology_bindings(reopened, **options(policy))
        assert {role: value.as_record() for role, value in after.items()} == old_descriptor
        for role in ROLES:
            assert type(after[role]) is type(before[role])
            assert after[role].jobs is reopened and after[role].parser_policy is policy
            assert after[role]._job_credit_calculator is before[role]._job_credit_calculator is operational_credit
            assert after[role].monitoring_projector is before[role].monitoring_projector is monitoring_credit
        result = {'descriptors': old_descriptor, 'registry_configuration': old_configuration,
            'registry_rows': old_rows, 'registry_files_before': old_files,
            'same_directory_and_all_saved_values': True, 'actual_typed_registry_reopened': True,
            'actual_private_types_and_caller_objects_preserved': True, 'submitted_jobs': 0}
        assert all(row['submission_requested'] == 0 for row in reopened.db.execute('SELECT submission_requested FROM orders'))
    finally:
        reopened.close()
    result['registry_files_after'] = registry_files(directory)
    assert result['registry_files_before'] == result['registry_files_after']
    return result


def actual_public_family_type_gate(store, jobs, policy, directory, *, reference):
    """Observe current unsupported family input at real run_workflow, without bypass."""
    family = (original_family_type()(jobs, **options(policy)) if reference == 'tracked_original_class'
        else own('homology_service_setup').create_homology_bindings(jobs, **options(policy)))
    assert reference in {'tracked_original_class', 'current_factory_map'}
    provider = Provider()
    before = registry_rows(jobs)
    try:
        value = asyncio.run(own('runtime').run_workflow(store, own('tools').ToolRegistry(store),
            provider=provider, run_dir=directory, controller_factory=controller_factory,
            project_credit=task_credit, job_episodes=family, episode_binding_factories=(),
            annotation_child_roles=(), decision_protocol=None))
        observed = {'status': 'returned', 'value': value}
    except Exception as error:
        observed = {'status': 'raised', 'type': type(error).__module__ + '.' + type(error).__qualname__,
            'message': str(error), 'args': list(error.args)}
    assert registry_rows(jobs) == before
    return {'input': reference, 'observation': observed, 'provider_calls': provider.calls,
        'registry_rows_unchanged': True, 'record_inferred_from_names': False,
        'original_reference_type_is_fixture_only': reference == 'tracked_original_class'}
