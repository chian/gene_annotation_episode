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
                     assignment=None,episode_id=None,run_id=None):
        require(type(details_limit) is int and type(details_offset) is int and min(details_limit,details_offset)>=0,
                'a103_nonnegative_detail_page_required')
        require(not isinstance(known_record_refs,(str,bytes,dict)),'a103_explicit_receipts_required')
        known = set(known_record_refs)
        require(all(type(r) is str for r in known),'a103_explicit_receipts_required')
        with store.read_snapshot():
            scope = store.validate_scope(scope)
            require(assignment is None or store.validate_scope(assignment['scope'])==scope,
                    'a103_scope_differs_from_original_commission')
            attachments = [r for r in received_attachments(store,known) if r['target_ref'] in scope['subject_refs']]
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
                    'value':row['score'],'target_regions':row['target_regions'],'policy':row['policy'],
                    'state':row['state'],'dependency_group':row.get('dependency_group')})
            targets = {}
            for target in scope['subject_refs']:
                regions = ([[s['start'],s['end']] for s in scope['segments'] if s['target_ref']==target]
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
