"""Use the existing bounded runner for one small schema/document check."""
from pathlib import Path
import json
import sys
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

root=Path(__file__).resolve().parent
cwd=root/('document_validation_job_'+sys.argv[1] if len(sys.argv)>1 else 'document_validation_job')
cwd.mkdir(exist_ok=True)
result=run_local_job([sys.executable,'-B',str(root/'validate_record_examples.py')],cwd=cwd,
    policy=LocalJobPolicy(memory_bytes=21474836480,scratch_bytes=4294967296,wall_seconds=None))
(root/'DOCUMENT_VALIDATION_JOB.json').write_text(json.dumps({'record_type':'document_validation_execution_only','returncode':result.returncode,'stdout_path':str(result.stdout_path),'stderr_path':str(result.stderr_path),'metadata':result.metadata},indent=2)+"\n")
if result.returncode==0:
    (root/'DOCUMENT_VALIDATION.json').write_bytes((cwd/'validation.json').read_bytes())
print(json.dumps({'returncode':result.returncode,'stdout':str(result.stdout_path),'stderr':str(result.stderr_path)}))
raise SystemExit(result.returncode)
