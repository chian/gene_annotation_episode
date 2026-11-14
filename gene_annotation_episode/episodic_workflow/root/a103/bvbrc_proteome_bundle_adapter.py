"""Pinned pure GenomeComparison provider facade for the existing API owner."""
import hashlib
from pathlib import Path

from .bvbrc_proteome_bundle_contracts import parameters_schema, validate_parameters
from .bvbrc_proteome_fact_contracts import requested_form_schema, validate_requested_form
from .bvbrc_proteome_bundle_resolution import consume_bundle

ADAPTER_ID = "bvbrc_proteome"
ADAPTER_VERSION = "1"

# Audited against the actual transitive package imports and schema assets.
# Host consumers, future full-report readers and tests are not dependencies.
_DEPENDENCIES = (
    "__init__.py",
    "bvbrc_appservice_contracts.py",
    "bvbrc_appservice_schemas.json",
    "bvbrc_proteome_bundle_adapter.py",
    "bvbrc_proteome_bundle_contracts.py",
    "bvbrc_proteome_bundle_projection.py",
    "bvbrc_proteome_bundle_resolution.py",
    "bvbrc_proteome_bundle_schemas.json",
    "bvbrc_proteome_calculators.py",
    "bvbrc_proteome_data_contracts.py",
    "bvbrc_proteome_data_schemas.json",
    "bvbrc_proteome_fact_contracts.py",
    "bvbrc_proteome_inputs.py",
    "bvbrc_proteome_joins.py",
    "bvbrc_proteome_native.py",
    "bvbrc_proteome_native_contracts.py",
    "bvbrc_proteome_native_schemas.json",
    "bvbrc_proteome_sheet.py",
    "bvbrc_proteome_sheet_contracts.py",
    "bvbrc_proteome_sheet_schemas.json",
)


def implementation_sha256() -> str:
    """Configuration-time digest of the full length-framed source/asset closure."""
    result = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        raw = Path(__file__).with_name(name).read_bytes()
        result.update(name.encode() + b"\0" + str(len(raw)).encode() + b"\0" + raw)
    return result.hexdigest()


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "consume_bundle", "implementation_sha256", "parameters_schema",
           "validate_parameters", "requested_form_schema", "validate_requested_form"]
