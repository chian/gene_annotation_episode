"""Durable execution authority. No Episode selection or scientific inference.

One fixed workload has one job identity. Detached execution survives the model
sessions and the workflow process. Result blocks are committed individually;
status and functional handoff checks read the same durable records.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid

from ..domain import canonical
from ..local_jobs import LocalJobPolicy, check_scratch_budget, run_local_job
from ..read_mapping import file_digest, parse_paf_line


def now():
    return datetime.now(timezone.utc).isoformat()


def token(kind, body):
    return kind + '_' + hashlib.sha256(canonical(body).encode()).hexdigest()[:24]


class JobStore:
    def __init__(self, directory):
        self.path = Path(directory).resolve()
        self.path.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path/'state.sqlite', timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS example_configuration(singleton INTEGER PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS execution_setup(name TEXT PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS detached_jobs(job_ref TEXT PRIMARY KEY, workload_ref TEXT NOT NULL,
            state TEXT NOT NULL, pid INTEGER, process_start TEXT, boot_id TEXT,
            submitted_at TEXT NOT NULL, started_at TEXT, finished_at TEXT, failure TEXT);
        CREATE TABLE IF NOT EXISTS mapping_blocks(block_index INTEGER PRIMARY KEY, read_count INTEGER NOT NULL,
            state TEXT NOT NULL, started_at TEXT, finished_at TEXT, elapsed_seconds REAL,
            result_path TEXT, result_sha256 TEXT, native_metadata TEXT);
        CREATE TABLE IF NOT EXISTS example_operations(operation_key TEXT PRIMARY KEY, name TEXT NOT NULL,
            arguments TEXT NOT NULL, result TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS job_samples(sample_ref TEXT PRIMARY KEY, episode_id TEXT NOT NULL,
            job_ref TEXT NOT NULL, sampled_at TEXT NOT NULL, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS result_deliveries(block_index INTEGER PRIMARY KEY, episode_id TEXT NOT NULL,
            summary TEXT NOT NULL, parsed_path TEXT NOT NULL, parsed_sha256 TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS handoff_receipts(receipt_ref TEXT PRIMARY KEY, job_ref TEXT NOT NULL,
            handoff TEXT NOT NULL, checked_at TEXT NOT NULL, sample TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS scheduled_commissions(commission_ref TEXT PRIMARY KEY,
            owner_episode_id TEXT NOT NULL, decision_index INTEGER NOT NULL, due_at REAL NOT NULL,
            request TEXT NOT NULL, state TEXT NOT NULL, child_episode_id TEXT,
            UNIQUE(owner_episode_id,decision_index));
        CREATE TABLE IF NOT EXISTS parent_accounts(account_ref TEXT PRIMARY KEY, episode_id TEXT NOT NULL,
            body TEXT NOT NULL, recorded_at TEXT NOT NULL);
        ''')
        self.db.commit()

    def close(self):
        self.db.close()

    def config(self):
        row = self.db.execute('SELECT body FROM example_configuration').fetchone()
        if row is None:
            raise ValueError('workload_not_registered')
        return json.loads(row[0])

    def setup(self, name):
        row = self.db.execute('SELECT body FROM execution_setup WHERE name=?', (name,)).fetchone()
        return json.loads(row[0]) if row else None

    def save_setup(self, name, body):
        self.db.execute('INSERT OR REPLACE INTO execution_setup VALUES(?,?)',(name,canonical(body)))
        self.db.commit()
        return body

    def job(self):
        row = self.db.execute('SELECT * FROM detached_jobs').fetchone()
        return dict(row) if row else None

    def validate_job(self, job_ref):
        row = self.job()
        if row is None or row['job_ref'] != job_ref or row['workload_ref'] != self.config()['workload_ref']:
            raise ValueError('job_reference_does_not_resolve_to_this_workload')
        return row

    def resolver(self, reference, namespace=None):
        if namespace in (None,'workload') and reference == self.config()['workload_ref']:
            return True
        kinds = {'job':('detached_jobs','job_ref'), 'sample':('job_samples','sample_ref'),
                 'receipt':('handoff_receipts','receipt_ref'), 'commission':('scheduled_commissions','commission_ref'),
                 'account':('parent_accounts','account_ref')}
        return any(self.db.execute(f'SELECT 1 FROM {table} WHERE {column}=?',(reference,)).fetchone()
            for kind,(table,column) in kinds.items() if namespace in (None,kind))

    def environment(self):
        configured = self.config()['minimap2_candidates']
        return {'candidates':[{'candidate_index':i,'exists':Path(p).is_file(),'path':p}
            for i,p in enumerate(configured)], 'cpu_count':os.cpu_count(),
            'job_limits':self.config()['job_limits'], 'setup':{
                key:self.setup(key) is not None for key in ('software','inputs','index')}}

    def configure(self, candidate_index, cpu):
        cfg = self.config()
        if type(candidate_index) is not int or not 0 <= candidate_index < len(cfg['minimap2_candidates']):
            raise ValueError('unknown_executable_candidate')
        if type(cpu) is not int or not 1 <= cpu <= cfg['max_cpu']:
            raise ValueError('cpu_outside_caller_allocation')
        if self.job():
            raise ValueError('submitted_execution_configuration_is_immutable')
        executable = str(Path(cfg['minimap2_candidates'][candidate_index]).resolve(strict=True))
        directory = self.path/'execution'; directory.mkdir(exist_ok=True)
        result = run_local_job([executable,'--version'],cwd=directory,policy=LocalJobPolicy.from_config(cfg['job_limits']))
        if result.returncode != 0:
            raise ValueError('native_version_probe_failed')
        return self.save_setup('software',{'executable':executable,'executable_sha256':file_digest(executable),
            'cpu':cpu,'version':result.stdout_path.read_text().strip(),'resource_measurement':result.metadata})

    def stage(self):
        cfg=self.config(); directory=self.path/'execution'; directory.mkdir(exist_ok=True)
        policy=LocalJobPolicy.from_config(cfg['job_limits'])
        expected=cfg['input_files']
        for row in expected:
            src=Path(row['path']); target=directory/row['staged_name']
            if not target.exists() or file_digest(target)!=row['sha256']:
                if file_digest(src)!=row['sha256']: raise ValueError('fixed_input_bytes_changed')
                check_scratch_budget(directory,policy,additional_bytes=src.stat().st_size)
                shutil.copyfile(src,target)
        with (directory/'reads.fastq').open() as inp:
            index=count=0; chunk=None; total=0
            try:
                while True:
                    header=inp.readline()
                    if not header: break
                    seq,plus,qual=inp.readline(),inp.readline(),inp.readline()
                    if not header.startswith('@') or not plus.startswith('+') or len(seq.rstrip())!=len(qual.rstrip()):
                        raise ValueError('malformed_fixed_fastq')
                    if count % cfg['reads_per_block']==0:
                        if chunk: chunk.close()
                        chunk=(directory/f'reads-{index:05}.fastq').open('w'); index+=1
                    chunk.writelines((header,seq,plus,qual)); count+=1; total+=len(seq.rstrip())
            finally:
                if chunk: chunk.close()
        self.db.execute('DELETE FROM mapping_blocks WHERE state="pending"')
        for i in range(index):
            size=min(cfg['reads_per_block'],count-i*cfg['reads_per_block'])
            self.db.execute('INSERT OR IGNORE INTO mapping_blocks(block_index,read_count,state) VALUES(?,?,?)',(i,size,'pending'))
        self.db.commit(); check_scratch_budget(directory,policy)
        return self.save_setup('inputs',{'read_count':count,'base_count':total,'blocks':index,
            'reference_sha256':expected[0]['sha256'],'reads_sha256':expected[1]['sha256']})

    def build_index(self):
        software=self.setup('software'); inputs=self.setup('inputs')
        if software is None or inputs is None: raise ValueError('software_and_staged_inputs_required')
        directory=self.path/'execution'; cfg=self.config(); target=directory/'reference.mmi'
        command=[software['executable'],'-x',cfg['preset'],'-t',str(software['cpu']),'-d',str(target),str(directory/'reference.fasta')]
        result=run_local_job(command,cwd=directory,policy=LocalJobPolicy.from_config(cfg['job_limits']),
            stdout_path=directory/'index.stdout',stderr_path=directory/'index.stderr')
        if result.returncode!=0: raise ValueError('native_index_build_failed')
        return self.save_setup('index',{'path':str(target),'sha256':file_digest(target),
            'reference_sha256':inputs['reference_sha256'],'executable_sha256':software['executable_sha256'],
            'command':command,'resource_measurement':result.metadata})

    def submit(self):
        cfg=self.config(); sw=self.setup('software'); idx=self.setup('index')
        if sw is None or idx is None or self.setup('inputs') is None: raise ValueError('execution_setup_incomplete')
        if file_digest(sw['executable'])!=sw['executable_sha256'] or file_digest(idx['path'])!=idx['sha256']:
            raise ValueError('prepared_execution_dependency_changed')
        old=self.job()
        if old: return {'job_ref':old['job_ref'],'state':self.status(old['job_ref'])['state'],'new_submission':False}
        job_ref=token('job',cfg['workload_ref'])
        self.db.execute('INSERT INTO detached_jobs(job_ref,workload_ref,state,submitted_at) VALUES(?,?,?,?)',
            (job_ref,cfg['workload_ref'],'submitted',now())); self.db.commit()
        log=(self.path/'execution'/'supervisor.log').open('ab')
        try:
            subprocess.Popen([sys.executable,'-m','gene_annotation_episode.local_example.worker',str(self.path)],
                stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,
                cwd=str(Path(__file__).resolve().parents[2]),close_fds=True)
        except OSError as error:
            self.db.execute('UPDATE detached_jobs SET state="failed",finished_at=?,failure=? WHERE job_ref=?',
                (now(),canonical({'code':'supervisor_launch_failed','exception_type':type(error).__name__}),job_ref))
            self.db.commit(); raise
        finally: log.close()
        return {'job_ref':job_ref,'state':'submitted','new_submission':True}

    def status(self, job_ref):
        job=self.validate_job(job_ref)
        state=job['state']
        if state=='running':
            from ..execution_timing import _process_identity
            identity=_process_identity(job['pid'])
            if identity!={'pid':job['pid'],'start_ticks':job['process_start'],'boot_id':job['boot_id']}:
                state='lost'
        counts={r['state']:r['n'] for r in self.db.execute('SELECT state,count(*) n FROM mapping_blocks GROUP BY state')}
        completed=list(self.db.execute('SELECT block_index,read_count,elapsed_seconds FROM mapping_blocks WHERE state="completed" ORDER BY block_index'))
        read_total=self.setup('inputs')['read_count']
        done=sum(r['read_count'] for r in completed)
        start=datetime.fromisoformat(job['submitted_at'])
        end=datetime.fromisoformat(job['finished_at']) if job['finished_at'] else datetime.now(timezone.utc)
        durations=[r['elapsed_seconds'] for r in completed if r['elapsed_seconds'] is not None]
        mean=sum(durations)/len(durations) if durations else None
        return {'job_ref':job_ref,'workload_ref':job['workload_ref'],'state':state,
            'elapsed_seconds':(end-start).total_seconds(),'completed_blocks':len(completed),
            'total_blocks':sum(counts.values()),'completed_reads':done,'total_reads':read_total,
            'available_blocks':[r['block_index'] for r in completed],
            'mean_completed_block_seconds':mean,
            'estimated_remaining_seconds':mean*(sum(counts.values())-len(completed)) if mean is not None else None,
            'duration_sample_count':len(durations),'estimate_meaning':'native_completed_block_mean_remaining_blocks_excludes_current_block_age',
            'failure':json.loads(job['failure']) if job['failure'] else None}

    def handoff(self, job_ref):
        self.validate_job(job_ref)
        return {'job_ref':job_ref,'workload_ref':self.config()['workload_ref'],
            'backend':'local_minimap2_v1','workspace_ref':self.config()['workspace_ref'],
            'status_interface':'job.status_v1','progress_interface':'job.progress_v1','results_interface':'job.results_v1'}

    def check_handoff(self, handoff):
        expected=self.handoff(handoff.get('job_ref'))
        if set(handoff)!=set(expected) or handoff!=expected:
            raise ValueError('handoff_fields_do_not_resolve_to_declared_interfaces')
        # A NEW connection, using only the declared persistent backend binding.
        # The same receiver below is used by monitoring, not a launcher-local PID.
        receiver=JobStore(self.path)
        try:
            sample=receiver.receive(handoff)
        finally: receiver.close()
        receipt_ref=token('receipt',handoff)
        self.db.execute('INSERT OR REPLACE INTO handoff_receipts VALUES(?,?,?,?,?)',
            (receipt_ref,handoff['job_ref'],canonical(handoff),now(),canonical(sample)))
        self.db.commit()
        return {'receipt_ref':receipt_ref,'handoff':handoff,'sample':sample}

    def receive(self, handoff):
        if handoff!=self.handoff(handoff.get('job_ref')): raise ValueError('monitor_handoff_mismatch')
        return self.status(handoff['job_ref'])

    def sample(self, handoff, episode_id):
        body=self.receive(handoff); sampled=now()
        reference=token('sample',{'job':body['job_ref'],'time':sampled,'episode':episode_id})
        self.db.execute('INSERT INTO job_samples VALUES(?,?,?,?,?)',
            (reference,episode_id,body['job_ref'],sampled,canonical(body))); self.db.commit()
        return {'sample_ref':reference,**body}

    def extract(self, handoff, block_index, episode_id):
        self.receive(handoff)
        block=self.db.execute('SELECT * FROM mapping_blocks WHERE block_index=?',(block_index,)).fetchone()
        if block is None or block['state']!='completed': raise ValueError('requested_result_block_not_available')
        path=Path(block['result_path'])
        if file_digest(path)!=block['result_sha256']: raise ValueError('native_result_bytes_changed')
        target=path.with_suffix('.parsed.jsonl'); rows=primary=reverse=aligned_bases=0; queries=set()
        with path.open('rb') as inp,target.open('w') as out:
            for line in inp:
                row=parse_paf_line(line); out.write(canonical(row)+'\n'); rows+=1
                queries.add(row['query_name']); primary+=row['native_alignment_type']=='P'; reverse+=row['strand']=='-'
                aligned_bases+=row['query_interval'][1]-row['query_interval'][0]
        summary={'block_index':block_index,'input_reads':block['read_count'],'mapped_reads':len(queries),
            'reported_alignments':rows,'primary_alignments':primary,'reverse_alignments':reverse,
            'aligned_query_bases':aligned_bases,'native_result_sha256':block['result_sha256']}
        self.db.execute('INSERT OR REPLACE INTO result_deliveries VALUES(?,?,?,?,?)',
            (block_index,episode_id,canonical(summary),str(target),file_digest(target))); self.db.commit()
        return summary

    def delivered_summary(self):
        rows=[json.loads(r[0]) for r in self.db.execute('SELECT summary FROM result_deliveries ORDER BY block_index')]
        return {'extracted_blocks':[r['block_index'] for r in rows],
            **{key:sum(r[key] for r in rows) for key in ('input_reads','mapped_reads','reported_alignments',
                'primary_alignments','reverse_alignments','aligned_query_bases')}}
