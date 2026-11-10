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
