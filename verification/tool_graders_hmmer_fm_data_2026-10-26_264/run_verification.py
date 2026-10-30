"""Run only this workload through the existing bounded local job adapter."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

HERE = Path(__file__).resolve().parent


def main():
    attempt = sys.argv[1]
    directory = HERE / attempt
    directory.mkdir()
    policy = LocalJobPolicy(memory_bytes=20*1024**3,scratch_bytes=4*1024**3,wall_seconds=None)
    command = [sys.executable,"-m","pytest","-q","-p","no:cacheprovider",
               str(ROOT/"tests/test_hmmer_fm_data.py"),str(ROOT/"tests/test_hmmer_fm_calculations.py")]
    if len(sys.argv)==3 and sys.argv[2]=="examples":
        command = [sys.executable,str(HERE/"generate_examples.py")]
    paths = [ROOT/"gene_annotation_episode/hmmer_fm_data.py",ROOT/"gene_annotation_episode/hmmer_fm_calculations.py",
             ROOT/"tests/test_hmmer_fm_data.py",ROOT/"tests/test_hmmer_fm_calculations.py"]
    intent = {"argv":command,"cwd":str(directory),"policy":asdict(policy),
              "source_sha256":{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}}
    (directory/"intent.json").write_text(json.dumps(intent,indent=2)+"\n")
    result = run_local_job(command,cwd=directory,policy=policy,
        env={"PYTHONPATH":str(ROOT),"PYTHONDONTWRITEBYTECODE":"1","PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1",
             "XDG_CACHE_HOME":str(directory/"cache"),"TMPDIR":str(directory)})
    receipt = {**intent,"returncode":result.returncode,"metadata":result.metadata,
               "stdout_path":str(result.stdout_path),"stderr_path":str(result.stderr_path)}
    (directory/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"attempt":attempt,"returncode":result.returncode,"receipt":str(directory/"receipt.json")}))
    print(result.stdout_path.read_text())


if __name__=="__main__":
    main()
