"""Original substantive ordinary-tool methods: tool_native_sequence."""
from __future__ import annotations
import json
import os
import sys
import tempfile
from pathlib import Path
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.local_jobs import run_local_job_async
from gene_annotation_episode.local_jobs import run_cancellable_native
from gene_annotation_episode.materials import artifact_file
from gene_annotation_episode.episodic_workflow.root.tool_values import SequenceWork

class OriginalToolNativeSequence:
    async def _sequence_worker_async(self, operation: str, arguments: dict, *, directory: Path,
                                     owned_directory: Path | None = None) -> SequenceWork:
        """Native work has no Store handle and no in-process fallback.

        This method is the explicit native-worker seam for synthetic publisher
        tests; production always uses the common bounded local-job runner.
        """
        if self.store.db.in_transaction:
            raise ContractError("native_sequence_work_requires_no_active_store_transaction")
        if owned_directory is not None:
            from gene_annotation_episode.molecular_measurement_tools import run_owned_molecular_worker
            selected_ports = {}
            if operation in {"protein_disorder", "arsenic_speciation", "protease_kinetics_native", "protease_kinetics_saved"}:
                from gene_annotation_episode.episodic_workflow.root.library import molecular_worker_ports
                selected_ports["worker_ports"] = molecular_worker_ports
            output, metadata = await run_cancellable_native(run_owned_molecular_worker,
                operation, arguments, directory=directory, owned_directory=owned_directory,
                policy=self.local_job_policy, **selected_ports)
            return SequenceWork(output, metadata)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="sequence-",
                suffix=".request.json", dir=directory, delete=False) as handle:
            json.dump({"operation": operation, "arguments": arguments}, handle, allow_nan=False)
            request = Path(handle.name)
        output = request.with_suffix(".result.json")
        stdout, stderr = request.with_suffix(".stdout"), request.with_suffix(".stderr")
        environment = dict(os.environ)
        package_root = str(Path(__file__).resolve().parents[3])
        environment["PYTHONPATH"] = package_root + os.pathsep + environment.get("PYTHONPATH", "")
        # cwd includes retained earlier sibling results, so the common scratch
        # monitor covers the entire staged selected operation, not just this row.
        completed = False
        try:
            job = await run_local_job_async([sys.executable, "-m", "gene_annotation_episode.sequence_worker",
                str(request), str(output)], cwd=directory, policy=self.local_job_policy,
                stdout_path=stdout, stderr_path=stderr, env=environment,
                **({'statistics': self.native_statistics.for_alignment(arguments, self.local_job_policy)}
                   if operation == 'align_pair' and self.native_statistics is not None else {}))
            if job.returncode == 2 and output.is_file():
                failure = json.loads(output.read_text(encoding="utf-8"))
                if failure.get("exception_type") == "ValueError":
                    raise ContractError(failure["code"], detail={'native_execution': job.metadata})
            if job.returncode != 0:
                worker_failure = {}
                if job.returncode == 3 and output.is_file():
                    failure = json.loads(output.read_text(encoding="utf-8"))
                    if failure.get("exception_type") == "MemoryError":
                        worker_failure = {"worker_failure": "native_memory_allocation_failed"}
                diagnostic = artifact_file(self.store, stderr, "text/plain") if stderr.exists() else None
                raise AcquisitionError("local_job_execution_failed", phase="local_execution", operational={
                    **job.metadata, **worker_failure, "diagnostic_ref": diagnostic,
                    "native_returncode": job.returncode, "worker_operation": operation})
            if not output.is_file():
                raise AcquisitionError("local_job_output_missing", phase="local_execution", operational={
                    **job.metadata, "worker_operation": operation})
            completed = True
            return SequenceWork(output, job.metadata)
        finally:
            # Keep only the staged successful native body until publication.
            request.unlink(missing_ok=True)
            stdout.unlink(missing_ok=True)
            stderr.unlink(missing_ok=True)
            if not completed:
                output.unlink(missing_ok=True)

