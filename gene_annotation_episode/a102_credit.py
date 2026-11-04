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
                     assignment=None,episode_id=None,run_id=None):
        require(type(details_limit) is int and details_limit>=0 and type(details_offset) is int
            and details_offset>=0,'a102_nonnegative_detail_page_required')
        require(not isinstance(known_record_refs,(str,bytes,dict)), 'a102_explicit_receipts_required')
        known=sorted(set(known_record_refs))
        require(all(type(ref) is str for ref in known),'a102_explicit_receipts_required')
        with store.read_snapshot():
            scope=store.validate_scope(scope)
            require(assignment is None or store.validate_scope(assignment['scope'])==scope,
                'a102_credit_scope_differs_from_original_commission')
            targets={}
            for ref in scope['subject_refs']:
                length=store.subject_length(ref)
                regions=([[s['start'],s['end']] for s in scope['segments'] if s['target_ref']==ref]
                    if scope.get('segments') is not None else [[0,length]])
                if regions:targets[ref]=(length,regions)
            require(bool(targets),'a102_required_scope_empty')
            rows={ref:[] for ref in targets};sources=[];feature_sheets=[];contrast_sheets=[]
            derived=store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='a102_derived_publications'").fetchone()
            for reference in known:
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
                require(store.subject_molecule(target)=='protein','a102_protein_target_required')
                rows[target].append(received['grade'])
                sources.append({key:received[key] for key in ('source_ref','grading_artifact_ref')}
                    | {'target_ref':target,'comparison_ref':received['grade']['variant_ref']})
            sheets={ref:compile_native_sheet(rows[ref],target_ref=ref,supplied_length=length,regions=regions)
                for ref,(length,regions) in targets.items()}
            attachments=[row for row in received_attachments(store,known) if row['target_ref'] in targets]
            for panel in contrast_sheets:
                grade=next((row for row in attachments if row.get('measurement_ref')==panel['source_ref']
                    and row['producer_operation']=='structure.contrast'),None)
                if grade:panel.update(grade['qualified_panel'],attribution_source_ref=grade['source_ref'])
            def preview(row):
                value={k:v for k,v in row.items() if k!='mapped_geometry'}
                if 'sequence_link' in value:value['sequence_link']={k:v for k,v in value['sequence_link'].items() if k!='pairs'}
                return value
            transferred=[row for row in attachments if row['policy']=='reference_fold_native_map_and_local_distance_v1' and row['state']!='excluded']
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
                        projected=reference_region_value(row,region['start'],region['end'])
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
