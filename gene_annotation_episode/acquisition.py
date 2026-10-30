"""Explicit public evidence acquisitions and source-preserving parsers.

No adaptive search, annotation selection, scientific acceptance or episode
continuation is hidden in these clients. Each call executes one requested
lookup/submission/status/result operation. Public annotations remain statements
about their source subjects, rather than facts about the caller's target.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import base64
import io
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from .domain import PUBLICATION_ID_PATTERNS
from .public_configuration import UNSET, ncbi_contact


@dataclass(frozen=True)
class SourceSnapshot:
    service: str
    url: str
    request: dict[str, Any]
    retrieved_at: str
    content: bytes
    media_type: str
    transport: dict[str, Any]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


@dataclass(frozen=True)
class RfamModelSnapshots:
    model: SourceSnapshot
    metadata: SourceSnapshot | None
    metadata_error: AcquisitionError | None = None


class AcquisitionError(RuntimeError):
    def __init__(self, code: str, *, retry_after: float | None = None, job_ref: str | None = None,
                 snapshot: SourceSnapshot | None = None, phase: str | None = None,
                 submission_outcome: str | None = None, diagnostic: dict | None = None,
                 operational: dict | None = None):
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after
        self.job_ref = job_ref
        self.snapshot = snapshot
        self.phase = phase
        self.submission_outcome = submission_outcome
        self.diagnostic = diagnostic
        self.operational = operational


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _skill_script(root: Path | None, skill: str, filename: str) -> Path:
    if root is not None:
        path = root / "skills" / skill / "scripts" / filename
        if not path.is_file():
            raise AcquisitionError("configured_skill_client_missing")
        return path
    directory = Path.home() / ".codex/plugins/cache/openai-curated-remote/life-science-research"
    candidates = list(directory.glob(f"*/skills/{skill}/scripts/{filename}"))
    if not candidates:
        raise AcquisitionError("skill_client_not_installed")
    def key(path: Path) -> tuple[int, ...]:
        try:
            return tuple(int(part) for part in path.parents[3].name.split("."))
        except ValueError:
            return (0,)
    return max(candidates, key=key)


def _capture_metadata(path: Path, metadata: dict) -> None:
    temporary = path.with_suffix(path.suffix + '.pending')
    temporary.write_text(json.dumps(metadata, allow_nan=False))
    temporary.replace(path)


def _bounded_skill_response(response, destination: str, entity_destination: str, limit: int):
    """Observe decoded entity bytes before the unchanged client accesses them."""
    metadata_path, entity_path = Path(destination), Path(entity_destination)
    metadata = {'status': response.status_code, 'url': response.url,
        'headers': {key.lower(): value for key, value in response.headers.items()},
        'request_method': response.request.method}
    try:
        with entity_path.open('wb', buffering=0) as output:
            def retain(block):
                remaining = memoryview(block)
                while remaining:
                    written = output.write(remaining)
                    if not written:
                        raise OSError('response_capture_write_incomplete')
                    remaining = remaining[written:]

            def progress(capture):
                metadata.update(capture, retained_body_bytes=entity_path.stat().st_size)
                _capture_metadata(metadata_path, metadata)

            # read1 returns an available prefix before a subsequent read can
            # fail, and selected urllib3 limits decoded output to the amount.
            class Reader:
                headers = response.headers

                def read(self, amount):
                    return response.raw.read1(amount, decode_content=True)

            raw, capture, failure = PublicClients._read_bounded_response(Reader(), limit,
                decoded=True, retain=retain, progress=progress)
            metadata.update(capture, retained_body_bytes=entity_path.stat().st_size)
            _capture_metadata(metadata_path, metadata)
    finally:
        # Closing never drains an unconsumed body. The native client receives
        # only the complete cached entity below, or its ordinary error path.
        response.close()
    if failure is not None:
        raise ValueError(failure)
    if 300 <= response.status_code < 400:
        raise ValueError('provider_redirect_not_followed')
    response._content = raw
    response._content_consumed = True
    return response


class PublicClients:
    """Caller-configured clients. Missing contact affects BLAST submission only.

    UniProt/BLAST use the installed skill clients whose protocol instructions
    were read during the rebuild. The dependency path and digest are recorded.
    No copyrighted client is silently copied or imported from another project.
    Other providers use their documented public HTTP interfaces directly.
    """

    def __init__(self, *, ncbi_email: str | None | object = UNSET, skill_root: Path | None = None,
                 timeout: int = 90, access_dir: Path | None = None,
                 rhea_response_byte_limit: int = 8 * 1024 * 1024,
                 chebi_response_byte_limit: int = 8 * 1024 * 1024):
        if type(timeout) is not int or timeout <= 0:
            raise ValueError("invalid_transport_timeout")
        if type(rhea_response_byte_limit) is not int or rhea_response_byte_limit <= 0:
            raise ValueError('invalid_rhea_response_byte_limit')
        if type(chebi_response_byte_limit) is not int or chebi_response_byte_limit <= 0:
            raise ValueError('invalid_chebi_response_byte_limit')
        self.ncbi_email = ncbi_contact(ncbi_email)
        self.skill_root = skill_root
        self.timeout = timeout
        self.access_dir = access_dir
        self.rhea_response_byte_limit = rhea_response_byte_limit
        self.chebi_response_byte_limit = chebi_response_byte_limit

    def _skill(self, skill: str, filename: str, payload: dict[str, Any], *,
               capture_headers: bool = False, service_name: str | None = None,
               max_bytes: int | None = None) -> tuple[dict, bytes, dict]:
        if max_bytes is not None and (not capture_headers or type(max_bytes) is not int or max_bytes <= 0):
            raise ValueError('explicit_observed_response_byte_limit_required')
        script = _skill_script(self.skill_root, skill, filename)
        observer_policy = (None if max_bytes is None else {
            'version': 'bounded_skill_http_entity_capture_v1',
            'adapter_module': __name__, 'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'response_byte_limit': max_bytes, 'byte_basis': 'requests_decoded_entity_bytes',
            'stream': True, 'automatic_redirects': False, 'redirect_preparation': False})
        # Full payloads are retained as provenance, as the user's workflow
        # requires. The helper's compact preview is never parsed as full data.
        with tempfile.TemporaryDirectory(prefix="gene-evidence-") as directory:
            output_path = Path(directory) / "response.json"
            headers_path = Path(directory) / "headers.json"
            entity_path = Path(directory) / "response.entity"
            request = {**payload, "save_raw": True, "raw_output_path": str(output_path)}
            if skill == "uniprot-skill":
                request["timeout_sec"] = self.timeout
            command = [sys.executable, str(script)]
            if capture_headers:
                # Run the installed client unchanged and observe its single HTTP
                # response. The client's compact envelope omits Link headers,
                # which would otherwise make subsequent search pages invisible.
                observer = '''import json, pathlib, requests, runpy, sys
script, destination, entity_destination = sys.argv[1:]
original = requests.Session.request
def observed(self, *args, **kwargs):
    response = original(self, *args, **kwargs)
    pathlib.Path(destination).write_text(json.dumps({"status": response.status_code, "url": response.url,
        "headers": {key.lower(): value for key, value in response.headers.items()},
        "request_method": response.request.method}))
    pathlib.Path(entity_destination).write_bytes(response.content)
    return response
requests.Session.request = observed
sys.argv = [script]
runpy.run_path(script, run_name="__main__")
'''
                command = [sys.executable, "-c", observer, str(script), str(headers_path), str(entity_path)]
                if max_bytes is not None:
                    observer = '''import hashlib, pathlib, requests, runpy, sys
script, package_root, adapter_sha256, limit, destination, entity_destination = sys.argv[1:]
sys.path.insert(0, package_root)
from gene_annotation_episode import acquisition as capture_adapter
if hashlib.sha256(pathlib.Path(capture_adapter.__file__).read_bytes()).hexdigest() != adapter_sha256:
    raise RuntimeError("response_capture_adapter_changed")
original_request = requests.Session.request
original_redirects = requests.Session.resolve_redirects
def observed(self, *args, **kwargs):
    kwargs.update(stream=True, allow_redirects=False)
    response = original_request(self, *args, **kwargs)
    return capture_adapter._bounded_skill_response(response, destination, entity_destination, int(limit))
def no_redirect_preparation(self, *args, **kwargs):
    return iter(())
requests.Session.request = observed
requests.Session.resolve_redirects = no_redirect_preparation
try:
    sys.argv = [script]
    runpy.run_path(script, run_name="__main__")
finally:
    requests.Session.request = original_request
    requests.Session.resolve_redirects = original_redirects
'''
                    command = [sys.executable, '-c', observer, str(script),
                        str(Path(__file__).resolve().parent.parent), observer_policy['adapter_sha256'],
                        str(max_bytes), str(headers_path), str(entity_path)]
            try:
                result = subprocess.run(command, input=json.dumps(request),
                                        text=True, capture_output=True, timeout=self.timeout)
            except subprocess.TimeoutExpired as error:
                # An observer may already have received the HTTP response
                # before the client exceeded its processing deadline.
                envelope = {"ok": False, "error": {"code": "provider_client_timeout"}}
            else:
                try:
                    envelope = json.loads(result.stdout)
                except (ValueError, TypeError):
                    envelope = {"ok": False, "error": {"code": "provider_client_invalid_response"}}
            captured_path = entity_path if entity_path.exists() else output_path
            if max_bytes is not None and captured_path.exists():
                with captured_path.open('rb') as stream:
                    captured = stream.read(max_bytes + 1)
                raw = captured[:max_bytes]
            else:
                captured = None
                raw = entity_path.read_bytes() if entity_path.exists() else output_path.read_bytes() if output_path.exists() else json.dumps(envelope).encode()
            response_metadata = json.loads(headers_path.read_text()) if headers_path.exists() else None
            if max_bytes is not None and response_metadata is not None:
                response_metadata['retained_body_bytes'] = len(raw)
                if not response_metadata.get('body_capture_finalized'):
                    previous = response_metadata.get('observed_body_bytes')
                    response_metadata.update(body_complete=False, total_body_bytes=None,
                        observed_body_bytes=None,
                        observed_body_bytes_lower_bound=max(len(raw), previous if type(previous) is int else 0))
                if captured is not None and len(captured) > max_bytes:
                    response_metadata.update(body_complete=False, total_body_bytes=None,
                        body_capture_failure='provider_response_byte_limit', observed_body_bytes=None,
                        observed_body_bytes_lower_bound=len(captured))
            capture_failure = (response_metadata or {}).get('body_capture_failure')
            if max_bytes is not None and envelope.get('ok') and (
                    not entity_path.exists() or response_metadata is None
                    or response_metadata.get('body_complete') is not True):
                capture_failure = capture_failure or 'provider_body_capture_failed'
                envelope = {'ok': False, 'error': {'code': capture_failure}}
            if not envelope.get("ok"):
                # The installed client's compact failure must not discard its
                # already returned HTTP entity. These bytes are diagnostics,
                # not a successful chemical/reaction record or local fake HTTP.
                status = (response_metadata or {}).get("status")
                snapshot = (SourceSnapshot(service_name or skill,
                    response_metadata.get("url", payload["base_url"].rstrip("/")+"/"+payload["path"].lstrip("/")),
                    payload.get("params", {}), _now(), raw,
                    response_metadata.get("headers", {}).get("content-type", "application/octet-stream"),
                     {"response": response_metadata, "representation": "http_entity_bytes_via_installed_client",
                      "script": str(script), "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                      **({'observer': observer_policy} if observer_policy is not None else {})})
                    if response_metadata and entity_path.exists() else None)
                code = ("provider_http_"+str(status) if isinstance(status, int) and status >= 400 else
                        'provider_redirect_not_followed' if max_bytes is not None and isinstance(status, int)
                        and 300 <= status < 400 else capture_failure or
                        envelope.get("error", {}).get("code", "provider_error"))
                raise AcquisitionError(code, snapshot=snapshot,
                    phase="http_response" if snapshot else "client_response",
                    diagnostic={"client_error": envelope.get("error"), "script": str(script),
                                "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest()})
        transport = {"script": str(script), "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                     "representation": "client_saved_provider_payload"}
        if response_metadata is not None:
            transport["response"] = response_metadata
            transport["representation"] = "http_entity_bytes_via_installed_client"
        if observer_policy is not None:
            transport['observer'] = observer_policy
        return envelope, raw, transport

    def rhea_search(self, query: str, *, limit: int = 10) -> SourceSnapshot:
        params = {"query": query, "format": "json", "limit": limit}
        _, content, transport = self._skill("rhea-skill", "rest_request.py", {
            "base_url": "https://www.rhea-db.org", "path": "rhea", "params": params,
            "response_format": "json", "timeout_sec": self.timeout}, capture_headers=True, service_name="rhea",
            max_bytes=self.rhea_response_byte_limit)
        return SourceSnapshot("rhea", "https://www.rhea-db.org/rhea", params,
                              _now(), content, "application/json", transport)

    def rhea_reaction(self, accession: str) -> SourceSnapshot:
        from .chemistry import accession as canonical_accession
        return self.rhea_search(canonical_accession(accession, "RHEA"), limit=1)

    def chebi_search(self, term: str, *, size: int = 10, page: int = 1) -> SourceSnapshot:
        # Current ChEBI OpenAPI calls this parameter term. The installed skill's
        # query example is ignored by the service and returns the whole database.
        params = {"term": term, "size": size, "page": page}
        path = "chebi/backend/api/public/es_search/"
        _, content, transport = self._skill("chebi-skill", "rest_request.py", {
            "base_url": "https://www.ebi.ac.uk", "path": path, "params": params,
            "response_format": "json", "timeout_sec": self.timeout}, capture_headers=True, service_name="chebi",
            max_bytes=self.chebi_response_byte_limit)
        return SourceSnapshot("chebi", "https://www.ebi.ac.uk/"+path, params,
                              _now(), content, "application/json", transport)

    def chebi_compound(self, accession: str) -> SourceSnapshot:
        from .chemistry import accession as canonical_accession
        cid = canonical_accession(accession, "CHEBI")
        path = "chebi/backend/api/public/compound/"+cid+"/"
        _, content, transport = self._skill("chebi-skill", "rest_request.py", {
            "base_url": "https://www.ebi.ac.uk", "path": path,
            "response_format": "json", "timeout_sec": self.timeout}, capture_headers=True, service_name="chebi",
            max_bytes=self.chebi_response_byte_limit)
        return SourceSnapshot("chebi", "https://www.ebi.ac.uk/"+path, {"accession": cid},
                              _now(), content, "application/json", transport)

    def uniprot_search(self, query: str, *, size: int = 10, cursor: str | None = None) -> SourceSnapshot:
        params: dict[str, Any] = {"query": query, "size": size, "format": "json"}
        if cursor:
            params["cursor"] = cursor
        _, content, transport = self._skill("uniprot-skill", "rest_request.py", {
            "base_url": "https://rest.uniprot.org", "path": "uniprotkb/search",
            "params": params, "max_items": size, "response_format": "json"}, capture_headers=True)
        return SourceSnapshot("uniprot", "https://rest.uniprot.org/uniprotkb/search", params,
                              _now(), content, "application/json", transport)

    def uniprot_record(self, accession: str) -> SourceSnapshot:
        path = f"uniprotkb/{urllib.parse.quote(accession, safe='')}"
        _, content, transport = self._skill("uniprot-skill", "rest_request.py", {
            "base_url": "https://rest.uniprot.org", "path": path,
            "params": {"format": "json"}, "response_format": "json"}, capture_headers=True)
        return SourceSnapshot("uniprot", "https://rest.uniprot.org/" + path,
                              {"accession": accession}, _now(), content, "application/json", transport)

    def blast_delay(self, action: str, rid: str | None = None) -> float:
        """Next permitted HTTP time within the caller's shared access directory."""
        if self.access_dir is None:
            raise AcquisitionError("blast_rate_state_not_configured", phase="local_preflight", submission_outcome="not_sent")
        import time
        import fcntl
        self.access_dir.mkdir(parents=True, exist_ok=True)
        with (self.access_dir / "ncbi-blast.json").open("a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_SH)
            handle.seek(0)
            state = json.loads(handle.read() or "{}")
        delay = max(0., 10. - (time.time()-state.get("last_request", 0)))
        if action == "status":
            delay = max(delay, 60. - (time.time()-state.get("rids", {}).get(rid, 0)))
        return delay

    def blast(self, action: str, *, query_fasta: str | None = None, rid: str | None = None,
              program: str = "blastp", database: str = "swissprot", hitlist_size: int = 50) -> SourceSnapshot:
        if action not in {"submit", "status", "fetch"}:
            raise ValueError("one_explicit_blast_operation_required")
        if action == "submit" and not self.ncbi_email:
            raise AcquisitionError("ncbi_contact_not_configured", phase="local_preflight", submission_outcome="not_sent")
        if self.access_dir is None:
            raise AcquisitionError("blast_rate_state_not_configured", phase="local_preflight", submission_outcome="not_sent")
        try:
            script = _skill_script(self.skill_root, "ncbi-blast-skill", "ncbi_blast.py")
        except AcquisitionError as error:
            error.phase, error.submission_outcome = "local_preflight", "not_sent"
            raise
        request = {"action": action, "tool": "gene-annotation-episode", "result_format": "json2",
            "email": self.ncbi_email, "rid": rid, "program": program, "database": database,
            "query_fasta": query_fasta, "hitlist_size": hitlist_size, "max_hits": 12, "max_queries": 1}
        # Invoke the installed single-request primitives unchanged. Its public
        # fetch_action also polls SearchInfo, so use the ready-result primitive
        # after the durable owner has already received actual READY status.
        observer = r'''import base64, hashlib, json, pathlib, requests, runpy, sys
script, entity_path, metadata_path = sys.argv[1:]
payload = json.load(sys.stdin)
module = runpy.run_path(script, run_name="installed_blast_client")
original = requests.Session.request
count = 0
def observed(self, *args, **kwargs):
    global count
    count += 1
    if count != 1:
        raise RuntimeError("single_blast_http_operation_required")
    kwargs["allow_redirects"] = False
    response = original(self, *args, **kwargs)
    pathlib.Path(entity_path).write_bytes(response.content)
    body = response.request.body
    if isinstance(body, str): body = body.encode()
    pathlib.Path(metadata_path).write_text(json.dumps({"status": response.status_code,
        "effective_url": response.url, "headers": dict(response.headers),
        "request": {"method": response.request.method, "url": response.request.url,
            "headers": dict(response.request.headers), "body_base64": base64.b64encode(body or b"").decode(),
            "body_sha256": hashlib.sha256(body or b"").hexdigest()}}))
    return response
requests.Session.request = observed
try:
    config = module["parse_input"](payload)
    session = module["make_session"](config["tool"], config["email"])
    throttle = module["RequestThrottle"]()
    if config["action"] == "submit":
        result = module["submit_search"](session, throttle, config)
    elif config["action"] == "status":
        result = module["get_search_info"](session, throttle, config["rid"], config["tool"], config["email"])
    else:
        result = module["_fetch_result_ready"](session, throttle, config["rid"], config)
    print(json.dumps(result))
except Exception as error:
    print(json.dumps({"ok": False, "error": {"code": "blast_client_error", "exception_type": type(error).__name__, "message": str(error)}}))
'''
        import fcntl
        import time
        self.access_dir.mkdir(parents=True, exist_ok=True)
        with (self.access_dir / "ncbi-blast.json").open("a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.seek(0)
            state = json.loads(handle.read() or "{}")
            delay = max(0., 10.-(time.time()-state.get("last_request", 0)))
            if action == "status":
                delay = max(delay, 60.-(time.time()-state.get("rids", {}).get(rid, 0)))
            if delay > 0:
                raise AcquisitionError("provider_spacing_required", retry_after=delay,
                    phase="local_preflight", submission_outcome="not_sent")
            state["last_request"] = time.time()
            if action == "status":
                state.setdefault("rids", {})[rid] = time.time()
            handle.seek(0); handle.truncate(); json.dump(state, handle); handle.flush(); os.fsync(handle.fileno())
            try:
                with tempfile.TemporaryDirectory(prefix="gene-blast-") as temporary:
                    entity, metadata = Path(temporary)/"entity", Path(temporary)/"metadata.json"
                    try:
                        process = subprocess.run([sys.executable, "-c", observer, str(script), str(entity), str(metadata)],
                            input=json.dumps(request), text=True, capture_output=True, timeout=self.timeout)
                        envelope = json.loads(process.stdout)
                    except (subprocess.TimeoutExpired, ValueError) as error:
                        envelope = {"ok": False, "error": {"code": "provider_client_timeout" if isinstance(error, subprocess.TimeoutExpired)
                            else "provider_client_invalid_response", "exception_type": type(error).__name__}}
                    if not metadata.exists() or not entity.exists():
                        raise AcquisitionError(envelope.get("error", {}).get("code", "provider_client_failed"),
                            phase="client_request", diagnostic=envelope)
                    native = json.loads(metadata.read_text())
                    content = entity.read_bytes()
            finally:
                # A slow worker must not make its old reservation look like an
                # old contact. Keep the lock until this conservative completion
                # (or uncertain failure) clock is durably advanced.
                state["last_request"] = time.time()
                if action == "status":
                    state.setdefault("rids", {})[rid] = time.time()
                handle.seek(0); handle.truncate(); json.dump(state, handle); handle.flush(); os.fsync(handle.fileno())

        transport = {**native, "script": str(script), "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
            "representation": "http_entity_bytes_via_installed_blast_client", "client_envelope": envelope,
            "provider_access_dir": str(self.access_dir.resolve()), "spacing_scope": "cooperating_clients_using_configured_directory",
            "rate_clock_meaning": "conservative_worker_completion_or_failure", "automatic_redirects": False}
        public = {"action": action, "rid": rid, "program": program, "database": database,
            "hitlist_size": hitlist_size, "query_sha256": hashlib.sha256(query_fasta.encode()).hexdigest() if query_fasta else None}
        snapshot = SourceSnapshot("ncbi_blast", "https://blast.ncbi.nlm.nih.gov/Blast.cgi", public, _now(), content,
            native["headers"].get("Content-Type", native["headers"].get("content-type", "application/octet-stream")), transport)
        if 300 <= native["status"] < 400:
            raise AcquisitionError("provider_redirect_not_followed", snapshot=snapshot, phase="http_response")
        if native["status"] >= 400:
            raise AcquisitionError("provider_http_"+str(native["status"]), snapshot=snapshot, phase="http_response")
        # Native bytes, not a compact helper verdict, determine protocol identity.
        return snapshot

    def _http(self, service: str, url: str, params: dict[str, Any], media_type: str, *,
              json_body: dict[str, Any] | None = None,
              body: bytes | None = None, content_type: str | None = None,
              accept: str | None = None, max_bytes: int | None = None,
              timeout_seconds: float | None = None,
              follow_redirects: bool = True) -> SourceSnapshot:
        if max_bytes is not None and (type(max_bytes) is not int or max_bytes <= 0):
            raise ValueError("explicit_response_byte_limit_required")
        if type(follow_redirects) is not bool:
            raise ValueError("explicit_http_redirect_policy_required")
        if timeout_seconds is not None:
            try:
                valid_timeout = (type(timeout_seconds) in (int, float)
                    and math.isfinite(timeout_seconds) and timeout_seconds > 0)
            except OverflowError:
                valid_timeout = False
            if not valid_timeout:
                raise ValueError("invalid_transport_timeout")
        selected_timeout = self.timeout if timeout_seconds is None else timeout_seconds
        address = url + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
        headers = {"User-Agent": "gene-annotation-episode/0.2",
                   "Accept": media_type if accept is None else accept}
        if json_body is not None and body is not None:
            raise ValueError("one_http_body_representation_required")
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        elif body is not None:
            if not content_type:
                raise ValueError("http_body_content_type_required")
            headers["Content-Type"] = content_type
        request = urllib.request.Request(address, headers=headers,
            data=json.dumps(json_body).encode() if json_body is not None else body)
        request_body = ({"body_base64": base64.b64encode(body).decode("ascii"),
                         "body_sha256": hashlib.sha256(body).hexdigest()}
                        if body is not None else {})
        policy = ({"request_policy": {"timeout_seconds": selected_timeout,
                                     "automatic_redirects": follow_redirects}}
                  if timeout_seconds is not None or not follow_redirects else {})
        open_response = (urllib.request.urlopen if follow_redirects else
                         urllib.request.build_opener(_NoRedirect()).open)
        try:
            with open_response(request, timeout=selected_timeout) as response:
                if max_bytes is None:
                    body = response.read()
                    capture, capture_failure = {}, None
                else:
                    body, capture, capture_failure = self._read_bounded_response(response, max_bytes)
                metadata = {"status": response.status, "representation": "http_response_bytes",
                            "headers": {key.lower(): value for key, value in response.headers.items()
                                        if key.lower() in {"etag", "last-modified", "content-type", "retry-after", "link"}}}
                metadata.update(effective_url=response.geturl(), header_items=list(response.headers.items()),
                    request={"method": request.get_method(), "url": address, "headers": dict(request.header_items()), **request_body})
                metadata.update(policy)
                metadata.update(capture)
                if capture_failure is not None:
                    snapshot = SourceSnapshot(service, url,
                        json_body if json_body is not None else params, _now(), body,
                        response.headers.get("content-type", media_type), metadata)
                    raise AcquisitionError(capture_failure, snapshot=snapshot, phase="http_response")
        except urllib.error.HTTPError as error:
            delay = error.headers.get("retry-after")
            metadata = {"status": error.code, "representation": "http_error_response_bytes",
                "headers": {key.lower(): value for key, value in error.headers.items()},
                "header_items": list(error.headers.items()),
                "request": {"method": request.get_method(), "url": address,
                            "headers": dict(request.header_items()), **request_body}, "body_complete": True}
            metadata.update(policy)
            if max_bytes is not None:
                body, capture, _ = self._read_bounded_response(error, max_bytes)
                metadata.update(capture)
            else:
                try:
                    body = error.read()
                except Exception as capture_error:
                    body = getattr(capture_error, "partial", b"")
                    metadata.update(body_complete=False,
                        body_capture_error=type(capture_error).__name__)
            snapshot = SourceSnapshot(service, address,
                json_body if json_body is not None else params, _now(), body,
                error.headers.get("content-type", "application/octet-stream"), metadata)
            raise AcquisitionError("provider_http_"+str(error.code),
                retry_after=float(delay) if delay and delay.isdigit() else None,
                snapshot=snapshot, phase="http_response") from error
        except urllib.error.URLError as error:
            raise AcquisitionError("provider_connection_failed", phase="http_request",
                diagnostic={"exception_type": type(error).__name__, "message": str(error)}) from error
        except TimeoutError as error:
            raise AcquisitionError("provider_request_timeout", phase="http_request",
                diagnostic={"exception_type": type(error).__name__, "message": str(error)}) from error
        return SourceSnapshot(service, url, json_body if json_body is not None else params,
                              _now(), body, media_type, metadata)

    @staticmethod
    def _read_bounded_response(response, limit, *, decoded=False, retain=None, progress=None):
        """Retain observed bytes under a caller limit, never infer completeness."""
        pieces, observed, failure, error_name = [], 0, None, None
        headers = getattr(response, "headers", {})
        length_text = headers.get("Content-Length")
        declared = (int(length_text) if isinstance(length_text, str)
                    and re.fullmatch(r"[0-9]+", length_text) is not None
                    and headers.get("Transfer-Encoding") is None
                    and (not decoded or (headers.get('Content-Encoding') or '').lower() in {'', 'identity'}) else None)
        def details(*, finalized):
            result = {'body_complete': finalized and failure is None,
                'response_byte_limit': limit,
                'observed_body_bytes': observed, 'retained_body_bytes': sum(map(len, pieces)),
                'declared_body_bytes': declared}
            if decoded or retain is not None or progress is not None:
                result.update(body_capture_finalized=finalized,
                    total_body_bytes=observed if finalized and failure is None else None)
            if error_name is not None:
                result['body_capture_error'] = error_name
            if failure is not None:
                result['body_capture_failure'] = failure
            return result

        def append(block):
            nonlocal observed
            remaining = max(0, limit - min(observed, limit))
            observed += len(block)
            retained = block[:remaining]
            pieces.append(retained)
            if retain is not None:
                retain(retained)
            if progress is not None:
                progress(details(finalized=False))

        if progress is not None:
            progress(details(finalized=False))
        while observed <= limit:
            try:
                block = response.read(min(65536, limit + 1 - observed))
            except Exception as error:
                partial = getattr(error, "partial", b"")
                if isinstance(partial, bytes) and partial:
                    append(partial)
                failure, error_name = "provider_body_capture_failed", type(error).__name__
                break
            if not block:
                break
            append(block)
            if observed > limit:
                failure = "provider_response_byte_limit"
                break
        if failure is None and declared is not None and observed != declared:
            failure, error_name = "provider_body_capture_failed", "IncompleteRead"
        return b"".join(pieces), details(finalized=True), failure

    def hmmer_databases(self) -> SourceSnapshot:
        return self._http("ebi_hmmer", "https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/databases",
                          {}, "application/json")

    def rfam_submit(self, sequence: str) -> SourceSnapshot:
        from .rfam_discovery import BASE_URL
        import uuid
        # The documented endpoint accepts a sequence_file, not a model, URL or
        # host path. This fixed wrapper contains the actual selected operand.
        if (not isinstance(sequence, str) or not sequence or
                not set(sequence) <= set("ACGTURYSWKMBDHVN")):
            raise AcquisitionError("rfam_nucleotide_processing_operand_required",
                phase="local_preflight", submission_outcome="not_sent")
        boundary = "gene-annotation-" + uuid.uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="sequence_file"; '
                f'filename="sequence.seq"\r\nContent-Type: text/plain\r\n\r\n'
                f'{sequence}\n\r\n--{boundary}--\r\n').encode("ascii")
        snapshot = self._http("rfam_batch", BASE_URL + "/submit-job", {}, "application/json",
            body=body, content_type="multipart/form-data; boundary=" + boundary)
        return SourceSnapshot(snapshot.service, snapshot.url,
            {"multipart_field": "sequence_file", "sequence_sha256": hashlib.sha256(sequence.encode()).hexdigest(),
             "sequence_length": len(sequence), "search_parameters": "provider_defaults_not_exposed"},
            snapshot.retrieved_at, snapshot.content, snapshot.media_type, snapshot.transport)

    def rfam_result(self, job_id: str) -> SourceSnapshot:
        from .rfam_discovery import result_url
        return self._http("rfam_batch", result_url(job_id), {}, "application/json")

    def rfam_model(self, accession: str) -> RfamModelSnapshots:
        import re
        if not re.fullmatch(r"RF[0-9]{5}", accession):
            raise ValueError("invalid_rfam_accession")
        # This download endpoint returns plain model bytes but rejects a strict
        # Accept:text/plain during its renderer negotiation. Request any native
        # representation; the CM parser still validates the actual body. Keep
        # negotiation separate from the received Content-Type and model format.
        model = self._http("rfam_covariance_model", f"https://rfam.org/family/{accession}/cm",
                           {}, "text/plain", accept="*/*")
        model = SourceSnapshot(model.service, model.url, {"accession": accession},
            model.retrieved_at, model.content,
            model.transport.get("headers", {}).get("content-type", model.media_type), model.transport)
        try:
            metadata = self._http("rfam_family_metadata", f"https://rfam.org/family/{accession}",
                                 {"content-type": "application/json"}, "application/json")
        except AcquisitionError as error:
            # The already acquired selected model remains usable. Publication
            # retains it and communicates the separate metadata failure.
            return RfamModelSnapshots(model, None, error)
        return RfamModelSnapshots(model, metadata)

    def pmc_versions(self, pmcid: str, *, continuation_token: str | None = None) -> SourceSnapshot:
        from .literature_assets import BASE_URL, PMCID
        if not PMCID.fullmatch(pmcid):
            raise ValueError("invalid_pmc_identifier")
        parameters = {"list-type": 2, "prefix": pmcid + ".", "delimiter": "/", "max-keys": 1000, "encoding-type": "url"}
        if continuation_token is not None:
            parameters["continuation-token"] = continuation_token
        return self._http("pmc_cloud_versions", BASE_URL, parameters, "application/xml")

    def pmc_files(self, prefix: str, *, continuation_token: str | None = None):
        from .literature_assets import BASE_URL, PmcFiles, parse_listing, version
        version(prefix)
        parameters = {"list-type": 2, "prefix": prefix, "max-keys": 1000, "encoding-type": "url"}
        if continuation_token is not None:
            parameters["continuation-token"] = continuation_token
        listing = self._http("pmc_cloud_objects", BASE_URL, parameters, "application/xml")
        try:
            page = parse_listing(listing.content)
        except ValueError as error:
            return PmcFiles(listing, error=AcquisitionError("pmc_object_listing_invalid", diagnostic={"code": str(error)}))
        # This documented metadata name is used only after the actual object
        # listing advertised it. There is no speculative URL fetch or version choice.
        key = prefix + prefix.rstrip("/") + ".json"
        if key not in {row["key"] for row in page["objects"]}:
            return PmcFiles(listing, error=AcquisitionError(
                "pmc_metadata_not_in_selected_listing_page" if page["truncated"] else "pmc_metadata_object_not_advertised"))
        try:
            metadata = self._http("pmc_cloud_metadata", BASE_URL + urllib.parse.quote(key, safe="/"), {}, "application/json")
        except AcquisitionError as error:
            return PmcFiles(listing, error=error)
        return PmcFiles(listing, metadata)

    def pmc_asset(self, original_uri: str, *, prefix: str) -> SourceSnapshot:
        from .literature_assets import advertised_asset
        asset = advertised_asset(original_uri, prefix=prefix)
        snapshot = self._http("pmc_cloud_asset", asset["https_uri"], {}, "application/octet-stream")
        return SourceSnapshot(snapshot.service, snapshot.url,
            {"original_advertised_uri": original_uri, "version_prefix": prefix},
            snapshot.retrieved_at, snapshot.content, snapshot.media_type, snapshot.transport)

    def hmmer_submit(self, query_fasta: str, *, algorithm: str, database: str,
                     parameters: dict[str, Any] | None = None) -> SourceSnapshot:
        if algorithm not in {"phmmer", "hmmscan"}:
            raise AcquisitionError("explicit_single_hmmer_search_required",
                phase="local_preflight", submission_outcome="not_sent")
        # Parameters alter this native search only. Native inclusion/reporting
        # thresholds are measurements' scope, never annotation permission rules.
        permitted = {"E", "domE", "incE", "incdomE", "T", "domT", "incT", "incdomT", "threshold",
                     "popen", "pextend", "mx", "include_taxonomy", "exclude_taxonomy"}
        if not set(parameters or {}) <= permitted:
            raise AcquisitionError("unsupported_hmmer_search_parameter",
                phase="local_preflight", submission_outcome="not_sent")
        return self._http("ebi_hmmer", "https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/" + algorithm,
            {}, "application/json", json_body={"input": query_fasta, "database": database, **(parameters or {})})

    def hmmer_status(self, job_id: str) -> SourceSnapshot:
        import uuid
        job_id = str(uuid.UUID(job_id))
        return self._http("ebi_hmmer", "https://www.ebi.ac.uk/Tools/hmmer/api/v1/search/" + job_id,
                          {}, "application/json")

    def hmmer_result(self, job_id: str, *, page: int = 1, page_size: int = 50,
                     with_domains: bool = True) -> SourceSnapshot:
        import uuid
        job_id = str(uuid.UUID(job_id))
        return self._http("ebi_hmmer", "https://www.ebi.ac.uk/Tools/hmmer/api/v1/result/" + job_id,
            {"page": page, "page_size": page_size, "with_domains": str(with_domains).lower()}, "application/json")

    def literature_search(self, query: str, *, size: int = 10, cursor: str = "*") -> SourceSnapshot:
        return self._http("europepmc", "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                          {"query": query, "pageSize": size, "cursorMark": cursor,
                           "format": "json", "resultType": "core"}, "application/json")

    def literature_read(self, pmcid: str) -> SourceSnapshot:
        if not pmcid.startswith("PMC") or not pmcid[3:].isdigit():
            raise ValueError("invalid_pmc_identifier")
        return self._http("europepmc", f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML",
                          {}, "application/xml")

    def ncbi_search(self, database: str, term: str, *, size: int = 10, offset: int = 0,
                    max_bytes: int | None = None) -> SourceSnapshot:
        if database not in {"gene", "protein", "nuccore", "assembly", "taxonomy", "biosample", "bioproject", "pubmed"}:
            raise ValueError("unsupported_ncbi_database")
        return self._http("ncbi_entrez", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                          {"db": database, "term": term, "retmax": size, "retstart": offset,
                           "retmode": "json", "tool": "gene-annotation-episode"}, "application/json",
                          **({"max_bytes": max_bytes} if max_bytes is not None else {}))

    def ncbi_sequence(self, accession: str, *, database: str = "nuccore",
                      start: int | None = None, end: int | None = None,
                      max_bytes: int | None = None) -> SourceSnapshot:
        if database not in {"protein", "nuccore"}:
            raise ValueError("sequence_database_required")
        params: dict[str, Any] = {"db": database, "id": accession,
                                  "rettype": "gp" if database == "protein" else "gbwithparts",
                                  "retmode": "text", "tool": "gene-annotation-episode"}
        if start is not None or end is not None:
            if database != "nuccore" or start is None or end is None or not 0 <= start < end:
                raise ValueError("invalid_requested_sequence_interval")
            params.update(seq_start=start + 1, seq_stop=end)
        return self._http("ncbi_entrez", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                          params, "text/x-genbank", **({"max_bytes": max_bytes} if max_bytes is not None else {}))

    def ncbi_gene(self, gene_ids: list[str], *, max_bytes: int) -> SourceSnapshot:
        if (type(gene_ids) is not list or not gene_ids or
                any(type(value) is not str or re.fullmatch(r"[0-9]+", value) is None for value in gene_ids)
                or len(set(gene_ids)) != len(gene_ids)):
            raise ValueError("explicit_ncbi_gene_ids_required")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("explicit_response_byte_limit_required")
        return self._http("ncbi_entrez", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            {"db": "gene", "id": ",".join(gene_ids), "retmode": "xml", "tool": "gene-annotation-episode"},
            "application/xml", max_bytes=max_bytes)

    def addgene_sequences(self, identifier: str, *, max_bytes: int) -> SourceSnapshot:
        if type(identifier) is not str or re.fullmatch(r"[0-9]+", identifier) is None:
            raise ValueError("explicit_addgene_id_required")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("explicit_response_byte_limit_required")
        return self._http("addgene", "https://www.addgene.org/" + identifier + "/sequences/",
            {}, "text/html", max_bytes=max_bytes)

    def taxonomy(self, taxon_id: int) -> SourceSnapshot:
        return self._http("ncbi_entrez", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                          {"db": "taxonomy", "id": taxon_id, "retmode": "xml"}, "application/xml")


