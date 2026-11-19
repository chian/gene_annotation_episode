"""The task: run the plan of the commission, one tool unit per step.

A plan step is ``{'tool': name, 'arguments': {...}}``. The task asks no model. It always offers a unit and never
ends the Episode: after the plan it offers ``idle``; the yield controller stops the Episode at the plan's last
step. Each tool calls library functions of ``episode_support/jobs`` on ``ctx.store`` and returns closed JSON."""
from importlib import import_module
import json
from pathlib import Path

from episode_runtime import Rejected, ToolCall

LIBRARY = 'gene_annotation_episode.episodic_workflow.episode_support.'
CHILD_SLOTS = {}
SERVICES = ()
STAMP = '2026-11-19T00:00:00+00:00'
FIELDS = ['execution_status', 'measurements', 'log_windows', 'committed_record_refs', 'dependencies',
          'result_available']


def _module(path):
    return import_module(LIBRARY + path)


def idle(arguments, ctx):
    return {'idle': True}


# -- native measurements ---------------------------------------------------------------------------------------
def measurement(axis, index, *, duration_kind='complete', attempt=None):
    """One real measured native execution of ``axis``, as its records module types it."""
    recording = _module('records.' + axis + '.execution_recording')
    ExecutionClass, RunStatistic = recording.ExecutionClass, recording.RunStatistic
    scope = ExecutionClass(phase='pairwise_sequence_alignment', backend='local', resource_id='local_test',
                           implementation_sha256='a' * 64, parameters_sha256='b' * 64, memory_bytes=1 << 28,
                           scratch_bytes=1 << 26, cpu_threads=None, query_residues=10 + index,
                           reference_residues=20, reference_records=1, reference_state='available',
                           duration_measure='systemd_service_wall_seconds')
    statistic = RunStatistic(attempt_sha256=('%064x' % (index if attempt is None else attempt)),
                             source_sha256='%064x' % (1000 + index), observed_at=STAMP, outcome='succeeded',
                             duration_kind=duration_kind,
                             elapsed_seconds=None if duration_kind == 'unmeasured' else 1.5 + index,
                             condition_ref=None)
    return recording.NativeMeasurement(scope, statistic, 'unavailable_before_submission')


def native_timing(arguments, ctx):
    """Record four native measurements (one the repeat of another attempt, one with an unmeasured duration) and
    read the monitoring credit back through the table."""
    axis = arguments['axis']
    timing = _module('jobs.local_execution.' + axis + '.native_timing_information')
    measured = [measurement(axis, 1), measurement(axis, 2), measurement(axis, 3, attempt=2),
                measurement(axis, 4, duration_kind='unmeasured')]
    refs = [timing.record_native_measurement(ctx.store, one, operation='align_pair', operands=[])
            for one in measured]
    return {'axis': axis, 'scope': arguments['scope'], 'refs': refs, 'details': read_timing(axis, ctx.store, arguments['scope'], refs)}


def read_timing(axis, reader, scope, refs):
    """What the rows say: every measurement read back, and where the axis has the monitoring credit, that too."""
    timing = _module('jobs.local_execution.' + axis + '.native_timing_information')
    read = [timing.read_measurement(reader, ref).as_record() for ref in refs]
    if not hasattr(timing, 'NativeTimingInformation'):
        return {'measurements': read}
    return {'measurements': read, **timing.NativeTimingInformation(2.0).read_details(
        reader, scope, known_execution_refs=refs, initial_execution_refs=[], details_limit=None, details_offset=0)}


