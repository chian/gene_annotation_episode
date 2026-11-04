"""Private user-local credentials, referenced by scoped opaque identifiers.

Only host code calls this module. References may be retained in configuration;
resolved values belong solely in the service's authentication transport.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import stat
from urllib.parse import urlsplit


_REFERENCE = re.compile(r"credential_[0-9a-f]{32}\Z")
_NAME = re.compile(r"[a-z][a-z0-9_\-]{0,63}\Z")
_STORE_LIMIT = 1024 * 1024
_STORE_NAME = "credentials.json"


class CredentialError(ValueError):
    """A controlled failure containing neither values nor filesystem paths."""


class ResolvedCredential:
    """Secret fields deliberately excluded from object representations."""

    __slots__ = ("__values",)

    def __init__(self, values):
        self.__values = _values(values)

    def __repr__(self):
        return "<ResolvedCredential redacted>"

    def field(self, name: str) -> str:
        if type(name) is not str or name not in self.__values:
            raise CredentialError("credential_field_unavailable")
        return self.__values[name]


def _name(value):
    if type(value) is not str or _NAME.fullmatch(value) is None:
        raise CredentialError("credential_name_invalid")
    return value


def _origin(value):
    valid, origin = False, None
    if type(value) is str and value and all(33 <= ord(char) <= 126 for char in value):
        try:
            parts = urlsplit(value)
            port = parts.port
            valid = (parts.scheme == "https" and bool(parts.hostname)
                and parts.username is None and parts.password is None
                and parts.path in ("", "/") and not parts.query and not parts.fragment)
            if valid:
                host = parts.hostname.lower()
                if ":" in host:
                    host = "[" + host + "]"
                origin = "https://" + host + (":" + str(port) if port not in (None, 443) else "")
        except ValueError:
            pass
    if not valid:
        raise CredentialError("credential_https_origin_required")
    return origin


def _reference(value):
    if type(value) is not str or _REFERENCE.fullmatch(value) is None:
        raise CredentialError("credential_reference_invalid")
    return value


def _values(value):
    if (type(value) is not dict or not value
            or any(type(name) is not str or _NAME.fullmatch(name) is None
                or type(item) is not str or not item for name, item in value.items())):
        raise CredentialError("credential_values_invalid")
    return dict(value)


def _private_stat(descriptor, *, directory=False):
    info = os.fstat(descriptor)
    expected = 0o700 if directory else 0o600
    if (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != expected
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or not directory and info.st_nlink != 1):
        raise CredentialError("credential_store_permissions_invalid")


def _directory(*, create=False):
    # No environment override or caller-selected run directory can redirect
    # authentication material into a source checkout or execution artifacts.
    path = Path.home() / ".config" / "gene_annotation_episode"
    if path.resolve().is_relative_to(Path(__file__).resolve().parent.parent):
        raise CredentialError("credential_store_location_invalid")
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except FileNotFoundError:
        if not create:
            return None
        raise
    try:
        if create:
            info = os.fstat(descriptor)
            if info.st_uid != os.getuid():
                raise CredentialError("credential_store_permissions_invalid")
            os.fchmod(descriptor, 0o700)
        _private_stat(descriptor, directory=True)
    except Exception:
        os.close(descriptor)
        raise
    return descriptor


def _read(directory):
    if directory is None:
        return {}
    try:
        descriptor = os.open(_STORE_NAME, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    except FileNotFoundError:
        return {}
    with os.fdopen(descriptor, "rb") as stream:
        _private_stat(stream.fileno())
        payload = stream.read(_STORE_LIMIT + 1)
    if len(payload) > _STORE_LIMIT:
        raise CredentialError("credential_store_invalid")
    data = json.loads(payload)
    if (type(data) is not dict or set(data) != {"version", "credentials"}
            or type(data["version"]) is not int or data["version"] != 1
            or type(data["credentials"]) is not dict):
        raise CredentialError("credential_store_invalid")
    for reference, row in data["credentials"].items():
        _reference(reference)
        if type(row) is not dict or set(row) != {"service", "endpoint", "values"}:
            raise CredentialError("credential_store_invalid")
        _name(row["service"])
        if _origin(row["endpoint"]) != row["endpoint"]:
            raise CredentialError("credential_store_invalid")
        _values(row["values"])
    return data["credentials"]


def _replace(directory, rows):
    payload = json.dumps({"version": 1, "credentials": rows},
        sort_keys=True, separators=(",", ":")).encode("utf-8")
    if len(payload) > _STORE_LIMIT:
        raise CredentialError("credential_store_capacity_exceeded")
    temporary = ".credentials-" + secrets.token_hex(16)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600, dir_fd=directory)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, _STORE_NAME, src_dir_fd=directory, dst_dir_fd=directory)
        os.fsync(directory)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass


def _access(operation, *, write=False):
    directory, lock, result, failure = None, None, None, None
    try:
        directory = _directory(create=write)
        if write:
            try:
                lock = os.open(".credentials.lock", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600, dir_fd=directory)
            except FileExistsError:
                lock = os.open(".credentials.lock", os.O_WRONLY | os.O_NOFOLLOW, dir_fd=directory)
            else:
                os.fchmod(lock, 0o600)
            _private_stat(lock)
            fcntl.flock(lock, fcntl.LOCK_EX)
        result = operation(directory, _read(directory))
    except CredentialError as error:
        failure = error.args[0]
    except Exception:
        failure = "credential_store_unavailable"
    finally:
        for descriptor in (lock, directory):
            if descriptor is not None:
                os.close(descriptor)
    # Raise after leaving the handler: original exceptions can contain private
    # paths or malformed stored content and must not become exception context.
    if failure is not None:
        raise CredentialError(failure)
    return result


def save_credential(service: str, endpoint: str, values: dict[str, str], *,
                    reference: str | None = None) -> str:
    """Atomically save explicit fields; return an opaque service/origin reference.

    Reusing a reference rotates its values without changing its existing scope.
    This is the sole operation that creates the private store and its directory.
    """
    service, endpoint, values = _name(service), _origin(endpoint), _values(values)
    reference = ("credential_" + secrets.token_hex(16)
                 if reference is None else _reference(reference))

    def save(directory, rows):
        previous = rows.get(reference)
        if previous is not None and (previous["service"], previous["endpoint"]) != (service, endpoint):
            raise CredentialError("credential_scope_mismatch")
        rows[reference] = {"service": service, "endpoint": endpoint, "values": values}
        _replace(directory, rows)
        return reference

    return _access(save, write=True)


def credential_reference(service: str, endpoint: str) -> str:
    """Find the single stored reference for an explicitly named service/origin."""
    service, endpoint = _name(service), _origin(endpoint)

    def lookup(directory, rows):
        matches = [reference for reference, row in rows.items()
            if (row["service"], row["endpoint"]) == (service, endpoint)]
        if not matches:
            raise CredentialError("credential_unavailable")
        if len(matches) != 1:
            raise CredentialError("credential_reference_ambiguous")
        return matches[0]

    return _access(lookup)


def resolve_credential(reference: str, *, service: str, endpoint: str) -> ResolvedCredential:
    """Resolve only the exact service and HTTPS origin bound to this reference."""
    reference, service, endpoint = _reference(reference), _name(service), _origin(endpoint)

    def resolve(directory, rows):
        row = rows.get(reference)
        if row is None:
            raise CredentialError("credential_unavailable")
        if (row["service"], row["endpoint"]) != (service, endpoint):
            raise CredentialError("credential_scope_mismatch")
        return ResolvedCredential(row["values"])

    return _access(resolve)


def credential_resolver(reference: str, *, service: str, endpoint: str, field: str):
    """Bind a lazy zero-argument field resolver for existing injected consumers."""
    reference, service, endpoint, field = (_reference(reference), _name(service),
        _origin(endpoint), _name(field))

    def resolve():
        return resolve_credential(reference, service=service, endpoint=endpoint).field(field)

    return resolve


__all__ = ["CredentialError", "ResolvedCredential", "save_credential",
           "credential_reference", "resolve_credential", "credential_resolver"]
