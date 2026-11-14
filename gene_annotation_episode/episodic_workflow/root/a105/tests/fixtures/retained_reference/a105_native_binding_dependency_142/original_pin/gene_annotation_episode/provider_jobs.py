"""Ordinary BLAST/Rfam protocols and read-only historical provider job records.

HMMER execution belongs to bounded API episode operations.
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
import hashlib
import json
from typing import Any

from .acquisition import AcquisitionError, PublicClients, SourceSnapshot
from .domain import ContractError, canonical, identity
from .rfam_discovery import submission_handle, result_body, validate_result_url, submission_failure_feedback
from . import blast_search as blast


HMMER_IDENTITY_VERSION = "hmmer_single_fasta_sequence_v2"


def request_identity_feedback(request: dict) -> dict:
    if (request.get("provider", "hmmer") == "hmmer"
            and request.get("identity_version") != HMMER_IDENTITY_VERSION):
        return {"identity_compatibility": "unsupported_historical_hmmer_request",
                "stored_identity_version": request.get("identity_version"),
                "supported_identity_version": HMMER_IDENTITY_VERSION}
    return {}


def require_hmmer_identity_version(request: dict) -> None:
    feedback = request_identity_feedback(request)
    if feedback:
        raise AcquisitionError("hmmer_request_identity_version_unsupported", phase="local_request_identity",
            operational=feedback)


def validate_remote_identity(native: dict, request: dict, remote_id: str, *, result: bool = False) -> None:
    """Check present source identities, without requiring undocumented fields."""
    import uuid
    require_hmmer_identity_version(request)
    checks = {"id": remote_id, "algo": request["algorithm"], "database": request["database"]}
    result_body = native.get("result")
    if result and not isinstance(result_body, dict):
        raise AcquisitionError("provider_result_representation")
    fields = result_body.get("stats", {}) if result else native
    if not isinstance(fields, dict):
        raise AcquisitionError("provider_result_representation")
    for key, expected in checks.items():
        actual = fields.get(key)
        if isinstance(actual, dict) and key == "database":
            actual = actual.get("id")
        if actual is None:
            continue
        if key == "id":
            try:
                actual = str(uuid.UUID(actual))
            except (ValueError, TypeError, AttributeError):
                pass
        if actual != expected:
            raise AcquisitionError("remote_identity_conflict_"+key)
    if not result and isinstance(native.get("input"), str) and "sequence_sha256" in request:
        from .domain import parse_sequences
        try:
            sequences = parse_sequences(native["input"], format="fasta" if native["input"].lstrip().startswith(">") else "raw", molecule="protein")
        except ValueError as error:
            raise AcquisitionError("remote_identity_conflict_input") from error
        if len(sequences) != 1 or hashlib.sha256(sequences[0].sequence.encode()).hexdigest() != request["sequence_sha256"]:
            raise AcquisitionError("remote_identity_conflict_input")


class RemoteSearches:
    def __init__(self, store: Any, clients: PublicClients, *, poll_interval_seconds: float = 5):
        if not isinstance(poll_interval_seconds, (int, float)) or poll_interval_seconds < 0:
            raise ValueError("invalid_provider_poll_interval")
        self.store, self.clients = store, clients
        self.poll_interval_seconds = poll_interval_seconds
        store.db.execute("""CREATE TABLE IF NOT EXISTS provider_jobs (
            id TEXT PRIMARY KEY, operation_key TEXT UNIQUE NOT NULL, request TEXT NOT NULL,
            state TEXT NOT NULL, remote_id TEXT, submission TEXT, latest_status TEXT,
            result TEXT, error_code TEXT)""")
        # Operational diagnostics are not scientific source records or results.
        # One current cause per job; exact failed attempts remain in tool audit.
        store.db.execute("""CREATE TABLE IF NOT EXISTS provider_job_failures (
            job_ref TEXT PRIMARY KEY, data TEXT NOT NULL)""")
        store.db.commit()

    def _snapshot(self, snapshot: SourceSnapshot) -> str:
        fields = asdict(snapshot)
        fields.pop("content")
        fields["content_ref"] = self.store.artifact(snapshot.content, snapshot.media_type)
        return canonical(fields)

    def _load_snapshot(self, saved: str) -> SourceSnapshot:
        fields = json.loads(saved)
        fields["content"] = self.store.get_artifact(fields.pop("content_ref"))
        return SourceSnapshot(**fields)

    def _get(self, job_ref: str) -> dict:
        row = self.store.db.execute("SELECT * FROM provider_jobs WHERE id=?", (job_ref,)).fetchone()
        if row is None:
            raise ContractError("unknown_provider_job")
        return dict(row)

    def _update(self, job_ref: str, **values) -> None:
        permitted = {"state", "remote_id", "submission", "latest_status", "result", "error_code"}
        if not set(values) <= permitted:
            raise ValueError("invalid_provider_job_field")
        with self.store.transaction():
            self.store.db.execute("UPDATE provider_jobs SET " + ",".join(key+"=?" for key in values) + " WHERE id=?",
                                  [*values.values(), job_ref])
            if "error_code" in values and values["error_code"] is None:
                self.store.db.execute("DELETE FROM provider_job_failures WHERE job_ref=?", (job_ref,))

    def _owner_state(self, row: dict) -> dict:
        failure = self.store.db.execute("SELECT data FROM provider_job_failures WHERE job_ref=?",
                                        (row["id"],)).fetchone()
        compatibility = request_identity_feedback(json.loads(row["request"]))
        return {"submission_state": row["state"], "remote_handle_known": row["remote_id"] is not None,
                # Means addressable through collect (or cached), not a promise
                # of a successful remote result or a scientific conclusion.
                "collectable": not compatibility and json.loads(row["request"]).get("provider", "hmmer") != "hmmer"
                    and (row["remote_id"] is not None or row["result"] is not None),
                "cause": json.loads(failure[0]) if failure else None, **compatibility}

    def _require_supported_request(self, row):
        request = json.loads(row["request"])
        if request.get("provider", "hmmer") == "hmmer":
            try:
                require_hmmer_identity_version(request)
            except AcquisitionError as error:
                error.job_ref = row["id"]
                error.operational = {**self._owner_state(row), **(error.operational or {})}
                raise

    def _record_failure(self, job_ref: str, error: BaseException, *, phase: str,
                        state: str | None = None, submitted_length: int | None = None) -> None:
        snapshot = getattr(error, "snapshot", None)
        response_ref = None
        if snapshot is not None:
            response_ref = self.store.artifact(self._snapshot(snapshot), "application/json")
        diagnostic = getattr(error, "diagnostic", None)
        cause = error.__cause__ or error
        diagnostic_ref = response_ref or self.store.artifact(canonical({
            "representation": "local_exception", "exception_type": type(cause).__name__,
            "message": str(cause), "details": diagnostic}), "application/json")
        outcome = getattr(error, "submission_outcome", None)
        if outcome is None:
            outcome = "remote_handle_returned" if self._get(job_ref)["remote_id"] is not None else "unknown"
        failure = {"code": error.code if isinstance(error, AcquisitionError) else "remote_submission_uncertain",
            "exception_type": type(cause).__name__, "phase": phase,
            "client_phase": getattr(error, "phase", None),
            # Only an explicit client preflight can establish not_sent. HTTP
            # statuses and exception classes alone never establish rejection.
            "submission_outcome": outcome,
            "retry_after": getattr(error, "retry_after", None),
            "diagnostic_ref": diagnostic_ref, "response_ref": response_ref,
            "http_status": snapshot.transport.get("status") if snapshot is not None else None}
        request = json.loads(self._get(job_ref)["request"])
        if (request.get("provider", "hmmer") == "rfam" and phase == "submission"
                and snapshot is not None and snapshot.service == "rfam_batch"):
            feedback = submission_failure_feedback(snapshot.content,
                http_status=snapshot.transport.get("status"), submitted_length=submitted_length)
            if feedback is not None:
                failure["provider_feedback"] = feedback
        with self.store.transaction():
            self.store.db.execute("INSERT OR REPLACE INTO provider_job_failures VALUES(?,?)",
                                  (job_ref, canonical(failure)))
            values = {"error_code": failure["code"]}
            if state is not None:
                values["state"] = state
            if phase == "submission" and snapshot is not None:
                values["submission"] = self._snapshot(snapshot)
            self._update(job_ref, **values)

    def _job_error(self, job_ref: str) -> AcquisitionError:
        row = self._get(job_ref)
        operational = self._owner_state(row)
        failure = operational["cause"] or {}
        saved = failure.get("response_ref")
        snapshot = self._load_snapshot(self.store.get_artifact(saved).decode()) if saved else None
        return AcquisitionError(row["error_code"] or "remote_submission_uncertain",
            job_ref=job_ref, retry_after=failure.get("retry_after"), snapshot=snapshot,
            phase=failure.get("phase"), submission_outcome=failure.get("submission_outcome"),
            operational=operational)

    def describe(self, job_ref: str) -> dict:
        row = self._get(job_ref)
        return {"job_ref": row["id"], "state": row["state"], "remote_id": row["remote_id"],
                "request": json.loads(row["request"]), "error_code": row["error_code"],
                **self._owner_state(row)}

    def jobs(self, *, limit: int = 100, offset: int = 0, active_only: bool = True) -> list[dict]:
        # Current ownership and handles only, not all HTTP bodies or audit history.
        return [{"job_ref": row["id"], "state": row["state"], "remote_id": row["remote_id"],
                 "request": json.loads(row["request"]), "error_code": row["error_code"],
                 **self._owner_state(dict(row))}
                for row in self.store.db.execute("SELECT * FROM provider_jobs" +
                    (" WHERE state NOT IN ('returned','SUCCESS','FAILURE','REVOKED','not_submitted','DEL') AND NOT (COALESCE(json_extract(request,'$.provider'),'hmmer')='blast' AND state IN ('FAILED','UNKNOWN'))" if active_only else "") +
                    " ORDER BY rowid LIMIT ? OFFSET ?", (limit, offset))]

    async def search(self, operation_key: str, *, subject_ref: str, query_fasta: str,
                     algorithm: str, database: str, parameters: dict | None = None,
                     page_size: int = 50, provider: str = "hmmer") -> SourceSnapshot:
        if provider == "hmmer":
            raise ContractError("hmmer_requires_api_execution_episode")
        request = {"subject_ref": subject_ref, "query_sha256": hashlib.sha256(query_fasta.encode()).hexdigest(),
                   "algorithm": algorithm, "database": database, "parameters": parameters or {}, "page_size": page_size}
        from .domain import parse_sequences
        if provider not in {"rfam", "blast"}:
            raise ContractError("unknown_remote_search_provider")
        if provider == "blast":
            if algorithm not in blast.PROGRAM_UNITS or set(parameters or {}) - {"hitlist_size"}:
                raise ContractError("unsupported_blast_search_configuration")
            request.pop("page_size")
            request.update(provider="blast", molecule_model="protein" if blast.PROGRAM_UNITS[algorithm][0] == "aa" else "dna",
                molecule_assignment="not_performed")
            sequence = parse_sequences(query_fasta, format="fasta", molecule="unspecified")
        elif provider == "rfam":
            if algorithm != "cmscan" or database != "Rfam" or parameters:
                raise ContractError("rfam_provider_defaults_search_required")
            request.pop("page_size")  # This API returns one complete result, not pages.
            request.update(provider="rfam", molecule_model="rna", molecule_assignment="not_performed",
                search_parameters="provider_defaults_not_exposed", database_release=None, model_release=None)
            sequence = parse_sequences(query_fasta, format="fasta", molecule="unspecified")
        if len(sequence) != 1:
            raise ContractError("single_query_required")
        request["sequence_sha256"] = hashlib.sha256(sequence[0].sequence.encode()).hexdigest()
        if provider == "blast":
            request["query_length"] = len(sequence[0].sequence)
        row = self.store.db.execute("SELECT * FROM provider_jobs WHERE operation_key=?", (operation_key,)).fetchone()
        if row is None:
            job_ref = identity("provider_job", {"operation_key": operation_key, "request": request})
            with self.store.transaction():
                self.store.db.execute("INSERT INTO provider_jobs VALUES(?,?,?,?,?,?,?,?,?)",
                    (job_ref, operation_key, canonical(request), "submitting", None, None, None, None, None))
            # The intent commits before the one remote submission. A process
            # dying in this gap leaves ambiguity, not permission to submit again.
            try:
                if provider == "blast":
                    await self._blast_wait("submit")
                snapshot = (await asyncio.to_thread(self.clients.blast, "submit", query_fasta=query_fasta,
                        program=algorithm, database=database, **(parameters or {})) if provider == "blast" else
                    await asyncio.to_thread(self.clients.rfam_submit, sequence[0].sequence))
                # The exact returned entity is durable BEFORE its contents or
                # handle are interpreted, including malformed HTTP-200 bodies.
                self._update(job_ref, submission=self._snapshot(snapshot))
                try:
                    if provider == "blast":
                        remote_id, _rtoe = blast.submission(snapshot.content)
                    else:
                        remote_id = submission_handle(snapshot.content)
                except (ValueError, KeyError, TypeError, AttributeError) as error:
                    raise AcquisitionError("provider_submission_response_invalid", snapshot=snapshot,
                                           phase="submission_response") from error
                self._update(job_ref, state="accepted", remote_id=remote_id, error_code=None)
            except BaseException as error:
                # A cancelled/failed POST may have reached the server. It is
                # never automatically retried, and is not a biological result.
                outcome = getattr(error, "submission_outcome", None)
                self._record_failure(job_ref, error, phase="submission",
                    state="not_submitted" if outcome == "not_sent" else "submission_uncertain",
                    submitted_length=len(sequence[0].sequence))
                if isinstance(error, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                    raise
                raise self._job_error(job_ref) from error
        else:
            job_ref = row["id"]
            if row["request"] != canonical(request):
                raise ContractError("provider_operation_reused_for_different_search")
        if row is None and provider == "rfam":
            # The official batch API requests a short delay before the first GET.
            # A cancellation here leaves the committed accepted handle reusable.
            await asyncio.sleep(self.poll_interval_seconds)
        return await self.collect(job_ref)

    async def _blast_wait(self, action: str, rid: str | None = None, *, submission=None):
        # Scheduling the next protocol operation is not an attempt/retry. A
        # racing process can still receive precise not-sent spacing feedback.
        delay = self.clients.blast_delay(action, rid) if hasattr(self.clients, "blast_delay") else 0.
        if submission is not None:
            from datetime import datetime, timezone
            _rid, rtoe = blast.submission(submission.content)
            elapsed = (datetime.now(timezone.utc)-datetime.fromisoformat(submission.retrieved_at)).total_seconds()
            delay = max(delay, max(rtoe or 0, 10)-elapsed)
        if delay > 0:
            await asyncio.sleep(delay)

    async def collect(self, job_ref: str) -> SourceSnapshot:
        row = self._get(job_ref)
        if json.loads(row["request"]).get("provider", "hmmer") == "hmmer":
            raise ContractError("hmmer_requires_api_execution_episode")
        if row["result"] is not None:
            self._update(job_ref, error_code=None)
            return self._load_snapshot(row["result"])
        if row["remote_id"] is None:
            raise self._job_error(job_ref)
        request = json.loads(row["request"])
        provider = request.get("provider", "hmmer")
        try:
            # One shared protocol wait loop. Polling does not choose another
            # scientific action, add an Episode, or create yield observations.
            while True:
                if provider == "blast":
                    initial = (self._load_snapshot(row["submission"]) if row["latest_status"] is None else None)
                    await self._blast_wait("status", row["remote_id"], submission=initial)
                snapshot = (await asyncio.to_thread(self.clients.blast, "status", rid=row["remote_id"]) if provider == "blast" else
                    await asyncio.to_thread(self.clients.rfam_result, row["remote_id"]))
                self._update(job_ref, latest_status=self._snapshot(snapshot))
                if provider == "blast":
                    try:
                        state = blast.status(snapshot.content)["status"]
                    except (ValueError, TypeError, UnicodeError) as error:
                        raise AcquisitionError("provider_status_response_invalid", snapshot=snapshot, phase="status_response") from error
                elif provider == "rfam":
                    try:
                        actual_url = snapshot.transport.get("effective_url", snapshot.url)
                        validate_result_url(actual_url, row["remote_id"])
                        status = snapshot.transport.get("status")
                        if status == 202:
                            state = snapshot.content.decode("ascii").strip()
                            if state.startswith('"'):
                                state = json.loads(state)
                            if state not in {"PEND", "RUN"}:
                                raise ValueError("rfam_pending_status_invalid")
                        elif status == 200:
                            result_body(snapshot.content, job_id=row["remote_id"],
                                        sequence_sha256=request["sequence_sha256"])
                            state = "SUCCESS"
                        else:
                            raise ValueError("rfam_result_http_status_invalid")
                    except (ValueError, KeyError, TypeError, AttributeError) as error:
                        raise AcquisitionError(str(error) if str(error).startswith("rfam_")
                            else "provider_result_response_invalid", snapshot=snapshot,
                            phase="result_response") from error
                self._update(job_ref, state=state, latest_status=self._snapshot(snapshot), error_code=None)
                if state == "SUCCESS" or (provider == "blast" and state == "READY"):
                    break
                if state in {"FAILURE", "REVOKED"} or (provider == "blast" and state in {"FAILED", "UNKNOWN"}):
                    raise AcquisitionError("remote_search_failed", job_ref=job_ref,
                                           snapshot=snapshot, phase="status_response")
                if state not in {"PENDING", "RECEIVED", "STARTED", "RETRY", "PEND", "RUN"} and not (provider == "blast" and state == "WAITING"):
                    raise AcquisitionError("unknown_remote_search_status", job_ref=job_ref,
                                           snapshot=snapshot, phase="status_response")
                await asyncio.sleep(self.poll_interval_seconds)
        except AcquisitionError as error:
            native_state = None
            if provider == "rfam" and error.snapshot is not None:
                # These are documented provider-job states, not scientific
                # stopping/completion decisions for the owning Episode.
                status = error.snapshot.transport.get("status")
                if status == 410:
                    native_state = "DEL"
                elif status == 503:
                    try:
                        body = error.snapshot.content.decode("ascii").strip()
                        if body.startswith('"'):
                            body = json.loads(body)
                        if body == "HOLD":
                            native_state = "HOLD"
                    except (ValueError, TypeError):
                        pass
            self._record_failure(job_ref, error, phase="result" if provider == "rfam" else "status",
                                 state=native_state)
            raise self._job_error(job_ref) from error
        if provider == "blast":
            try:
                await self._blast_wait("fetch", row["remote_id"])
                result = await asyncio.to_thread(self.clients.blast, "fetch", rid=row["remote_id"])
                try:
                    parsed = blast.document(result.content)
                    blast.validate_identity(parsed, request)
                except Exception as error:
                    raise AcquisitionError(str(error) if str(error).startswith("blast_") else "provider_result_response_invalid",
                        snapshot=result, phase="result_response") from error
                result = replace(result, request={**request, "job_id": row["remote_id"]},
                    transport={**result.transport, "job_ref": job_ref})
                self._update(job_ref, state="returned", error_code=None, result=self._snapshot(result))
                return result
            except AcquisitionError as error:
                self._record_failure(job_ref, error, phase="result")
                raise self._job_error(job_ref) from error
        if provider == "rfam":
            result = replace(snapshot, request={**request, "job_id": row["remote_id"]},
                transport={**snapshot.transport, "job_ref": job_ref})
            self._update(job_ref, state="returned", error_code=None, result=self._snapshot(result))
            return result
