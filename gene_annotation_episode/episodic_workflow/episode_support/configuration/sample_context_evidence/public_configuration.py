"""The NCBI contact address used by the A108 public acquisition clients.

This contains configuration only: no service discovery, request or episode work.
An explicit value (including null) is authoritative.
"""
from __future__ import annotations

import os
from pathlib import Path
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