def parse_uniprot(content: bytes) -> list[dict[str, Any]]:
    """Legacy keys from the shared native parser; original request is unknown."""
    from .uniprot_native import legacy_uniprot_records, parse_uniprot_native
    parsed = parse_uniprot_native(content, request=None, response_headers=None)
    return legacy_uniprot_records(parsed, content)


def parse_genbank(content: bytes) -> list[dict[str, Any]]:
    """Preserve the fetched record's feature coordinates and source semantics.

    Integer boundaries are Biopython's nominal values in the FETCHED record,
    not automatically coordinates in a full accession fetched as a subsequence.
    Fuzzy position classes/text, part order and remote references are retained.
    Partial markers describe the source location, not inferred sequence damage.
    """
    from Bio import SeqIO
    from Bio.Seq import UndefinedSequenceError

    def position(value):
        try:
            number = int(value)
        except TypeError:
            number = None
        kind = type(value).__name__
        return number, kind, str(value)

    def boundary_partial(kind):
        if kind == "ExactPosition":
            return False
        if kind in {"BeforePosition", "AfterPosition"}:
            return True
        return None

    records = []
    for record_index, record in enumerate(SeqIO.parse(io.StringIO(content.decode("utf-8")), "genbank")):
        features, unlocated = [], []
        for feature_index, feature in enumerate(record.features):
            if feature.location is None:
                unlocated.append({"source_feature_index": feature_index,
                    "kind": feature.type, "qualifiers": dict(feature.qualifiers),
                    "location_text": None})
                continue
            segments = []
            for part in feature.location.parts:
                start, start_kind, start_text = position(part.start)
                end, end_kind, end_text = position(part.end)
                segments.append({"start": start, "end": end,
                    "strand": "+" if part.strand == 1 else "-" if part.strand == -1 else "unknown",
                    "start_kind": start_kind, "end_kind": end_kind,
                    "start_text": start_text, "end_text": end_text,
                    "partial_start": boundary_partial(start_kind),
                    "partial_end": boundary_partial(end_kind),
                    "ref": part.ref, "ref_db": part.ref_db})
            _, start_kind, _ = position(feature.location.start)
            _, end_kind, _ = position(feature.location.end)
            features.append({"kind": feature.type, "segments": segments,
                "source_feature_index": feature_index,
                "location_text": str(feature.location),
                "operator": getattr(feature.location, "operator", None),
                "strand": "+" if feature.location.strand == 1 else "-" if feature.location.strand == -1 else "unknown",
                "partial_start": boundary_partial(start_kind),
                "partial_end": boundary_partial(end_kind),
                "partialness_basis": "source_location_markers_not_inferred_sequence_damage",
                "qualifiers": dict(feature.qualifiers)})
        annotations = {key: value for key, value in record.annotations.items() if key != "references"}
        annotations["references"] = [{"title": item.title, "authors": item.authors,
                                       "journal": item.journal, "pubmed_id": item.pubmed_id}
                                      for item in record.annotations.get("references", [])]
        try:
            sequence = str(record.seq)
        except UndefinedSequenceError:
            sequence = None
        records.append({"accession": record.id, "sequence": sequence,
                        "source_record_index": record_index, "name": record.name,
                        "length": len(record.seq), "sequence_available": sequence is not None,
                        "topology": record.annotations.get("topology"),
                        "accessions": list(record.annotations.get("accessions", [])),
                        "sequence_version": record.annotations.get("sequence_version"),
                        "dbxrefs": list(record.dbxrefs),
                        "description": record.description, "annotations": annotations,
                        "features": features, "unlocated_features": unlocated,
                        "coordinate_system": "zero_based_half_open",
                        "interpretation": "external_features_not_target_annotations"})
    return records


