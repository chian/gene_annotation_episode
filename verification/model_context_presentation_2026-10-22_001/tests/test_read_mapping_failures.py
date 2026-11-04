"""Synthetic native-process fixtures through the real Store and ToolRegistry.

The temporary executable below is explicitly not minimap2. It supplies only
controlled process/output conditions; these tests make no mapping accuracy or
biological truth claim and use no model, provider, or network connection.
"""

import asyncio
import json
import os
from pathlib import Path
import sys

import pytest

from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


BAD_SYNTHETIC_ROW = b"synthetic damaged PAF row\n"
FAILURE_STDERR = b"synthetic mapper execution failure; fixture exit 17\n"


def synthetic_executable(tmp_path, mode):
    """Create a real temporary process with a declared synthetic protocol."""
    path = tmp_path/"synthetic_mapper.py"
    path.write_text(f"#!{sys.executable}\n" + '''
"""Synthetic process fixture, not minimap2 or an alignment implementation."""
import json
import os
from pathlib import Path
import signal
import sys
import time

MODE = ''' + repr(mode) + '''
ROOT = Path(__file__).resolve().parent
args = sys.argv[1:]
if args == ["--version"]:
    print("synthetic-process-fixture-not-minimap2")
    raise SystemExit(0)
if args == ["-h"]:
    print("Synthetic version/help/index stubs; no mapping algorithm is implemented.")
    raise SystemExit(0)
if "-d" in args:
    Path(args[args.index("-d")+1]).write_bytes(b"synthetic index fixture\\n")
    sys.stderr.write("synthetic index stub completed\\n")
    raise SystemExit(0)

if MODE == "cancel":
    def terminated(signum, frame):
        (ROOT/"termination-observed.json").write_text(json.dumps({"pid": os.getpid(), "signal": signum}))
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM, terminated)
    (ROOT/"mapping-started.json").write_text(json.dumps({"pid": os.getpid()}))
    while True:
        time.sleep(1)

if MODE == "failure":
    sys.stderr.write("synthetic mapper execution failure; fixture exit 17\\n")
    raise SystemExit(17)

def fasta(path):
    # The production adapter writes exactly one sequence line per operand.
    lines = Path(path).read_text().splitlines()
    return [(lines[i][1:], lines[i+1]) for i in range(0, len(lines), 2)]

query_path = Path(args[-1])
queries = fasta(query_path)
reference, reference_sequence = fasta(query_path.parent/"references.fasta")[0]
for ordinal, (query, sequence) in enumerate(queries):
    if ordinal:
        sys.stdout.write("synthetic damaged PAF row\\n")
    length = len(sequence)
    fields = [query, str(length), "0", str(length), "+", reference,
        str(len(reference_sequence)), "0", str(length), str(length), str(length),
        "60", "tp:A:P", "cg:Z:"+str(length)+"M", "cs:Z:="+sequence]
    sys.stdout.write("\\t".join(fields)+"\\n")
    if MODE == "resource_after_row" and ordinal == 0:
        sys.stdout.flush()
        while True:
            time.sleep(.05)
sys.stderr.write("synthetic mapper emitted controlled PAF records\\n")
''')
    path.chmod(0o755)
    return path


def setup_synthetic_process_case(tmp_path, mode, *, job_limits=None):
    reads = tmp_path/"synthetic_reads.fastq"
    reads.write_text("@duplicate first\nACGT\n+\nIIII\n@duplicate second\nACGT\n+\n!!!!\n")
    store = Store(tmp_path/"state")
    store.create_problem(reads, molecule="dna")
    target, = store.targets()
    tools = ToolRegistry(store, minimap2_executable=synthetic_executable(tmp_path, mode), job_limits=job_limits)
    material = store.register_material(data=">synthetic_reference\nACGT\n", format="fasta", molecule="dna")
    parsed = store.parse_material(material["id"])
    member, = store.material_members(parsed["collection_ref"])["members"]
    reference = store.material_reference(member["id"])
    selected = tools.execute("library.select", {"library_ref": target["id"],
        "ordinal_ranges": [{"start": 0, "end": 2}]}, operation_key="synthetic-selection")
    assert selected["status"] == "completed", selected
    args = {"query_selection_ref": selected["result"]["selection"]["id"],
        "reference_refs": [reference["id"]], "preset": "map-ont"}
    return store, tools, args


def alignment_records(store):
    return [row for row in store.list("observation") if row["kind"] == "alignment"]


def test_malformed_independent_native_row_preserves_both_valid_siblings_and_raw_error(tmp_path):
    store, tools, args = setup_synthetic_process_case(tmp_path, "partial")
    with store:
        output = tools.execute("reads.map", args, operation_key="synthetic-partial-rows")
        assert output["status"] == "partial", output
        result = output["result"]
        assert result["native_returncode"] == 0
        assert result["reported_placement_count"] == 2
        assert result["projection_error_count"] == 1
        assert output["feedback"]["code"] == "native_mapping_rows_partially_projected"
        assert output["feedback"]["error_source_ref"] == result["error_source_ref"]
        observations = alignment_records(store)
        assert len(observations) == 2
        assert {row["native_minimap2"]["line_number"] for row in observations} == {1, 3}
        assert len({row["subject_refs"][0] for row in observations}) == 2
        assert all(row["source_ref"] == result["source_ref"] for row in observations)
        assert {row["id"] for row in observations} <= set(output["record_refs"])
        source = store.get(result["source_ref"])
        assert source["version"] == "synthetic-process-fixture-not-minimap2"
        raw = store.get_artifact(source["stdout_ref"])
        assert raw.splitlines(keepends=True)[1] == BAD_SYNTHETIC_ROW
        error_source = store.get(result["error_source_ref"])
        assert error_source["parent_source_refs"] == [source["id"]]
        error, = [json.loads(line) for line in store.get_artifact(error_source["artifact_ref"]).splitlines()]
        assert error["code"] == "invalid_native_paf_row"
        assert error["line_number"] == 2
        assert raw[error["row_start"]:error["row_end"]] == BAD_SYNTHETIC_ROW
        assert error_source["artifact_ref"] in source["auxiliary_artifact_refs"]
        for observation in observations:
            locator = observation["native_minimap2"]
            assert raw[locator["row_start"]:locator["row_end"]].split(b"\t")[0].decode() == observation["subject_refs"][0]
        assert not list(store.path.glob(".native-read-mapping-*"))


