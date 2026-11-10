"""Pure A104 credit projection over explicitly received tool attachments."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .a104_attachments import received_attachments
from .a104_hpc import require
from .a104_scoring import PROFILE, VERSION


@dataclass(frozen=True)
class A104EvolutionaryCredit:
    requires_episode_receipts = True
    requires_known_record_refs = True

    def _annotation_measurements(self, store, known, annotation, target, scope):
        from .component_assessment_dependencies import annotation_assessments
        from .evidence_geometry import _merge
        attachments = received_attachments(store, known)
        links, selected, selected_assessments = [], {}, {}
        for row in annotation_assessments(store, known, annotation, target, scope):
            source = row['observation']['source_ref']
            references = [item['source_ref'] for item in attachments if item['target_ref'] == target
                and (item['source_ref'] == source or item.get('measurement_ref') == source)]
            if not references:
                continue
            links.append(row)
            if row['transfer_status'] != 'established' or row['relation'] != 'strengthens':
                continue
            for reference in references:
                selected[reference] = _merge([*selected.get(reference, ()), *row['regions']])
                selected_assessments.setdefault(reference, set()).add(row['assessment_ref'])
        return links, selected, selected_assessments

    def annotation_contribution(self, store, context, *, target, annotation, scope,
                                comparison_ref=None, selection=None, details_limit=0, details_offset=0):
        """Identify and score this axis's received evidence for one proposed annotation."""
        from .component_assessment_dependencies import assessment_transfer, assessment_details
        from .root_axis_scalars import _result, correspondence_scalar, require_attribution, bind_contribution
        known = set(context.received_record_refs)
        links, selected, selected_assessments = self._annotation_measurements(store, known, annotation, target, scope)
        details, count, measured = [], 0, False
        if not selected:
            reason = ('no_received_applicable_supporting_assessment' if not links else
                'assessed_observation_has_no_received_applicable_supporting_measurement')
            scalar = _result('A104', None, formula='received_current_axis_result_required', inputs={}, reasons=[reason])
        else:
            native = self.read_details(store, scope, known_record_refs=known, subjects=(target,),
                evidence_regions=selected, details_limit=details_limit, details_offset=details_offset)
            measured = native['source_contribution_count'] > 0
            scalar = correspondence_scalar('A104', native['credit'], measured=measured)
            if native.get('target_sheets', {}).get(target, {}).get('status') == 'unresolved_attribution':
                scalar = require_attribution(scalar, missing=['unresolved_native_attribution'])
            count = native['source_contribution_count']
            for item in native['source_contributions']:
                refs = selected_assessments.get(item['source_ref'], set())
                details.append({**item, 'assessment_refs': sorted(refs),
                    'assessment_qualifications': assessment_details(links, refs)})
        refs = {reference for group in selected_assessments.values() for reference in group}
        scalar.update(assessment_refs=sorted(refs), assessment_qualifications=assessment_details(links, refs),
            question={'assertion_ref': annotation['id']}, source_contribution_count=count)
        scalar = bind_contribution(scalar, annotation=annotation, subject=target, scope=scope,
            transfer=assessment_transfer(links, missing=scalar['missing_inputs']),
            source_refs=sorted({row['observation']['source_ref'] for row in links}))
        return scalar, details

    def as_record(self):
        return {'kind': 'a104_evolutionary_history', 'version': VERSION, 'profile': PROFILE,
            'receipt': 'explicit_received_host_issued_per_use_attribution',
            'projection': 'max_compatible_native_value_per_dimension_and_region_then_length_weighted_mean',
            'dimensions': ['placement', 'history_comparison', 'characterized_clade'],
            'dimension_formula': '((1+placement)*(1+history_comparison)*(1+characterized_clade)-1)/7',
            'interpretation': 'native_phylogenetic_progress; not_function_probability'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, **kwargs):
        return self.read_details(store, scope, known_record_refs=known_record_refs, assignment=assignment,
                                 details_limit=0, details_offset=0)

    def read_details(self, store, scope, *, known_record_refs, details_limit, details_offset,
                     assignment=None, subjects=None, evidence_regions=None, **kwargs):
        require(type(details_limit) is int and type(details_offset) is int and min(details_limit, details_offset) >= 0,
                'a104_nonnegative_detail_window_required')
        require(not isinstance(known_record_refs, (str, bytes, dict)), 'a104_explicit_receipts_required')
        known = set(known_record_refs)
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            require(assignment is None or store.validate_scope(assignment['scope']) == scope,
                    'a104_original_commission_scope_required')
            from .evidence_geometry import native_subject_regions, _intersection
            from .component_assessment_dependencies import assigned_annotation
            annotation = assigned_annotation(store, known, assignment)
            if annotation is not None:
                subjects, evidence_regions = annotation['subject_refs'], {}
                for subject in subjects:
                    _, selected, _ = self._annotation_measurements(store, known, annotation, subject, scope)
                    evidence_regions.update(selected)
            selected_regions = native_subject_regions(store, scope, subjects) if subjects is not None else None
            selected_subjects = selected_regions if selected_regions is not None else scope['subject_refs']
            attachments = [row for row in received_attachments(store, known) if row['target_ref'] in selected_subjects
                and (evidence_regions is None or row['source_ref'] in evidence_regions)]
            # Late receipt yields a new immutable sheet. Retain the sheet with
            # the encompassing actual qualification inputs, not a prior unknown
            # sheet or a scalar selected because its value happens to be larger.
            attachments = [row for row in attachments if not any(
                other['measurement_ref'] == row['measurement_ref'] and
                set(row['qualification_dependencies']) < set(other['qualification_dependencies'])
                for other in attachments)]
            by_measurement = {}
            for row in attachments:
                by_measurement.setdefault(row['measurement_ref'], []).append(row)
            incompatible_qualifications = {key for key, values in by_measurement.items()
                if len({frozenset(row['qualification_dependencies']) for row in values}) > 1}
            variants = {}
            for row in attachments:
                if row.get('variant_group'):
                    variants.setdefault(row['variant_group'], set()).add(row['variant'])
            competing = {key for key, values in variants.items() if len(values) > 1}
            contributions = [{'source_ref': row['source_ref'], 'grading_artifact_ref': row['grading_artifact_ref'],
                'measurement_ref': row['measurement_ref'], 'target_ref': row['target_ref'],
                'target_regions': (_intersection(row['target_regions'], evidence_regions[row['source_ref']])
                    if evidence_regions is not None else row['target_regions']), 'value': row['score'], 'policy': row['policy'],
                'dimension': 'history_comparison' if 'compare_histories' in row['policy'] else
                             'characterized_clade' if 'clade_functions' in row['policy'] else 'placement',
                'state': row['state']} for row in attachments if row['score'] is not None
                and row.get('variant_group') not in competing and row['measurement_ref'] not in incompatible_qualifications
                and (not row.get('compared_variant_group') or
                     variants.get(row['compared_variant_group'], set()) <= set(row['compared_variants']))]
            contributions = [row for row in contributions if row['target_regions']]
            targets = {}
            for target in selected_subjects:
                regions = (selected_regions[target] if selected_regions is not None else
                    [[row['start'], row['end']] for row in scope['segments'] if row['target_ref'] == target]
                    if 'segments' in scope else [[0, store.subject_length(target)]])
                if not regions:
                    continue
                own, cells = [row for row in contributions if row['target_ref'] == target], []
                for start, end in regions:
                    points = sorted({start, end, *[p for row in own for span in row['target_regions'] for p in span if start < p < end]})
                    for a, b in zip(points, points[1:]):
                        dimensions = {name: max((row['value'] for row in own if row['dimension'] == name
                            and any(x <= a and b <= y for x, y in row['target_regions'])), default=0.)
                            for name in ('placement', 'history_comparison', 'characterized_clade')}
                        p, h, c = (dimensions[name] for name in ('placement', 'history_comparison', 'characterized_clade'))
                        cells.append({'start': a, 'end': b, 'value': ((1+p)*(1+h)*(1+c)-1)/7,
                                      'native_dimensions': dimensions})
                length = sum(b-a for a, b in regions)
                value = math.fsum((row['end']-row['start'])*row['value'] for row in cells)/length
                pending = [row['measurement_ref'] for row in attachments if row['target_ref'] == target and row['missing']]
                targets[target] = {'assigned_length': length, 'value': value, 'cells': cells,
                    'pending_measurement_refs': sorted(set(pending)), 'unresolved_variant_groups': sorted(competing),
                    'status': 'attributed_phylogeny_received' if own else 'unresolved_attribution' if pending
                              else 'no_received_native_phylogeny_test'}
            denominator = sum(row['assigned_length'] for row in targets.values())
            require(denominator > 0, 'a104_nonempty_original_scope_required')
            value = math.fsum(row['value']*row['assigned_length'] for row in targets.values())/denominator
            page = contributions[details_offset:details_offset+details_limit]
            return {'credit': value, 'scope': scope, 'target_sheets': targets,
                'a104_sheet': {'placement': [row for row in attachments if 'measure_placement' in row['policy']],
                    'history_comparison': [row for row in attachments if 'compare_histories' in row['policy']],
                    'characterized_clades': [row for row in attachments if 'clade_functions' in row['policy']],
                    'robustness': [row for row in attachments if 'compare_placements' in row['policy']]},
                'tool_attachments': attachments, 'source_contributions': page,
                'source_contribution_count': len(contributions), 'inactive_dependencies': [], 'inactive_dependency_count': 0,
                'next_offset': details_offset+len(page) if details_limit and details_offset+len(page) < len(contributions) else None,
                'interpretation': 'native_tree_tests_with_specific_target_region_and_reference_attribution'}
