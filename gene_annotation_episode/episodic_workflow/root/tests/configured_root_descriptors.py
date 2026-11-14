"""Observe real configured Root families without acquiring an action.

The observer constructs the actual catalogued classes with explicit caller
settings and controlled external ports. It invokes their real descriptor
methods, retains their returned records, and authenticates every descriptor
source read. It does not replace constructors, descriptor functions, schemas,
credit projectors or scientific parents. No provider, native job or transport
operation is invoked. Annotation and the implicit improvement host keep their
actual distinct record interfaces; no fingerprint is invented for either.
"""
from collections import Counter
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import ast
import hashlib
import inspect
import json
from pathlib import Path
import textwrap
from types import SimpleNamespace
from unittest.mock import patch

ROOT = 'gene_annotation_episode.episodic_workflow.root'
ROOT_PATH = 'gene_annotation_episode/episodic_workflow/root'
FAMILY_COUNTS = {'Annotation': 1, 'Execution': 60, 'HPC': 9, 'Homology': 6,
                 'Legacy improvement': 1, 'Literature': 21, 'Monitor': 9,
                 'Resource': 45, 'Scientific process': 1, 'Terminal': 6}
APP_SERVICE = {'kind': 'api', 'service': 'bvbrc_appservice',
    'execution_contract': 'bvbrc_appservice_execution_v1',
    'endpoints': {'AppService': 'https://app.example.invalid/rpc',
                  'Workspace': 'https://workspace.example.invalid/rpc'},
    'scientific_adapters': []}


def forbidden(*args, **kwargs):
    raise AssertionError('descriptor observation cannot dispatch external work')


class EmptyCatalogPort:
    """A real supported catalog interface with no adopted scientific options."""
    def as_record(self):
        return {'descriptor_observer': 'explicit_empty_catalog_no_scientific_execution'}

    def headers(self):
        return ()

    resolve = staticmethod(forbidden)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def _configuration(directory):
    workspace = directory / 'workspace'
    workspace.mkdir()
    local = {'kind': 'local', 'workspace': str(workspace),
             'policy': {'memory_bytes': 128 * 1024 ** 2, 'scratch_bytes': 8 * 1024 ** 2}}
    hpc = {'kind': 'pbs_ssh', 'workspace': str(workspace),
           'ssh_argv': ['never-dispatch-this-observer-transport'],
           'python_executable': '/usr/bin/python3', 'account': 'BioReason-Aurora-Test',
           'scheduler': {'kind': 'pbs', 'required_resources': []}}
    return {'here': local, 'remote': hpc, 'appservice': deepcopy(APP_SERVICE)}