def test_native_nonzero_exit_without_placements_retains_source_and_exact_streams(tmp_path):
    store, tools, args = setup_synthetic_process_case(tmp_path, "failure")
    with store:
        output = tools.execute("reads.map", args, operation_key="synthetic-native-failure")
        assert output["status"] == "failed", output
        result = output["result"]
        assert result["native_returncode"] == 17
        assert result["native_phase"] == "native_mapping"
        assert result["reported_placement_count"] == 0
        assert output["feedback"] == {"category": "execution", "code": "native_mapping_error",
            "native_phase": "native_mapping", "native_returncode": 17,
            "source_ref": result["source_ref"]}
        source = store.get(result["source_ref"])
        assert source["id"] in output["record_refs"]
        assert source["provider"] == "minimap2.mapping"
        assert source["version"] == "synthetic-process-fixture-not-minimap2"
        assert store.get_artifact(source["stdout_ref"]) == b""
        assert store.get_artifact(source["stderr_ref"]) == FAILURE_STDERR
        provenance = json.loads(store.get_artifact(source["artifact_ref"]))
        assert provenance["returncode"] == 17
        assert provenance["artifacts"]["mappings.paf"] == source["stdout_ref"]
        assert provenance["artifacts"]["mapping.stderr"] == source["stderr_ref"]
        assert not alignment_records(store)
        assert not list(store.path.glob(".native-read-mapping-*"))


def test_resource_limited_native_mapping_publishes_valid_row_and_specific_failure(tmp_path):
    policy = {"memory_bytes": 256*1024**2, "scratch_bytes": 2*1024**2, "wall_seconds": 1}
    store, tools, args = setup_synthetic_process_case(tmp_path, "resource_after_row", job_limits=policy)
    with store:
        output = tools.execute("reads.map", args, operation_key="synthetic-resource-after-row")
        assert output["status"] == "partial", output
        assert output["feedback"]["category"] == "execution"
        assert output["feedback"]["code"] == "local_job_resource_limit"
        assert output["feedback"]["resource"] == "wall_seconds"
        assert output["feedback"]["policy"] == policy
        result = output["result"]
        assert result["reported_placement_count"] == 1
        assert result["resource_failure"]["code"] == "local_job_resource_limit"
        assert result["search_result_observation_ref"] is None
        assert result["result_meaning"] == "partial_native_reported_placements_from_resource_limited_search_not_biological_absence"
        observation, = alignment_records(store)
        source = store.get(result["source_ref"])
        assert observation["source_ref"] == source["id"]
        assert observation["id"] in output["record_refs"]
        raw = store.get_artifact(source["stdout_ref"])
        assert raw.split(b"\t", 1)[0].decode() == observation["subject_refs"][0]
        assert not [row for row in store.list("observation") if row["kind"] == "source_content"]
        provenance = json.loads(store.get_artifact(source["artifact_ref"]))
        assert provenance["resource_failure"] == result["resource_failure"]
        assert not store.current_annotations()
        assert not list(store.path.glob(".native-read-mapping-*"))


def test_cancelled_native_process_is_terminated_waited_and_cleaned_without_completed_record(tmp_path):
    store, tools, args = setup_synthetic_process_case(tmp_path, "cancel")
    with store:
        before_sources = store.count("source")
        before_observations = store.count("observation")

        async def exercise_cancellation():
            task = asyncio.create_task(tools.execute_async("reads.map", args,
                operation_key="synthetic-cancelled-mapping"))
            try:
                # This is a test watchdog, not a workflow timeout or stopping
                # rule. Cancel only after the actual mapping process is ready.
                async def await_ready():
                    while not (tmp_path/"mapping-started.json").exists():
                        if task.done():
                            pytest.fail(f"mapping ended before cancellation fixture was ready: {task.result()}")
                        await asyncio.sleep(0.01)
                await asyncio.wait_for(await_ready(), timeout=5)
                pid = json.loads((tmp_path/"mapping-started.json").read_text())["pid"]
                assert list(store.path.glob(".native-read-mapping-*"))
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await asyncio.wait_for(task, timeout=5)
                return pid
            finally:
                if not task.done():
                    task.cancel()
                    try:
                        await asyncio.wait_for(task, timeout=5)
                    except asyncio.CancelledError:
                        pass

        pid = asyncio.run(exercise_cancellation())
        # The resource runner kills the whole systemd cgroup and waits. SIGKILL
        # intentionally cannot run the synthetic process's SIGTERM handler;
        # the contract is a reaped process and uncommitted scientific work.
        # kill(0) cannot succeed for a process the runtime has fully reaped.
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
        assert not list(store.path.glob(".native-read-mapping-*"))
        assert store.db.execute("SELECT 1 FROM tool_operations WHERE operation_key=?",
            ("synthetic-cancelled-mapping",)).fetchone() is None
        assert store.count("source") == before_sources
        assert store.count("observation") == before_observations
