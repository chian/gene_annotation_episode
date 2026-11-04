"""Bounded native workers and ordinary action accounting; no model/provider calls."""
import asyncio
import json

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


def test_real_pairwise_worker_runs_outside_host_and_sql_transaction(tmp_path, monkeypatch):
    from gene_annotation_episode import tools as module
    from gene_annotation_episode import sequence_ops
    real = module.run_local_job_async
    selected = []
    with Store(tmp_path / "state") as store:
        subject = store.create_problem(raw_sequence="ACGTTGCA", molecule="dna")["subject_refs"][0]
        async def observed(command, **kwargs):
            assert not store.db.in_transaction
            selected.append(command)
            return await real(command, **kwargs)
        def forbidden(*args, **kwargs):
            raise AssertionError("native alignment must never execute in workflow host")
        monkeypatch.setattr(module, "run_local_job_async", observed)
        monkeypatch.setattr(sequence_ops, "align_pair", forbidden)
        registry = ToolRegistry(store)
        result = registry.execute("sequence.align", {"query_ref": subject, "reference_ref": subject,
            "molecule": "dna", "mode": "global"})
        assert result["status"] == "completed", result
        assert len(selected) == 1 and selected[0][1:3] == ["-m", "gene_annotation_episode.sequence_worker"]
        body = json.loads(store.get_artifact(store.get(result["result"]["source_ref"])["artifact_ref"]))
        assert body["aligned_query"] == body["aligned_reference"] == "ACGTTGCA"
        assert body["native_score"] == 16 and body["identity_fraction"] == 1
        assert 'local_job' not in body
        assert result['result']['local_job']['policy'] == registry.local_job_policy.to_dict()
        assert store.count("observation") == 1
        assert list(store.path.glob(".native-sequence-*")) == []


def test_resource_failure_reaches_next_episode_decision_without_yield_observation(tmp_path, monkeypatch):
    from gene_annotation_episode import tools as module
    from gene_annotation_episode import sequence_ops
    with Store(tmp_path / "state") as store:
        subject = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"][0]
        async def bounded_failure(*args, **kwargs):
            assert not store.db.in_transaction
            raise AcquisitionError("local_job_resource_limit", phase="local_execution", operational={
                "resource": "memory_bytes", "limit": 2147483648,
                "evidence": {"kind": "explicitly_synthetic_resource_feedback"}})
        def forbidden(*args, **kwargs):
            raise AssertionError("resource failure cannot select an in-process fallback")
        monkeypatch.setattr(module, "run_local_job_async", bounded_failure)
        monkeypatch.setattr(sequence_ops, "align_pair", forbidden)
        tools = ToolRegistry(store)
        def revise(context):
            assert context["feedback"]["category"] == "execution"
            assert context["feedback"]["code"] == "local_job_resource_limit"
            assert context["feedback"]["resource"] == "memory_bytes"
            assert context["controller"]["scores"] == []
            assert store.count("observation") == 0
            return {"selection": {"kind": "tool", "tool": "sequence.inspect",
                "arguments": {"subject_ref": subject}}, "report_update": {}}
        provider = ScriptedProvider([{"selection": {"kind": "tool", "tool": "sequence.align",
            "arguments": {"query_ref": subject, "reference_ref": subject, "molecule": "dna", "mode": "global"}},
            "report_update": {}}, revise])
        summary = asyncio.run(run_workflow(store, tools, provider=provider, run_dir=tmp_path / "run",
            controller_factory=lambda path, initial: FixtureController(str(path), initial, 1)))
        assert summary["completed_actions"] == 1
        assert store.count("observation") == 1
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 1
        failed = json.loads(store.db.execute("SELECT result FROM tool_operations WHERE name='sequence.align'").fetchone()[0])
        assert failed["status"] == "failed" and failed["record_refs"] == []
        assert list(store.path.glob(".native-sequence-*")) == []


