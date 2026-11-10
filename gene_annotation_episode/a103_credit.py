"""Read-only A103 projection from actual admitted measurement attachments."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .a103_attachments import received_attachments
from .a103_publication import received_measurement
from .a103_scoring import VERSION, PROFILE, require


@dataclass(frozen=True)
class A103ContextCredit:
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
            scalar = _result('A103', None, formula='received_current_axis_result_required', inputs={}, reasons=[reason])
        else:
            native = self.read_details(store, scope, known_record_refs=known, subjects=(target,),
                evidence_regions=selected, details_limit=details_limit, details_offset=details_offset)
            measured = native['source_contribution_count'] > 0
            scalar = correspondence_scalar('A103', native['credit'], measured=measured)
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
        return {'kind':'a103_context_credit','version':VERSION,'profile':PROFILE,
            'receipt':'explicit_received_host_issued_context_attachment',
            'aggregation':'maximum_eligible_context_per_original_scope_cell_then_length_weighted_mean',
            'missing':'unknown_qualification_retained; no_fabricated_association',
            'interpretation':'investigation_progress_not_exact_function_probability'}

    def __call__(self,store,scope,*,known_record_refs,assignment=None,episode_id=None,run_id=None):
        return self.read_details(store,scope,known_record_refs=known_record_refs,assignment=assignment,
            episode_id=episode_id,run_id=run_id,details_limit=0,details_offset=0)

    def read_details(self,store,scope,*,known_record_refs,details_limit,details_offset,
                     assignment=None,episode_id=None,run_id=None,subjects=None,evidence_regions=None):
        require(type(details_limit) is int and type(details_offset) is int and min(details_limit,details_offset)>=0,
                'a103_nonnegative_detail_page_required')
        require(not isinstance(known_record_refs,(str,bytes,dict)),'a103_explicit_receipts_required')
        known = set(known_record_refs)
        require(all(type(r) is str for r in known),'a103_explicit_receipts_required')
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            require(assignment is None or store.validate_scope(assignment['scope'])==scope,
                    'a103_scope_differs_from_original_commission')
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
            attachments = [r for r in received_attachments(store,known) if r['target_ref'] in selected_subjects
                and (evidence_regions is None or r['source_ref'] in evidence_regions)]
            variants = {}
            for row in attachments:
                if row.get('dependency_group') is not None:
                    variants.setdefault(row['dependency_group'],set()).add(row['variant'])
            ambiguous = {key for key,values in variants.items() if len(values)>1}
            contributions = []
            for row in attachments:
                if row.get('score') is None or row.get('dependency_group') in ambiguous:
                    continue
                require(type(row['score']) in {int,float} and math.isfinite(row['score']) and 0<=row['score']<=1,
                        'a103_attachment_score_invalid')
                contributions.append({'source_ref':row['source_ref'],'grading_artifact_ref':row['grading_artifact_ref'],
                    'measurement_ref':row['measurement_ref'],'target_ref':row['target_ref'],
                    'value':row['score'],'target_regions':(_intersection(row['target_regions'],
                        evidence_regions[row['source_ref']]) if evidence_regions is not None else row['target_regions']),
                    'policy':row['policy'],
                    'state':row['state'],'dependency_group':row.get('dependency_group')})
            contributions = [row for row in contributions if row['target_regions']]
            targets = {}
            for target in selected_subjects:
                regions = (selected_regions[target] if selected_regions is not None else
                    [[s['start'],s['end']] for s in scope['segments'] if s['target_ref']==target]
                    if 'segments' in scope else [[0,store.subject_length(target)]])
                if not regions:continue
                own = [r for r in contributions if r['target_ref']==target]
                cells = []
                for start,end in regions:
                    boundaries = sorted({start,end,*[p for r in own for span in r['target_regions']
                        for p in span if start<p<end]})
                    for a,b in zip(boundaries,boundaries[1:]):
                        values = [r['value'] for r in own if any(x<=a and b<=y for x,y in r['target_regions'])]
                        cells.append({'start':a,'end':b,'value':max(values,default=0.)})
                length = sum(b-a for a,b in regions)
                value = math.fsum((c['end']-c['start'])*c['value'] for c in cells)/length
                own_attachments = [r for r in attachments if r['target_ref']==target]
                pending = [r for r in own_attachments if r['missing']]
                targets[target] = {'value':value,'assigned_length':length,'regions':regions,'cells':cells,
                    'status':'partial_attribution' if value and pending else 'attributed_context_received' if own else
                        'unresolved_attribution' if pending else 'no_received_context_association',
                    'unresolved_variant_groups':sorted(ambiguous & {r.get('dependency_group') for r in own_attachments}),
                    'pending_measurement_refs':sorted({r['measurement_ref'] for r in pending})}
            denominator = sum(t['assigned_length'] for t in targets.values())
            require(denominator>0,'a103_nonempty_original_scope_required')
            value = math.fsum(t['value']*t['assigned_length'] for t in targets.values())/denominator
            sheets = {'locus_binding':[],'organization':[],'recurrence':[],'fusion':[],
                      'cooccurrence':[],'native_channel':[],'functional_contrast':[],'component_detection':[]}
            for ref in sorted(known):
                measured = received_measurement(store,ref)
                if measured is not None and measured['body']['target_ref'] in targets:
                    body = measured['body']
                    # Full native component arrays remain in retained artifacts.
                    preview = {k:v for k,v in body.items() if k not in {
                        'raw_neighborhood','cds','coding_locus','selected_loci'}}
                    if measured['grade']['kind']=='functional_contrast':
                        qualified = next((r for r in attachments if r['measurement_ref']==ref
                            and r['policy']=='functional_contrast_matched_native_context_and_bounds_v1'),None)
                        if qualified is not None:
                            preview.update(qualified_panel=qualified['qualified_panel'],
                                attribution_source_ref=qualified['source_ref'],qualification_state=qualified['state'])
                    sheets[measured['grade']['kind']].append({'source_ref':ref,
                        'grading_artifact_ref':measured['grading_artifact_ref'],**preview})
            page = contributions[details_offset:details_offset+details_limit]
            def preview(value):
                if isinstance(value,dict):return {k:preview(v) for k,v in value.items() if k!='pairs'}
                if isinstance(value,list):return [preview(v) for v in value]
                return value
            return {'credit':value,'scope':scope,'target_sheets':targets,'a103_sheet':sheets,
                'tool_attachments':preview(attachments),'source_contributions':page,
                'source_contribution_count':len(contributions),'inactive_dependencies':[],
                'inactive_dependency_count':0,'next_offset':details_offset+len(page)
                    if details_limit and details_offset+len(page)<len(contributions) else None,
                'interpretation':'measured_context_with_specific_entity_and_region_attribution'}
