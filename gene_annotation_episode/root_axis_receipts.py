"""Bind the actual receiver to declared contribution readers owned by each axis.

Scientific measurement selection, applicability and scalar mapping belong to
those owners. This module provides receiver identity and composition wiring.
"""
from dataclasses import replace
import json

from .communication import plain
from .episode_return_records import EpisodeReturnRecords


def receiver_context(store, run_id, episode_id, known_record_refs):
    if not run_id or not episode_id:
        raise ValueError('signed_root_actual_receiver_identity_required')
    if store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_episodes'").fetchone() is None:
        raise ValueError('signed_root_saved_context_required')
    context = EpisodeReturnRecords(store, run_id, failure_prefix='signed_root_').context(episode_id)
    return replace(context, received_record_refs=tuple(known_record_refs))


def received_axis_task_credit(store, context):
    """Yield each immediate child's own credited result once from typed returns."""
    from .scientific_process_records import selection_fields, scientific_digest
    from .scientific_process_reports import validate_process_result, credit_binding_ref
    from .scientific_process_episodes import original_axis_task_projector

    returns = EpisodeReturnRecords(store, context.run_id, failure_prefix='signed_root_')
    seen = {}
    for child, form, schema in returns.received_attempts(context):
        if child.path[:-1] != context.path or child.role != 'scientific_process':
            continue
        fields = [name for name, node in schema.get('properties', {}).items()
            if node.get('x-source') == 'scientific_process_results']
        if len(fields) != 1 or not isinstance(form.get(fields[0]), list):
            raise ValueError('root_axis_return_requires_process_result')
        invocation_ref = child.request['message'].get('scientific_invocation_ref')
        own = [validate_process_result(item) for item in form[fields[0]]
            if item.get('invocation_ref') == invocation_ref]
        if len(own) != 1:
            raise ValueError('root_axis_own_process_result_required')
        result = own[0]
        digest = scientific_digest(result)
        if invocation_ref in seen:
            if seen[invocation_ref] != digest:
                raise ValueError('root_axis_replayed_result_conflict')
            continue
        seen[invocation_ref] = digest
        selection = plain(child.assignment['selection'])
        axis = selection[selection_fields(selection)[0]]['option_id']
        if (result['selection']['evidence_axis']['option_id'] != axis
                or result['proposed_annotation_ref'] != child.assignment.get('proposed_annotation_ref')
                or result['credit_kind'] != 'scientific'
                or result['credit_binding_ref'] is None):
            raise ValueError('root_axis_local_credit_definition_or_assignment_conflict')
        projector = original_axis_task_projector(axis, child.assignment, merged_a102=True)
        definition = {**plain(projector.as_record()),
            'proposed_annotation_ref': result['proposed_annotation_ref']}
        expected = credit_binding_ref({'credit_kind': 'scientific', 'credit_binding': definition})
        if result['credit_binding_ref'] != expected:
            raise ValueError('root_axis_original_task_credit_definition_conflict')
        admitted = []
        for attempt in store.db.execute('SELECT decision_index FROM runtime_report_attempts '
                'WHERE run_id=? AND parent_episode_id=? AND child_episode_id=? '
                'AND failure IS NULL AND form IS NOT NULL ORDER BY decision_index',
                (context.run_id, context.episode_id, child.episode_id)):
            index = attempt['decision_index']
            recorded_child, recorded_form, recorded_schema = returns._attempt(context, index)
            if (recorded_child.episode_id != child.episode_id
                    or not returns._equal(recorded_form, form)
                    or not returns._equal(recorded_schema, schema)):
                continue
            projection = returns.recorded_admission_references(context, form, schema, index)
            if projection is not None:
                admitted.extend(projection)
                continue
            action = store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? '
                'AND episode_id=? AND decision_index=?',
                (context.run_id, context.episode_id, index)).fetchone()
            if action is None or action['result'] is None:
                continue
            outcome = json.loads(action['result'])
            if outcome.get('status') != 'completed' or not isinstance(outcome.get('record_refs'), list):
                continue
            for ref in outcome['record_refs']:
                if not isinstance(ref, str):
                    raise ValueError('root_axis_original_return_reference_not_received')
                record = store.get(ref)
                if record['record_type'] == 'collection_member':
                    continue
                if ref not in context.received_record_refs:
                    raise ValueError('root_axis_original_return_reference_not_received')
                receipt = store.db.execute('SELECT receipt_kind,source_index FROM runtime_record_receipts '
                    'WHERE run_id=? AND episode_id=? AND record_ref=?',
                    (context.run_id, context.episode_id, ref)).fetchone()
                if not ((receipt is not None and receipt['receipt_kind'] == 'child_form'
                        and receipt['source_index'] == index)
                        or returns._received_before(context.episode_id, ref, index)):
                    raise ValueError('root_axis_original_return_reference_not_received')
                admitted.append(ref)
        yield {'invocation_ref': invocation_ref,
            'proposed_annotation_ref': result['proposed_annotation_ref'],
            'scope': store.validate_scope(plain(child.scope)), 'axis': axis,
            'credit_binding_ref': result['credit_binding_ref'],
            'earned_credit': result['credit'] - result['initial_credit'],
            'assignment': plain(child.assignment),
            'credit_projector': projector,
            'record_refs': sorted(set(admitted) & set(context.received_record_refs))}


