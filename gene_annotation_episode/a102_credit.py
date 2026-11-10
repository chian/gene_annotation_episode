"""Receipt-scoped A102 compiler shared by controllers and receiving parents."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math

from .a102_publication import received_grade
from .a102_scoring import VERSION, compile_native_sheet, require
from .a102_attachments import VERSION as ATTACHMENT_VERSION, received_attachments, reference_region_value, qualified_feature


@dataclass(frozen=True)
class A102StructuralCredit:
    requires_episode_receipts=True
    requires_known_record_refs=True
    yield_method = 'bounded_quality'
    native_score_maximum = 1.

    def _annotation_measurements(self, store, known, annotation, target, scope):
        from .component_assessment_dependencies import annotation_assessments
        from .evidence_geometry import _merge
        from .a102_publication import received_grade
        from .a102_attachments import received_attachments
        attachments = received_attachments(store, known)
        links, selected, selected_assessments = [], {}, {}
        for row in annotation_assessments(store, known, annotation, target, scope):
            observation = row['observation']
            source = observation['source_ref']
            grade = received_grade(store, source) if source in known else None
            references = [source] if grade is not None and grade['grade']['target_ref'] == target else []
            references.extend(item['source_ref'] for item in attachments if item['target_ref'] == target
                and (item['source_ref'] == source or item.get('measurement_ref') == source))
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
            scalar = _result('A102', None, formula='received_current_axis_result_required', inputs={}, reasons=[reason])
        else:
            native = self.read_details(store, scope, known_record_refs=known, subjects=(target,),
                evidence_regions=selected, details_limit=details_limit, details_offset=details_offset)
            measured = native['source_contribution_count'] > 0
            scalar = correspondence_scalar('A102', native['credit'], measured=measured)
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
        return {'kind':'a102_native_structural_correspondence','version':VERSION,'axis':'A102',
            'tool_attribution_version':ATTACHMENT_VERSION,
            'receipt':'explicit_known_record_refs_and_a102_scoring_grant',
            'profile':'symmetric_extent_times_rmsd_kernel_2A',
            'required_scopes':'geometric_mean','targets':'scope_length_weighted_mean',
            'function_specific_support':'separate_unknown_without_grounded_inputs',
            'interpretation':'native_and_explicitly_attributed_correspondence_with_separate_local_traits'}

    def __call__(self,store,scope,*,known_record_refs,assignment=None,episode_id=None,run_id=None):
        return self.read_details(store,scope,known_record_refs=known_record_refs,assignment=assignment,
            episode_id=episode_id,run_id=run_id,details_limit=0,details_offset=0)

    def read_details(self,store,scope,*,known_record_refs,details_limit,details_offset,
                     assignment=None,episode_id=None,run_id=None,subjects=None,evidence_regions=None):
        require(type(details_limit) is int and details_limit>=0 and type(details_offset) is int
            and details_offset>=0,'a102_nonnegative_detail_page_required')
        require(not isinstance(known_record_refs,(str,bytes,dict)), 'a102_explicit_receipts_required')
        known=sorted(set(known_record_refs))
        require(all(type(ref) is str for ref in known),'a102_explicit_receipts_required')
        with store.read_snapshot():
            scope=store.validate_scope(scope)
            require(assignment is None or store.validate_scope(assignment['scope'])==scope,
                'a102_credit_scope_differs_from_original_commission')
            from .evidence_geometry import native_subject_regions
            from .component_assessment_dependencies import assigned_annotation
            annotation = assigned_annotation(store, known, assignment)
            if annotation is not None:
                subjects, evidence_regions = annotation['subject_refs'], {}
                for subject in subjects:
                    _, selected, _ = self._annotation_measurements(store, known, annotation, subject, scope)
                    evidence_regions.update(selected)
            selected_regions = native_subject_regions(store, scope, subjects) if subjects is not None else None
            targets={}
            for ref in selected_regions if selected_regions is not None else scope['subject_refs']:
                length=store.subject_length(ref)
                regions=(selected_regions[ref] if selected_regions is not None else
                    [[s['start'],s['end']] for s in scope['segments'] if s['target_ref']==ref]
                    if scope.get('segments') is not None else [[0,length]])
                if regions:targets[ref]=(length,regions)
            require(bool(targets),'a102_required_scope_empty')
            rows={ref:[] for ref in targets};sources=[];feature_sheets=[];contrast_sheets=[];allowed={}
            derived=store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='a102_derived_publications'").fetchone()
            for reference in known:
                if evidence_regions is not None and reference not in evidence_regions:
                    continue
                if derived:
                    row=store.db.execute('SELECT * FROM a102_derived_publications WHERE source_ref=?',(reference,)).fetchone()
                    if row is not None:
                        source=store.get(reference);body=json.loads(row['body'])
                        require(source['origin']=='tool' and row['permitted_use']=='a102_scoring'
                            and json.loads(store.get_artifact(source['artifact_ref']))==body,'a102_derived_sheet_custody_conflict')
                        if body.get('target_ref') in targets:
                            if source['provider']=='native.a102.features':feature_sheets.append({'source_ref':reference,**qualified_feature(store,reference,body,known)})
                            elif source['provider']=='native.a102.contrast':contrast_sheets.append({'source_ref':reference,**body})
                received=received_grade(store,reference)
                if received is None:continue
                target=received['grade']['target_ref']
                if target not in targets:continue
                if evidence_regions is not None and not any(a <= position < b
                        for position in received['grade']['target_positions']
                        for a,b in evidence_regions[reference]):
                    continue
                require(store.subject_molecule(target)=='protein','a102_protein_target_required')
                rows[target].append(received['grade'])
                if evidence_regions is not None:
                    allowed[received['grade']['variant_ref']] = evidence_regions[reference]
                sources.append({key:received[key] for key in ('source_ref','grading_artifact_ref')}
                    | {'target_ref':target,'comparison_ref':received['grade']['variant_ref']})
            sheets={ref:compile_native_sheet(rows[ref],target_ref=ref,supplied_length=length,regions=regions,
                evidence_regions=allowed if evidence_regions is not None else None)
                for ref,(length,regions) in targets.items()}
            attachments=[row for row in received_attachments(store,known) if row['target_ref'] in targets
                and (evidence_regions is None or row['source_ref'] in evidence_regions)]
            for panel in contrast_sheets:
                grade=next((row for row in attachments if row.get('measurement_ref')==panel['source_ref']
                    and row['producer_operation']=='structure.contrast'),None)
                if grade:panel.update(grade['qualified_panel'],attribution_source_ref=grade['source_ref'])
            def preview(row):
                value={k:v for k,v in row.items() if k!='mapped_geometry'}
                if 'sequence_link' in value:value['sequence_link']={k:v for k,v in value['sequence_link'].items() if k!='pairs'}
                return value
            transferred=[row for row in attachments if row['policy']=='reference_fold_native_map_and_local_distance_v1'
                and row['state']!='excluded' and (evidence_regions is None or any(a <= item[0] < b
                    for item in row.get('mapped_geometry', ()) for a,b in evidence_regions[row['source_ref']]))]
            groups={}
            for row in transferred:groups.setdefault(row.get('comparison_group',row['measurement_ref']),set()).add(row.get('comparison_variant',row['measurement_ref']))
            ambiguous={group for group,variants in groups.items() if len(variants)>1}
            for ref,sheet in sheets.items():
                sheet['native_value']=sheet['value'];sheet['reference_attributions']=[]
                for region in sheet['regions']:
                    region['native_value']=region['value'];region['attributed_comparisons']=[]
                    for row in transferred:
                        if row['target_ref']!=ref:continue
                        if row.get('comparison_group',row['measurement_ref']) in ambiguous:continue
                        projected=reference_region_value(row,region['start'],region['end'],
                            evidence_regions=evidence_regions[row['source_ref']] if evidence_regions is not None else None)
                        if projected is not None:
                            region['attributed_comparisons'].append(projected)
                    region['value']=max([region['native_value'],*[r['value'] for r in region['attributed_comparisons']]])
                sheet['reference_attributions']=[preview(row) for row in transferred if row['target_ref']==ref]
                sheet['unresolved_reference_variants']=sorted(group for group in ambiguous if any(
                    row['target_ref']==ref and row.get('comparison_group',row['measurement_ref'])==group for row in transferred))
                values=[r['value'] for r in sheet['regions']]
                sheet['value']=math.exp(math.fsum(math.log(v) for v in values)/len(values)) if all(values) else 0.
                if not sheet['comparison_count'] and sheet['reference_attributions']:
                    sheet['status']='attributed_reference_geometry' if any(r['attributed_comparisons'] for r in sheet['regions']) else 'unresolved_attribution'
            sources.extend({'source_ref':row['source_ref'],'grading_artifact_ref':row['grading_artifact_ref'],
                'target_ref':row['target_ref'],'comparison_ref':row['request_ref'],'attribution_kind':'reference_fold'} for row in transferred)
            lengths={ref:sum(b-a for a,b in regions) for ref,(_,regions) in targets.items()}
            denominator=sum(lengths.values())
            credit=math.fsum(sheets[ref]['value']*length for ref,length in lengths.items())/denominator
            page=sources[details_offset:details_offset+details_limit]
            return {'credit':credit,'axis_components':{'A102':credit},'sheet_version':VERSION,
                'scope':scope,'target_sheets':sheets,'source_contributions':page,
                'functional_sheets':{'features':feature_sheets,'contrasts':contrast_sheets,
                    'traits':[row for row in attachments if row['producer_operation']=='structure.reference_traits'],
                    'interfaces':[row for row in attachments if row['producer_operation']=='structure.interface_geometry'],
                    'controller_credit':'native_or_specifically_attributed_fold_correspondence'},
                'tool_attachments':[preview(row) for row in attachments],
                'source_contribution_count':len(sources),
                'next_offset':details_offset+len(page) if details_limit and details_offset+len(page)<len(sources) else None,
                'inactive_dependencies':[],'inactive_dependency_count':0,
                'interpretation':'native_structural_correspondence_not_function_probability'}


def _received_task_sheet(store, reference, known, provider):
    """Read the original tool-published numerical sheet and its exact artifact."""
    if reference not in known:
        return None
    source = store.get(reference)
    if source['record_type'] != 'source' or source.get('provider') != provider:
        return None
    row = store.db.execute('SELECT body,permitted_use FROM a102_derived_publications '
        'WHERE source_ref=?', (reference,)).fetchone()
    from .a102_tools import VERSION as TOOLS_VERSION
    require(row is not None and row['permitted_use'] == 'a102_scoring'
        and source['origin'] == 'tool' and source['version'] == TOOLS_VERSION,
        'a102_task_native_sheet_custody_required')
    body = json.loads(row['body'])
    require(json.loads(store.get_artifact(source['artifact_ref'])) == body,
        'a102_task_native_sheet_custody_conflict')
    return body


@dataclass(frozen=True)
class A102FeatureGeometryCredit:
    """One credit per resolved source-defined feature for this annotation."""

    requires_episode_receipts = True
    requires_known_record_refs = True
    yield_method = 'accumulation'

    def as_record(self):
        return {'kind': 'a102_resolved_feature_geometry',
            'unit': 'one_distinct_received_qualified_physical_feature',
            'annotation': 'original_commission_matches_native_function_ref',
            'deduplication': 'comparison_source_definition_sources_physical_feature_key',
            'valid_zero': 'counted_as_resolved_measurement', 'preparation': 'no_credit'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, **kwargs):
        return self.read_details(store, scope, known_record_refs=known_record_refs,
            assignment=assignment, details_limit=0, details_offset=0)

    def read_details(self, store, scope, *, known_record_refs, assignment=None,
                     details_limit=0, details_offset=0, **kwargs):
        require(type(details_limit) is int and type(details_offset) is int
            and min(details_limit, details_offset) >= 0, 'a102_nonnegative_detail_page_required')
        require(not isinstance(known_record_refs, (str, bytes, dict)), 'a102_explicit_receipts_required')
        from .component_assessment_dependencies import assigned_annotation
        from .evidence_geometry import _intersection, native_subject_regions
        from .domain import canonical
        known = set(known_record_refs)
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            require(assignment is not None and store.validate_scope(assignment['scope']) == scope,
                'a102_credit_scope_differs_from_original_commission')
            annotation = assigned_annotation(store, known, assignment)
            require(annotation is not None, 'a102_feature_proposed_annotation_required')
            regions = native_subject_regions(store, scope, annotation['subject_refs'])
            selected = {}
            for item in received_attachments(store, known):
                if (item['producer_operation'] != 'structure.feature_geometry'
                        or item['target_ref'] not in regions):
                    continue
                body = _received_task_sheet(store, item['measurement_ref'], known,
                    'native.a102.features')
                if (body is None or body['function_ref'] != annotation['id']
                        or body['target_ref'] != item['target_ref']
                        or body['comparison_source_ref'] not in known
                        or not set(body['definition_source_refs']) <= known
                        or not _intersection([body['target_scope']], regions[item['target_ref']])):
                    continue
                comparison = received_grade(store, body['comparison_source_ref'])
                require(comparison is not None and comparison['grade']['target_ref'] == item['target_ref'],
                    'a102_feature_native_comparison_required')
                for feature in item['features']:
                    if feature['state'] != 'evaluated' or feature['score'] is None:
                        continue
                    position = feature['target_position']
                    if position is not None and not any(a <= position < b for a, b in regions[item['target_ref']]):
                        continue
                    key = canonical([item['target_ref'], body['comparison_source_ref'],
                        sorted(body['definition_source_refs']), feature['physical_feature_key']])
                    selected[key] = {'source_ref': item['source_ref'],
                        'measurement_ref': item['measurement_ref'],
                        'physical_feature_key': feature['physical_feature_key'],
                        'native_value': feature['score'], 'credit': 1}
            details = [selected[key] for key in sorted(selected)]
            return {'credit': len(details), 'scope': scope,
                'source_contributions': details[details_offset:details_offset+details_limit],
                'source_contribution_count': len(details), 'policy': self.as_record()}


@dataclass(frozen=True)
class A102FunctionalContrastCredit:
    """Credit a resolved witnessed contrast, including an opposing zero."""

    requires_episode_receipts = True
    requires_known_record_refs = True
    yield_method = 'accumulation'

    def as_record(self):
        return {'kind': 'a102_resolved_functional_contrast',
            'unit': 'one_distinct_received_source_witnessed_contrast_panel',
            'annotation': 'original_commission_matches_native_function_ref',
            'deduplication': 'function_scope_support_opposition_witness_sources',
            'valid_zero': 'counted_as_resolved_measurement', 'preparation': 'no_credit'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, **kwargs):
        return self.read_details(store, scope, known_record_refs=known_record_refs,
            assignment=assignment, details_limit=0, details_offset=0)

    def read_details(self, store, scope, *, known_record_refs, assignment=None,
                     details_limit=0, details_offset=0, **kwargs):
        require(type(details_limit) is int and type(details_offset) is int
            and min(details_limit, details_offset) >= 0, 'a102_nonnegative_detail_page_required')
        require(not isinstance(known_record_refs, (str, bytes, dict)), 'a102_explicit_receipts_required')
        from .component_assessment_dependencies import assigned_annotation
        from .evidence_geometry import _intersection, native_subject_regions
        from .domain import canonical
        known = set(known_record_refs)
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            require(assignment is not None and store.validate_scope(assignment['scope']) == scope,
                'a102_credit_scope_differs_from_original_commission')
            annotation = assigned_annotation(store, known, assignment)
            require(annotation is not None, 'a102_contrast_proposed_annotation_required')
            regions = native_subject_regions(store, scope, annotation['subject_refs'])
            selected = {}
            for item in received_attachments(store, known):
                if (item['producer_operation'] != 'structure.contrast'
                        or item['target_ref'] not in regions
                        or item['state'] != 'derived' or item['score'] is None):
                    continue
                body = _received_task_sheet(store, item['measurement_ref'], known,
                    'native.a102.contrast')
                panel = item['qualified_panel']
                if (body is None or body['function_ref'] != annotation['id']
                        or panel['function_ref'] != annotation['id']
                        or body['target_ref'] != item['target_ref']
                        or not set((*body['supporting_source_refs'], *body['opposing_source_refs'],
                            *body['contrast_witness_refs'])) <= known):
                    continue
                declared_scope = json.loads(body['scope_ref'])
                measured_regions = declared_scope['regions']
                if (isinstance(measured_regions, list) and len(measured_regions) == 2
                        and all(type(value) is int for value in measured_regions)):
                    measured_regions = [measured_regions]
                if (declared_scope['target_ref'] != item['target_ref']
                        or not _intersection(measured_regions, regions[item['target_ref']])):
                    continue
                key = canonical([item['target_ref'], annotation['id'], body['scope_ref'],
                    sorted(body['supporting_source_refs']), sorted(body['opposing_source_refs']),
                    sorted(body['contrast_witness_refs'])])
                selected[key] = {'source_ref': item['source_ref'],
                    'measurement_ref': item['measurement_ref'], 'native_value': item['score'],
                    'support_value': panel['S'], 'opposition_value': panel['O'], 'credit': 1}
            details = [selected[key] for key in sorted(selected)]
            return {'credit': len(details), 'scope': scope,
                'source_contributions': details[details_offset:details_offset+details_limit],
                'source_contribution_count': len(details), 'policy': self.as_record()}


def _assessed_a102_attachments(store, scope, known, assignment):
    """Find current annotation links to received, host-graded A102 uses."""
    from .component_assessment_dependencies import assigned_annotation, annotation_assessments
    from .evidence_geometry import native_subject_regions
    require(assignment is not None and store.validate_scope(assignment['scope']) == scope,
        'a102_credit_scope_differs_from_original_commission')
    annotation = assigned_annotation(store, known, assignment)
    require(annotation is not None, 'a102_task_proposed_annotation_required')
    regions = native_subject_regions(store, scope, annotation['subject_refs'])
    links = {}
    for subject in regions:
        for row in annotation_assessments(store, known, annotation, subject, scope):
            if row['transfer_status'] == 'established' and row['regions']:
                links.setdefault(row['observation']['source_ref'], []).append(row)
    for item in received_attachments(store, known):
        if item['target_ref'] not in regions:
            continue
        matched = [row for source in (item['source_ref'], item.get('measurement_ref'))
            for row in links.get(source, ())]
        if matched:
            yield item, matched, regions[item['target_ref']]


@dataclass(frozen=True)
class A102ReferenceAttributionCredit:
    """Credit each resolved, assessed native reference-to-target region."""

    requires_episode_receipts = True
    requires_known_record_refs = True
    yield_method = 'accumulation'

    def as_record(self):
        return {'kind': 'a102_resolved_reference_attribution',
            'unit': 'one_distinct_assessed_native_reference_region',
            'annotation': 'current_received_assessment_with_established_scope_transfer',
            'deduplication': 'native_measurement_target_region',
            'valid_zero': 'counted_as_resolved_measurement', 'preparation': 'no_credit'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, **kwargs):
        return self.read_details(store, scope, known_record_refs=known_record_refs,
            assignment=assignment, details_limit=0, details_offset=0)

    def read_details(self, store, scope, *, known_record_refs, assignment=None,
                     details_limit=0, details_offset=0, **kwargs):
        require(type(details_limit) is int and type(details_offset) is int
            and min(details_limit, details_offset) >= 0, 'a102_nonnegative_detail_page_required')
        require(not isinstance(known_record_refs, (str, bytes, dict)), 'a102_explicit_receipts_required')
        from .evidence_geometry import _intersection
        from .domain import canonical
        known = set(known_record_refs)
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            selected = {}
            for item, links, regions in _assessed_a102_attachments(store, scope, known, assignment):
                if (item['producer_operation'] != 'structure.reference_align'
                        or item['state'] != 'evaluated_transfer'):
                    continue
                for region in item['region_scores']:
                    if region['value'] is None:
                        continue
                    span = [[region['start'], region['end']]]
                    matched = [row for row in links if _intersection(span, row['regions'])
                        and _intersection(span, regions)]
                    if not matched:
                        continue
                    key = canonical([item['measurement_ref'], item['target_ref'], span])
                    selected[key] = {'source_ref': item['source_ref'],
                        'measurement_ref': item['measurement_ref'], 'target_ref': item['target_ref'],
                        'target_regions': span, 'native_value': region['value'],
                        'assessment_refs': sorted({row['assessment_ref'] for row in matched}),
                        'credit': 1}
            details = [selected[key] for key in sorted(selected)]
            return {'credit': len(details), 'scope': scope,
                'source_contributions': details[details_offset:details_offset+details_limit],
                'source_contribution_count': len(details), 'policy': self.as_record()}


@dataclass(frozen=True)
class A102LocalTraitCredit:
    """Credit resolved source-defined traits, including measured loss."""

    requires_episode_receipts = True
    requires_known_record_refs = True
    yield_method = 'accumulation'

    def as_record(self):
        return {'kind': 'a102_resolved_local_trait_attribution',
            'unit': 'one_distinct_assessed_resolved_physical_trait',
            'annotation': 'current_received_assessment_with_established_scope_transfer',
            'deduplication': 'original_request_physical_feature_key',
            'valid_zero': 'counted_as_resolved_measurement', 'preparation': 'no_credit'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, **kwargs):
        return self.read_details(store, scope, known_record_refs=known_record_refs,
            assignment=assignment, details_limit=0, details_offset=0)

    def read_details(self, store, scope, *, known_record_refs, assignment=None,
                     details_limit=0, details_offset=0, **kwargs):
        require(type(details_limit) is int and type(details_offset) is int
            and min(details_limit, details_offset) >= 0, 'a102_nonnegative_detail_page_required')
        require(not isinstance(known_record_refs, (str, bytes, dict)), 'a102_explicit_receipts_required')
        from .domain import canonical
        known = set(known_record_refs)
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            selected = {}
            for item, links, regions in _assessed_a102_attachments(store, scope, known, assignment):
                if (item['producer_operation'] != 'structure.reference_traits'
                        or item['state'] == 'unresolved' or item['score'] is None):
                    continue
                positions = item['target_positions']
                if (not positions or any(position is None or not any(a <= position < b
                        for a, b in regions) for position in positions)):
                    continue
                matched = [row for row in links if all(any(a <= position < b
                    for a, b in row['regions']) for position in positions)]
                if not matched:
                    continue
                key = canonical([item['target_ref'], item['request_ref'],
                    item['physical_feature_key']])
                selected[key] = {'source_ref': item['source_ref'],
                    'measurement_ref': item.get('measurement_ref'),
                    'physical_feature_key': item['physical_feature_key'],
                    'target_positions': positions, 'native_value': item['score'],
                    'assessment_refs': sorted({row['assessment_ref'] for row in matched}),
                    'credit': 1}
            details = [selected[key] for key in sorted(selected)]
            return {'credit': len(details), 'scope': scope,
                'source_contributions': details[details_offset:details_offset+details_limit],
                'source_contribution_count': len(details), 'policy': self.as_record()}


@dataclass(frozen=True)
class A102InterfaceContactCredit:
    """Credit received contacts with resolved component links and assessed target sites."""

    requires_episode_receipts = True
    requires_known_record_refs = True
    yield_method = 'accumulation'

    def as_record(self):
        return {'kind': 'a102_resolved_interface_contact',
            'unit': 'one_distinct_assessed_resolved_native_contact',
            'annotation': 'current_received_assessment_with_established_scope_transfer',
            'deduplication': 'native_measurement_and_physical_contact_anchor',
            'valid_zero': 'counted_as_resolved_measurement', 'preparation': 'no_credit'}

    def __call__(self, store, scope, *, known_record_refs, assignment=None, **kwargs):
        return self.read_details(store, scope, known_record_refs=known_record_refs,
            assignment=assignment, details_limit=0, details_offset=0)

    def read_details(self, store, scope, *, known_record_refs, assignment=None,
                     details_limit=0, details_offset=0, **kwargs):
        require(type(details_limit) is int and type(details_offset) is int
            and min(details_limit, details_offset) >= 0, 'a102_nonnegative_detail_page_required')
        require(not isinstance(known_record_refs, (str, bytes, dict)), 'a102_explicit_receipts_required')
        from .domain import canonical
        known = set(known_record_refs)
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            selected = {}
            for item, links, regions in _assessed_a102_attachments(store, scope, known, assignment):
                if (item['producer_operation'] != 'structure.interface_geometry'
                        or item['state'] != 'evaluated_transfer' or item['score'] is None):
                    continue
                measurement = item['measurement_ref']
                if measurement not in known:
                    continue
                source = store.get(measurement)
                publication = store.db.execute('SELECT body FROM a102_derived_publications '
                    'WHERE source_ref=?', (measurement,)).fetchone()
                if (source['record_type'] != 'source' or source['origin'] != 'tool'
                        or source['provider'] != 'native.a102.interface_geometry'
                        or publication is None):
                    continue
                body = json.loads(publication['body'])
                require(json.loads(store.get_artifact(source['artifact_ref'])) == body,
                    'a102_interface_contact_source_conflict')
                if (body.get('schema') != 'a102_interface_constraint_v1'
                        or body.get('target_ref') != item['target_ref']):
                    continue
                for contact in body['contacts']:
                    if (contact['kernel'] is None
                            or not set(contact['definition_source_refs']) <= known):
                        continue
                    positions = [contact[side + '_position'] for side, target in
                        zip(('left', 'right'), body['target_refs'], strict=True)
                        if target == item['target_ref']]
                    if not positions or any(not any(a <= p < b for a, b in regions)
                            for p in positions):
                        continue
                    matched = [row for row in links if all(any(a <= p < b
                        for a, b in row['regions']) for p in positions)]
                    if not matched:
                        continue
                    anchor = [contact[key] for key in ('left_position', 'left_atom',
                        'right_position', 'right_atom')]
                    key = canonical([measurement, anchor])
                    selected[key] = {'source_ref': item['source_ref'],
                        'measurement_ref': measurement,
                        'physical_feature_key': contact['physical_feature_key'],
                        'target_positions': positions, 'native_value': contact['kernel'],
                        'assessment_refs': sorted({row['assessment_ref'] for row in matched}),
                        'credit': 1}
            details = [selected[key] for key in sorted(selected)]
            return {'credit': len(details), 'scope': scope,
                'source_contributions': details[details_offset:details_offset+details_limit],
                'source_contribution_count': len(details), 'policy': self.as_record()}


def combine_received_task_progress(projected_tasks):
    """A102's one-to-one axis progress from its received task projections.

    Native correspondence contributes its bounded quality once. Each resolved
    feature, contrast, reference, trait, or contact contributes one. Typed
    experimental findings contribute one per distinct retained meaning.
    """
    from .investigation_progress import ScientificFindingProgress

    allowed = (A102StructuralCredit, A102FeatureGeometryCredit,
        A102FunctionalContrastCredit, A102ReferenceAttributionCredit,
        A102LocalTraitCredit, A102InterfaceContactCredit, ScientificFindingProgress)
    seen, units = set(), []
    for projector, result in projected_tasks:
        if type(projector) not in allowed or not isinstance(result, dict):
            raise ValueError('a102_axis_task_projection_not_owned')
        kind = projector.as_record()['kind']
        if kind in seen:
            raise ValueError('a102_axis_task_projection_repeated')
        seen.add(kind)
        value = (projector.received_axis_credit(result)
            if isinstance(projector, ScientificFindingProgress) else result.get('credit'))
        if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
                or isinstance(projector, A102StructuralCredit) and value > 1):
            raise ValueError('a102_axis_task_progress_invalid')
        units.append(value)
    return math.fsum(units)
