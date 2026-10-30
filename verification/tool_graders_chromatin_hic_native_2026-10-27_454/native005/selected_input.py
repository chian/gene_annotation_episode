"""Selected tiny native CLI variants, with independent input expectations."""
from pathlib import Path
import hashlib
import json
import math
import os
import subprocess
import sys

ROOT=Path.cwd(); PACKET=ROOT.parent
def save(path,value): Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def pin(path):
    path=Path(path); raw=path.read_bytes()
    return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest(),'size_bytes':len(raw)}
native=PACKET/'prerequisite003/hictk'
assert pin(native)['sha256']=='aaae1ec459a63ff8be922b026c4799da4135bb81df78c756feae9dc7a8176afe'
inspector=ROOT/'byte_inspector.py'; inspector.write_bytes((PACKET/'byte_inspector.py').read_bytes())
sys.path.insert(0,str(ROOT)); from byte_inspector import inspect
save(ROOT/'SELECTED_DEPENDENCIES.json',[pin(native),pin(inspector)])

def case(name,chroms,rows,res=10,all_matrix=False):
    path=ROOT/name; path.mkdir(); (path/'tmp').mkdir()
    (path/'input.chrom.sizes').write_text(''.join(f'{name}\t{length}\n' for name,length in chroms))
    (path/'input.coo').write_text(''.join('\t'.join(map(str,row))+'\n' for row in rows))
    env={**os.environ,'HICTK_NO_TELEMETRY':'1','TMPDIR':str(path/'tmp')}
    def run(command,args):
        argv=[str(native),*args]
        save(path/(command+'.request.json'),{'argv':argv,'cwd':str(path),'environment_overrides':{'HICTK_NO_TELEMETRY':'1','TMPDIR':str(path/'tmp')}})
        with (path/(command+'.stdout.txt')).open('wb') as out,(path/(command+'.stderr.txt')).open('wb') as err:
            result=subprocess.run(argv,cwd=path,env=env,stdout=out,stderr=err)
        save(path/(command+'.result.json'),{'returncode':result.returncode})
        return result.returncode
    rc=run('load',['load','--format','coo','--output-fmt','hic','--bin-size',str(res),'--chrom-sizes',str(path/'input.chrom.sizes'),'--assembly','synthetic_'+name,'--zero-based','--validate-pixels','--no-transpose-lower-triangular-pixels','--no-skip-all-vs-all' if all_matrix else '--skip-all-vs-all','--threads','2','--chunk-size','32','--tmpdir',str(path/'tmp'),str(path/'input.coo'),str(path/'output.hic')])
    if rc:
        save(path/'OUTCOME.json',{'status':'native_writer_failed','exit':rc}); return
    audit=inspect(path/'output.hic',path/'blocks'); save(path/'BYTE_AUDIT.json',audit)
    validate_rc=run('validate',['validate','--output-format','json',str(path/'output.hic')])
    actual=[]
    offset=0
    for chrom,length in chroms:
        dump_rc=run('dump_'+chrom,['dump','--resolution',str(res),'--matrix-type','observed','--matrix-unit','BP','--range',chrom,'--balance','NONE','--sorted',str(path/'output.hic')])
        expected=[r for r in rows if offset<=r[0]<(offset+(length+res-1)//res) and offset<=r[1]<(offset+(length+res-1)//res)]
        if dump_rc==0:
            dump=[tuple(map(float,line.split())) for line in (path/('dump_'+chrom+'.stdout.txt')).read_text().splitlines()]
            assert sorted(dump)==sorted(expected),(name,chrom,dump,expected)
            actual.extend(dump)
        elif expected: raise RuntimeError(f'{name}/{chrom}: independent dump failed')
        offset+=(length+res-1)//res
    records=[]
    for matrix in audit['matrices']:
        chromosome=next(c for c in audit['chromosomes'] if c['index']==matrix['chr1'])
        if chromosome['name'] in {'All','ALL','all'}: continue
        offset=sum((length+res-1)//res for chrom,length in chroms[:[c[0] for c in chroms].index(chromosome['name'])])
        for zoom in matrix['zooms']:
            for block in zoom['blocks']:
                for record in block['records']:
                    records.append((record['x']+offset,record['y']+offset,record['value']))
                    expected_bid=int(math.log2(1+abs(record['x']-record['y'])/(math.sqrt(2)*zoom['block_bin_count'])))*zoom['block_column_count']+(record['x']+record['y'])//(2*zoom['block_bin_count'])
                    assert expected_bid==block['block_id'],(name,record,expected_bid,block['block_id'])
    assert sorted(records)==sorted(rows)
    save(path/'OUTCOME.json',{'status':'native_written_and_independently_checked','validate_exit':validate_rc,'source_rows':rows,'actual_native_dump_rows':actual,'matrix_keys':[m['key'] for m in audit['matrices']],
        'present_zero_block_matrix':any(z['declared_block_count']==0 for m in audit['matrices'] for z in m['zooms']),
        'matrix_absent':not audit['matrices'],'source_pairs_match_byte_decoder':True,'rotated_v9_block_ownership_matches':True})
    save(path/'PINS.json',[pin(path/f) for f in ['input.chrom.sizes','input.coo','output.hic','BYTE_AUDIT.json','OUTCOME.json']])
    print(json.dumps({'case':name,'file':pin(path/'output.hic'),'matrices':[{k:v for k,v in m.items() if k!='zooms'} for m in audit['matrices']],'block_counts':[z['declared_block_count'] for m in audit['matrices'] for z in m['zooms']]}),flush=True)

case('six_insulation',[('chrA',60)],[(i,i+1,value) for i,value in enumerate([5,1,5,1,5])])
case('terminal_two_chromosomes',[('chrA',40),('chrB',35)],[(0,0,7),(4,4,4),(4,6,6),(5,7,2),(7,7,4)])
case('terminal_with_all',[('chrA',10000),('chrB',35)],[(0,0,7),(1000,1000,4),(1000,1002,6),(1001,1003,2),(1003,1003,4)],all_matrix=True)
# Source mapper constants imply 10000 bins / 11 columns => block_bin_count 910.
# Inputs straddle diagonal pad boundary x+y=1820 and depth boundary d=ceil(sqrt(2)*910)=1287.
case('sparse_multiblock',[('chrA',10000000)],[(0,0,1),(0,1286,2),(0,1287,3),(0,1820,4),(100,9000,5),(909,909,6),(909,910,7),(909,911,8),(910,910,9),(910,911,10),(9099,9100,11),(9999,9999,12)],res=1000)
case('empty_input',[('chrA',40)],[])
save(ROOT/'INDEPENDENT_EXPECTATIONS.json',{
 'six_insulation':{'adjacent_contacts':[5,1,5,1,5],'full_window_count':5,'w_bins':1,'mean':3.4,'population_variance':3.84,'low_z':'-3/sqrt(6)','high_z':'2/sqrt(6)','strict_z_threshold':-1,'boundaries_bp':[20,40],'domain_bp':[20,40],'domain_length_bp':20,'domain_length_kb':0.02,'threshold_minus_1_3_boundaries':[]},
 'terminal_two_chromosomes':{'chrB_original_index':1,'chrB_length_bp':35,'resolution_bp':10,'physical_bins':[[0,10],[10,20],[20,30],[30,35]],'last_base34_bin':3,'end35_valid':True,'end40_valid':False,'start31_aligned':False},
 'sparse_multiblock':{'resolution_bp':1000,'chromosome_bins':10000,'expected_block_bin_count':910,'expected_block_column_count':11,'depth_transition_pair':[[0,1286],[0,1287]],'pad_transition_pairs':[[909,910],[909,911]]}})
