"""Parent-visible access diagnostics for the A107/A110 source work it owns.

Access notices are control metadata. The own-inspection view redisplays only
that episode's already received source operands and component results. No new
scientific receipt, credit, permission, retry, wake-up or stop is created here.
"""
import json

from .communication import plain
from .domain import identity
from .episode_return_records import EpisodeReturnRecords
from .scientific_process_records import SELECTION_VERSION


VERSION = 'component_axis_source_access_v1'
ERROR = 'literature_reading_outside_assigned_source'
AXES = {'A107', 'A110'}
RECOVERY = (
    'This page/reader is restricted to its assigned Source and derived Sources. '
    'A received sibling dataset is still outside that reading assignment. '
    'An owning literature, strategy or search parent with both received Sources '
    'can perform the joint calculation. Alternatively select supported operands '
    'entirely within the assigned source. Report the particular missing access '
    'to the parent; repeating the rejected read does not widen this assignment. '
    'This is an access limitation, not scientific absence or opposition.')


def source_received_inputs(tools, name, arguments, scope, operation_key, selected):
    """Bind an original source-reader action across frozen/plain scope views.

    This passes only its existing receipt set. Explicit subsets stay selected;
    an unbound action, a different invocation or an unauthenticated context
    acquires no extra source access. No record, evidence or credit is created.
    """
    if selected is not None or name not in {'source.locate', 'source.sequence.scan',
            'source.sequence.references', 'source.experimental.records'}:
        return selected
    invocation = tools._current_invocation.get()
    if invocation is None or operation_key is None or invocation[2:] != (name, arguments, operation_key):
        return None
    context = invocation[0]
    try:
        if tools.store.validate_scope(scope) != plain(context.scope):
            return None
        exists = tools.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='runtime_episodes'").fetchone()
        if exists is None:
            return ()
        EpisodeReturnRecords(tools.store, context.run_id,
            failure_prefix='component_source_').authenticate(context)
    except (ValueError, KeyError, TypeError):
        return ()  # Prevent the generic fallback from binding an invalid host context.
    return tuple(context.received_record_refs)


def _rows(workflow):
    return workflow.store.db.execute('SELECT episode_id,path,state, '
        "json_extract(request,'$.message.episode_assignment.selection.version') selection_version, "
        "json_extract(request,'$.message.episode_assignment.selection.evidence_axis.option_id') axis, "
        "json_extract(request,'$.message.episode_assignment.page.source_ref') page_source, "
        "json_extract(request,'$.message.episode_assignment.source_ref') source "
        'FROM runtime_episodes WHERE run_id=? ORDER BY episode_id', (workflow.run_id,)).fetchall()


def _path(row):
    return tuple(map(tuple, json.loads(row['path'])))


def _axes(rows):
    return {_path(row): row['axis'] for row in rows
        if row['selection_version'] == SELECTION_VERSION}


def _axis(axes, path):
    for length in range(len(path), 0, -1):
        if path[length - 1][0] == 'scientific_process':
            return axes.get(path[:length])
    return None


def rejection_detail(workflow, context, root, blocked):
    if workflow is None or not hasattr(getattr(workflow, 'store', None), 'db'):
        return None
    if _axis(_axes(_rows(workflow)), context.path) not in AXES:
        return None
    return {'version': VERSION, 'assigned_source_ref': root,
        'blocked_source_refs': sorted(set(blocked)),
        'scientific_inference_authorized': False, 'recovery': RECOVERY}


def decision_context(workflow, context):
    if (workflow.receipts is None or not hasattr(workflow.store, 'db')
            or context.role not in {'annotation', 'scientific_process'}
                and not context.role.startswith('literature')):
        return None
    rows = _rows(workflow)
    axes = _axes(rows)
    axis = _axis(axes, context.path)
    root = context.role == 'annotation' and len(context.path) == 1
    if axis not in AXES and not root:
        return None
    EpisodeReturnRecords(workflow.store, workflow.run_id,
        failure_prefix='component_source_access_').authenticate(context)
    known = set(context.received_record_refs)
    assignment = plain(context.assignment)
    page = assignment if context.role == 'literature_page' else assignment.get('page')
    result = {'version': VERSION, 'operational_metadata_only': True,
        'permission_and_receipt_changes': False, 'recovery': RECOVERY}
    if axis in AXES or root and any(value in AXES for value in axes.values()):
        from .component_axis_inspection import inspection_index
        inspected = inspection_index(workflow.store, run_id=workflow.run_id,
            episode_id=context.episode_id, known_source_refs=known)
        if inspected is not None:
            result['own_source_inspection'] = inspected
            result['operational_metadata_only'] = False
            result['already_received_information_only'] = True
    if axis in AXES and page is not None:
        result['own_assigned_source_ref'] = page['source_ref']
    notices, seen = [], set()
    for row in rows:
        path = _path(row)
        if (len(path) < len(context.path) or path[:len(context.path)] != context.path
                or _axis(axes, path) not in AXES):
            continue
        failures = workflow.store.db.execute('SELECT decision_index, '
            "json_extract(action,'$.tool') tool, "
            "json_extract(action,'$.arguments.source_ref') source_ref, "
            "json_extract(action,'$.arguments.data_source_ref') data_source_ref, "
            "json_extract(result,'$.feedback.detail.blocked_source_refs') blocked "
            'FROM runtime_actions WHERE run_id=? AND episode_id=? '
            "AND json_extract(result,'$.feedback.code')=? ORDER BY decision_index DESC",
            (workflow.run_id, row['episode_id'], ERROR))
        for failure in failures:
            assigned = row['source'] if path[-1][0] == 'literature_page' else row['page_source']
            blocked = (json.loads(failure['blocked']) if failure['blocked'] is not None else
                [value for value in (failure['source_ref'], failure['data_source_ref'])
                    if value is not None and value != assigned])
            key = (row['episode_id'], failure['tool'], tuple(sorted(blocked)))
            if key in seen:
                continue
            seen.add(key)
            branch = path[len(context.path)] if len(path) > len(context.path) else None
            notices.append({'handle': identity('source_access_need', {
                    'run_id': workflow.run_id, 'receiver': context.episode_id,
                    'requester': row['episode_id'], 'decision_index': failure['decision_index']}),
                'own_attempt': branch is None,
                'owned_child_role': None if branch is None else branch[0],
                'owned_child_label': None if branch is None else branch[1],
                'requesting_role': path[-1][0], 'requester_state': row['state'],
                'rejected_operation': failure['tool'], 'code': ERROR,
                'assigned_source_ref': assigned if assigned in known else None,
                'blocked_received_source_refs': sorted(set(blocked) & known),
                'other_rejected_input_count': len(set(blocked) - known),
                'status': 'retained_access_rejection; parent_reassesses_remaining_need',
                'meaning': 'No scientific contents delivered; no absence or opposition inferred.'})
    if not notices and not {'own_assigned_source_ref', 'own_source_inspection'}.intersection(result):
        return None
    result.update(notices=notices[:12], total_distinct_notices=len(notices),
        omitted_notices=max(0, len(notices) - 12),
        parent_use='Metadata from actual owned child branches is available on the next '
            'decision. This notice does not reassign work or promise a reply.')
    return result
