"""One operator-selected live request; never selects or repeats another action."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.rfam_batch_transport import RfamBatchHTTP
from gene_annotation_episode.rfam_discovery import validate_result_url


def durable_write(path, content):
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


job, action = Path(sys.argv[1]), sys.argv[2]
manifest = json.loads((job / "input-manifest.json").read_bytes())
client = RfamBatchHTTP(timeout_seconds=45)
try:
    if action == "submit":
        if (job / "original_handle.json").exists():
            raise RuntimeError("an original handle already exists; no second POST")
        if job.name == "single":
            snapshot = client.submit(manifest["records"][0]["submitted_sequence"])
        else:
            snapshot = client.submit_file((job / "input.seq").read_bytes(), filename=manifest["filename"])
    else:
        handle = json.loads((job / "original_handle.json").read_bytes())
        snapshot = (client.status(handle["job_id"]) if action == "status" else
                    client.result(handle["job_id"], representation=action.removeprefix("fetch-")))
except AcquisitionError as error:
    failure = {"code": error.code, "phase": error.phase,
               "submission_outcome": error.submission_outcome, "job_ref": error.job_ref,
               "diagnostic": error.diagnostic}
    durable_write(Path("failure.json"), (json.dumps(failure, indent=2) + "\n").encode())
    print(json.dumps({"action": action, "failure": failure}))
    raise SystemExit(2)

# Retain the original body before any identity interpretation or display.
durable_write(Path("response.body"), snapshot.content)
native = asdict(snapshot)
native.pop("content")
native["content_sha256"] = snapshot.sha256
durable_write(Path("snapshot.json"), (json.dumps(native, indent=2) + "\n").encode())
if action == "submit":
    result = json.loads(snapshot.content)
    handle = {"job_id": result["jobId"], "result_url": result["resultURL"]}
    validate_result_url(handle["result_url"], handle["job_id"])
    durable_write(job / "original_handle.json", (json.dumps(handle, indent=2) + "\n").encode())
    print(json.dumps({"original_handle_saved": handle, "job": job.name}))
print(json.dumps({"action": action, "job": job.name,
                  "http_status": snapshot.transport["status"],
                  "body_complete": snapshot.transport["body_complete"],
                  "bytes": len(snapshot.content), "sha256": snapshot.sha256,
                  "elapsed_seconds": snapshot.transport["elapsed_seconds"]}))
