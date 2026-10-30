"""Selected tiny examples, each a separate original native invocation.

All sequence derivatives are synthetic engineering inputs. No database is built
or searched. The outer existing local lifecycle owns 20 GiB/4 GiB/no wall cap.
"""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.native_blast_contracts import requested_job_from_native, native_blast_digest

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent / 'native_ranges'
BIN = ROOT / 'resources/software/ncbi-blast-2.17.0+/bin'
POLICY = LocalJobPolicy(20*1024**3, 4*1024**3, None)
FIELDS = 'qseqid sseqid qlen slen qstart qend sstart send qframe sframe length nident gaps mismatch score bitscore evalue qseq sseq btop'.split()
CODONS = dict(zip('ACDEFGHIKLMNPQRSTVWY', 'GCT TGT GAT GAA TTT GGT CAT ATT AAA CTG ATG AAT CCT CAA CGT TCT ACT GTT TGG TAT'.split()))


def rc(s):
    return s.translate(str.maketrans('ACGT','TGCA'))[::-1]


def main():
    DEST.mkdir(exist_ok=True)
    old = json.loads((ROOT/'tests/fixtures/blast_grading_inputs/native_pair_result.json').read_text())
    hsp = old['BlastOutput2'][0]['report']['results']['bl2seq'][0]['hits'][0]['hsps'][0]
    protein, derivative = hsp['qseq'], hsp['hseq'].replace('-', '')
    small = protein[:80]
    coding = ''.join(CODONS[a] for a in small)
    specs = [
        ('blastn_range_forward','blastn',coding,coding,['-task','blastn','-dust','no','-strand','plus','-query_loc','31-210','-subject_loc','31-240']),
        ('blastn_reverse','blastn',coding,rc(coding),['-task','blastn','-dust','no','-strand','both']),
        ('blastx_range_reverse','blastx',rc('AA'+coding+'GG'),small,['-strand','minus','-query_gencode','11','-seg','no','-query_loc','30-215']),
    ]
    receipts=[]
    for case, program, query, subject, options in specs:
        for fmt in ('json15', 'tabular6' if case.endswith('no_hits') else 'tabular7'):
            selected=case+'_'+fmt
            directory=DEST/selected
            if directory.exists():
                raise ValueError('example_already_selected:'+selected)
            directory.mkdir()
            roles=[]
            bindings=[]
            for role, seq, ident in [('query_sequence',query,'query_'+case),('subject_sequence',subject,'subject_'+case)]:
                path=directory/(role+'.fa')
                path.write_text('>'+ident+'\n'+seq+'\n')
                data=path.read_bytes()
                roles.append({'role':role,'format':'fasta','path':str(path),'sha256':hashlib.sha256(data).hexdigest(),'size_bytes':len(data),'artifact_ref':None})
                bindings.append({'operand_role':role,'record_ordinal':0,'native_name':ident,'native_accession':None,
                                 'subject_ref':'query_subject' if role=='query_sequence' else None,
                                 'reference_ref':'paired_reference' if role=='subject_sequence' else None})
            executable=BIN/program
            outputs=[{'role':role,'format':'text','relative_path':role+'.txt','fields':None,'delimiter':None} for role in ('stdout','stderr')]
            outputs.append({'role':'primary_report','format':fmt,'relative_path':'report.json' if fmt=='json15' else 'report.tsv',
                'fields':None if fmt=='json15' else FIELDS,'delimiter':None if fmt=='json15' else '@' if program=='tblastx' else '\t'})
            job={'version':'native_blast_job_v1','program':program,'mode':'pairwise',
                 'software':{'executable':str(executable),'sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),'engine_version':'2.17.0+'},
                 'environment':{},'operands':roles,'operand_bindings':bindings,'options':[*options,'-num_threads','1'],
                 'outputs':outputs,'metadata':{'engineering_example':selected,'input_kind':'synthetic_derivative_of_retained_public_sequence'},'grading_parameters':{}}
            request=requested_job_from_native(job)
            plan={'version':'native_blast_run_plan_v1','identity':{'run_id':'verification294','episode_id':'explicit-example-selection',
                'resource_id':'local','execution_id':selected,'attempt_id':selected,'operation_key':'selected:'+selected,
                'requested_job_sha256':native_blast_digest(request)},'requested_job':request,'attempt_directory':str(directory/'attempt'),
                'policy':asdict(POLICY)}
            plan_path=directory/'plan.json'
            plan_path.write_text(json.dumps(plan,indent=2)+'\n')
            command=[str(ROOT/'.venv/bin/python'),'-m','gene_annotation_episode.native_blast_driver',str(plan_path)]
            result=run_local_job(command,cwd=directory,policy=POLICY,stdout_path=directory/'producer.stdout',stderr_path=directory/'producer.stderr',
                env={'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(directory),'XDG_CACHE_HOME':str(directory/'cache')})
            receipt={'case':selected,'program':program,'format':fmt,'command':command,'returncode':result.returncode,'metadata':result.metadata,
                     'plan':str(plan_path),'bundle':str(directory/'attempt/bundle.json'),'query_length':len(query),'reference_length':len(subject)}
            (directory/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
            receipts.append(receipt)
            (DEST/'receipts.json').write_text(json.dumps({'purpose':'actual_native_pairwise_engineering_examples','policy':asdict(POLICY),'receipts':receipts},indent=2)+'\n')
            print(json.dumps({'case':selected,'returncode':result.returncode,'bundle':receipt['bundle']}),flush=True)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
