"""User-supplied public-service contact defaults and frozen caller operands.

This contains configuration only: no service discovery, request or episode work.
An explicit value (including null) is authoritative when reopening a saved run.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import tomllib


UNSET = object()


def public_config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home()/".config").expanduser()
    return root/"gene_annotation_episode"/"public.toml"


def _email(value):
    if value is None:
        return None
    if (not isinstance(value, str) or not value.strip()
            or any(character.isspace() for character in value.strip())
            or value.strip().count("@") != 1
            or not all(value.strip().split("@"))):
        raise ValueError("invalid_ncbi_contact_email")
    return value.strip()


def ncbi_contact(explicit=UNSET) -> str | None:
    """Explicit caller value > environment > persistent user default.

    Saved null means unconfigured, not permission to adopt a newer default.
    Contact is not authentication; no email address is inferred from identity.
    """
    if explicit is not UNSET:
        return _email(explicit)
    environment = os.environ.get("NCBI_EMAIL")
    if environment:
        return _email(environment)
    try:
        data = tomllib.loads(public_config_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    return _email(data.get("public", {}).get("ncbi_email"))


def configured_tools(configuration=None) -> dict:
    """Freeze the actual contact with the existing tool reconstruction inputs."""
    result = deepcopy(configuration or {})
    public = result.setdefault("public", {})
    public["ncbi_email"] = ncbi_contact(public.get("ncbi_email", UNSET))
    return result


def save_ncbi_contact(email: str) -> Path:
    """Persist an explicitly supplied contact without editing package defaults."""
    email = _email(email)
    if email is None:
        raise ValueError("ncbi_contact_email_required")
    path = public_config_path()
    try:
        previous = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        previous = {}
    if set(previous) - {"public"} or set(previous.get("public", {})) - {"ncbi_email"}:
        raise ValueError("unexpected_persistent_public_configuration_fields")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".public-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write("[public]\nncbi_email = " + json.dumps(email) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path