def article_details(content: bytes) -> dict[str, Any]:
    """Project actual primary metadata and ordered text in one XML parse.

    Identifiers describe this article, never articles cited in its bibliography.
    They do not identify experiments, establish scientific independence or award
    progress. Invalid/ambiguous metadata stays actionable without losing text.
    """
    root = ET.fromstring(content)
    def local(node):
        return node.tag.rsplit('}', 1)[-1] if isinstance(node.tag, str) else ''
    identifiers, issues = set(), []
    fronts = [item for item in root if local(item) == 'front'] if local(root) == 'article' else []
    candidates = [item for front in fronts for item in front if local(item) == 'article-meta']
    if len(fronts) > 1 or len(candidates) > 1:
        # No candidate is privileged by element order. The original retains all
        # assertions; text remains usable without claiming a primary identity.
        issues.append({'code': 'ambiguous_primary_article_metadata',
            'front_count': len(fronts), 'article_meta_count': len(candidates)})
        metadata = None
    else:
        metadata = candidates[0] if candidates else None
    if metadata is not None:
        for index, item in enumerate(metadata):
            if local(item) != 'article-id':
                continue
            kind = item.get('pub-id-type', '').lower()
            namespace = 'pmcid' if kind == 'pmc' else kind
            if namespace not in PUBLICATION_ID_PATTERNS:
                continue
            value = ''.join(item.itertext()).strip()
            if namespace == 'doi':
                value = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', value, flags=re.I).lower()
            elif namespace == 'pmcid':
                value = value.upper()
                if value.isascii() and value.isdigit():
                    value = 'PMC'+(value.lstrip('0') or '0')
            if re.fullmatch(PUBLICATION_ID_PATTERNS[namespace], value) and len(value) <= 512:
                identifiers.add((namespace, value))
            else:
                issues.append({'code': 'invalid_publication_identifier',
                    'namespace': namespace, 'metadata_child_index': index})
    for namespace in PUBLICATION_ID_PATTERNS:
        if sum(kind == namespace for kind, _ in identifiers) > 1:
            issues.append({'code': 'conflicting_publication_identifiers', 'namespace': namespace})
    sections = []
    # Paragraphs are visited once in document order; their text, including
    # inline elements, is preserved rather than flattened from search snippets.
    for index, node in enumerate(node for node in root.iter() if local(node) == 'p'):
        text = "".join(node.itertext())
        if text.strip():
            sections.append({"paragraph_index": index, "text": text})
    return {'sections': sections, 'publication_identifiers': [
        {'namespace': namespace, 'value': value} for namespace, value in sorted(identifiers)],
        'metadata_issues': issues}


