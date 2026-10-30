"""Reproduce service/publication examples without a network or model call."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.acquisition import SourceSnapshot
from gene_annotation_episode.api_bvbrc_minhash import BVBRCMinhashService, LAUNCH_OPERATIONS
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import source_tool_gradings
from gene_annotation_episode.tools import ToolRegistry


DIRECTORY = Path(__file__).resolve().parent
ENDPOINT = "https://minhash.example.invalid/selected-rpc"


class SuppliedResponse:
    def __init__(self, rows):
        self.rows, self.calls = deepcopy(rows), []

    def rpc(self, request):
        self.calls.append(deepcopy(request))
        body = json.dumps(request, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), allow_nan=False).encode()
        content = json.dumps({"version": "1.1", "id": request["id"],
            "result": [self.rows]}, allow_nan=False).encode()
        return SourceSnapshot("bvbrc_analysis", ENDPOINT, {"kind": "rpc", "rpc": request},
            "2026-10-24T12:00:00+00:00", content, "application/json", {
                "status": 200, "body_complete": True,
                "representation": "synthetic_supplied_response_no_http",
                "request": {"method": "POST", "url": ENDPOINT,
                    "body_bytes": len(body), "body_sha256": hashlib.sha256(body).hexdigest()}})


def example(name, mode, rows, provenance):
    with TemporaryDirectory(prefix="bvbrc-minhash-publication-") as directory:
        with Store(Path(directory) / "state") as store:
            store.create_problem(raw_sequence="MACDEFGH", molecule="protein")
            client = SuppliedResponse(rows)
            tools = ToolRegistry(store, clients=client)
            service = BVBRCMinhashService(tools, {
                "kind": "api", "service": "bvbrc_minhash", "endpoint": ENDPOINT}, client=client)
            request = {"mode": mode, "query": "511145.12" if mode == "genome"
                else "/synthetic-owner/workspace/input.fa", "max_pvalue": .2,
                "max_distance": 1, "max_hits": 1, "include_reference": 1,
                "include_representative": 0, "bacterial": 1, "viral": 0}
            scope = store.validate_scope(None)
            prepared = service.prepare(LAUNCH_OPERATIONS[mode], request, {},
                scope=scope, previous_events=[])
            snapshot = service.invoke(prepared)
            event = service.decode(prepared, snapshot)
            result = service.publish(request, {}, snapshot, scope, name)
            grading, = source_tool_gradings(store, result["result"]["source_ref"])
            assert service.publish(request, {}, snapshot, scope, name) == result
            assert len(client.calls) == 1
            assert store.count("annotation") == store.count("observation") == 0
            assert all(row["recomputed_distance"] is None and row["recomputed_pvalue"] is None
                for row in grading["components"]["rows"])
            return {"name": name, "fixture_provenance": provenance, "prepared": prepared,
                "raw_response": snapshot.content.decode(), "event": event,
                "publication": result, "grading": grading,
                "supplied_response_call_count": len(client.calls), "live_http_calls": 0}


def main():
    source = ROOT / "verification/tool_graders_bvbrc_native_rpc_contract_2026-10-24/sources/Mash/test/ref/genomes.dist"
    line = source.read_text().splitlines()[0]
    _, _, distance, pvalue, counts = line.split()
    upstream = ["synthetic-reference", distance, pvalue, counts]
    native_provenance = {"kind": "upstream_Mash_values_in_synthetic_BVBRC_envelope",
        "path": str(source.relative_to(ROOT)), "row": line,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "genome_id": "invented fixture identity; not a retained BV-BRC result"}
    examples = [example("upstream-values-" + mode, mode, [upstream], native_provenance)
        for mode in ("genome", "fasta")]
    synthetic = {"kind": "synthetic_native_format_fixture"}
    examples.extend([
        example("duplicates-and-partial", "genome", [upstream, deepcopy(upstream),
            ["synthetic-other", "bad-distance", "0.1", "2/3"], None], synthetic),
        example("zero-denominator", "fasta", [["synthetic-reference", 0, 1, "0/0"]], synthetic),
        example("empty-array", "genome", [], synthetic),
        example("invalid-row", "fasta", [None], synthetic),
    ])
    assert examples[0]["grading"]["components"]["rows"][0]["shared_hash_fraction"] == .041
    result = {"schema": "bvbrc_minhash_service_offline_examples_v1", "examples": examples,
        "verification_limits": ["No live BV-BRC call or credentials used",
            "No native Minhash/Mash algorithm executed",
            "No model-directed scientific investigation",
            "Selected tool/resource-child/typed receiver integration belongs to root-owned C4d",
            "Actual k/length/alphabet metadata acquisition and binding remain unfinished"]}
    (DIRECTORY / "FILLED_EXAMPLES.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"examples": len(examples), "shared_hash_fraction": .041,
        "reported_distance": float(distance), "reported_pvalue": float(pvalue),
        "recomputed_distance": None, "recomputed_pvalue": None,
        "live_http_calls": 0, "annotation_observations_created": 0}, indent=2))


if __name__ == "__main__":
    main()