def test_reads_align_keeps_valid_siblings_as_one_action_on_resource_failure(tmp_path, monkeypatch):
    from gene_annotation_episode import tools as module
    fastq = tmp_path / "reads.fastq"
    fastq.write_text("@a\nACGTACGT\n+\nIIIIIIII\n@b\nTTTTTTTT\n+\nIIIIIIII\n@c\nACGTTCGT\n+\nIIIIIIII\n")
    with Store(tmp_path / "state") as store:
        library = store.create_problem(fastq, molecule="dna")["subject_refs"][0]
        tools = ToolRegistry(store)
        reads = tools.execute("library.members", {"library_ref": library})["result"]["members"]
        real = module.run_local_job_async
        count = 0
        async def one_failure(command, **kwargs):
            nonlocal count
            count += 1
            assert not store.db.in_transaction
            if count == 2:
                raise AcquisitionError("local_job_resource_limit", phase="local_execution", operational={
                    "resource": "memory_bytes", "limit": 2147483648})
            return await real(command, **kwargs)
        monkeypatch.setattr(module, "run_local_job_async", one_failure)
        result = tools.execute("reads.align", {"subject_refs": [row["id"] for row in reads],
            "reference_ref": reads[0]["id"], "molecule": "dna", "mode": "global"})
        assert result["status"] == "partial", result
        assert result["result"]["completed_count"] == 2 and count == 3
        assert result["result"]["errors"] == [{"row_index": 1, "subject_ref": reads[1]["id"],
            "code": "local_job_resource_limit", "category": "execution", "phase": "local_execution",
            "resource": "memory_bytes", "limit": 2147483648}]
        assert result["published_batch"]["published_rows_total"] == 2
        assert result["published_batch"]["failure_rows_total"] == 1
        assert store.count("observation") == 2
        assert store.db.execute("SELECT count(*) FROM tool_operations WHERE name='reads.align'").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM tool_operations WHERE name='sequence.align'").fetchone()[0] == 0
        assert list(store.path.glob(".native-sequence-*")) == []
        async def all_fail(*args, **kwargs):
            raise AcquisitionError("local_job_resource_limit", phase="local_execution", operational={
                "resource": "memory_bytes", "limit": 2147483648})
        monkeypatch.setattr(module, "run_local_job_async", all_fail)
        failed = tools.execute("reads.align", {"subject_refs": [row["id"] for row in reads],
            "reference_ref": reads[0]["id"], "molecule": "dna", "mode": "global"})
        assert failed["status"] == "failed" and failed["feedback"]["category"] == "execution"
        assert failed["published_batch"]["published_rows_total"] == 0
        assert failed["published_batch"]["failure_rows_total"] == 3
        assert failed["record_refs"] == [] and store.count("observation") == 2
        for reference in result["record_refs"]:
            assert store.get(reference)["id"] == reference


def test_memory_allocation_failure_preserves_basic_reason_without_claiming_cgroup_oom(tmp_path, monkeypatch):
    from gene_annotation_episode import tools as module
    from gene_annotation_episode.local_jobs import LocalJobResult
    async def memory_error(command, **kwargs):
        from pathlib import Path
        Path(command[-1]).write_text(json.dumps({"code": "native_memory_allocation_failed", "exception_type": "MemoryError"}))
        return LocalJobResult(3, kwargs["stdout_path"], kwargs["stderr_path"], {"policy": kwargs["policy"].to_dict()})
    monkeypatch.setattr(module, "run_local_job_async", memory_error)
    with Store(tmp_path / "state") as store:
        subject = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"][0]
        result = ToolRegistry(store).execute("sequence.align", {"query_ref": subject, "reference_ref": subject,
            "molecule": "dna", "mode": "global"})
        assert result["status"] == "failed" and result["feedback"]["category"] == "execution"
        assert result["feedback"]["worker_failure"] == "native_memory_allocation_failed"
        assert "resource" not in result["feedback"] and "evidence" not in result["feedback"]
        assert store.count("observation") == 0
