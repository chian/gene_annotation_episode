"""Real legacy Workflow/Store/Journal/Monitor; explicit inert ordinary/model ports.

No Episode identity/build/selected/registry/credit/receipt method is replaced.
Native status and handoff transport alone are controlled; no worker is launched.
"""
from gene_annotation_episode.episodic_workflow.root.a103.tests.hierarchy_paths import current_module_name as _a103_current_module_name
from contextlib import contextmanager
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a103'

def module(name):
    return import_module(_a103_current_module_name(PACKAGE + '.' + name))

def zero(*args, **kwargs):
    return 0.0

def forbidden(*args, **kwargs):
    raise AssertionError('unselected model/tool/native work is forbidden in direction fixture')

class ToolPort:

    def __init__(self, source):
        self.knowledge_library_directory = source
        self.launch_instruction_library_directory = source

    def workflow_services(self, workflow):
        return module('episode_services').WorkflowServices(workflow)

    def catalog(self, scope=None):
        return []
    execute = forbidden

class ProviderPort:
    complete = forbidden

def raw_rows(flow):
    available = {r[0] for r in flow.store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    tables = [n for n in ('runtime_episodes', 'runtime_actions', 'runtime_observations', 'runtime_report_attempts', 'runtime_receipt_inheritance', 'runtime_record_receipts', 'runtime_progress_receipts', 'runtime_progress_deliveries') if n in available]
    return {name: [dict(row) for row in flow.store.db.execute('SELECT * FROM ' + name + ' WHERE run_id=? ORDER BY rowid', (flow.run_id,))] for name in tables}

def form():
    return {'type': 'object', 'properties': {'state': {'type': 'string', 'enum': ['unresolved']}}, 'required': ['state'], 'additionalProperties': False}

@contextmanager
def actual(directory, *, parent='annotation', marker=False, receipts=False, role='job_monitor', inprocess_completion_order=None):
    assert parent in ('annotation', 'improvement') and type(marker) is bool and (type(receipts) is bool)
    assert role in ('job_launch', 'job_monitor', 'job_results')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    library = directory / 'instruction-source'
    library.mkdir(exist_ok=True)
    raw = json.dumps({'version': 'tool_knowledge_v1', 'entries': []}, sort_keys=True) + '\n'
    if (library / 'index.json').exists():
        assert (library / 'index.json').read_text() == raw
    else:
        (library / 'index.json').write_text(raw)
    with module('state').Store(directory / 'store') as store:
        try:
            store.problem()
        except module('domain').ContractError as error:
            if str(error) != 'problem_not_initialized':
                raise
            store.create_problem(raw_sequence='MACDEFGH', molecule='protein')
        query = store.targets()[0]['id']
        scope = store.validate_scope()
        jm = module('homology_jobs')
        policy = module('local_jobs').LocalJobPolicy(128 * 1024 ** 2, 4 * 1024 ** 2)
        if not (directory / 'jobs/configuration.json').exists():
            program = directory / 'unexecuted-program'
            program.write_text('engineering identity; never execute\n')
            database = directory / 'reference.faa'
            database.write_text('>fixture\nMACDEFGH\n')
            jobs = jm.HomologyJobs.create(directory / 'jobs', executable=jm.FileAsset(program, jm.digest(program)), reference_database=jm.FileAsset(database, jm.digest(database)), policy=policy, max_cpu=1)
        else:
            jobs = jm.HomologyJobs(directory / 'jobs')
        try:
            families = module('homology_service_setup').create_homology_bindings(jobs, parser_policy=policy, credit_projector=zero, credit_binding={'version': 'engineering-no-operational-credit'}, monitoring_projector=module('monitoring_credit').MonitoringInformationCredit(information_unit=3), monitoring_binding={'version': 'engineering-original-information-unit', 'information_unit': 3})
            parent_home = 'legacy_' + parent
            bindings = families[parent_home]
            binding = bindings[role]
            runtime = module('runtime')
            job = jobs.order(query_ref=query, query_fasta='>query\nMACDEFGH\n', cpu=1, operation_key='original-direction-job')
            handoff = {'job_ref': job, 'registry_ref': jobs.config['registry_ref'], 'backend': jm.VERSION, 'status_interface': 'homology.status.v1', 'progress_interface': 'homology.progress.v1', 'results_interface': 'homology.results.v1'}
            status = {'job_ref': job, 'registry_ref': jobs.config['registry_ref'], 'state': 'running', 'outcome': 'pending', 'elapsed_seconds': 1.0, 'duration_measure': 'systemd_service_wall_seconds', 'native_returncode': None, 'failure_code': None, 'resource': None, 'progress_kind': 'native_execution_state_and_output_bytes_not_search_fraction', 'outputs': [{'role': role, 'available': False, 'bytes': None, 'writer_closed': False} for role in jm.OUTPUTS]}
            original_handoff = jm.HomologyJobs.handoff
            original_status = jm.HomologyJobs.status

            def fixture_job(receiver, job_ref):
                if type(receiver) is not jm.HomologyJobs or receiver.directory != jobs.directory or receiver.config != jobs.config or (job_ref != job):
                    return False
                assert receiver._row(job_ref) == jobs._row(job_ref)
                return True

            def controlled_handoff(receiver, job_ref):
                if fixture_job(receiver, job_ref):
                    return deepcopy(handoff)
                return original_handoff(receiver, job_ref)

            def controlled_status(receiver, job_ref):
                if fixture_job(receiver, job_ref):
                    return deepcopy(status)
                return original_status(receiver, job_ref)
            with patch.object(jm.HomologyJobs, 'handoff', controlled_handoff), patch.object(jm.HomologyJobs, 'status', controlled_status):
                flow = runtime.Workflow(store, ToolPort(library), ProviderPort(), directory / 'workflow', 'homology-directions', controller_factory=forbidden, project_credit=zero, job_episodes=binding, episode_binding_factories=(), root_role=parent, annotation_child_roles=(role,) if marker else None, episode_record_receipts=receipts, initial_known_record_refs=[query] if receipts else None, root_action_boundary=None, inprocess_completion_order=inprocess_completion_order)
                families = flow.homology_episode_bindings
                bindings = families[parent_home]
                binding = bindings[role]
                root = flow.build(parent, 'original-parent', 'Preserve the requested execution information.', scope)
                source = root.source
                assert type(flow) is runtime.Workflow and source.path == ((parent, 'original-parent'),)
                home = {'job_launch': 'homology_job_submission', 'job_monitor': 'homology_job_monitoring', 'job_results': 'homology_result_acquisition'}[role]
                assert type(binding) is module(parent_home + '.' + home + '.episode').HomologyEpisode
                assert type(source) is flow.legacy_parent_for_path(source.path).decision_source_type
                assert flow.job_episode_for_child(source.path, role) is binding
                assert flow.specialist(source) is None
                selection = {'kind': 'job_child', 'role': role, 'goal': 'Observe the originally assigned execution.', 'scope': deepcopy(scope), 'purpose': 'Return only the requested unresolved interpretation.', 'schema_json': json.dumps(form()), 'initial_report_json': json.dumps({'state': 'unresolved'}), **({'existing_job_ref': job} if role == 'job_launch' else {'handoff': deepcopy(handoff)}), **({'prior_sample_refs': []} if role == 'job_monitor' else {})}
                yield SimpleNamespace(flow=flow, root=root, source=source, binding=binding, bindings=bindings, jobs=jobs, store=store, scope=scope, selection=selection, job=job, directory=directory, status=status, role=role, parent=parent, parent_home=parent_home, families=families)
        finally:
            jobs.close()

def commission(f, index=0, selection=None):
    selection = deepcopy(f.selection if selection is None else selection)
    unit = f.flow.selected(f.source, selection, index)
    assert type(unit.child.source) is f.binding.decision_source_type
    assert f.flow.job_episode_for_path(unit.child.source.path) is f.binding
    identity = module('runtime').Episode.identity(f.flow.context, f.flow.grains[f.role], 'child_' + str(index), parent_path=f.source.path)
    row = f.flow.journal.row('runtime_episodes', identity.episode_id)
    assert row is not None
    request = json.loads(row['request'])
    message = request['message']
    assert message['job_assignment']['job_ref'] == f.job and message['scope'] == module('communication').plain(f.scope)
    assert message['initial_report'] == {'state': 'unresolved'}
    assert json.loads(f.flow.journal.row('runtime_actions', f.source.episode_id, index)['action']) == selection
    return {'unit_type': type(unit).__module__ + '.' + type(unit).__qualname__, 'child_id': identity.episode_id, 'request_raw': row['request'], 'path_raw': row['path'], 'assignment': message['job_assignment'], 'descriptor': deepcopy(f.binding.as_record()), 'rows': raw_rows(f.flow), 'owner_module': type(f.binding).__module__, 'task_module': type(unit.child.source).__module__, 'binding_path': f.binding.binding_path}
