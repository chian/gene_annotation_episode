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

from gene_annotation_episode.acquisition import AcquisitionError

class _NoRedirect(urllib.request.HTTPRedirectHandler):

    def redirect_request(self, request, response, code, message, headers, new_url):
        return None

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _skill_script(root: Path | None, skill: str, filename: str) -> Path:
    if root is not None:
        path = root / 'skills' / skill / 'scripts' / filename
        if not path.is_file():
            raise AcquisitionError('configured_skill_client_missing')
        return path
    directory = Path.home() / '.codex/plugins/cache/openai-curated-remote/life-science-research'
    candidates = list(directory.glob(f'*/skills/{skill}/scripts/{filename}'))
    if not candidates:
        raise AcquisitionError('skill_client_not_installed')

    def key(path: Path) -> tuple[int, ...]:
        try:
            return tuple((int(part) for part in path.parents[3].name.split('.')))
        except ValueError:
            return (0,)
    return max(candidates, key=key)

def _capture_metadata(path: Path, metadata: dict) -> None:
    temporary = path.with_suffix(path.suffix + '.pending')
    temporary.write_text(json.dumps(metadata, allow_nan=False))
    temporary.replace(path)

def _bounded_skill_response(response, destination: str, entity_destination: str, limit: int):
    """Observe decoded entity bytes before the unchanged client accesses them."""
    metadata_path, entity_path = (Path(destination), Path(entity_destination))
    metadata = {'status': response.status_code, 'url': response.url, 'headers': {key.lower(): value for key, value in response.headers.items()}, 'request_method': response.request.method}
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

            class Reader:
                headers = response.headers

                def read(self, amount):
                    return response.raw.read1(amount, decode_content=True)
            raw, capture, failure = PublicClients._read_bounded_response(Reader(), limit, decoded=True, retain=retain, progress=progress)
            metadata.update(capture, retained_body_bytes=entity_path.stat().st_size)
            _capture_metadata(metadata_path, metadata)
    finally:
        response.close()
    if failure is not None:
        raise ValueError(failure)
    if 300 <= response.status_code < 400:
        raise ValueError('provider_redirect_not_followed')
    response._content = raw
    response._content_consumed = True
    return response

