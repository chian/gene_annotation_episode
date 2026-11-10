"""Separate received evidence, support and opposition for proposed annotations.

The root's task credit comes from reprojecting received child evidence. Annotation
support and opposition retain their separate scientific meaning.
"""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import math
from types import MappingProxyType

from .communication import plain
from .evidence_root import SIGNED_COMBINATION_VERSION, SIGNED_COMBINATION_FORMULA
from .root_axis_receipts import (receiver_context, axis_contribution_readers,
    received_axis_task_credit, axis_progress_from_received)
from .root_axis_scalars import (
    AXES, UNSIGNED_AXES, VERSION, combine_scalars, _result,
)


@dataclass(frozen=True)
class SignedRootEpisodeBinding:
    """The annotation root's own credit, score, and continuation binding."""

    initial_known_record_refs: tuple[str, ...]
    axis_yield_cutoffs: Mapping[str, float]
    yield_parameters: object
    annotation_support: SignedEvidenceRootSupport

    @classmethod
    def from_record(cls, record):
        from .numerical import AnnotationAxisYieldController, YieldParameters
        if isinstance(record, dict) and record.get('version') == 'signed_root_episode_binding_v1':
            raise ValueError('legacy_signed_root_scalar_credit_incompatible')
        if (not isinstance(record, dict) or set(record) != {
                'version', 'initial_known_record_refs', 'root_task', 'annotation_support'}
                or record['version'] != 'signed_root_episode_binding_v2'):
            raise ValueError('explicit_signed_root_episode_binding_required')
        task = record['root_task']
        if (not isinstance(task, dict) or set(task) != {'kind', 'cutoffs', 'yield_parameters'}
                or task['kind'] != 'annotation_axis_credit'
                or not isinstance(task['cutoffs'], dict) or set(task['cutoffs']) != set(AXES)
                or not isinstance(task['yield_parameters'], dict)):
            raise ValueError('explicit_root_axis_yield_binding_required')
        support = record['annotation_support']
        if (not isinstance(support, dict) or not {'version'} <= set(support) <= {
                'version', 'assertion_ref', 'comparison_ref', 'selections'}
                or support['version'] != VERSION
                or not isinstance(support.get('selections', {}), dict)):
            raise ValueError('explicit_signed_root_annotation_support_required')
        refs = record['initial_known_record_refs']
        if (not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs)
                or len(refs) != len(set(refs))):
            raise ValueError('explicit_initial_known_record_refs_required')
        scorer = SignedEvidenceRootSupport(support.get('assertion_ref'),
            support.get('comparison_ref'), tuple(support.get('selections', {}).items()))
        if scorer.provides_single_annotation_score:
            raise ValueError('annotation_axis_root_requires_collection_scorer')
        parameters = YieldParameters(**task['yield_parameters'])
        cutoffs = dict(task['cutoffs'])
        AnnotationAxisYieldController('configuration',
            {'mode': 'annotation_axis_credit', 'arms': []}, cutoffs, parameters)
        return cls(tuple(refs), MappingProxyType(cutoffs), parameters, scorer)

    @property
    def task_credit(self):
        from dataclasses import replace
        return replace(self.annotation_support, task_credit=True)

    def yield_controller(self, path, initial_credit):
        from .domain import canonical
        from .numerical import AnnotationAxisYieldController
        if len(path) != 1 or path[0][0] != 'annotation':
            raise ValueError('episode_owner_yield_binding_required:' + path[-1][0])
        epoch = hashlib.sha256(canonical(path).encode()).hexdigest()
        return AnnotationAxisYieldController(epoch, initial_credit,
            self.axis_yield_cutoffs, self.yield_parameters)

    def controller_record(self):
        return {'version': 'signed_root_axis_yield_v2',
            'cutoffs': dict(self.axis_yield_cutoffs),
            'parameters': self.yield_parameters.as_record(),
            'forecast_unit': 'another_whole_axis_invocation',
            'credit_aggregation': 'received_axis_owner_progress_v1',
            'unresolved_execution': 'unidentifiable_yield_until_original_pending_result_is_received_or_fails',
            'continuation': 'each_annotation_axis_forecast_compared_with_own_cutoff'}


