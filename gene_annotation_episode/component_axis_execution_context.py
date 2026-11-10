"""Project received native-request/host-commission links for the next decision.

This is operational metadata over actual producer records and receipts. It
does not grant a Source, submit a job, infer job state or publish evidence.
"""
import hashlib
import json

from .communication import plain
from .component_axis_native_hpc import REQUEST_PROVIDER, read
from .domain import canonical
from .episode_return_records import EpisodeReturnRecords
from .hpc_commission_sources import read as read_commission


VERSION = 'component_axis_execution_context_v1'
MEANING = (
    'These links join original prepared native requests to host commission Sources '
    'actually received by this episode. A scientific request reference is not a '
    'commission_source_ref. Use the recorded hpc_assignment with its original scope '
    'if commissioning the existing HPC owner. Check actual pending work and owner '
    'state first: this metadata establishes neither submission nor completion and '
    'must not cause duplicate execution. Scientific results require their original '
    'authenticated publication and grader; these links carry no scientific credit. '
    'The HPC result recorded-fact source is hpc_result_refs; obtain its actual '
    'saved-fact type through episode.return_contract for role hpc.')


def _matching_actions(store, context, reference, body):
    rows = store.db.execute(
        "SELECT request,result FROM component_native_actions WHERE "
        "json_extract(result,'$.status')='completed' AND "
        "json_extract(result,'$.result.request_ref')=?", (reference,))
    for row in rows:
        signature, outcome = json.loads(row['request']), json.loads(row['result'])
        if (signature.get('run_id') != context.run_id
                or signature.get('version') != body['version']
                or signature.get('scope') != body['scope']
                or signature.get('operation') != body['operation']
                or hashlib.sha256(canonical(signature.get('arguments')).encode()).hexdigest()
                    != body.get('arguments_sha256')):
            continue
        result = outcome.get('result', {})
        commission_ref = result.get('commission_source_ref')
        if (not commission_ref
                or result.get('hpc_assignment') != {'commission_source_ref': commission_ref}
                or not {reference, commission_ref} <= set(outcome.get('record_refs', ()))):
            continue
        yield commission_ref


def prepared_assignments(store, *, context, execution_findings, resources):
    """Use both delivered Sources; an undelivered grant remains undisclosed."""
    pending = [row for row in execution_findings
        if row.get('status') == 'native_work_requested'
        and not row.get('superseded_by_received_admission')
        and row.get('run_id') == context.run_id]
    if not pending:
        return None
    EpisodeReturnRecords(store, context.run_id,
        failure_prefix='component_execution_').authenticate(context)
    known = set(context.received_record_refs)
    installed = store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='component_native_actions'").fetchone() is not None
    requests = []
    for row in pending:
        reference = row['request_ref']
        if reference not in known:
            continue
        body = read(store, reference, REQUEST_PROVIDER)
        if (body is None or body['run_id'] != context.run_id
                or not store.scope_contains(plain(context.scope), body['scope'])):
            continue
        received = sorted(set(_matching_actions(store, context, reference, body)) & known) if installed else []
        commissions = []
        for commission_ref in received:
            entry = {'commission_source_ref': commission_ref, 'hpc_assignment': None,
                'validation_failure': None}
            if resources is None:
                entry['validation_failure'] = 'execution_resources_not_configured'
            else:
                try:
                    commission = read_commission(store, commission_ref,
                        scope=body['scope'], resources=resources)
                    if commission['resource_id'] != body['resource_id']:
                        raise ValueError('received_commission_resource_conflict')
                    entry['hpc_assignment'] = {'commission_source_ref': commission_ref}
                except (ValueError, KeyError, TypeError, OSError) as error:
                    entry['validation_failure'] = str(error)
            commissions.append(entry)
        requests.append({'axis': body['axis'], 'request_ref': reference,
            'scope': plain(body['scope']), 'resource_id': body['resource_id'],
            'logical_work_sha256': body['logical_work_sha256'],
            'received_commissions': commissions,
            'link_status': 'matching_received_commissions' if commissions
                else 'no_matching_commission_in_received_subset'})
    return {'version': VERSION, 'meaning': MEANING, 'requests': requests}
