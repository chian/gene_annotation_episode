"""Research-only mmCIF token extraction; no structural alignment or target transfer."""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).parent

def parse(path):
    tokens=[]; lines=path.read_text().splitlines(); i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith(';'):
            body=[line[1:]];i+=1
            while i<len(lines) and not lines[i].startswith(';'): body.append(lines[i]);i+=1
            tokens.append('\0'+'\n'.join(body))
        elif not line.startswith('#'):
            for m in re.finditer(r'''(?:'[^']*'|"[^"]*")(?=\s|$)|[^\s]+''',line):
                s=m.group(); tokens.append("\0"+s[1:-1] if len(s)>1 and s[0] in "\"'" and s[-1]==s[0] else s)
        else:tokens.append('#')
        i+=1
    out={};i=0
    while i<len(tokens):
        s=tokens[i]
        if s=='loop_':
            i+=1; cols=[]
            while i<len(tokens) and tokens[i].startswith('_'):cols.append(tokens[i]);i+=1
            vals=[]
            while i<len(tokens) and tokens[i]!='#' and tokens[i]!='loop_' and not tokens[i].startswith('_') and not tokens[i].startswith('data_'):vals.append(tokens[i]);i+=1
            assert len(vals)%len(cols)==0,(path,cols,len(vals))
            for j,c in enumerate(cols):out[c]=vals[j::len(cols)]
        elif s.startswith('_'):
            out[s]=[tokens[i+1]];i+=2
        else:i+=1
    return {k:[v.removeprefix('\0') for v in vs] for k,vs in out.items()}

def category(d,cat):
    ks=[k for k in d if k.startswith(cat+'.')]
    return [{k.split('.',1)[1]:d[k][i] for k in ks} for i in range(len(d[ks[0]]))] if ks else []

out={}
for accession in ['4HF0','4HF1','4HF2']:
    f=ROOT/f'{accession}_cif';d=parse(f)
    cats=['_entity','_entity_poly','_entity_src_gen','_exptl','_exptl_crystal_grow','_diffrn','_reflns','_refine','_refine_ls_shell','_refine_ls_restr','_pdbx_struct_assembly','_pdbx_struct_assembly_gen','_pdbx_unobs_or_zero_occ_residues','_pdbx_unobs_or_zero_occ_atoms','_pdbx_audit_revision_history']
    item={'file':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'native_categories':{c:category(d,c) for c in cats}}
    atoms=category(d,'_atom_site'); chains={}
    for chain in sorted({a['auth_asym_id'] for a in atoms}):
        rows=[a for a in atoms if a['auth_asym_id']==chain and a['label_seq_id'] not in ['.','?']]; residues=sorted({int(a['auth_seq_id']) for a in rows});alts=sorted({a['label_alt_id'] for a in rows})
        chains[chain]={'atom_count':len(rows),'modeled_residue_count':len(residues),'modeled_auth_residues':residues,'alt_ids':alts,'occupancy_field_values':sorted({a['occupancy'] for a in rows}),'minimum_B_iso_or_equiv':min(float(a['B_iso_or_equiv']) for a in rows),'maximum_B_iso_or_equiv':max(float(a['B_iso_or_equiv']) for a in rows)}
    item['coordinate_inventory_derived']=chains
    item['selected_site_atom_rows']=[a for a in atoms if a['auth_asym_id'] in ['A','B'] and int(a['auth_seq_id']) in [40,41,43,44,59,92,98,104,107]]
    sf=ROOT/f'{accession}_sf_cif'; sftext=sf.read_text(); item['structure_factor_file']={'file':sf.name,'sha256':hashlib.sha256(sf.read_bytes()).hexdigest(),'header':sftext[:sftext.index('_refln.index_h')+len('_refln.index_h')] if '_refln.index_h' in sftext else sftext[:1200],'data_blocks':re.findall(r'^data_.*$',sftext,re.M),'row_count_not_calculated':True,'density_maps_not_computed':True}
    out[accession]=item
(ROOT/'DEPOSITION_EXTRACTION_001.json').write_text(json.dumps(out,indent=2)+'\n')
for acc,x in out.items():
 print(acc)
 for c in ['_entity','_entity_poly','_pdbx_struct_assembly']:
  print(c,json.dumps(x['native_categories'][c]))
 print('refine',json.dumps({k:v for k,v in x['native_categories']['_refine'][0].items() if k in ['ls_R_factor_R_work','ls_R_factor_R_free','ls_d_res_high','ls_number_reflns_R_free','ls_percent_reflns_R_free','overall_SU_ML']}))
 for c in ['A','B']:
  rows=x['native_categories']['_pdbx_unobs_or_zero_occ_residues'];seq=sorted({int(r['auth_seq_id']) for r in rows if r['auth_asym_id']==c});print('unmodeled',c,seq)
  y=x['coordinate_inventory_derived'][c]; print('polymer_count',c,y['atom_count'],y['modeled_residue_count'], 'range',min(y['modeled_auth_residues']),max(y['modeled_auth_residues']), 'alt_ids',y['alt_ids'],'occupancy',y['occupancy_field_values'])
 print('SF header',x['structure_factor_file']['header'][:400])
