"""Owned, resource-bounded verification runner; no wall-time limit."""
import datetime, json, os, pathlib, resource, subprocess, sys, time
own = pathlib.Path(__file__).resolve().parent
label, *command = sys.argv[1:]
output = own / label
output.mkdir(exist_ok=False)
env = os.environ.copy()
env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(own / "candidate"), TMPDIR=str(output))
def limits():
    resource.setrlimit(resource.RLIMIT_AS, (20 * 1024**3, 20 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024**3, 4 * 1024**3))
record = dict(argv=command, cwd=str(own / "candidate"), started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              environment={key:env[key] for key in ("PYTHONDONTWRITEBYTECODE", "PYTHONPATH", "TMPDIR")},
              memory_limit_bytes=20 * 1024**3, single_file_limit_bytes=4 * 1024**3, wall_time_limit=None)
(output / "command.json").write_text(json.dumps(record, indent=2)+"\n")
start=time.perf_counter()
with (output / "output.log").open("w") as log:
    result=subprocess.run(command, cwd=own / "candidate", env=env, stdout=log, stderr=subprocess.STDOUT, preexec_fn=limits)
record.update(exit_code=result.returncode, seconds=time.perf_counter()-start, finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
(output / "receipt.json").write_text(json.dumps(record, indent=2)+"\n")
print(json.dumps(record,indent=2),flush=True)
sys.exit(result.returncode)
