"""Experimental root composition of independently graded evidence axes.

The root recomputes from its own receipts. Its offset product is an explicit
progress policy, without any assertion of statistical independence or function
probability. Adding an empty dimension cannot change the unnormalised score.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import math


VERSION = 'native_evidence_root_offset_product_v1'
AXES = ('A101', 'A102', 'A103')


def offset_volume(evidence):
    if not evidence:
        raise ValueError('evidence_root_nonempty_axis_vector_required')
    for axis, value in evidence.items():
        if not isinstance(axis, str) or not axis or type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('evidence_root_axis_value_outside_unit_interval')
    terms = []
    attribution = dict.fromkeys(evidence, 0.)
    for size in range(1, len(evidence) + 1):
        for members in combinations(evidence, size):
            value = math.prod(evidence[axis] for axis in members)
            terms.append({'axes': list(members), 'value': value})
            for axis in members:
                attribution[axis] += value / size
    additive = math.fsum(row['value'] for row in terms if len(row['axes']) == 1)
    interaction = math.fsum(row['value'] for row in terms if len(row['axes']) > 1)
    return {'credit': math.fsum([additive, interaction]), 'additive': additive,
        'interaction': interaction, 'terms': terms, 'attribution': attribution,
        'maximum': 2 ** len(evidence) - 1}


def _projector(axis):
    if axis == 'A101':
        from .a101_credit import A101SequenceCredit
        return A101SequenceCredit()
    if axis == 'A102':
        from .a102_credit import A102StructuralCredit
        return A102StructuralCredit()
    if axis == 'A103':
        from .a103_credit import A103ContextCredit
        return A103ContextCredit()
    raise ValueError('evidence_root_axis_scorer_not_bound')


@dataclass(frozen=True)
class NativeEvidenceRootCredit:
    axes: tuple = AXES
    requires_episode_receipts = True
    requires_known_record_refs = True

    def __post_init__(self):
        if not self.axes or len(set(self.axes)) != len(self.axes):
            raise ValueError('evidence_root_unique_enabled_axes_required')
        for axis in self.axes:
            _projector(axis)
        object.__setattr__(self, 'axes', tuple(self.axes))

    def as_record(self):
        return {'kind': 'native_evidence_root', 'version': VERSION,
            'axes': list(self.axes), 'formula': 'product(1 + received_axis_credit) - 1',
            'maximum': 2 ** len(self.axes) - 1,
            'scope_aggregation': 'offset_product_per_target_then_scope_length_weighted_mean',
            'axis_graders': {axis: _projector(axis).as_record() for axis in self.axes},
            'receipt': 'receiving_root_explicit_known_record_refs',
            'missing': 'zero_earned_credit_with_unknown_evidence_status_retained',
            'attribution': 'each_product_term_split_equally_between_its_axes',
            'connection_credit': 'per_tool_attribution_in_axis_contributions',
            'interpretation': 'experimental_investigation_progress_not_function_probability_or_independence'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, episode_id=None, run_id=None):
        return self.read_details(store, scope, known_record_refs=known_record_refs, assignment=assignment,
            episode_id=episode_id, run_id=run_id, details_limit=0, details_offset=0)

    def read_details(self, store, scope, *, known_record_refs, details_limit, details_offset,
                     assignment=None, episode_id=None, run_id=None):
        if type(details_limit) is not int or type(details_offset) is not int or min(details_limit, details_offset) < 0:
            raise ValueError('evidence_root_nonnegative_detail_page_required')
        if isinstance(known_record_refs, (str, bytes, dict)):
            raise ValueError('evidence_root_explicit_receipts_required')
        known = sorted(set(known_record_refs))
        if any(not isinstance(ref, str) for ref in known):
            raise ValueError('evidence_root_explicit_receipts_required')
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            if assignment is not None and store.validate_scope(assignment['scope']) != scope:
                raise ValueError('evidence_root_scope_differs_from_original_commission')
            targets, sources, source_count = {}, [], 0
            for target in scope['subject_refs']:
                local = {'subject_refs': [target]}
                segments = [row for row in scope.get('segments', []) if row['target_ref'] == target]
                if 'segments' in scope:
                    if not segments:
                        continue
                    local['segments'] = segments
                length = sum(row['end']-row['start'] for row in segments) if segments else store.subject_length(target)
                vector, statuses = {}, {}
                for axis in self.axes:
                    view = _projector(axis).read_details(store, local, known_record_refs=known,
                        details_limit=details_limit+details_offset if details_limit else 0, details_offset=0)
                    vector[axis] = view['credit']
                    if axis == 'A101':
                        count = view['detail_pages']['source_contributions_total']
                        measured = bool(view['a101_sheet']['targets'][target]['profile'])
                    else:
                        count = view['source_contribution_count']
                        measured = count > 0
                    statuses[axis] = 'native_evidence_received' if measured else 'no_received_native_measurement'
                    target_status=view.get('target_sheets',{}).get(target,{}).get('status')
                    if axis=='A102' and target_status in {'unresolved_attribution','attributed_reference_geometry'}:
                        statuses[axis]=target_status
                    if axis=='A103' and target_status in {'unresolved_attribution','partial_attribution','attributed_context_received'}:
                        statuses[axis]=target_status
                    source_count += count
                    sources.extend({'axis': axis, **row} for row in view['source_contributions'])
                targets[target] = {'assigned_length': length, 'axis_components': vector,
                    'axis_status': statuses, **offset_volume(vector)}
            denominator = sum(row['assigned_length'] for row in targets.values())
            if denominator <= 0:
                raise ValueError('evidence_root_nonempty_original_scope_required')
            def mean(field):
                return math.fsum(row[field]*row['assigned_length'] for row in targets.values())/denominator
            vector = {axis: math.fsum(row['axis_components'][axis]*row['assigned_length']
                for row in targets.values())/denominator for axis in self.axes}
            attribution = {axis: math.fsum(row['attribution'][axis]*row['assigned_length']
                for row in targets.values())/denominator for axis in self.axes}
            page = sources[details_offset:details_offset+details_limit]
            return {'credit': mean('credit'), 'axis_components': vector,
                'volume_components': {'additive': mean('additive'), 'interaction': mean('interaction')},
                'axis_attribution': attribution, 'target_sheets': targets, 'scope': scope,
                'maximum': 2**len(self.axes)-1, 'connection_credit': None,
                'connection_status': 'per_tool_and_feature_attribution', 'source_contributions': page,
                'source_contribution_count': source_count,
                'inactive_dependencies': [], 'inactive_dependency_count': 0,
                'next_offset': details_offset+len(page) if details_limit and details_offset+len(page)<source_count else None,
                'interpretation': 'native_evidence_progress_with_explicit_interaction_not_function_probability'}


def create_evidence_root_workflow(store, tools, provider, directory, run_id, controller_factory,
                                  *, initial_known_record_refs, axes=AXES, **options):
    from .investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from .runtime import Workflow
    if 'project_credit' in options or 'credit_binding' in options:
        raise ValueError('evidence_root_numeric_binding_is_host_owned')
    if options.get('episode_record_receipts', True) is not True:
        raise ValueError('evidence_root_requires_explicit_receipts')
    options['episode_record_receipts'] = True
    if 'project_child_credit' not in options:
        fallback = ScientificFindingProgress(FindingProgressPolicy(1))
        options.update(project_child_credit=fallback, child_credit_binding=fallback.as_record())
    scorer = NativeEvidenceRootCredit(tuple(axes))
    return Workflow(store, tools, provider, directory, run_id, controller_factory, scorer,
        credit_binding=scorer.as_record(), initial_known_record_refs=initial_known_record_refs, **options)
