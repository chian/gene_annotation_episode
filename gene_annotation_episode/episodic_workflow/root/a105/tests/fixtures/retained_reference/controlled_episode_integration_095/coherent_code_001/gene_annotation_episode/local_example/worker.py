"""Detached deterministic execution of one fixed mapping workload; no agent loop."""
import fcntl
from pathlib import Path
import sys
import time

from .service import JobStore, canonical, now
from ..execution_timing import _process_identity
from ..local_jobs import LocalJobPolicy, run_local_job
from ..read_mapping import file_digest


def run(directory):
    store=JobStore(directory)
    lock=(store.path/'execution'/'supervisor.lock').open('a')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        store.close(); lock.close(); return
    job=store.job()
    if job is None or job['state'] in ('succeeded','failed'):
        store.close(); lock.close(); return
    identity=_process_identity(); cfg=store.config(); software=store.setup('software'); index=store.setup('index')
    store.db.execute('UPDATE detached_jobs SET state="running",pid=?,process_start=?,boot_id=?,started_at=coalesce(started_at,?)',
        (identity['pid'],identity['start_ticks'],identity['boot_id'],now())); store.db.commit()
    directory=store.path/'execution'
    try:
        for block in list(store.db.execute('SELECT * FROM mapping_blocks ORDER BY block_index')):
            if block['state']=='completed': continue
            i=block['block_index']; target=directory/f'mappings-{i:05}.paf'
            command=[software['executable'],'-x',cfg['preset'],'-c','--cs=long','-t',str(software['cpu']),
                index['path'],str(directory/f'reads-{i:05}.fastq')]
            store.db.execute('UPDATE mapping_blocks SET state="running",started_at=? WHERE block_index=?',(now(),i));store.db.commit()
            start=time.monotonic()
            result=run_local_job(command,cwd=directory,policy=LocalJobPolicy.from_config(cfg['job_limits']),
                stdout_path=target,stderr_path=directory/f'mapping-{i:05}.stderr')
            if result.returncode!=0: raise RuntimeError(f'native_mapping_exit_{result.returncode}')
            store.db.execute('UPDATE mapping_blocks SET state="completed",finished_at=?,elapsed_seconds=?,result_path=?,result_sha256=?,native_metadata=? WHERE block_index=?',
                (now(),time.monotonic()-start,str(target),file_digest(target),canonical({'command':command,**result.metadata}),i));store.db.commit()
        store.db.execute('UPDATE detached_jobs SET state="succeeded",finished_at=?',(now(),));store.db.commit()
    except BaseException as error:
        detail={'code':getattr(error,'code','native_execution_failed'),'exception_type':type(error).__name__,
            'detail':str(error),'operational':getattr(error,'operational',None)}
        store.db.execute('UPDATE detached_jobs SET state="failed",finished_at=?,failure=?',(now(),canonical(detail)));store.db.commit()
        raise
    finally:
        store.close(); lock.close()


if __name__=='__main__':
    run(Path(sys.argv[1]))
