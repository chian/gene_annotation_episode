"""Receipt-scoped automatic routing of native graders into the A101 sheet.

The optimization scalar is the sheet's native sequence-correspondence component,
not a function probability or a count of assertions. Function-specific and
feature-qualified indices remain unavailable without their own grounded inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math

from .a101_scoring import (VERSION, SCALES, A101ScoringUnavailable,
    compile_native_sheet, intervals, route_native_grading)
from .tool_grading_artifacts import source_tool_grading_entries


def _known(values):
    if isinstance(values, (str, bytes, dict)):
        raise TypeError('a101_explicit_received_record_references_required')
    result = set(values)
    if any(not isinstance(ref, str) for ref in result):
        raise TypeError('a101_explicit_received_record_references_required')
    return sorted(result)


def _regions(store, scope, target):
    length = store.subject_length(target)
    segments = scope.get('segments')
    selected = ([[row['start'],row['end']] for row in segments if row['target_ref'] == target]
        if segments is not None else [[0,length]])
    return intervals(selected, length=length)


@dataclass(frozen=True)
class A101SequenceCredit:
    """One deterministic projection for normal actions, details and parents."""
    requires_episode_receipts = True
    requires_known_record_refs = True
    yield_method = 'bounded_quality'
    native_score_maximum = 1.

    def _annotation_measurements(self, store, known, annotation, target, scope):
        from .component_assessment_dependencies import annotation_assessments
        from .evidence_geometry import _merge
        from .tool_grading_artifacts import source_tool_grading_entries
        links, selected, selected_assessments = [], {}, {}
        for row in annotation_assessments(store, known, annotation, target, scope):
            observation = row['observation']
            source = store.get(observation['source_ref']) if observation['source_ref'] in known else None
            native_sequence = source is not None and observation['origin'] == 'tool' and (
                'native_blast' in observation or source.get('provider') in {'ncbi_blast', 'native.phmmer.alignment'}
                or any((entry['grading'].get('sheet') or {}).get('schema', '').startswith('blast_')
                    or (entry['grading'].get('sheet') or {}).get('schema') == 'hmmer_search_sheet_v1'
                    for entry in source_tool_grading_entries(store, source['id'])))
            references = [observation['id']] if native_sequence else []
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
            scalar = _result('A101', None, formula='received_current_axis_result_required', inputs={}, reasons=[reason])
        else:
            native = self.read_details(store, scope, known_record_refs=known, subjects=(target,),
                evidence_regions=selected, details_limit=details_limit, details_offset=details_offset)
            measured = bool(native['a101_sheet']['targets'][target]['profile'])
            scalar = correspondence_scalar('A101', native['credit'], measured=measured)
            if native.get('target_sheets', {}).get(target, {}).get('status') == 'unresolved_attribution':
                scalar = require_attribution(scalar, missing=['unresolved_native_attribution'])
            count = native['detail_pages']['source_contributions_total']
            for item in native['source_contributions']:
                refs = selected_assessments.get(item.get('observation_ref'), set())
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
        return {'kind': 'a101_native_sequence_correspondence', 'version': VERSION,
            'axis': 'A101', 'sheet': 'convention_015_native_correspondence',
            'supported_algorithms': ['blastp', 'phmmer', 'hmmsearch', 'hmmscan'],
            'inverse_bit_scales': dict(SCALES),
            'receipt': 'explicit_known_record_refs',
            'target_aggregation': 'supplied_scope_length_weighted_mean',
            'function_specific_support': 'separate_unknown_without_grounded_inputs',
            'interpretation': 'dimensionless_native_correspondence_not_function_probability',
            'duplicate_handling': 'per_position_max_not_sum_of_hits_or_assertions'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None,
                 episode_id=None, run_id=None):
        return self.read_details(store, scope, known_record_refs=known_record_refs,
            assignment=assignment, episode_id=episode_id, run_id=run_id,
            details_limit=0, details_offset=0)

    def read_details(self, store, scope, *, known_record_refs, details_limit,
                     details_offset, assignment=None, episode_id=None, run_id=None,
                     subjects=None, evidence_regions=None):
        if (type(details_limit) is not int or details_limit < 0
                or type(details_offset) is not int or details_offset < 0):
            raise ValueError('a101_nonnegative_detail_page_required')
        known = _known(known_record_refs)
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            if assignment is not None and store.validate_scope(assignment['scope']) != scope:
                raise ValueError('a101_credit_scope_differs_from_original_commission')
            from .evidence_geometry import native_subject_regions, _intersection
            from .component_assessment_dependencies import assigned_annotation
            annotation = assigned_annotation(store, known, assignment)
            if annotation is not None:
                subjects, evidence_regions = annotation['subject_refs'], {}
                for subject in subjects:
                    _, selected, _ = self._annotation_measurements(store, known, annotation, subject, scope)
                    evidence_regions.update(selected)
            targets = (native_subject_regions(store, scope, subjects) if subjects is not None else
                {ref: _regions(store,scope,ref) for ref in scope['subject_refs']})
            targets = {ref:regions for ref,regions in targets.items() if regions}
            rows = {ref: [] for ref in targets}
            profiles = {ref:set() for ref in targets}
            sources, unsupported = [], []
            cached_grades = {}
            routed_grades, target_sequences = {}, {}
            # Included, complete empty analyses still belong to the profile.
            # Producer identities and original tool operands establish this;
            # no model flag or score-maximizing profile selection is involved.
            for reference in known:
                if evidence_regions is not None:
                    continue  # An unassessed complete source does not establish an annotation's profile.
                source = store.get(reference)
                if source['record_type'] != 'source' or source['origin'] not in {'tool','external'}:
                    continue
                if source.get('provider') == 'native.phmmer.parsed_snapshot':
                    captured = store.db.execute('SELECT query_ref FROM homology_result_snapshots WHERE source_ref=?',
                        (reference,)).fetchone()
                    if captured and captured[0] in targets:
                        profiles[captured[0]].add('hmmer')
                grades = cached_grades[reference] = source_tool_grading_entries(store,reference)
                for entry in grades:
                    schema = (entry['grading'].get('sheet') or {}).get('schema','')
                    if not schema.startswith('blast_'):
                        continue
                    for operation in store.db.execute("SELECT result FROM tool_operations WHERE json_extract(result,'$.result.source_ref')=?",(reference,)):
                        query = (json.loads(operation[0]).get('result') or {}).get('subject_ref')
                        if query in targets:
                            profiles[query].add('blast')
            for reference in known:
                if evidence_regions is not None and reference not in evidence_regions:
                    continue
                observed = store.get(reference)
                if observed['record_type'] != 'observation' or observed['kind'] not in {'alignment','comparison'}:
                    continue
                # Reasoning and extracted assertions cannot mint native credit.
                if observed['origin'] != 'tool':
                    continue
                subjects = [ref for ref in observed['subject_refs'] if ref in targets]
                if not subjects:
                    continue
                source = store.get(observed['source_ref'])
                grades = cached_grades.get(source['id'])
                if grades is None:
                    grades = source_tool_grading_entries(store,source['id'])
                native_candidate = (observed['kind'] == 'alignment'
                    or 'native_blast' in observed)
                if native_candidate and not grades:
                    raise A101ScoringUnavailable('a101_native_grader_not_attached',
                        observation_ref=reference, source_ref=source['id'])
                for entry in grades:
                    grading = entry['grading']
                    if grading.get('failure'):
                        if native_candidate:
                            raise A101ScoringUnavailable('a101_native_grader_failed',
                                observation_ref=reference, failure=grading['failure'])
                        continue
                    schema = (grading.get('sheet') or {}).get('schema','')
                    if not (schema == 'hmmer_search_sheet_v1' or schema.startswith('blast_')):
                        if observed['kind'] == 'alignment':
                            unsupported.append({'observation_ref':reference, 'schema':schema})
                        continue
                    if entry['artifact_ref'] not in routed_grades:
                        routed_grades[entry['artifact_ref']] = route_native_grading(grading)
                    populated = routed_grades[entry['artifact_ref']]
                    if 'native_blast' in observed:
                        native = observed['native_blast']
                        address = native.get('shared_projection', {})
                        if address.get('grading_artifact_ref') != entry['artifact_ref']:
                            continue
                        populated = [row for row in populated if
                            row.get('hit_index') == native.get('hit_ordinal')
                            and row.get('hsp_index') == native.get('hsp_ordinal')]
                    for target in subjects:
                        if store.subject_molecule(target) != 'protein':
                            raise A101ScoringUnavailable('a101_original_protein_mapping_required',target_ref=target)
                        length = store.subject_length(target)
                        declared = [operand for operand in observed.get('operand_intervals',[])
                            if operand['subject_ref'] == target and operand['role'] == 'query']
                        if not declared:
                            raise A101ScoringUnavailable('a101_target_correspondence_unavailable',
                                observation_ref=reference)
                        if any(operand['unit'] != 'aa' for operand in declared):
                            raise A101ScoringUnavailable('a101_original_protein_mapping_required',target_ref=target)
                        # phmmer publishes paired intervals; BLAST publishes its HSP
                        # span and retains the exact native HSP address separately.
                        expected = intervals([[p['start'],p['end']] for p in declared],length=length)
                        matches = [row for row in populated if
                            (intervals(row['target_intervals'],length=length) == expected
                             if source.get('provider') == 'native.phmmer.alignment' else
                             all(any(a<=x and y<=b for a,b in expected) for x,y in row['target_intervals']))]
                        if len(matches) != 1:
                            raise A101ScoringUnavailable('a101_observation_grader_join_ambiguous',
                                observation_ref=reference, candidate_count=len(matches))
                        row = dict(matches[0])
                        if target not in target_sequences:
                            target_sequences[target] = store.get_artifact(store.get(target)['sequence_ref']).decode('ascii').upper()
                        sequence = target_sequences[target]
                        if any(sequence[position] != symbol for position,symbol in row.pop('target_symbols')):
                            raise A101ScoringUnavailable('a101_target_sequence_conflict',observation_ref=reference)
                        row.pop('residue_pairs',None)  # retained in the native grader for specific attachment consumers
                        row['target_intervals'] = intervals(row['target_intervals'],length=length)
                        if evidence_regions is not None:
                            row['native_target_intervals'] = row['target_intervals']
                            row['target_intervals'] = _intersection(row['target_intervals'],
                                intervals(evidence_regions[reference], length=length))
                            if not row['target_intervals']:
                                continue
                        row.update(observation_ref=reference, source_ref=source['id'],
                            grading_artifact_ref=entry['artifact_ref'], target_ref=target)
                        rows[target].append(row)
                        profiles[target].add(row['algorithm'])
                        sources.append({'observation_ref':reference, 'source_ref':source['id'],
                            'grading_artifact_ref':entry['artifact_ref'], 'target_ref':target,
                            'native_record_key':row['native_record_key']})
            if unsupported and not sources:
                raise A101ScoringUnavailable('a101_unsupported_score_profile',profiles=unsupported)
            sheets = {target:compile_native_sheet(rows[target],
                supplied_length=store.subject_length(target), regions=regions, profile=profiles[target])
                for target,regions in targets.items()}
            denominator = sum(sum(b-a for a,b in regions) for regions in targets.values())
            if denominator <= 0:
                raise A101ScoringUnavailable('a101_required_scope_empty')
            credit = math.fsum(sheet['value']*sum(b-a for a,b in targets[target])
                for target,sheet in sheets.items())/denominator
            calculated = [row for sheet in sheets.values() for row in sheet['comparisons']]
            summaries = {target:{**{key:value for key,value in sheet.items() if key!='comparisons'},
                'comparison_count':len(sheet['comparisons'])} for target,sheet in sheets.items()}
            return {'credit':credit, 'axis_components':{'A101':credit},
                'interpretation':'native_correspondence_not_assertion_count_or_function_probability',
                'a101_sheet':{'version':VERSION, 'targets':summaries,
                    'unsupported_profiles':unsupported, 'policy':self.as_record()},
                'source_contributions':calculated[details_offset:details_offset+details_limit],
                'inactive_dependencies':[],
                'detail_pages':{'offset':details_offset, 'limit':details_limit,
                    'source_contributions_total':len(calculated), 'inactive_dependencies_total':0}}
