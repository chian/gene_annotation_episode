"""Exactly one authorized format-acquisition GET for the original 243 job.

This is an operator acquisition, not a live composed Workflow execution.
"""
import base64
from dataclasses import asdict
import json
from pathlib import Path

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.rfam_batch_transport import RfamBatchHTTP


JOB = "infernal_cmscan-R20261026-041949-0621-14761545-p2m"
DIRECTORY = Path.cwd()


def write(name, value):
    with (DIRECTORY / name).open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


write("acquisition-intent.json", {
    "job_id": JOB, "operation": "RfamBatchHTTP.result", "representation": "out",
    "timeout_seconds": 90, "allowed_http_request_count": 1,
    "qualification": "Independent operator format acquisition of the original live job; no new Workflow, POST, job, retry or polling",
})
try:
    snapshot = RfamBatchHTTP(timeout_seconds=90).result(JOB, representation="out")
except AcquisitionError as error:
    failure = {"code": error.code, "phase": error.phase,
        "submission_outcome": error.submission_outcome, "job_ref": error.job_ref,
        "diagnostic": error.diagnostic}
    write("failure.json", failure)
    print(json.dumps(failure))
    raise SystemExit(2)

with (DIRECTORY / "response.body").open("xb") as stream:
    stream.write(snapshot.content)
record = asdict(snapshot)
record.pop("content")
record.update(content_base64=base64.b64encode(snapshot.content).decode("ascii"),
    content_sha256=snapshot.sha256)
write("snapshot.json", record)
write("http-request.json", snapshot.transport["request"])
write("http-transport.json", snapshot.transport)
print(json.dumps({"status": snapshot.transport["status"], "body_complete": snapshot.transport["body_complete"],
    "http_request_count": snapshot.transport["http_request_count"], "bytes": len(snapshot.content),
    "sha256": snapshot.sha256, "qualification": "Original-job format acquisition only"}))