def axis_progress_from_received(store, context, returned):
    """Reproject one axis's distinct received work in its owner's native units.

    Each local task definition was checked against its original commission by
    ``received_axis_task_credit``. A native quality projection is used once;
    finding and resolved-use projections use their physical identity rules.
    """
    from .domain import canonical, identity
    from .episode_receipts import EpisodeReceipts
    from .investigation_progress import ScientificFindingProgress

    by_arm = {}
    for item in returned:
        key = (item['proposed_annotation_ref'], canonical(item['scope']), item['axis'])
        by_arm.setdefault(key, []).append(item)
    known_root = set(context.received_record_refs)
    receipts = EpisodeReceipts(store, context.run_id)
    progress = {}
    for (annotation, scope_key, axis), items in by_arm.items():
        scope = items[0]['scope']
        if any(canonical(item['scope']) != scope_key for item in items):
            raise ValueError('root_axis_original_scope_conflict')
        by_projection = {}
        for item in items:
            projector = item['credit_projector']
            kind = ('received_scientific_finding_progress'
                if isinstance(projector, ScientificFindingProgress) else
                projector.as_record()['kind'])
            selected = by_projection.setdefault(kind, {'projector': projector, 'refs': set(),
                'definitions': set()})
            if (kind != 'received_scientific_finding_progress'
                    and canonical(selected['projector'].as_record()) != canonical(projector.as_record())):
                raise ValueError('root_axis_same_task_definition_changed')
            selected['refs'].update(item['record_refs'])
            selected['definitions'].add(item['credit_binding_ref'])
        projected_tasks = []
        definitions = set()
        for selected in by_projection.values():
            references = {annotation, *scope['subject_refs']}
            pending = list(selected['refs'])
            while pending:
                ref = pending.pop()
                if ref in references or ref not in known_root:
                    continue
                references.add(ref)
                pending.extend(reference for reference in
                    receipts.forward_references(store.get(ref)) if reference in known_root)
            projector = selected['projector']
            assignment = {'scope': scope, 'proposed_annotation_ref': annotation}
            if isinstance(projector, ScientificFindingProgress):
                result = projector(store, scope, assignment=assignment,
                    known_assessment_refs=sorted(ref for ref in references
                        if ref.startswith('assessment_')))
            else:
                result = projector(store, scope, assignment=assignment,
                    known_record_refs=sorted(references))
            projected_tasks.append((projector, result))
            definitions.update(selected['definitions'])
        if axis == 'A102':
            from .a102_credit import combine_received_task_progress
            value = combine_received_task_progress(projected_tasks)
        elif axis == 'A104':
            from .a104_credit import combine_received_task_progress
            value = combine_received_task_progress(projected_tasks)
        else:
            if len(projected_tasks) != 1:
                raise ValueError('root_axis_single_owner_projection_required')
            projector, result = projected_tasks[0]
            if axis in {'A105', 'A106', 'A107', 'A108', 'A110'}:
                if not isinstance(projector, ScientificFindingProgress):
                    raise ValueError('root_axis_finding_owner_required')
                value = projector.received_axis_credit(result)
            else:
                from .a101_credit import A101SequenceCredit
                from .a103_credit import A103ContextCredit
                owner = {'A101': A101SequenceCredit, 'A103': A103ContextCredit}.get(axis)
                if owner is None or not isinstance(projector, owner):
                    raise ValueError('root_axis_native_owner_required')
                value = result['credit']
        progress[annotation, scope_key, axis] = {
            'credit': value,
            'credit_binding_ref': identity('axis_progress_binding',
                {'version': 'received_axis_progress_v1', 'axis': axis}),
            'task_credit_binding_refs': sorted(definitions)}
    return progress


def axis_contribution_readers(store, run_id):
    from .a101_credit import A101SequenceCredit
    from .a102_credit import A102StructuralCredit
    from .a103_credit import A103ContextCredit
    from .a104_credit import A104EvolutionaryCredit
    from .literature_a105_aggregation_storage import LiteratureA105AggregationRepository
    from .literature_a106_subscore_storage import LiteratureA106SubscoreRepository
    from .literature_a108_aggregation_storage import LiteratureA108AggregationRepository
    from .a107_qualification import annotation_contribution as a107
    from .a110_qualification import annotation_contribution as a110
    return {'A101': A101SequenceCredit().annotation_contribution,
        'A102': A102StructuralCredit().annotation_contribution,
        'A103': A103ContextCredit().annotation_contribution,
        'A104': A104EvolutionaryCredit().annotation_contribution,
        'A105': LiteratureA105AggregationRepository(store, run_id).annotation_contribution,
        'A106': LiteratureA106SubscoreRepository(store, run_id).annotation_contribution,
        'A107': a107, 'A108': LiteratureA108AggregationRepository(store, run_id).annotation_contribution,
        'A110': a110}