@contextmanager
def configured_families(directory):
    """Use the original constructors and literal catalogues for every family."""
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    from gene_annotation_episode.run_statistics import RunHistory
    from gene_annotation_episode.episodic_workflow.root.library.progress_information_credit import ProgressInformationCredit
    from gene_annotation_episode.episodic_workflow.root.episode import SignedRootEpisodeBinding
    from gene_annotation_episode.episodic_workflow.root.episode_journal import Journal
    from gene_annotation_episode.episodic_workflow.root.execution_episodes import ExecutionEpisodes
    from gene_annotation_episode.episodic_workflow.root.execution_binding_catalogue import execution_bindings
    from gene_annotation_episode.episodic_workflow.root.execution_family_composition import PARENTS as EXECUTION_PARENTS
    from gene_annotation_episode.episodic_workflow.root.execution_service_setup import _ProgressReader
    from gene_annotation_episode.episodic_workflow.root.resource_episodes import ResourceEpisodes
    from gene_annotation_episode.episodic_workflow.root.resource_binding_catalogue import resource_bindings, PARENTS as RESOURCE_PARENTS
    from gene_annotation_episode.episodic_workflow.root.homology_resource_adapter import HomologyResourceAdapter
    from gene_annotation_episode.episodic_workflow.root.hpc_service_composition import hpc_bindings, PARENTS as HPC_PARENTS
    from gene_annotation_episode.episodic_workflow.root.monitor_binding_catalogue import monitor_bindings
    from gene_annotation_episode.episodic_workflow.root.terminal_binding_catalogue import construct_fixed_children
    from gene_annotation_episode.episodic_workflow.root.literature_families import construct as literature_construct
    from gene_annotation_episode.episodic_workflow.root.scientific_process.episode import ScientificProcessEpisodes
    from gene_annotation_episode.episodic_workflow.root.legacy_annotation.episode import LegacyAnnotationEpisodeBinding
    from gene_annotation_episode.episodic_workflow.root.homology_jobs import HomologyJobs
    from gene_annotation_episode.episodic_workflow.root.execution_recording import HomologyStatistics
    from gene_annotation_episode.episodic_workflow.root.library.homology_job_inputs import FileAsset
    from gene_annotation_episode.episodic_workflow.root.library.homology_episode_family import HomologyEpisodes
    from gene_annotation_episode.episodic_workflow.root.library.resource_estimation import ResourceToolEstimator
    from gene_annotation_episode.episodic_workflow.root.library.resource_operational_credit import ResourceOperationalCredit

    with ExitStack() as cleanup:
        store = Store(directory / 'store')
        cleanup.callback(store.close)
        problem = store.create_problem(raw_sequence='ATGAAATAA', molecule='dna', role='gene')
        assert len(problem['subject_refs']) == 1
        journal = Journal(store, 'configured-root-descriptor-observer')
        services = SimpleNamespace(capabilities=lambda: (), model=forbidden)
        ports = {}
        tools = SimpleNamespace(store=store, clients={}, ordinary_flux_balance_backend=None,
            bind_molecular_sequence_results=lambda value: ports.__setitem__('molecular_results', value),
            bind_execution_owner=lambda value: ports.__setitem__('execution_owner', value))
        resources = _configuration(directory)
        execution_owner = ExecutionEpisodes(services, store=store, directory=directory / 'execution',
            run_id=journal.run_id, resources=resources, initial_information={}, tool_registry=tools,
            handoff_unit=3, acquired_record_unit=2, log_window_bytes=4, log_roles=['stdout', 'stderr'])
        execution = execution_bindings(execution_owner, parents=EXECUTION_PARENTS)
        assert len(execution) == 60
        assert ports['execution_owner'] is execution_owner
        assert ports['molecular_results'] is execution_owner.molecular_sequence_results
        assert execution_owner.api_execution.services['appservice'].service == 'bvbrc_appservice'

        fixtures = Path(__file__).parent / 'fixtures/public_callers'
        executable, database = fixtures / 'inert_native', fixtures / 'references.faa'
        policy = LocalJobPolicy(memory_bytes=128 * 1024 ** 2, scratch_bytes=8 * 1024 ** 2)
        jobs = HomologyJobs.create(directory / 'jobs',
            executable=FileAsset(executable, sha(executable.read_bytes())),
            reference_database=FileAsset(database, sha(database.read_bytes())), policy=policy, max_cpu=1)
        cleanup.callback(jobs.close)
        history_path = directory / 'history.sqlite3'
        history = RunHistory(history_path)
        history.close()
        statistics = HomologyStatistics(history_path, 'configured-observer-host', 1, 3)
        homology = HomologyEpisodes(jobs, parser_policy=policy, credit_projector=forbidden,
            credit_binding={'kind': 'explicit_unexecuted_operational_credit_port'},
            monitoring_projector=forbidden,
            monitoring_binding={'kind': 'explicit_unexecuted_monitoring_credit_port'}, statistics=statistics)
        homology_members = tuple(homology.implementation_for(role) for role in homology.roles) + tuple(
            homology.implementation_for_path((('improvement', 'host'),), child_role=role)
            for role in homology.roles)
        adapter = HomologyResourceAdapter(homology, store, journal, ResourceToolEstimator())
        resource_owner = ResourceEpisodes(services, resource_adapters=(adapter,))
        resource = resource_bindings(resource_owner, parents=RESOURCE_PARENTS)
        resource_credit = ResourceOperationalCredit(adapter.information, handoff_unit=3, acquired_record_unit=2)
        monitor_credit = ProgressInformationCredit(_ProgressReader(store, journal.run_id), information_unit=2)
        monitors = monitor_bindings(services, outcome_page_size=20, information_unit=2)
        hpc = hpc_bindings(services, store=store, run_id=journal.run_id, directory=directory / 'hpc',
            resources=resources, commissions={}, parents=HPC_PARENTS)
        terminal = construct_fixed_children(services, store=store, directory=directory / 'terminal',
            configuration={'resources': {'local': resources['here'], 'hpc': resources['remote']},
                           'initial_information': {}})
        literature = literature_construct(services, rate_population=True, a106_intervention=True)
        scientific = ScientificProcessEpisodes(services, library=EmptyCatalogPort(),
            tool_library=EmptyCatalogPort(), child_roles=('scientific_process', 'literature'))
        root_fixture = Path(__file__).parent / 'fixtures/fresh_decision_binding.json'
        annotation = SignedRootEpisodeBinding.from_record(json.loads(root_fixture.read_bytes()))
        improvement = LegacyAnnotationEpisodeBinding()
        families = {'Annotation': (annotation,), 'Execution': execution, 'HPC': hpc,
            'Homology': homology_members, 'Legacy improvement': (improvement,),
            'Literature': literature, 'Monitor': monitors, 'Resource': resource,
            'Scientific process': (scientific,), 'Terminal': terminal}
        assert {name: len(values) for name, values in families.items()} == FAMILY_COUNTS
        # This account records actual providers; it never substitutes a fake
        # Monitor or Resource credit implementation or calls either projector.
        configuration = {'resources': resources, 'initial_information': {},
            'execution_units': {'handoff_unit': 3, 'acquired_record_unit': 2},
            'monitor_credit': monitor_credit.as_record(), 'resource_credit': resource_credit.as_record(),
            'literature': {'rate_population': True, 'a106_intervention': True},
            'scientific_catalog': scientific.library.as_record(),
            'homology_external_projectors': 'explicit forbidden ports, never invoked',
            'default_tool_registry_executed': False, 'native_provider_transport_executed': False}
        yield families, configuration