@dataclass(frozen=True)
class SignedEvidenceRootSupport:
    assertion_ref: str | None = None
    comparison_ref: str | None = None
    selections: tuple[tuple[str, str], ...] = ()
    task_credit: bool = False
    requires_episode_receipts = True
    requires_known_record_refs = True
    requires_receiver_context = True

    def __post_init__(self):
        if type(self.task_credit) is not bool or self.task_credit and self.assertion_ref is not None:
            raise ValueError('annotation_axis_task_credit_requires_dynamic_collection')
        if self.assertion_ref is not None and (not isinstance(self.assertion_ref, str)
                or not self.assertion_ref.startswith('hypothesis_')):
            raise ValueError('signed_root_explicit_functional_assertion_required')
        if self.comparison_ref is not None and (not isinstance(self.comparison_ref, str)
                or not self.comparison_ref.startswith('hypothesis_')):
            raise ValueError('signed_root_named_alternative_required')
        selections = tuple(tuple(row) for row in self.selections)
        if (any(len(row) != 2 or row[0] not in AXES[4:] or not isinstance(row[1], str)
                or not row[1].startswith('source_') for row in selections)
                or len({row[0] for row in selections}) != len(selections)):
            raise ValueError('signed_root_unique_native_axis_selections_required')
        object.__setattr__(self, 'selections', selections)
        if self.assertion_ref is None and (self.comparison_ref is not None or selections):
            raise ValueError('collection_mode_requires_per_annotation_results_not_global_selectors')

    @property
    def provides_single_annotation_score(self):
        return self.assertion_ref is not None

    def as_record(self):
        return {'kind': 'signed_evidence_root_support', 'version': VERSION,
            'annotation_binding_version': ('received_proposed_annotation_axis_progress_v3'
                if self.task_credit else 'received_proposed_annotation_scores_v2'),
            'annotation_selection': ('explicit_proposed_annotation' if self.assertion_ref is not None
                else 'received_proposed_annotations_each_native_subject'),
            'axes': list(AXES), 'assertion_ref': self.assertion_ref,
            'task_credit': self.task_credit,
            'comparison_ref': self.comparison_ref, 'selections': dict(self.selections),
            'aggregation_version': SIGNED_COMBINATION_VERSION,
            'formula': SIGNED_COMBINATION_FORMULA,
            'scope_aggregation': ('per_native_subject_then_original_scope_length_weighted_mean'
                if self.assertion_ref is not None else 'separate_score_per_proposed_annotation_and_native_subject'),
            'missing': 'unknown_neutral_dimension_not_opposing_evidence',
            'axis_contributions': 'declared_by_existing_axis_owners',
            'attribution': 'owner_declared_application_to_this_proposed_annotation_and_native_subject',
            'revisions': 'receiver_current_versions_only; historical_receipts_immutable',
            'continuation': ('per_annotation_axis_credit_and_explicit_cutoff' if self.task_credit
                else 'separately_bound_task_credit_and_controller'),
            **({'root_task_credit_formula': 'max_per_annotation_sum_of_axis_owner_received_progress'}
                if self.task_credit else {}),
            'interpretation': 'explicit_mixed_evidence_index; not_calibrated_function_probability'}

    def __call__(self, store, scope, *, known_record_refs, run_id, episode_id, assignment=None):
        return self.read_details(store, scope, known_record_refs=known_record_refs,
            run_id=run_id, episode_id=episode_id, assignment=assignment,
            details_limit=0, details_offset=0)

    def read_details(self, store, scope, *, known_record_refs, run_id, episode_id,
                     details_limit, details_offset, assignment=None):
        if (type(details_limit) is not int or type(details_offset) is not int
                or min(details_limit, details_offset) < 0):
            raise ValueError('signed_root_nonnegative_detail_page_required')
        if isinstance(known_record_refs, (str, bytes, dict)):
            raise ValueError('signed_root_explicit_receipts_required')
        known = tuple(dict.fromkeys(known_record_refs))
        if any(not isinstance(ref, str) for ref in known):
            raise ValueError('signed_root_explicit_receipts_required')
        with store.read_snapshot():
            scope = store.validate_scope(plain(scope))
            context = receiver_context(store, run_id, episode_id, known)
            if not store.scope_contains(plain(context.scope), scope):
                raise ValueError('signed_root_scope_outside_original_receiver')
            if assignment is not None and store.validate_scope(plain(assignment['scope'])) != scope:
                raise ValueError('signed_root_scope_differs_from_original_commission')
            window = details_limit + details_offset if details_limit else 0
            annotations = [store.get(reference) for reference in sorted(known)
                if reference.startswith('hypothesis_')
                and (self.assertion_ref is None or reference == self.assertion_ref)]
            if self.assertion_ref is not None:
                annotation = annotations[0] if annotations else None
                return self._single(store, context, annotation, scope, window,
                    details_limit=details_limit, details_offset=details_offset)
            rows, sources, source_count = [], [], 0
            for annotation in annotations:
                for subject in annotation['subject_refs']:
                    result = self._subject(store, context, annotation, subject, scope, window)
                    if result is None:
                        continue
                    row = {'proposed_annotation_ref': annotation['id'], 'subject_ref': subject,
                        'predicate': annotation['predicate'], 'value': plain(annotation['value']),
                        'context_refs': list(annotation['context_refs']), 'scope': result['scope'],
                        'score': result['credit'] if any(value is not None
                            for value in result['axis_components'].values()) else None,
                        **{key: result[key] for key in ('support', 'opposition', 'axis_components',
                            'axis_status', 'axis_missing_inputs', 'axis_transfer', 'native_regions', 'native_unit')}}
                    row['status'] = 'scored' if row['score'] is not None else 'unscored'
                    rows.append(row)
                    source_count += result['source_contribution_count']
                    sources.extend({'proposed_annotation_ref': annotation['id'], 'subject_ref': subject, **source}
                        for source in result['source_contributions'])
            from .domain import canonical
            groups = {}
            for row in rows:
                group = {key: row[key] for key in ('subject_ref', 'scope', 'predicate', 'context_refs')}
                group['context_refs'] = sorted(group['context_refs'])
                key = canonical(group)
                groups.setdefault(key, {'group': group, 'rows': []})['rows'].append(row)
            comparisons = []
            for group in groups.values():
                scored = [row for row in group['rows'] if row['score'] is not None]
                best = max((row['score'] for row in scored), default=None)
                comparisons.append({**group['group'],
                    'candidate_refs': [row['proposed_annotation_ref'] for row in group['rows']],
                    'best_scored_refs': [row['proposed_annotation_ref'] for row in scored if row['score'] == best],
                    'best_score': best,
                    'unscored_refs': [row['proposed_annotation_ref'] for row in group['rows'] if row['score'] is None],
                    'annotation_selected': False})
            page = sources[details_offset:details_offset + details_limit]
            result = {'mode': 'proposed_annotation_collection', 'proposed_annotations': rows,
                'comparisons': comparisons, 'scope': scope, 'scalar_mapping_version': VERSION,
                'aggregation_version': SIGNED_COMBINATION_VERSION, 'formula': SIGNED_COMBINATION_FORMULA,
                'source_contributions': page, 'source_contribution_count': source_count,
                'next_offset': details_offset + len(page) if details_limit and
                    details_offset + len(page) < source_count else None,
                'interpretation': 'separate_proposed_annotation_scores; episode_owns_annotation_decision'}
            if self.task_credit:
                from .numerical import annotation_credit_summary
                from .domain import canonical
                returned_credits = list(received_axis_task_credit(store, context))
                for returned in returned_credits:
                    matches = [row for row in rows
                        if row['proposed_annotation_ref'] == returned['proposed_annotation_ref']
                        and returned['axis'] in row['axis_components']
                        and row['scope'] == returned['scope']]
                    if len(matches) != 1:
                        raise ValueError('root_axis_return_requires_one_original_arm')
                progress = axis_progress_from_received(store, context, returned_credits)
                result['credit'] = {'mode': 'annotation_axis_credit', 'arms': [
                    {'proposed_annotation_ref': row['proposed_annotation_ref'],
                        'subject_ref': row['subject_ref'], 'scope': row['scope'], 'axis': axis,
                        'credit': progress.get((row['proposed_annotation_ref'],
                            canonical(row['scope']), axis), {}).get('credit', 0.),
                        'credit_binding_ref': progress.get((row['proposed_annotation_ref'],
                            canonical(row['scope']), axis), {}).get('credit_binding_ref'),
                        'task_credit_binding_refs': progress.get((row['proposed_annotation_ref'],
                            canonical(row['scope']), axis), {}).get('task_credit_binding_refs', []),
                        'status': row['axis_status'][axis],
                        'transfer': row['axis_transfer'][axis]}
                    for row in rows for axis in AXES]}
                annotation_credits, root_score = annotation_credit_summary(result['credit']['arms'])
                result['credit'].update(annotation_credits=annotation_credits, root_score=root_score)
            return result

    def _subject(self, store, context, annotation, subject, scope, window):
        from .evidence_geometry import native_subject_regions
        known = set(context.received_record_refs)
        if subject not in known and subject not in store.problem()['subject_refs']:
            return None
        record = store.get(subject)
        if record['record_type'] not in {'input', 'feature', 'product', 'read_subject'}:
            return None
        footprint = []
        for assigned in store.coverage(subject):
            for allowed in store.scope_coverage(scope):
                if (store.footprint_dimension(assigned) == store.footprint_dimension(allowed)
                        and max(assigned['start'], allowed['start']) < min(assigned['end'], allowed['end'])):
                    footprint.append({**assigned, 'start': max(assigned['start'], allowed['start']),
                        'end': min(assigned['end'], allowed['end'])})
        footprint = store._merge_segments(footprint)
        if not footprint:
            return None
        local = store.validate_scope({'subject_refs': sorted({row['target_ref'] for row in footprint}),
            'segments': footprint})
        regions = native_subject_regions(store, local, (subject,))
        source_count, sources, scalars = 0, [], []
        readers = axis_contribution_readers(store, context.run_id)
        contexts_received = set(annotation['context_refs']) <= known
        for axis in AXES:
            if not contexts_received or subject not in regions:
                scalar = _result(axis, None, formula='received_annotation_and_exact_native_subject_required',
                    inputs={}, reasons=['annotation_context_or_exact_native_mapping_unavailable'])
                scalar['transfer'] = {'status': 'unresolved', 'missing_inputs': scalar['missing_inputs'],
                    'needed_refs': sorted(set(annotation['context_refs']) - known), 'link_refs': []}
            else:
                scalar, contributions = readers[axis](store, context, target=subject,
                    annotation=annotation, scope=local, comparison_ref=self.comparison_ref,
                    selection=dict(self.selections).get(axis), details_limit=window)
                if (scalar['axis'] != axis or scalar['proposed_annotation_ref'] != annotation['id']
                        or scalar['subject_ref'] != subject or scalar['scope'] != local):
                    raise ValueError('axis_contribution_identity_mismatch')
                source_count += scalar.get('source_contribution_count', 0)
                sources.extend({'axis': axis, **row} for row in contributions)
            scalars.append(scalar)
        return {'scope': local, 'native_regions': regions.get(subject, []),
            'native_unit': store.subject_unit(subject),
            'assigned_length': sum(row['end'] - row['start'] for row in footprint),
            **combine_scalars(scalars), 'source_contributions': sources,
            'axis_missing_inputs': {row['axis']: row['missing_inputs'] for row in scalars},
            'axis_transfer': {row['axis']: row['transfer'] for row in scalars},
            'source_contribution_count': source_count}

    def _single(self, store, context, annotation, scope, window, *, details_limit, details_offset):
        targets = {subject: result for subject in annotation['subject_refs']
            if (result := self._subject(store, context, annotation, subject, scope, window)) is not None
        } if annotation is not None else {}
        denominator = sum(row['assigned_length'] for row in targets.values())
        vector = {axis: (math.fsum(row['assigned_length'] * row['axis_components'][axis]
            for row in targets.values()) / denominator
            if targets and all(row['axis_components'][axis] is not None for row in targets.values()) else None)
            for axis in AXES}
        support = math.fsum(row['support'] * row['assigned_length'] for row in targets.values()) / denominator if targets else 0.
        opposition = math.fsum(row['opposition'] * row['assigned_length'] for row in targets.values()) / denominator if targets else 0.
        sources = [source for row in targets.values() for source in row['source_contributions']]
        source_count = sum(row['source_contribution_count'] for row in targets.values())
        page = sources[details_offset:details_offset + details_limit]
        return {'credit': math.fsum([support, -opposition]), 'support': support, 'opposition': opposition,
            'axis_components': vector,
            'axis_status': {axis: ('unavailable_or_partially_resolved' if vector[axis] is None
                else 'partial' if any(row['axis_status'][axis] == 'partial' for row in targets.values())
                else 'available') for axis in AXES},
            'scalar_mapping_version': VERSION, 'aggregation_version': SIGNED_COMBINATION_VERSION,
            'formula': SIGNED_COMBINATION_FORMULA, 'target_sheets': targets,
            'assertion_ref': self.assertion_ref, 'comparison_ref': self.comparison_ref,
            'scope': scope, 'source_contributions': page, 'source_contribution_count': source_count,
            'next_offset': details_offset + len(page) if details_limit
                and details_offset + len(page) < source_count else None,
            'minimum': -(2 ** (len(AXES) - len(UNSIGNED_AXES)) - 1), 'maximum': 2 ** len(AXES) - 1,
            'interpretation': 'signed_mixed_evidence_index_not_calibrated_function_probability'}


def create_signed_evidence_root_workflow(store, tools, provider, directory, run_id, controller_factory,
                                         *, assertion_ref=None, initial_known_record_refs,
                                         project_credit, credit_binding, comparison_ref=None,
                                         selections=(), **options):
    """Attach signed support while retaining the caller's actual progress policy."""
    from .runtime import Workflow
    if ('project_annotation_score' in options or 'annotation_score_binding' in options
            or options.get('episode_record_receipts', True) is not True):
        raise ValueError('signed_root_owns_annotation_binding_and_requires_receipts')
    options['episode_record_receipts'] = True
    scorer = SignedEvidenceRootSupport(assertion_ref, comparison_ref, selections)
    return Workflow(store, tools, provider, directory, run_id, controller_factory, project_credit,
        credit_binding=credit_binding, initial_known_record_refs=initial_known_record_refs,
        project_annotation_score=scorer, annotation_score_binding=scorer.as_record(), **options)