# -- practical job receipts, their job provider and their progress observations ----------------------------------
def publish_practical_job(arguments, ctx):
    """Publish the receipts one local job execution Episode leaves: one ``source`` per executed command."""
    axis = arguments['axis']
    digest = _module('records.' + axis + '.practical_execution_records').digest
    assignment = {'assignment_id': 'job-1', 'resource_kind': 'local', 'resource_id': 'local_test',
                  'endpoint': 'local_test', 'requested_job': {'command': ['true']}, 'completion_keys': ['answer']}
    scope = {'subject_refs': arguments['subject_refs']}
    sha = digest(assignment)
    snapshot = ctx.store.artifact(json.dumps({
        'version': 'practical_receipt_assignment_v1', 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
        'scope': scope, 'assignment': assignment}), 'application/json')
    refs = []
    for index, state in enumerate(arguments['states']):
        receipt = {'assignment_sha256': sha, 'finished_at': '2026-11-19T00:00:0%d+00:00' % index,
                   'outcome': {'facts': {'requested_job': {'status': state, 'returncode': 0 if state == 'completed'
                                                           else None}},
                               'native_outcome': {'output_snapshots': [
                                   {'path': 'answer.txt', 'available': state == 'completed',
                                    'size_bytes': 12 if state == 'completed' else None}]}}}
        artifact = ctx.store.artifact(json.dumps({
            'version': 'practical_receipt_information_v1', 'run_id': ctx.run_id, 'episode_id': ctx.episode_id,
            'assignment_sha256': sha, 'scope': scope, 'receipt': receipt}), 'application/json')
        refs.append(ctx.store.put('source', {
            'provider': 'episode.practical_receipt', 'accession': 'receipt-%d' % index, 'uri': None,
            'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': snapshot, 'version': None,
            'retrieved_at': None}, origin='tool')['id'])
    return {'source_refs': refs}


def progress_observe(arguments, ctx):
    """Observe the job the receipts record, twice (the second observation is the first), expose one more
    committed record, and read the observation back by its reference."""
    axis = arguments['axis']
    progress = _module('jobs.service_calls.' + axis + '.progress_provider')
    jobs = _module('jobs.service_calls.' + axis + '.job_provider').JobProvider(ctx.store)
    provider = progress.ProgressProvider(ctx.store, job_provider=jobs)
    handle = next(iter(jobs.jobs()))
    scope = jobs.scope(handle)
    first = provider.observe(handle, FIELDS, scope, permitted_committed_record_types=['source'])
    second = provider.observe(handle, FIELDS, scope, permitted_committed_record_types=['source'])
    exposure = provider.expose(handle, committed_record_refs=arguments['expose'])
    again = provider.expose(handle, committed_record_refs=arguments['expose'])
    third = provider.observe(handle, FIELDS, scope, permitted_committed_record_types=['source'])
    return {'axis': axis, 'handle': handle, 'scope': scope, 'first': first, 'second_is_first': second == first,
            'exposure': exposure, 'exposure_again_is_same': again == exposure, 'third': third,
            'read_back': provider.read_progress(first['progress_ref'], scope) == first,
            'resolves': [provider.resolve(first['progress_ref'], scope, 'progress'),
                         provider.resolve(exposure['publication_ref'], scope, 'progress_provenance'),
                         provider.resolve(handle, scope, 'execution_handle'),
                         provider.resolve('progress_nothing', scope, 'progress')],
            'description': provider.describe_target(handle, scope)['kind']}


def read_progress(reader, outcome):
    axis = outcome['axis']
    jobs = _module('jobs.service_calls.' + axis + '.job_provider').JobProvider(reader)
    provider = _module('jobs.service_calls.' + axis + '.progress_provider').ProgressProvider(reader, job_provider=jobs)
    return provider.read_progress(outcome['first']['progress_ref'], outcome['scope']) == outcome['first']


# -- provider jobs of remote searches ----------------------------------------------------------------------------
async def remote_search(arguments, ctx):
    """A BLAST search whose submission the real client refuses before any request is sent (no contact address is
    configured): the job row, its failure row, their descriptions, and the failure withdrawn when it is cleared."""
    axis = arguments['axis']
    acquisition = _module('acquisition.' + axis + '.acquisition')
    jobs = _module('jobs.service_calls.' + axis + '.provider_jobs')
    searches = jobs.RemoteSearches(ctx.store, acquisition.PublicClients(
        ncbi_email=None, access_dir=Path(arguments['directory'])), poll_interval_seconds=0)

    async def search():
        try:
            await searches.search('search-1', subject_ref=arguments['subject_ref'],
                                        query_fasta='>q\nMKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ\n',
                                        algorithm='blastp', database='swissprot',
                                        parameters={'hitlist_size': 5}, provider='blast')
        except acquisition.AcquisitionError as error:
            return {'code': error.code, 'job_ref': error.job_ref, 'outcome': error.submission_outcome,
                    'cause': error.operational['cause'] and error.operational['cause']['code']}
        return None
    first = await search()
    job_ref = first['job_ref']
    held = {'failure': ctx.store.table(jobs.PROVIDER_JOB_FAILURES).select({'job': job_ref}),
            'job': ctx.store.table(jobs.PROVIDER_JOBS).select({'job': job_ref})}
    described = searches.describe(job_ref)
    listed = [row['job_ref'] for row in searches.jobs()]
    listed_all = [row['job_ref'] for row in searches.jobs(active_only=False)]
    searches._update(job_ref, error_code=None)
    cleared = searches.describe(job_ref)
    withdrawn = ctx.store.table(jobs.PROVIDER_JOB_FAILURES).select({'job': job_ref}, withdrawn=True)
    return {'search': first, 'state': described['state'], 'cause': described['cause'] and described['cause']['code'],
            'listed': listed, 'listed_all': listed_all, 'cleared_cause': cleared['cause'],
            'failure_rows_live': len(held['failure']), 'job_rows': len(held['job']),
            'failure_revisions': [row['revision'] for row in withdrawn], 'withdrawn': [row['withdrawn'] for row in withdrawn],
            'artifacts_held': all(ctx.store.holds(ref) for ref in held['failure'][0]['artifact_refs']),
            'again': (await search())['job_ref'] == job_ref}


