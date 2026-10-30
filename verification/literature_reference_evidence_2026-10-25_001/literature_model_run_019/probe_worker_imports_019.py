"""Read-only -P import probe from the coordinator's actual repository cwd.

This does not commission an episode or invoke its factory/model transport. It
uses the selected runtime and PYTHONPATH construction in the durable launcher.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


owned = Path(__file__).resolve().parent
pin = owned / "pin_002"
repository = owned.parents[2]
assert Path.cwd() == repository, "probe_requires_actual_main_caller_cwd"
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("selected_source_caller", pin / "runner/run_literature_source_job_019.py")
caller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(caller)
caller.configure_pin(pin)
from gene_annotation_episode.independent_execution import implementation_sha256

expected = implementation_sha256()
environment = dict(os.environ)
roots = [str(pin), *(str(Path(entry or os.getcwd()).resolve()) for entry in sys.path)]
environment["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(roots))
probe = """
import hashlib, inspect, json, os, sys
from pathlib import Path
import method_loop.durable as durable
import method_loop.durable_worker as worker
import gene_annotation_episode.independent_execution as reconstruction
from gene_annotation_episode.state import Store
from method_loop.episode import Episode
pin=Path(sys.argv[1]).resolve()
paths={name:str(Path(inspect.getfile(value)).resolve()) for name,value in
       [('durable',durable),('durable_worker',worker),('factory',inspect.unwrap(reconstruction.open_commission)),
        ('Store',Store),('Episode',Episode)]}
assert all(Path(path).is_relative_to(pin) for path in paths.values()), paths
assert sys.flags.safe_path and sys.dont_write_bytecode
assert reconstruction.implementation_sha256()==sys.argv[2]
print(json.dumps({'cwd':str(Path.cwd()),'safe_path':sys.flags.safe_path,
    'dont_write_bytecode':sys.dont_write_bytecode,'selected_paths':paths,
    'factory_module':reconstruction.FACTORY_MODULE,'factory_name':reconstruction.FACTORY_NAME,
    'implementation_sha256':reconstruction.implementation_sha256(),
    'durable_sha256':hashlib.sha256(Path(durable.__file__).read_bytes()).hexdigest()}))
"""
completed = subprocess.run([sys.executable, "-P", "-c", probe, str(pin), expected],
    env=environment, capture_output=True, text=True)
if completed.returncode:
    caller.save_new(owned / ("WORKER_IMPORT_PROBE_FAILURE_" + str(os.getpid()) + ".json"),
        {"returncode": completed.returncode, "stderr": completed.stderr,
         "model_calls": 0, "episodes_commissioned": 0})
    raise RuntimeError(completed.stderr)
observed = json.loads(completed.stdout)
assert observed["cwd"] == str(repository)
assert not completed.stderr
source = (pin / "method_loop/durable.py").read_text()
assert 'subprocess.Popen([sys.executable, "-P", "-m", "method_loop.durable_worker"' in source
caller.verify_pin(pin)
receipt = {"status": "passed", "pin": str(pin),
    "pin_manifest_sha256": caller.digest(pin / "SOURCE_MANIFEST.json"),
    "root_caller_cwd": str(Path.cwd()), "changed_cwd": False,
    "probe_prefix": [sys.executable, "-P", "-c"],
    "durable_launcher_prefix_verified": [sys.executable, "-P", "-m", "method_loop.durable_worker"],
    "worker_environment_construction": "selected runtime followed by caller sys.path; inherited PYTHONDONTWRITEBYTECODE=1",
    "observed": observed, "model_calls": 0, "episodes_commissioned": 0,
    "limitation": "Actual safe-path worker/factory imports and implementation identity only; no commissioned episode or model execution"}
caller.save_new(owned / "WORKER_IMPORT_PROBE_002.json", receipt)
print(json.dumps(receipt, indent=2))
