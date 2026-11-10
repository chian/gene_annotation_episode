"""Bind the actual receiver to declared contribution readers owned by each axis.

Scientific measurement selection, applicability and scalar mapping belong to
those owners. This module provides receiver identity and composition wiring.
"""
from dataclasses import replace

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
    from .scientific_process_reports import validate_process_result

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
        yield {'invocation_ref': invocation_ref,
            'proposed_annotation_ref': result['proposed_annotation_ref'],
            'scope': store.validate_scope(plain(child.scope)), 'axis': axis,
            'credit_binding_ref': result['credit_binding_ref'],
            'earned_credit': result['credit'] - result['initial_credit']}


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
