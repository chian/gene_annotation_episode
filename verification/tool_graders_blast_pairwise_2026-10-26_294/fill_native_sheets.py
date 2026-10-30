"""Retain all native example sheets/calculations under the protected lifecycle."""
import hashlib
import json
from pathlib import Path
import sys
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
ROOT=Path(__file__).resolve().parents[2]
DEST=Path(__file__).resolve().parent


def worker(directory):
    # Fixture adapter qualifies the supplied bytes/selected options; this is not
    # the root-owned Workflow acquisition/authentication implementation.
    sys.path.insert(0,str(ROOT/'tests'))
    from test_blast_pairwise_results import from_native
    from gene_annotation_episode.blast_pairwise_results import populate_blast_pairwise_sheet,calculate_blast_pairwise_components
    rows=[]
    for plan_path in sorted(DEST.glob('native_examples/*/plan.json'))+sorted(DEST.glob('native_ranges/*/plan.json')):
        search,bindings=from_native(plan_path.parent)
        sheet=populate_blast_pairwise_sheet(search,operand_bindings=bindings)
        result=calculate_blast_pairwise_components(sheet)
        data=json.dumps({'sheet':sheet,'calculation':result},indent=2,allow_nan=False).encode()+b'\n'
        output=directory/(plan_path.parent.name+'.json');output.write_bytes(data)
        component=result['components'];hsp=component['hsps'][0]['components'] if component['hsps'] else None
        row={'case':plan_path.parent.name,'program':search['program_context']['execution_program'],
            'source_plan':str(plan_path.relative_to(ROOT)),'source_report_sha256':search['normalized']['native']['sha256'],
            'filled_path':str(output.relative_to(ROOT)),'filled_sha256':hashlib.sha256(data).hexdigest(),
            'status':component['status'],'hsp_count':len(component['hsps']),
            'first_hsp_counts':hsp['counts'] if hsp else None,'first_hsp_fractions':hsp['fractions'] if hsp else None,
            'coordinate_context':component['coordinate_context'],'selected_operand_coverage':component['selected_operand_coverage']}
        rows.append(row)
        print(json.dumps({key:row[key] for key in ('case','status','hsp_count','first_hsp_counts','first_hsp_fractions')}),flush=True)
    (directory/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        worker(Path(sys.argv[2]));return 0
    directory=DEST/'filled_001';directory.mkdir()
    command=[str(ROOT/'.venv/bin/python'),str(Path(__file__).resolve()),'--worker',str(directory)]
    policy=LocalJobPolicy(20*1024**3,4*1024**3,None)
    result=run_local_job(command,cwd=directory,policy=policy,stdout_path=directory/'stdout.txt',stderr_path=directory/'stderr.txt',
        env={'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(directory),'XDG_CACHE_HOME':str(directory/'cache')})
    (directory/'receipt.json').write_text(json.dumps({'command':command,'returncode':result.returncode,'metadata':result.metadata},indent=2)+'\n')
    print((directory/'stdout.txt').read_text());print((directory/'stderr.txt').read_text())
    return result.returncode
if __name__=='__main__':raise SystemExit(main())
