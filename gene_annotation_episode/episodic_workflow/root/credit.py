"""Root investigation credit from authenticated received axis progress."""
from importlib import import_module
from .library.record_values import plain
from .root_axis_scalars import AXES
from .axis_return_admission import received_axis_task_credit

class RootCredit:

    @property
    def task_credit(self):
        from dataclasses import replace
        return replace(self.annotation_support, task_credit=True)

def _finding_progress_type(axis):
    module = {'A101': '.a101.investigation_progress', 'A102': '.a102.investigation_progress', 'A103': '.a103.investigation_progress', 'A104': '.a104.investigation_progress', 'A105': '.a105.investigation_progress', 'A106': '.a106.investigation_progress', 'A107': '.a107.investigation_progress', 'A108': '.a108.investigation_progress', 'A110': '.a110.investigation_progress'}[axis]
    return import_module(module, __package__).ScientificFindingProgress

def axis_progress_from_received(store, context, returned):
    """Reproject one axis's distinct received work in its private projector's native units.

    Each local task definition was checked against its original commission by
    ``received_axis_task_credit``. A native quality projection is used once;
    finding and resolved-use projections use their physical identity rules.
    """
    from .library.record_values import canonical, identity
    from .episode_receipts import EpisodeReceipts
    by_arm = {}
    for item in returned:
        key = (item['proposed_annotation_ref'], canonical(item['scope']), item['axis'])
        by_arm.setdefault(key, []).append(item)
    known_root = set(context.received_record_refs)
    receipts = EpisodeReceipts(store, context.run_id)
    progress = {}
    for (annotation, scope_key, axis), items in by_arm.items():
        scope = items[0]['scope']
        finding_type = _finding_progress_type(axis)
        if any((canonical(item['scope']) != scope_key for item in items)):
            raise ValueError('root_axis_original_scope_conflict')
        by_projection = {}
        for item in items:
            projector = item['credit_projector']
            kind = 'received_scientific_finding_progress' if isinstance(projector, finding_type) else projector.as_record()['kind']
            selected = by_projection.setdefault(kind, {'projector': projector, 'refs': set(), 'definitions': set()})
            if kind != 'received_scientific_finding_progress' and canonical(selected['projector'].as_record()) != canonical(projector.as_record()):
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
                pending.extend((reference for reference in receipts.forward_references(store.get(ref)) if reference in known_root))
            projector = selected['projector']
            assignment = {'scope': scope, 'proposed_annotation_ref': annotation}
            if isinstance(projector, finding_type):
                result = projector(store, scope, assignment=assignment, known_assessment_refs=sorted((ref for ref in references if ref.startswith('assessment_'))))
            else:
                result = projector(store, scope, assignment=assignment, known_record_refs=sorted(references))
            projected_tasks.append((projector, result))
            definitions.update(selected['definitions'])
        if axis == 'A102':
            from .a102.a102_credit import combine_received_task_progress
            value = combine_received_task_progress(projected_tasks)
        elif axis == 'A104':
            from .a104.a104_credit import combine_received_task_progress
            value = combine_received_task_progress(projected_tasks)
        else:
            if len(projected_tasks) != 1:
                raise ValueError('root_axis_single_projection_required')
            projector, result = projected_tasks[0]
            if axis in {'A105', 'A106', 'A107', 'A108', 'A110'}:
                if not isinstance(projector, finding_type):
                    raise ValueError('root_axis_private_finding_projector_required')
                value = projector.received_axis_credit(result)
            else:
                from gene_annotation_episode.episodic_workflow.root.a101.sequence_homology_evidence.native_correspondence_credit import A101SequenceCredit
                from .a103.a103_credit import A103ContextCredit
                projector_type = {'A101': A101SequenceCredit, 'A103': A103ContextCredit}.get(axis)
                if projector_type is None or not isinstance(projector, projector_type):
                    raise ValueError('root_axis_private_native_projector_required')
                value = result['credit']
        progress[annotation, scope_key, axis] = {'credit': value, 'credit_binding_ref': identity('axis_progress_binding', {'version': 'received_axis_progress_v1', 'axis': axis}), 'task_credit_binding_refs': sorted(definitions)}
    return progress

def project_collection_credit(store, context, rows, result):
    from .numerical import annotation_credit_summary
    from .library.record_values import canonical
    returned_credits = list(received_axis_task_credit(store, context))
    for returned in returned_credits:
        matches = [row for row in rows if row['proposed_annotation_ref'] == returned['proposed_annotation_ref'] and returned['axis'] in row['axis_components'] and (row['scope'] == returned['scope'])]
        if len(matches) != 1:
            raise ValueError('root_axis_return_requires_one_original_arm')
    progress = axis_progress_from_received(store, context, returned_credits)
    result['credit'] = {'mode': 'annotation_axis_credit', 'arms': [{'proposed_annotation_ref': row['proposed_annotation_ref'], 'subject_ref': row['subject_ref'], 'scope': row['scope'], 'axis': axis, 'credit': progress.get((row['proposed_annotation_ref'], canonical(row['scope']), axis), {}).get('credit', 0.0), 'credit_binding_ref': progress.get((row['proposed_annotation_ref'], canonical(row['scope']), axis), {}).get('credit_binding_ref'), 'task_credit_binding_refs': progress.get((row['proposed_annotation_ref'], canonical(row['scope']), axis), {}).get('task_credit_binding_refs', []), 'status': row['axis_status'][axis], 'transfer': row['axis_transfer'][axis]} for row in rows for axis in AXES]}
    annotation_credits, root_score = annotation_credit_summary(result['credit']['arms'])
    result['credit'].update(annotation_credits=annotation_credits, root_score=root_score)
