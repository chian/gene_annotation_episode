"""One explicit observation/fetch of the existing test RID; no polling loop."""
from pathlib import Path
from dataclasses import asdict
from datetime import datetime, timezone
import argparse
import json

from gene_annotation_episode.acquisition import PublicClients
from gene_annotation_episode.blast_search import status
from gene_annotation_episode.blast_grading_inputs import parse_blast_json

HERE = Path(__file__).resolve().parent
out = HERE / "live_api"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("action", choices=("status", "fetch"))
action = parser.parse_args().action
job = json.loads((out / "job.json").read_text())
client = PublicClients(ncbi_email="chia@anl.gov",
    access_dir=Path.home() / ".cache/gene_annotation_episode/provider_access")
delay = client.blast_delay(action, job["rid"])
if delay:
    print(json.dumps({"rid": job["rid"], "action": action, "spacing_seconds": delay}))
    raise SystemExit(0)
snapshot = client.blast(action, rid=job["rid"])
prefix = action + "_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
(out / (prefix + ".body")).write_bytes(snapshot.content)
metadata = asdict(snapshot)
metadata.pop("content")
(out / (prefix + ".metadata.json")).write_text(json.dumps(metadata, indent=2) + "\n")
if action == "status":
    summary = status(snapshot.content)
else:
    try:
        normalized = parse_blast_json(snapshot.content, mode="database", resource="api",
            request={"program": "blastp", "query_length": job["query_length"]})
    except ValueError as error:
        try:
            summary = {**status(snapshot.content), "native_result_available": False}
        except ValueError:
            summary = {"native_result_available": False, "parser_error": str(error)}
    else:
        # Timestamped receipt remains immutable; the convenience result path is
        # published only after native database-result parsing succeeds.
        (out / "result.body").write_bytes(snapshot.content)
        (out / "result.metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        summary = {"native_result_available": True, "bytes": len(snapshot.content),
                   "native_hit_count": normalized["search"]["reported_hit_count"]}
print(json.dumps({"rid": job["rid"], "action": action, **summary}))
