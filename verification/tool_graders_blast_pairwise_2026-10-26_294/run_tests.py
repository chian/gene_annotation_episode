"""Run explicitly supplied checks under the existing local resource lifecycle."""
import json
from pathlib import Path
import sys
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
ROOT=Path(__file__).resolve().parents[2]
def main():
    label,*selected=sys.argv[1:]
    directory=Path(__file__).resolve().parent/label
    directory.mkdir()
    (directory/'temporary').mkdir()
    command=[str(ROOT/'.venv/bin/python'),'-m','pytest','-q',*selected,'--basetemp',str(directory/'temporary/pytest')]
    policy=LocalJobPolicy(20*1024**3,4*1024**3,None)
    result=run_local_job(command,cwd=directory,policy=policy,stdout_path=directory/'stdout.txt',stderr_path=directory/'stderr.txt',
        env={'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(directory/'temporary'),'XDG_CACHE_HOME':str(directory/'cache')})
    (directory/'receipt.json').write_text(json.dumps({'command':command,'returncode':result.returncode,'metadata':result.metadata},indent=2)+'\n')
    print(json.dumps({'returncode':result.returncode,'receipt':str(directory/'receipt.json')}))
    print((directory/'stdout.txt').read_text())
    print((directory/'stderr.txt').read_text())
    return result.returncode
if __name__=='__main__':raise SystemExit(main())