# -- registries of HPC requests and results, commission sources, component requests ------------------------------
def hpc_registry(arguments, ctx):
    """Register a request source the way each axis's HPC module does, and read it back through the table: the
    registered source is found, a source of another provider is not, an unregistered one is refused."""
    axis, scope = arguments['axis'], {'subject_refs': arguments['subject_refs']}
    hpc = _module('jobs.hpc.' + axis + '.hpc')
    body = {'version': hpc.VERSION, 'scope': scope, 'note': 'request'}
    if axis == 'structural_homology_evidence':
        request_ref = hpc._source(ctx.store, hpc.REQUEST_PROVIDER, body, scope)
        unregistered = hpc._source(ctx.store, hpc.RESULT_PROVIDER, {**body, 'note': 'result'}, scope)
        declaration = hpc.HPC_REQUESTS
    elif axis == 'evolutionary_history_evidence':
        request_ref = hpc._source(ctx.store, hpc.REQUEST_PROVIDER, body, arguments['subject_refs'])
        unregistered = hpc._source(ctx.store, hpc.RESULT_PROVIDER, {**body, 'note': 'result'},
                                   arguments['subject_refs'])
        declaration = hpc.NATIVE_REQUESTS
    else:
        request_ref = hpc.source(ctx.store, hpc.REQUEST_PROVIDER, body)
        unregistered = hpc.source(ctx.store, hpc.RESULT_PROVIDER, {**body, 'note': 'result'})
        declaration = hpc.HPC_REQUESTS
    try:
        hpc.request_body(ctx.store, request_ref)
    except ValueError as error:
        refused = str(error)
    ctx.store.table(declaration).put({'source_ref': request_ref, 'body': body})
    return {'request_ref': request_ref, 'unregistered_ref': unregistered, 'refused': refused,
            'registered': hpc.request_body(ctx.store, request_ref) == body,
            'other_provider': hpc.request_body(ctx.store, unregistered),
            'rows': [row['source_ref'] for row in ctx.store.table(declaration).select()]}


def component_request(arguments, ctx):
    """Publish a native component request source of the A107 component axis and read it back; its execution
    finding is the request the Episode holds."""
    native = _module('jobs.sequence_and_context_sources.component_axis_native_hpc')
    body = {'version': native.VERSION, 'axis': 'A107', 'scope': {'subject_refs': arguments['subject_refs']},
            'logical_work_sha256': 'c' * 64, 'resource_id': 'aurora', 'arguments_sha256': 'd' * 64,
            'request': {'selection': {'rows': 3}}}
    reference = native.publish(ctx.store, native.REQUEST_PROVIDER, body)
    return {'reference': reference, 'read': native.read(ctx.store, reference, native.REQUEST_PROVIDER) == body,
            'other_provider': native.read(ctx.store, reference, native.RESULT_PROVIDER),
            'findings': native.execution_findings(ctx.store, [reference], {'subject_refs': arguments['subject_refs']}),
            'rows': [row['source_ref'] for row in ctx.store.table(native.COMPONENT_REQUESTS).select()]}


TOOLS = {'idle': idle, 'native_timing': native_timing, 'publish_practical_job': publish_practical_job,
         'progress_observe': progress_observe, 'remote_search': remote_search,
         'hpc_registry': hpc_registry, 'component_request': component_request}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    item = summary['plan'][step]
    return ToolCall(item['tool'], item['arguments'])


def action(response, summary, records, ctx):
    raise Rejected({'library_probe': 'this episode asks no model'})