class DescriptorReads:
    """Forward real reads unchanged, retaining their actual source operands."""
    def __init__(self, tree, selected):
        self.tree, self.selected = tree.resolve(strict=True), selected
        self.reads = []

    def __enter__(self):
        self.original = Path.read_bytes
        def read(path):
            value = self.original(path)
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(self.tree):
                raise AssertionError('descriptor read outside selected source tree: ' + str(path))
            target = resolved.relative_to(self.tree).as_posix()
            if target not in self.selected or sha(value) != self.selected[target]['sha256']:
                raise AssertionError('descriptor operand not selected or changed: ' + target)
            self.reads.append({'target': target, 'sha256': sha(value), 'bytes': len(value)})
            return value
        self.patch = patch.object(Path, 'read_bytes', read)
        self.patch.start()
        return self

    def __exit__(self, *exception):
        self.patch.stop()


def _definition(value, tree, selected):
    function = getattr(value, '__func__', value)
    file = Path(inspect.getsourcefile(function)).resolve(strict=True)
    target = file.relative_to(tree).as_posix()
    raw = file.read_bytes()
    assert sha(raw) == selected[target]['sha256'], target
    lines, start = inspect.getsourcelines(function)
    return {'module': function.__module__, 'qualname': function.__qualname__,
            'target': target, 'source_sha256': sha(raw), 'line': start,
            'definition_sha256': sha(''.join(lines).encode()), 'line_count': len(lines)}


def _literal_hash_account(binding, record, reads, tree, selected):
    """Independently evaluate the actual Homology/Monitor labelled hash map.

    The literal operand tuple is read from the selected defining function AST;
    no expected digest is supplied by metadata or copied from the returned
    descriptor. The serializer's exact canonical output is independently
    reproduced using the existing sorted compact JSON definition.
    """
    function = binding.as_record.__func__
    file = Path(inspect.getsourcefile(function)).resolve(strict=True)
    node = ast.parse(textwrap.dedent(inspect.getsource(function))).body[0]
    assignments = {target.id: statement.value for statement in node.body
        if isinstance(statement, ast.Assign) for target in statement.targets
        if isinstance(target, ast.Name)}
    paths = ast.literal_eval(assignments['paths'])
    assert isinstance(paths, tuple) and all(type(path) is str for path in paths)
    assert len(paths) == len(set(paths))
    root = assignments['root']
    assert ast.unparse(root).startswith('Path(__file__).resolve().parents[')
    depth = ast.literal_eval(root.slice)
    assert type(depth) is int and depth >= 0
    base = file.parents[depth]
    assert base == tree / ROOT_PATH
    operands = {}
    for label in paths:
        path = (base / label).resolve(strict=True)
        target = path.relative_to(tree).as_posix()
        digest = sha(path.read_bytes())
        assert digest == selected[target]['sha256']
        operands[label] = {'target': target, 'sha256': digest}
    expected_reads = Counter((row['target'], row['sha256']) for row in operands.values())
    # Homology's nested statistics record has no source-reading formula; any
    # unaccounted operand is an error, not silently omitted.
    assert Counter((row['target'], row['sha256']) for row in reads) == expected_reads
    value = sha(canonical({label: row['sha256'] for label, row in operands.items()}).encode())
    assert value == record['implementation_sha256']
    return {'formula': 'sha256(sorted_compact_json(label_to_sha256(source_bytes)))',
            'value': value, 'operands': operands, 'independently_recomputed': True}