def article_sections(content: bytes) -> list[dict[str, Any]]:
    """Ordered original article text; shared parser retains primary metadata."""
    return article_details(content)['sections']


def uniprot_pagination(snapshot: SourceSnapshot) -> dict[str, Any]:
    """Compatibility fields from the same native/header interpretation."""
    from .uniprot_native import parse_uniprot_native
    request = None
    if "query" in snapshot.request:
        request = {"operation": "search", **{key: snapshot.request[key]
                   for key in ("query", "size", "cursor") if key in snapshot.request}}
    elif "accession" in snapshot.request:
        request = {"operation": "record", "accession": snapshot.request["accession"]}
    response = snapshot.transport.get("response")
    headers = response.get("headers") if isinstance(response, dict) else None
    page = parse_uniprot_native(snapshot.content, request=request, response_headers=headers)["page"]
    return {"next_cursor": page["next_cursor"], "total_results": page["total_results"]["value"],
            "release": page["release"]["value"], "release_date": page["release_date"]["value"],
            "pagination_metadata_available": page["pagination_metadata_available"]}


def parse_hmmer(content: bytes, *, algorithm: str) -> dict[str, Any]:
    """Translate reported native coordinates; do not interpret function/taxonomy.

    In phmmer the query is the model; in hmmscan it is the sequence. Confusing
    those axes changes query coverage and the original input receiving credit.
    Full native bodies retain fields not represented in this useful projection.
    """
    if algorithm not in {"phmmer", "hmmscan"}:
        raise ValueError("unsupported_hmmer_result_algorithm")
    payload = json.loads(content)
    status = payload["status"]
    if status != "SUCCESS":
        return {"status": status, "hits": [], "page_count": payload.get("page_count"), "stats": None}
    result = payload["result"]
    hits = []
    for hit in result["hits"]:
        metadata = hit.get("metadata") or {}
        domains = []
        for domain in hit.get("domains", []):
            alignment = domain.get("alignment_display")
            normalized: dict[str, Any] = {"bitscore": domain.get("bitscore"),
                "conditional_evalue": domain.get("cevalue"), "independent_evalue": domain.get("ievalue"),
                "native_included": domain.get("is_included"), "native_reported": domain.get("is_reported")}
            if alignment is not None:
                model_interval = [alignment["hmmfrom"] - 1, alignment["hmmto"]]
                sequence_interval = [alignment["sqfrom"] - 1, alignment["sqto"]]
                if algorithm == "phmmer":
                    query_interval, reference_interval = model_interval, sequence_interval
                    query_length, reference_length = alignment.get("m"), alignment.get("l")
                else:
                    query_interval, reference_interval = sequence_interval, model_interval
                    query_length, reference_length = alignment.get("l"), alignment.get("m")
                if not (0 <= query_interval[0] < query_interval[1] and
                        0 <= reference_interval[0] < reference_interval[1]):
                    raise ValueError("provider_alignment_coordinates_outside_sequence")
                if ((query_length is not None and query_interval[1] > query_length)
                        or (reference_length is not None and reference_interval[1] > reference_length)):
                    raise ValueError("provider_alignment_coordinates_outside_sequence")
                normalized.update(query_interval=query_interval, reference_interval=reference_interval,
                    query_length=query_length, reference_length=reference_length,
                    coordinate_system="zero_based_half_open")
                if isinstance(alignment.get("identity"), list) and alignment["identity"]:
                    normalized["identity_fraction"] = alignment["identity"][0]
            domains.append(normalized)
        hits.append({"native_index": hit["index"], "accession": metadata.get("uniprot_accession") or
            metadata.get("accession") or hit.get("acc"), "native_name": hit.get("name"),
            "source_label": metadata.get("description") or hit.get("description") or hit.get("desc"),
            "taxon_id": metadata.get("taxonomy_id"), "source_organism": metadata.get("species"),
            "source_lineage": metadata.get("lineage"), "bitscore": hit.get("score"), "evalue": hit.get("evalue"),
            "native_included": hit.get("is_included"), "native_reported": hit.get("is_reported"), "domains": domains})
    return {"status": status, "hits": hits, "page_count": payload.get("page_count"), "stats": result.get("stats")}