class PublicClients:
    """Caller-configured A105 source acquisition clients.

    UniProt uses the installed skill clients whose protocol instructions
    were read during the rebuild. The dependency path and digest are recorded.
    No copyrighted client is silently copied or imported from another project.
    Other providers use their documented public HTTP interfaces directly.
    """

    def __init__(self, *, ncbi_email: str | None | object=UNSET, skill_root: Path | None=None, timeout: int=90, access_dir: Path | None=None):
        if type(timeout) is not int or timeout <= 0:
            raise ValueError('invalid_transport_timeout')
        self.ncbi_email = ncbi_contact(ncbi_email)
        self.skill_root, self.timeout, self.access_dir = (skill_root, timeout, access_dir)

    def _skill(self, skill: str, filename: str, payload: dict[str, Any], *, capture_headers: bool=False, service_name: str | None=None, max_bytes: int | None=None) -> tuple[dict, bytes, dict]:
        if max_bytes is not None and (not capture_headers or type(max_bytes) is not int or max_bytes <= 0):
            raise ValueError('explicit_observed_response_byte_limit_required')
        script = _skill_script(self.skill_root, skill, filename)
        observer_policy = None if max_bytes is None else {'version': 'bounded_skill_http_entity_capture_v1', 'adapter_module': __name__, 'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'response_byte_limit': max_bytes, 'byte_basis': 'requests_decoded_entity_bytes', 'stream': True, 'automatic_redirects': False, 'redirect_preparation': False}
        with tempfile.TemporaryDirectory(prefix='gene-evidence-') as directory:
            output_path = Path(directory) / 'response.json'
            headers_path = Path(directory) / 'headers.json'
            entity_path = Path(directory) / 'response.entity'
            request = {**payload, 'save_raw': True, 'raw_output_path': str(output_path)}
            if skill == 'uniprot-skill':
                request['timeout_sec'] = self.timeout
            command = [sys.executable, str(script)]
            if capture_headers:
                observer = 'import json, pathlib, requests, runpy, sys\nscript, destination, entity_destination = sys.argv[1:]\noriginal = requests.Session.request\ndef observed(self, *args, **kwargs):\n    response = original(self, *args, **kwargs)\n    pathlib.Path(destination).write_text(json.dumps({"status": response.status_code, "url": response.url,\n        "headers": {key.lower(): value for key, value in response.headers.items()},\n        "request_method": response.request.method}))\n    pathlib.Path(entity_destination).write_bytes(response.content)\n    return response\nrequests.Session.request = observed\nsys.argv = [script]\nrunpy.run_path(script, run_name="__main__")\n'
                command = [sys.executable, '-c', observer, str(script), str(headers_path), str(entity_path)]
                if max_bytes is not None:
                    observer = 'import hashlib, pathlib, requests, runpy, sys\nscript, package_root, adapter_sha256, limit, destination, entity_destination = sys.argv[1:]\nsys.path.insert(0, package_root)\nfrom gene_annotation_episode.episodic_workflow.root.a105 import acquisition as capture_adapter\nif hashlib.sha256(pathlib.Path(capture_adapter.__file__).read_bytes()).hexdigest() != adapter_sha256:\n    raise RuntimeError("response_capture_adapter_changed")\noriginal_request = requests.Session.request\noriginal_redirects = requests.Session.resolve_redirects\ndef observed(self, *args, **kwargs):\n    kwargs.update(stream=True, allow_redirects=False)\n    response = original_request(self, *args, **kwargs)\n    return capture_adapter._bounded_skill_response(response, destination, entity_destination, int(limit))\ndef no_redirect_preparation(self, *args, **kwargs):\n    return iter(())\nrequests.Session.request = observed\nrequests.Session.resolve_redirects = no_redirect_preparation\ntry:\n    sys.argv = [script]\n    runpy.run_path(script, run_name="__main__")\nfinally:\n    requests.Session.request = original_request\n    requests.Session.resolve_redirects = original_redirects\n'
                    command = [sys.executable, '-c', observer, str(script), str(Path(__file__).resolve().parents[4]), observer_policy['adapter_sha256'], str(max_bytes), str(headers_path), str(entity_path)]
            try:
                result = subprocess.run(command, input=json.dumps(request), text=True, capture_output=True, timeout=self.timeout)
            except subprocess.TimeoutExpired as error:
                envelope = {'ok': False, 'error': {'code': 'provider_client_timeout'}}
            else:
                try:
                    envelope = json.loads(result.stdout)
                except (ValueError, TypeError):
                    envelope = {'ok': False, 'error': {'code': 'provider_client_invalid_response'}}
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
                    response_metadata.update(body_complete=False, total_body_bytes=None, observed_body_bytes=None, observed_body_bytes_lower_bound=max(len(raw), previous if type(previous) is int else 0))
                if captured is not None and len(captured) > max_bytes:
                    response_metadata.update(body_complete=False, total_body_bytes=None, body_capture_failure='provider_response_byte_limit', observed_body_bytes=None, observed_body_bytes_lower_bound=len(captured))
            capture_failure = (response_metadata or {}).get('body_capture_failure')
            if max_bytes is not None and envelope.get('ok') and (not entity_path.exists() or response_metadata is None or response_metadata.get('body_complete') is not True):
                capture_failure = capture_failure or 'provider_body_capture_failed'
                envelope = {'ok': False, 'error': {'code': capture_failure}}
            if not envelope.get('ok'):
                status = (response_metadata or {}).get('status')
                snapshot = SourceSnapshot(service_name or skill, response_metadata.get('url', payload['base_url'].rstrip('/') + '/' + payload['path'].lstrip('/')), payload.get('params', {}), _now(), raw, response_metadata.get('headers', {}).get('content-type', 'application/octet-stream'), {'response': response_metadata, 'representation': 'http_entity_bytes_via_installed_client', 'script': str(script), 'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest(), **({'observer': observer_policy} if observer_policy is not None else {})}) if response_metadata and entity_path.exists() else None
                code = 'provider_http_' + str(status) if isinstance(status, int) and status >= 400 else 'provider_redirect_not_followed' if max_bytes is not None and isinstance(status, int) and (300 <= status < 400) else capture_failure or envelope.get('error', {}).get('code', 'provider_error')
                raise AcquisitionError(code, snapshot=snapshot, phase='http_response' if snapshot else 'client_response', diagnostic={'client_error': envelope.get('error'), 'script': str(script), 'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest()})
        transport = {'script': str(script), 'script_sha256': hashlib.sha256(script.read_bytes()).hexdigest(), 'representation': 'client_saved_provider_payload'}
        if response_metadata is not None:
            transport['response'] = response_metadata
            transport['representation'] = 'http_entity_bytes_via_installed_client'
        if observer_policy is not None:
            transport['observer'] = observer_policy
        return (envelope, raw, transport)

    def uniprot_search(self, query: str, *, size: int=10, cursor: str | None=None) -> SourceSnapshot:
        params: dict[str, Any] = {'query': query, 'size': size, 'format': 'json'}
        if cursor:
            params['cursor'] = cursor
        _, content, transport = self._skill('uniprot-skill', 'rest_request.py', {'base_url': 'https://rest.uniprot.org', 'path': 'uniprotkb/search', 'params': params, 'max_items': size, 'response_format': 'json'}, capture_headers=True)
        return SourceSnapshot('uniprot', 'https://rest.uniprot.org/uniprotkb/search', params, _now(), content, 'application/json', transport)

    def uniprot_record(self, accession: str) -> SourceSnapshot:
        path = f"uniprotkb/{urllib.parse.quote(accession, safe='')}"
        _, content, transport = self._skill('uniprot-skill', 'rest_request.py', {'base_url': 'https://rest.uniprot.org', 'path': path, 'params': {'format': 'json'}, 'response_format': 'json'}, capture_headers=True)
        return SourceSnapshot('uniprot', 'https://rest.uniprot.org/' + path, {'accession': accession}, _now(), content, 'application/json', transport)

    def _http(self, service: str, url: str, params: dict[str, Any], media_type: str, *, json_body: dict[str, Any] | None=None, body: bytes | None=None, content_type: str | None=None, accept: str | None=None, max_bytes: int | None=None, timeout_seconds: float | None=None, follow_redirects: bool=True, bearer_token: str | None=None) -> SourceSnapshot:
        if max_bytes is not None and (type(max_bytes) is not int or max_bytes <= 0):
            raise ValueError('explicit_response_byte_limit_required')
        if type(follow_redirects) is not bool:
            raise ValueError('explicit_http_redirect_policy_required')
        if timeout_seconds is not None:
            try:
                valid_timeout = type(timeout_seconds) in (int, float) and math.isfinite(timeout_seconds) and (timeout_seconds > 0)
            except OverflowError:
                valid_timeout = False
            if not valid_timeout:
                raise ValueError('invalid_transport_timeout')
        authenticated = bearer_token is not None
        if authenticated:
            if type(bearer_token) is not str or not bearer_token or any((not 33 <= ord(character) <= 126 for character in bearer_token)):
                raise ValueError('invalid_http_bearer_token')
            selected_url = urllib.parse.urlsplit(url)
            if selected_url.scheme != 'https' or not selected_url.hostname or selected_url.username is not None or (selected_url.password is not None) or selected_url.fragment:
                raise ValueError('authenticated_http_requires_https')
            if follow_redirects:
                raise ValueError('authenticated_http_redirects_forbidden')
            if max_bytes is None:
                raise ValueError('authenticated_http_byte_limit_required')
        authentication = {'scheme': 'Bearer', 'credential_value_retained': False}

        def literal_echo(*values):
            if not authenticated:
                return False
            for value in values:
                if isinstance(value, str) and bearer_token in value:
                    return True
                if isinstance(value, (bytes, bytearray, memoryview)) and bearer_token.encode('ascii') in bytes(value):
                    return True
                if isinstance(value, dict) and literal_echo(*value.keys(), *value.values()):
                    return True
                if isinstance(value, (list, tuple)) and literal_echo(*value):
                    return True
                if (value is None or type(value) in (bool, int, float)) and bearer_token in json.dumps(value):
                    return True
            return False

        def error_echo(error):
            try:
                return literal_echo(str(error), type(error).__name__)
            except Exception:
                return False

        def authentication_error(code, *, phase, status=None, captured=None, capture=None, exception_type=None):
            details = {'authentication': dict(authentication)}
            if type(status) is int:
                details['http_status'] = status
            if isinstance(captured, bytes):
                details.update(captured_body_bytes=len(captured), captured_body_sha256=hashlib.sha256(captured).hexdigest())
            if isinstance(capture, dict) and type(capture.get('observed_body_bytes')) is int:
                details['observed_body_bytes'] = capture['observed_body_bytes']
            if exception_type is not None:
                details.update(exception_type=exception_type, message_retained=False)
            return AcquisitionError(code, phase=phase, diagnostic=details)
        selected_timeout = self.timeout if timeout_seconds is None else timeout_seconds
        address = url + ('?' + urllib.parse.urlencode(params, doseq=True) if params else '')
        headers = {'User-Agent': 'gene-annotation-episode/0.2', 'Accept': media_type if accept is None else accept}
        if json_body is not None and body is not None:
            raise ValueError('one_http_body_representation_required')
        if json_body is not None:
            headers['Content-Type'] = 'application/json'
        elif body is not None:
            if not content_type:
                raise ValueError('http_body_content_type_required')
            headers['Content-Type'] = content_type
        if authenticated and (literal_echo(service, url, address, headers, params) or (json_body is not None and literal_echo(json_body)) or (body is not None and literal_echo(body))):
            raise ValueError('http_bearer_request_conflict')
        if authenticated:
            headers['Authorization'] = 'Bearer ' + bearer_token
        request = urllib.request.Request(address, headers=headers, data=json.dumps(json_body).encode() if json_body is not None else body)
        request_body = {'body_base64': base64.b64encode(body).decode('ascii'), 'body_sha256': hashlib.sha256(body).hexdigest()} if body is not None else {}

        def retained_request():
            result = {'method': request.get_method(), 'url': address, 'headers': {key: value for key, value in request.header_items() if not authenticated or key.lower() != 'authorization'}, **request_body}
            if authenticated:
                result['authentication'] = dict(authentication)
            return result
        policy = {'request_policy': {'timeout_seconds': selected_timeout, 'automatic_redirects': follow_redirects}} if timeout_seconds is not None or not follow_redirects else {}
        open_response = urllib.request.urlopen if follow_redirects else urllib.request.build_opener(_NoRedirect()).open
        response_phase = 'http_request'
        try:
            with open_response(request, timeout=selected_timeout) as response:
                response_phase = 'http_response'
                if max_bytes is None:
                    body = response.read()
                    capture, capture_failure = ({}, None)
                else:
                    body, capture, capture_failure = self._read_bounded_response(response, max_bytes)
                metadata = {'status': response.status, 'representation': 'http_response_bytes', 'headers': {key.lower(): value for key, value in response.headers.items() if key.lower() in {'etag', 'last-modified', 'content-type', 'retry-after', 'link'}}}
                effective_url = response.geturl()
                response_headers = list(response.headers.items())
                if authenticated and literal_echo(body, response_headers, effective_url, capture.get('body_capture_error', '')):
                    raise authentication_error('provider_authentication_echo_rejected', phase='http_response', status=response.status, captured=body, capture=capture) from None
                metadata.update(effective_url=effective_url, header_items=response_headers, request=retained_request())
                metadata.update(policy)
                metadata.update(capture)
                if capture_failure is not None:
                    snapshot = SourceSnapshot(service, url, json_body if json_body is not None else params, _now(), body, response.headers.get('content-type', media_type), metadata)
                    raise AcquisitionError(capture_failure, snapshot=snapshot, phase='http_response')
        except urllib.error.HTTPError as error:
            delay = error.headers.get('retry-after')
            metadata = {'status': error.code, 'representation': 'http_error_response_bytes', 'headers': {key.lower(): value for key, value in error.headers.items()}, 'header_items': list(error.headers.items()), 'request': retained_request(), 'body_complete': True}
            metadata.update(policy)
            if max_bytes is not None:
                body, capture, _ = self._read_bounded_response(error, max_bytes)
                metadata.update(capture)
            else:
                try:
                    body = error.read()
                except Exception as capture_error:
                    body = getattr(capture_error, 'partial', b'')
                    metadata.update(body_complete=False, body_capture_error=type(capture_error).__name__)
            if authenticated and (literal_echo(body, metadata['header_items'], error.geturl(), metadata.get('body_capture_error', '')) or error_echo(error)):
                raise authentication_error('provider_authentication_echo_rejected', phase='http_response', status=error.code, captured=body, capture=metadata) from None
            snapshot = SourceSnapshot(service, address, json_body if json_body is not None else params, _now(), body, error.headers.get('content-type', 'application/octet-stream'), metadata)
            failure = AcquisitionError('provider_http_' + str(error.code), retry_after=float(delay) if delay and delay.isdigit() else None, snapshot=snapshot, phase='http_response')
            if authenticated:
                raise failure from None
            raise failure from error
        except urllib.error.URLError as error:
            if authenticated:
                raise authentication_error('provider_authentication_echo_rejected' if error_echo(error) else 'provider_connection_failed', phase='http_request', exception_type='URLError') from None
            raise AcquisitionError('provider_connection_failed', phase='http_request', diagnostic={'exception_type': type(error).__name__, 'message': str(error)}) from error
        except TimeoutError as error:
            if authenticated:
                raise authentication_error('provider_authentication_echo_rejected' if error_echo(error) else 'provider_request_timeout', phase='http_request', exception_type='TimeoutError') from None
            raise AcquisitionError('provider_request_timeout', phase='http_request', diagnostic={'exception_type': type(error).__name__, 'message': str(error)}) from error
        except AcquisitionError:
            raise
        except Exception as error:
            if not authenticated:
                raise
            raise authentication_error('provider_authentication_echo_rejected' if error_echo(error) else 'provider_authenticated_request_failed', phase=response_phase, exception_type='Exception') from None
        return SourceSnapshot(service, url, json_body if json_body is not None else params, _now(), body, media_type, metadata)

    @staticmethod
    def _read_bounded_response(response, limit, *, decoded=False, retain=None, progress=None):
        """Retain observed bytes under a caller limit, never infer completeness."""
        pieces, observed, failure, error_name = ([], 0, None, None)
        headers = getattr(response, 'headers', {})
        length_text = headers.get('Content-Length')
        declared = int(length_text) if isinstance(length_text, str) and re.fullmatch('[0-9]+', length_text) is not None and (headers.get('Transfer-Encoding') is None) and (not decoded or (headers.get('Content-Encoding') or '').lower() in {'', 'identity'}) else None

        def details(*, finalized):
            result = {'body_complete': finalized and failure is None, 'response_byte_limit': limit, 'observed_body_bytes': observed, 'retained_body_bytes': sum(map(len, pieces)), 'declared_body_bytes': declared}
            if decoded or retain is not None or progress is not None:
                result.update(body_capture_finalized=finalized, total_body_bytes=observed if finalized and failure is None else None)
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
                partial = getattr(error, 'partial', b'')
                if isinstance(partial, bytes) and partial:
                    append(partial)
                failure, error_name = ('provider_body_capture_failed', type(error).__name__)
                break
            if not block:
                break
            append(block)
            if observed > limit:
                failure = 'provider_response_byte_limit'
                break
        if failure is None and declared is not None and (observed != declared):
            failure, error_name = ('provider_body_capture_failed', 'IncompleteRead')
        return (b''.join(pieces), details(finalized=True), failure)

    def pmc_versions(self, pmcid: str, *, continuation_token: str | None=None) -> SourceSnapshot:
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assets import BASE_URL, PMCID
        if not PMCID.fullmatch(pmcid):
            raise ValueError('invalid_pmc_identifier')
        parameters = {'list-type': 2, 'prefix': pmcid + '.', 'delimiter': '/', 'max-keys': 1000, 'encoding-type': 'url'}
        if continuation_token is not None:
            parameters['continuation-token'] = continuation_token
        return self._http('pmc_cloud_versions', BASE_URL, parameters, 'application/xml')

    def pmc_files(self, prefix: str, *, continuation_token: str | None=None):
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assets import BASE_URL, PmcFiles, parse_listing, version
        version(prefix)
        parameters = {'list-type': 2, 'prefix': prefix, 'max-keys': 1000, 'encoding-type': 'url'}
        if continuation_token is not None:
            parameters['continuation-token'] = continuation_token
        listing = self._http('pmc_cloud_objects', BASE_URL, parameters, 'application/xml')
        try:
            page = parse_listing(listing.content)
        except ValueError as error:
            return PmcFiles(listing, error=AcquisitionError('pmc_object_listing_invalid', diagnostic={'code': str(error)}))
        key = prefix + prefix.rstrip('/') + '.json'
        if key not in {row['key'] for row in page['objects']}:
            return PmcFiles(listing, error=AcquisitionError('pmc_metadata_not_in_selected_listing_page' if page['truncated'] else 'pmc_metadata_object_not_advertised'))
        try:
            metadata = self._http('pmc_cloud_metadata', BASE_URL + urllib.parse.quote(key, safe='/'), {}, 'application/json')
        except AcquisitionError as error:
            return PmcFiles(listing, error=error)
        return PmcFiles(listing, metadata)

    def pmc_asset(self, original_uri: str, *, prefix: str) -> SourceSnapshot:
        from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assets import advertised_asset
        asset = advertised_asset(original_uri, prefix=prefix)
        snapshot = self._http('pmc_cloud_asset', asset['https_uri'], {}, 'application/octet-stream')
        return SourceSnapshot(snapshot.service, snapshot.url, {'original_advertised_uri': original_uri, 'version_prefix': prefix}, snapshot.retrieved_at, snapshot.content, snapshot.media_type, snapshot.transport)

    def literature_search(self, query: str, *, size: int=10, cursor: str='*') -> SourceSnapshot:
        return self._http('europepmc', 'https://www.ebi.ac.uk/europepmc/webservices/rest/search', {'query': query, 'pageSize': size, 'cursorMark': cursor, 'format': 'json', 'resultType': 'core'}, 'application/json')

    def literature_read(self, pmcid: str) -> SourceSnapshot:
        if not pmcid.startswith('PMC') or not pmcid[3:].isdigit():
            raise ValueError('invalid_pmc_identifier')
        return self._http('europepmc', f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML', {}, 'application/xml')

    def ncbi_search(self, database: str, term: str, *, size: int=10, offset: int=0, max_bytes: int | None=None) -> SourceSnapshot:
        if database not in {'gene', 'protein', 'nuccore', 'assembly', 'taxonomy', 'biosample', 'bioproject', 'pubmed'}:
            raise ValueError('unsupported_ncbi_database')
        return self._http('ncbi_entrez', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi', {'db': database, 'term': term, 'retmax': size, 'retstart': offset, 'retmode': 'json', 'tool': 'gene-annotation-episode'}, 'application/json', **{'max_bytes': max_bytes} if max_bytes is not None else {})

    def ncbi_sequence(self, accession: str, *, database: str='nuccore', start: int | None=None, end: int | None=None, max_bytes: int | None=None) -> SourceSnapshot:
        if database not in {'protein', 'nuccore'}:
            raise ValueError('sequence_database_required')
        params: dict[str, Any] = {'db': database, 'id': accession, 'rettype': 'gp' if database == 'protein' else 'gbwithparts', 'retmode': 'text', 'tool': 'gene-annotation-episode'}
        if start is not None or end is not None:
            if database != 'nuccore' or start is None or end is None or (not 0 <= start < end):
                raise ValueError('invalid_requested_sequence_interval')
            params.update(seq_start=start + 1, seq_stop=end)
        return self._http('ncbi_entrez', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi', params, 'text/x-genbank', **{'max_bytes': max_bytes} if max_bytes is not None else {})

    def taxonomy(self, taxon_id: int) -> SourceSnapshot:
        return self._http('ncbi_entrez', 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi', {'db': 'taxonomy', 'id': taxon_id, 'retmode': 'xml'}, 'application/xml')

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
        return (number, kind, str(value))

    def boundary_partial(kind):
        if kind == 'ExactPosition':
            return False
        if kind in {'BeforePosition', 'AfterPosition'}:
            return True
        return None
    records = []
    for record_index, record in enumerate(SeqIO.parse(io.StringIO(content.decode('utf-8')), 'genbank')):
        features, unlocated = ([], [])
        for feature_index, feature in enumerate(record.features):
            if feature.location is None:
                unlocated.append({'source_feature_index': feature_index, 'kind': feature.type, 'qualifiers': dict(feature.qualifiers), 'location_text': None})
                continue
            segments = []
            for part in feature.location.parts:
                start, start_kind, start_text = position(part.start)
                end, end_kind, end_text = position(part.end)
                segments.append({'start': start, 'end': end, 'strand': '+' if part.strand == 1 else '-' if part.strand == -1 else 'unknown', 'start_kind': start_kind, 'end_kind': end_kind, 'start_text': start_text, 'end_text': end_text, 'partial_start': boundary_partial(start_kind), 'partial_end': boundary_partial(end_kind), 'ref': part.ref, 'ref_db': part.ref_db})
            _, start_kind, _ = position(feature.location.start)
            _, end_kind, _ = position(feature.location.end)
            features.append({'kind': feature.type, 'segments': segments, 'source_feature_index': feature_index, 'location_text': str(feature.location), 'operator': getattr(feature.location, 'operator', None), 'strand': '+' if feature.location.strand == 1 else '-' if feature.location.strand == -1 else 'unknown', 'partial_start': boundary_partial(start_kind), 'partial_end': boundary_partial(end_kind), 'partialness_basis': 'source_location_markers_not_inferred_sequence_damage', 'qualifiers': dict(feature.qualifiers)})
        annotations = {key: value for key, value in record.annotations.items() if key != 'references'}
        annotations['references'] = [{'title': item.title, 'authors': item.authors, 'journal': item.journal, 'pubmed_id': item.pubmed_id} for item in record.annotations.get('references', [])]
        try:
            sequence = str(record.seq)
        except UndefinedSequenceError:
            sequence = None
        records.append({'accession': record.id, 'sequence': sequence, 'source_record_index': record_index, 'name': record.name, 'length': len(record.seq), 'sequence_available': sequence is not None, 'topology': record.annotations.get('topology'), 'accessions': list(record.annotations.get('accessions', [])), 'sequence_version': record.annotations.get('sequence_version'), 'dbxrefs': list(record.dbxrefs), 'description': record.description, 'annotations': annotations, 'features': features, 'unlocated_features': unlocated, 'coordinate_system': 'zero_based_half_open', 'interpretation': 'external_features_not_target_annotations'})
    return records

def article_details(content: bytes) -> dict[str, Any]:
    """Project actual primary metadata and ordered text in one XML parse.

    Publication identifiers describe this article. Cited publications remain a
    separate discovery projection and never enter the article's own identity.
    They do not identify experiments, establish scientific independence or award
    progress. Invalid/ambiguous metadata stays actionable without losing text.
    """
    root = ET.fromstring(content)

    def local(node):
        return node.tag.rsplit('}', 1)[-1] if isinstance(node.tag, str) else ''

    def paragraph_text(node):
        blocks = {'table', 'thead', 'tbody', 'tfoot', 'tr'}
        pieces, pending = ([], [(node, False)])
        while pending:
            current, closing = pending.pop()
            tag = local(current)
            if closing:
                if tag in {'td', 'th'}:
                    pieces.append('\t')
                elif tag in blocks:
                    pieces.append('\n')
                if current is not node and current.tail:
                    pieces.append(current.tail)
                continue
            if tag in blocks:
                pieces.append('\n')
            if current.text:
                pieces.append(current.text)
            pending.append((current, True))
            pending.extend(((child, False) for child in reversed(current)))
        return ''.join(pieces)
    identifiers, issues = (set(), [])
    fronts = [item for item in root if local(item) == 'front'] if local(root) == 'article' else []
    candidates = [item for front in fronts for item in front if local(item) == 'article-meta']
    if len(fronts) > 1 or len(candidates) > 1:
        issues.append({'code': 'ambiguous_primary_article_metadata', 'front_count': len(fronts), 'article_meta_count': len(candidates)})
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
                value = re.sub('^https?://(?:dx\\.)?doi\\.org/', '', value, flags=re.I).lower()
            elif namespace == 'pmcid':
                value = value.upper()
                if value.isascii() and value.isdigit():
                    value = 'PMC' + (value.lstrip('0') or '0')
            if re.fullmatch(PUBLICATION_ID_PATTERNS[namespace], value) and len(value) <= 512:
                identifiers.add((namespace, value))
            else:
                issues.append({'code': 'invalid_publication_identifier', 'namespace': namespace, 'metadata_child_index': index})
    for namespace in PUBLICATION_ID_PATTERNS:
        if sum((kind == namespace for kind, _ in identifiers)) > 1:
            issues.append({'code': 'conflicting_publication_identifiers', 'namespace': namespace})
    sections, cited_in = ([], {})
    for index, node in enumerate((node for node in root.iter() if local(node) == 'p')):
        text = paragraph_text(node)
        if text.strip():
            sections.append({'paragraph_index': index, 'text': text})
        for citation in node.iter():
            if local(citation) == 'xref' and citation.get('ref-type') == 'bibr':
                for reference_id in citation.get('rid', '').split():
                    cited_in.setdefault(reference_id, set()).add(index)
    references = []
    for back in (node for node in root if local(node) == 'back'):
        for reference in (node for node in back.iter() if local(node) == 'ref'):

            def field(name):
                values = [''.join(node.itertext()).strip() for node in reference.iter() if local(node) == name]
                return list(dict.fromkeys((value for value in values if value)))
            cited_identifiers, cited_issues = (set(), [])
            for node in reference.iter():
                if local(node) != 'pub-id':
                    continue
                namespace = node.get('pub-id-type', '').lower()
                namespace = 'pmcid' if namespace == 'pmc' else namespace
                if namespace not in PUBLICATION_ID_PATTERNS:
                    continue
                value = ''.join(node.itertext()).strip()
                if namespace == 'doi':
                    value = re.sub('^https?://(?:dx\\.)?doi\\.org/', '', value, flags=re.I).lower()
                elif namespace == 'pmcid':
                    value = value.upper()
                    if value.isascii() and value.isdigit():
                        value = 'PMC' + (value.lstrip('0') or '0')
                if re.fullmatch(PUBLICATION_ID_PATTERNS[namespace], value) and len(value) <= 512:
                    cited_identifiers.add((namespace, value))
                else:
                    cited_issues.append({'code': 'invalid_cited_publication_identifier', 'namespace': namespace})
            reference_id = reference.get('id')
            references.append({'reference_id': reference_id, 'labels': field('label'), 'titles': field('article-title'), 'years': field('year'), 'citation_text': ''.join(reference.itertext()).strip(), 'identifiers': [{'namespace': namespace, 'value': value} for namespace, value in sorted(cited_identifiers)], 'cited_in_paragraphs': sorted(cited_in.get(reference_id, ())), 'metadata_issues': cited_issues})
    return {'sections': sections, 'publication_identifiers': [{'namespace': namespace, 'value': value} for namespace, value in sorted(identifiers)], 'metadata_issues': issues, 'cited_publications': references}

def article_sections(content: bytes) -> list[dict[str, Any]]:
    """Ordered original article text; shared parser retains primary metadata."""
    return article_details(content)['sections']

def uniprot_pagination(snapshot: SourceSnapshot) -> dict[str, Any]:
    """Compatibility fields from the same native/header interpretation."""
    from .uniprot_native import parse_uniprot_native
    request = None
    if 'query' in snapshot.request:
        request = {'operation': 'search', **{key: snapshot.request[key] for key in ('query', 'size', 'cursor') if key in snapshot.request}}
    elif 'accession' in snapshot.request:
        request = {'operation': 'record', 'accession': snapshot.request['accession']}
    response = snapshot.transport.get('response')
    headers = response.get('headers') if isinstance(response, dict) else None
    page = parse_uniprot_native(snapshot.content, request=request, response_headers=headers)['page']
    return {'next_cursor': page['next_cursor'], 'total_results': page['total_results']['value'], 'release': page['release']['value'], 'release_date': page['release_date']['value'], 'pagination_metadata_available': page['pagination_metadata_available']}
