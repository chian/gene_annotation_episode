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
from .tool_values import SequenceWork

class ToolNativeSequence:
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
                from .library import molecular_worker_ports
                selected_ports["worker_ports"] = molecular_worker_ports
            elif operation in {"protein_conservation_native", "protein_conservation_result",
                    "protein_phylogeny_iqtree_native", "protein_phylogeny_result", "macs2_peak_result",
                    "somatic_variant_native", "somatic_variant_result"}:
                from .library import ordinary_scientific_worker_ports
                selected_ports["worker_ports"] = ordinary_scientific_worker_ports
            elif operation in {"homer_motif_result", "tf_binding_native", "tf_binding_result"}:
                from .library import homer_tf_worker_ports
                selected_ports["worker_ports"] = homer_tf_worker_ports
            elif operation in {"itc_binding", "liftover_point", "circular_dichroism"}:
                from .library import physical_measurement_worker_ports
                selected_ports["worker_ports"] = physical_measurement_worker_ports
            elif operation == "esm_gene_embedding":
                from .library.esm_worker_ports import ESMWorkerPorts
                selected_ports["worker_ports"] = ESMWorkerPorts(arguments)
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
            job = await run_local_job_async([sys.executable, "-m",
                ("gene_annotation_episode.episodic_workflow.root.library.sequence_analysis_worker"
                 if operation in {"align_pair", "predict_genes"} else "gene_annotation_episode.sequence_worker"),
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

    async def _prepare_sequence_work_async(self, name: str, args: dict, scope: dict | None):
        if self.store.db.in_transaction:
            raise ContractError("native_sequence_work_requires_no_active_store_transaction")
        directory = Path(tempfile.mkdtemp(prefix=".native-sequence-", dir=self.store.path))
        self._mapping_directories.get().append(directory)
        if name == "reads.align":
            prepared = []
            for index, reference in enumerate(args["subject_refs"]):
                selected = {"query_ref": reference,
                    **{key: args[key] for key in ("reference_ref", "molecule", "mode")}}
                try:
                    if self.store.get(reference)["record_type"] != "read_subject":
                        raise ContractError("original_read_subject_required")
                    native = await self._prepare_alignment_async(selected, scope, directory)
                    prepared.append({"arguments": selected, "native": native})
                except (ContractError, ValueError, AcquisitionError) as error:
                    operational = isinstance(error, AcquisitionError)
                    row = {"row_index": index, "subject_ref": reference,
                        "code": error.code if operational else str(error) if isinstance(error, ContractError) else "native_alignment_input_error"}
                    if operational:
                        row.update(category="execution", phase=error.phase, **(error.operational or {}))
                    elif isinstance(error, ContractError) and error.detail:
                        row["detail"] = error.detail
                    prepared.append({"error": row})
            return prepared
        if name == "sequence.align":
            return await self._prepare_alignment_async(args, scope, directory)
        subject = self.store.get(args["subject_ref"])
        sequence = self._sequence(subject["id"], molecule_model="dna")
        start, end = args.get("start", 0), args.get("end", len(sequence))
        if not 0 <= start < end <= len(sequence):
            raise ContractError("requested_interval_outside_subject")
        footprint = self.store.map_segments(subject["id"], [{"start": start, "end": end}])
        self._check_sequence_operand(subject["id"], scope, footprint=footprint)
        if self.store.sequence_mapping(subject["id"])["units_per_symbol"] != 1:
            raise ContractError("translation_requires_nucleotide_symbol_mapping")
        return await self._sequence_worker_async("predict_genes", {"sequence": sequence[start:end],
            "code": args["code"], "mode": args["mode"]}, directory=directory)

    def _alignment_arguments(self, args, scope):
        query = self._check_sequence_operand(args["query_ref"], scope)
        self.store.subject_length(args["reference_ref"])
        return query, {'query': self._sequence(query['id'], molecule_model=args['molecule']),
            'reference': self._sequence(args['reference_ref'], molecule_model=args['molecule']),
            'molecule': args['molecule'], 'mode': args['mode']}

    def _estimate_native(self, args, scope):
        from .execution_expectations import capture_execution_scopes
        if args['tool'] == 'sequence.align':
            _, native = self._alignment_arguments(args['arguments'], scope)
            execution_class = self.native_statistics.alignment_class(native, self.local_job_policy)
        else:
            _, path, operation, selected = self._spreadsheet_arguments(args['tool'], args['arguments'])
            execution_class = self.native_statistics.spreadsheet_class(path, operation, selected, self.local_job_policy)
        recovery = self.native_statistics.recover_pending_statistics()
        return {'tool': args['tool'], 'arguments': args['arguments'],
            'execution_expectations': {**capture_execution_scopes(self.native_statistics.history_path, [execution_class]),
                                       'statistics_recovery': recovery}}

    async def _prepare_alignment_async(self, args: dict, scope: dict | None, directory: Path):
        query, arguments = self._alignment_arguments(args, scope)
        operands = [{'role': 'query', 'subject_ref': query['id']},
                    {'role': 'reference', 'subject_ref': args['reference_ref']}]
        try:
            native = await self._sequence_worker_async('align_pair', arguments, directory=directory)
        except (AcquisitionError, ContractError) as error:
            metadata = error.operational if isinstance(error, AcquisitionError) else error.detail.get('native_execution')
            if metadata:
                self._record_native_execution(metadata, operation='align_pair', operands=operands)
            raise
        self._record_native_execution(native.metadata, operation='align_pair', operands=operands)
        return native

    def _record_native_execution(self, metadata, *, operation, operands):
        """Retain actual timing independently of scientific publication success."""
        from .native_measurement import NativeMeasurement
        from .native_timing_information import record_native_measurement
        measured = (metadata.get('statistics_export') or {}).get('measurement')
        if measured is None:
            return
        measurement = NativeMeasurement.from_record(measured)
        reference = record_native_measurement(self.store, measurement, operation=operation, operands=operands)
        # Do not append this to _written: a timing receipt does not turn a
        # failed scientific publisher into partially successful science.
        self._native_execution_refs.get().append(reference)
        metadata['native_execution_ref'] = reference

    def _publish_read_alignments(self, args, scope, prepared):
        batch = self._begin_publication_batch(failures=True)
        rows, errors, refs, completed = [], [], [], 0
        for index, item in enumerate(prepared):
            before = len(self._written)
            if "error" in item:
                errors.append(item["error"])
                batch["failure_rows_total"] = len(errors)
                continue
            try:
                result, published = self._align_one(item["arguments"], scope, item["native"])
                refs.extend(published)
                completed += 1
                batch["published_rows_total"] = completed
                if len(rows) < 12:
                    rows.append({"subject_ref": args["subject_refs"][index], **result})
            except (ContractError, ValueError) as error:
                refs.extend(self._written[before:])
                errors.append({"row_index": index, "subject_ref": args["subject_refs"][index],
                    "code": str(error) if isinstance(error, ContractError) else "native_alignment_input_error",
                    **({"detail": error.detail} if isinstance(error, ContractError) and error.detail else {})})
                batch["failure_rows_total"] = len(errors)
            finally:
                item["native"].output_path.unlink(missing_ok=True)
        return {"count": len(args["subject_refs"]), "completed_count": completed,
            "records": rows, "preview_limit": 12, "errors": errors,
            "more_records_available_through_state_query": completed > 12,
            "target_annotation": "not_performed"}, list(dict.fromkeys(refs))

    @staticmethod
    async def _native_thread_async(function, *args, **kwargs):
        """Cancellation waits for the native adapter to reap its process tree."""
        return await run_cancellable_native(function, *args, **kwargs)