def observe(tree, work, roster, selected, emit):
    """Return one truthful observation per roster home, or fail explicitly."""
    tree, work = tree.resolve(strict=True), work.resolve(strict=True)
    expected = {row['home']: row for row in roster['homes']}
    assert len(expected) == len(roster['homes']) == 159
    assert roster['counts']['by_family'] == FAMILY_COUNTS
    accounts = {}
    with configured_families(work) as (families, configuration):
        for family, bindings in families.items():
            for binding in bindings:
                cls = type(binding)
                declaration = _definition(cls, tree, selected)
                home = str(Path(declaration['target']).parent)
                assert home in expected and expected[home]['family'] == family
                assert home not in accounts
                row = {'home': home, 'family': family, 'class': declaration,
                    'roles': list(binding.roles),
                    'binding_path': getattr(binding, 'binding_path', None),
                    'commissioning_parent': getattr(binding, 'commissioning_parent', None),
                    'installed_claim': False}
                if family == 'Annotation':
                    assert not callable(getattr(binding, 'as_record', None))
                    with DescriptorReads(tree, selected) as trace:
                        record = {'task_credit': binding.task_credit.as_record(),
                                  'controller': binding.controller_record()}
                    row.update(record_interface='task_credit.as_record + controller_record',
                        descriptor=record, classification='configuration_records_without_source_fingerprint',
                        descriptor_reads=trace.reads,
                        producers=[_definition(type(binding).task_credit.fget, tree, selected),
                                   _definition(binding.controller_record, tree, selected)])
                elif family == 'Legacy improvement':
                    assert not callable(getattr(binding, 'as_record', None))
                    row.update(record_interface=None, descriptor=None,
                        classification='implicit_original_host_without_descriptor_api', descriptor_reads=[],
                        producers=[_definition(binding.decision_source_type, tree, selected),
                                   _definition(binding.source_credit_binding, tree, selected),
                                   _definition(binding.controller, tree, selected)])
                else:
                    producer = _definition(binding.as_record, tree, selected)
                    with DescriptorReads(tree, selected) as trace:
                        record = binding.as_record()
                    assert type(record) is dict
                    canonical(record)  # reject non-finite/non-serializable records
                    fingerprint = record.get('implementation_sha256')
                    row.update(record_interface='as_record', descriptor=record,
                        producers=[producer], descriptor_reads=trace.reads,
                        classification=('actual_source_fingerprint' if fingerprint is not None
                                        else 'configuration_only_descriptor'))
                    if fingerprint is not None:
                        assert type(fingerprint) is str and len(fingerprint) == 64
                        assert all(character in '0123456789abcdef' for character in fingerprint)
                        assert trace.reads, 'fingerprint has no authenticated source reads: ' + home
                    if family in ('Homology', 'Monitor'):
                        row['formula_account'] = _literal_hash_account(binding, record,
                            trace.reads, tree, selected)
                        assert len(row['formula_account']['operands']) == (29 if family == 'Homology' else 24)
                accounts[home] = row
                emit(row)
        assert set(accounts) == set(expected)
        assert Counter(row['family'] for row in accounts.values()) == FAMILY_COUNTS
        assert len({row['class']['module'] for row in accounts.values()}) == 159
        return {'version': 'configured_root_descriptor_observation_v1',
            'homes': accounts, 'home_count': 159, 'family_counts': FAMILY_COUNTS,
            'configuration': configuration, 'homology_formulas_verified': 6,
            'monitor_formulas_verified': 9,
            'scope': 'Actual configured constructors and descriptor/source operands; no task, scientific, provider, transport, native job or full restoration execution.'}
