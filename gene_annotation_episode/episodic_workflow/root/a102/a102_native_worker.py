"""Bounded native A102 worker; all subprocesses stay in its admitted cgroup."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

from .a102_scoring import NATIVE_SCHEMA, digest, require
from .a102_structures import bind_structure, ca_pdb, comparison_identity


def _run(command,directory,name):
    with (directory/(name+'.stdout')).open('wb') as stdout,(directory/(name+'.stderr')).open('wb') as stderr:
        result=subprocess.run(command,cwd=directory,stdout=stdout,stderr=stderr,check=False)
    require(result.returncode==0,'a102_native_process_failed',command=command,returncode=result.returncode)
    return (directory/(name+'.stdout')).read_text()


def _transform(rotation,translation,point):
    return [math.fsum(a*b for a,b in zip(row,point,strict=True))+shift
        for row,shift in zip(rotation,translation,strict=True)]


def _validated_transform(rotation,translation,*,rounding_precision=None):
    import numpy as np
    matrix=np.array(rotation,dtype=float)
    require(matrix.shape==(3,3) and len(translation)==3
        and np.isfinite(matrix).all() and all(math.isfinite(x) for x in translation)
        and np.allclose(matrix@matrix.T,np.eye(3),atol=.0031 if rounding_precision else 1e-5,rtol=0)
        and abs(float(np.linalg.det(matrix))-1)<(.0031 if rounding_precision else 1e-5),'a102_invalid_native_transform')
    return {'rotation':rotation,'translation_A':translation,
        'convention':'column_xyz_reference=rotation@target_xyz+translation',
        **({'native_rounding_precision':rounding_precision} if rounding_precision else {})}


def _native(request,q,t,pairs,rotation,translation,metrics,algorithm,software):
    transform=_validated_transform(rotation,translation,rounding_precision=request.get('native_transform_precision'))
    qrows,trows=q['coordinates'],t['coordinates']
    distances=[]
    for i,j in pairs:
        require(0<=i<len(qrows) and 0<=j<len(trows),'a102_native_pair_outside_staged_population')
        # Native programs read staged PDB coordinates, rounded to 0.001 A.
        moved=_transform(rotation,translation,[round(v,3) for v in qrows[i]['xyz_A']])
        distances.append(math.dist(moved,[round(v,3) for v in trows[j]['xyz_A']]))
    return {'schema':NATIVE_SCHEMA,'producer':algorithm,'software':software,
        'target_ref':q['target_ref'],'reference_ref':request['reference_binding_ref'],
        'target_binding_ref':request['target_binding_ref'],
        'target_sequence_sha256':digest(q['sequence']) if q.get('sequence') else None,
        'reference_sequence_sha256':digest(t['sequence']) if t.get('sequence') else None,
        'supplied_length':q['length'],'target_scope':q['target_scope'], 'reference_length':t['length'],
        'target_positions':[qrows[i]['position'] for i,j in pairs],
        'reference_positions':[trows[j]['position'] for i,j in pairs],
        'target_native_positions':[qrows[i]['position_key'] for i,j in pairs],
        'reference_native_positions':[trows[j]['position_key'] for i,j in pairs],
        'distances_A':distances,'atom_selection':'CA','transform':transform,'transform_sha256':digest(transform),
        'native_metrics':metrics,'target_model':deepcopy(q['model_metadata']),
        'reference_model':deepcopy(t['model_metadata']),
        'target_structure_sha256':q['file_identity']['sha256'],
        'reference_structure_sha256':t['file_identity']['sha256'],
        'target_coordinate_sha256':q.get('coordinate_sha256'),
        'reference_coordinate_sha256':t.get('coordinate_sha256'),
        'target_selection':deepcopy(q['selection']),'reference_selection':deepcopy(t['selection']),
        'target_mapping_sha256':digest(q['coordinate_to_input_mapping']),
        'reference_mapping_sha256':digest(t['coordinate_to_input_mapping']),
        'comparison_group':request['comparison_group'],'variant_ref':request['variant_ref'],
        'primary':request['primary'],'qualifications':list(dict.fromkeys([
            *q['qualifications'],*t['qualifications'],'staged_CA_coordinates_rounded_to_0.001_A',
            'shared_fold_does_not_establish_exact_function'])),
        'tm_profile':{'status':'unavailable','reason':'native_normalizations_not_proven_same_map_and_transform'}}


def usalign(request,directory):
    q,t=request['target'],request['reference']
    (directory/'query.pdb').write_text(ca_pdb(q));(directory/'reference.pdb').write_text(ca_pdb(t))
    command=[request['executable'],str(directory/'query.pdb'),str(directory/'reference.pdb'),
        '-mol','prot','-m',str(directory/'transform.txt'),'-do']
    output=_run(command,directory,'usalign')
    require('Version 20261019' in output,'a102_unsupported_usalign_version')
    pairs=[];reported=[]
    for line in output.splitlines():
        fields=line.split('\t')
        if len(fields)!=3 or not fields[0].lstrip().startswith('CA '):continue
        i=re.fullmatch(r'\s*CA\s+\S+\s+A\s*(\d+)\s*',fields[0])
        j=re.fullmatch(r'\s*CA\s+\S+\s+A\s*(\d+)\s*',fields[1])
        require(i is not None and j is not None,'a102_usalign_native_map_unreadable')
        pairs.append((int(i[1])-1,int(j[1])-1));reported.append(float(fields[2]))
    summary=re.search(r'Aligned length=\s*(\d+), RMSD=\s*([\d.]+)',output)
    require(summary is not None and int(summary[1])==len(pairs) and bool(pairs),
        'a102_usalign_paired_extent_conflict')
    rows=[]
    for line in (directory/'transform.txt').read_text().splitlines():
        if re.match(r'^[012]\s',line):rows.append([float(v) for v in line.split()[1:]])
    require(len(rows)==3 and all(len(r)==4 for r in rows),'a102_usalign_transform_unavailable')
    translation=[r[0] for r in rows];rotation=[r[1:] for r in rows]
    tms=re.findall(r'TM-score=\s*([\d.]+) \(normalized by length of Structure_([12]): L=(\d+), d0=([\d.]+)\)',output)
    metrics={'algorithm':'US-align','reported_rmsd_A':float(summary[2]),'aligned_CA_pairs':len(pairs),
        'native_TM_scores':[{'value':float(value),'normalized_by':side,'normalization_length':int(length),
            'd0_A':float(d0)} for value,side,length,d0 in tms],
        'original_stdout_sha256':hashlib.sha256(output.encode()).hexdigest(),
        'command':command,'native_version':'20261019'}
    native=_native(request,q,t,pairs,rotation,translation,metrics,'US-align',request['software'])
    require(all(abs(a-b)<0.0011 for a,b in zip(native['distances_A'],reported,strict=True)),
        'a102_usalign_transform_distance_conflict')
    return {'comparisons':[native],'leads':[]}


FOLDSEEK_FIELDS=['query','target','qlen','tlen','qstart','qend','tstart','tend','qaln','taln',
    'alnlen','rmsd','qtmscore','ttmscore','alntmscore','u','t','lddt','evalue','bits']


def foldseek(request,directory):
    q=request['target'];panel=request['references']
    version=_run([request['executable'],'version'],directory,'foldseek-version').strip()
    require(version==request['software']['version'],'a102_unsupported_foldseek_version')
    (directory/'query.pdb').write_text(ca_pdb(q))
    references=directory/'panel';references.mkdir(exist_ok=True)
    by_name={}
    for i,item in enumerate(panel):
        name=f'ref{i:04d}';(references/(name+'.pdb')).write_text(ca_pdb(item['binding']))
        by_name[name]=item
    command=[request['executable'],'easy-search',str(directory/'query.pdb'),str(references),
        str(directory/'hits.tsv'),str(directory/'foldseek-tmp'),'--threads','1','--alignment-type','1',
        '--exhaustive-search','1','--max-seq-len','4096',
        '--format-output',','.join(FOLDSEEK_FIELDS),'--max-seqs',str(len(panel)),
        '--split-memory-limit','512M','-e','1.0','--exact-tmscore','1']
    _run(command,directory,'foldseek')
    comparisons=[];leads=[]
    for ordinal,line in enumerate((directory/'hits.tsv').read_text().splitlines()):
        values=line.split('\t');require(len(values)==len(FOLDSEEK_FIELDS),'a102_foldseek_columns_conflict')
        cells=dict(zip(FOLDSEEK_FIELDS,values,strict=True))
        name=re.sub(r'(?:\.pdb)?_A$','',cells['target']).removesuffix('.pdb')
        require(name in by_name,'a102_foldseek_database_identity_conflict')
        item=by_name[name];t=item['binding']
        lead={'native_cells':cells,'reference_binding_ref':item['binding_ref'],'qualification':None}
        try:
            rotation=[float(v) for v in cells['u'].split(',')]
            translation=[float(v) for v in cells['t'].split(',')]
            require(len(rotation)==9 and len(translation)==3,'a102_foldseek_transform_unavailable')
            rotation=[rotation[i:i+3] for i in range(0,9,3)]
            # Foldseek 10 prints reference -> query, to 0.001 per entry.
            # Invert the reported transform algebraically, without a refit.
            import numpy as np
            original_rotation=deepcopy(rotation);original_translation=list(translation)
            _validated_transform(rotation,translation,rounding_precision={'matrix_entry':.001,'translation_A':.001})
            inverse=np.linalg.inv(np.array(rotation))
            rotation=inverse.tolist();translation=(-inverse@np.array(translation)).tolist()
            require(int(cells['qlen'])==len(q['coordinates']) and int(cells['tlen'])==len(t['coordinates']),
                'a102_foldseek_staged_extent_conflict')
            qa,ta=cells['qaln'],cells['taln'];require(len(qa)==len(ta),'a102_foldseek_traceback_conflict')
            i,j=int(cells['qstart'])-1,int(cells['tstart'])-1;pairs=[]
            for a,b in zip(qa,ta,strict=True):
                if a!='-':require(a==q['coordinates'][i]['symbol'],'a102_foldseek_query_symbol_conflict')
                if b!='-':require(b==t['coordinates'][j]['symbol'],'a102_foldseek_reference_symbol_conflict')
                if a!='-' and b!='-':pairs.append((i,j))
                i+=a!='-';j+=b!='-'
            require(i==int(cells['qend']) and j==int(cells['tend']) and pairs,'a102_foldseek_extent_conflict')
            nested={**request,'reference_binding_ref':item['binding_ref'],
                'native_transform_precision':{'matrix_entry':.001,'translation_A':.001,
                    'derivation':'inverse_of_reported_reference_to_query_transform_no_refit'},
                'comparison_group':comparison_identity(q,t),
                'variant_ref':digest({'request':request['request_identity'],'row':ordinal,'native':cells})}
            metrics={'algorithm':'Foldseek','mode':'global_TMalign_1','native_cells':cells,
                'reported_rmsd_A':float(cells['rmsd']),'database_manifest':request['database_manifest'],
                'native_reference_to_query_transform':{'rotation':original_rotation,'translation_A':original_translation},
                'command':command,'exhaustive_bounded_panel':True,'native_version':request['software']['version']}
            native=_native(nested,q,t,pairs,rotation,translation,metrics,'Foldseek',request['software'])
            actual=math.sqrt(math.fsum(d*d for d in native['distances_A'])/len(pairs))
            metrics.update(computed_rmsd_from_retained_map_transform_A=actual,
                reported_rmsd_reproduces_retained_transform=abs(actual-float(cells['rmsd']))<.03,
                scoring_operand='paired_distances_from_retained_native_map_and_algebraically_inverted_reported_transform')
            error_translation=math.sqrt(3)*.0005
            inverse_norm=float(np.linalg.norm(inverse,ord=2))
            native['distance_rounding_bounds_A']=[inverse_norm*(.0015*(float(np.linalg.norm(
                np.array(q['coordinates'][i]['xyz_A'])-np.array(original_translation)))+error_translation)+error_translation)
                for i,j in pairs]
            native['qualifications'].extend(['native_transform_rounded_to_0.001_per_entry',
                'RMSD_derived_from_retained_map_and_transform_without_new_alignment_or_refit'])
            if not metrics['reported_rmsd_reproduces_retained_transform']:
                native['qualifications'].append('reported_RMSD_does_not_reproduce_retained_transform_and_is_not_scoring_operand')
        except (ValueError,IndexError) as error:
            lead['qualification']=str(error);leads.append(lead)
        else:comparisons.append(native)
    return {'comparisons':comparisons,'leads':leads,'database_manifest':request['database_manifest'],
        'search_mode':'global_TMalign_1','searched_reference_count':len(panel)}


def main():
    request_path=Path(sys.argv[1]).resolve();request=json.loads(request_path.read_text())
    directory=request_path.parent
    try:
        if request['operation']=='bind':result=bind_structure(Path(request['input_path']).read_bytes(),request)
        elif request['operation']=='usalign':result=usalign(request,directory)
        elif request['operation']=='foldseek':result=foldseek(request,directory)
        else:raise ValueError('a102_worker_operation_unavailable')
        value={'status':'completed','result':result,'failure':None}
    except Exception as error:
        value={'status':'failed','result':None,'failure':{'code':str(error),'type':type(error).__name__,
            'detail':getattr(error,'detail',{})}}
    path=directory/'worker-result.json';temporary=directory/'worker-result.writing'
    temporary.write_text(json.dumps(value,sort_keys=True,allow_nan=False));temporary.replace(path)
    return 0 if value['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
