"""Pinned pure ComparativeSystems provider for the existing API result owner."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .bvbrc_comparative_systems_bundle_contracts import parameters_schema, validate_parameters
from .bvbrc_comparative_systems_fact_contracts import requested_form_schema, validate_requested_form
from .bvbrc_comparative_systems_bundle_resolution import consume_bundle
from .bvbrc_comparative_systems_bundle_projection import validate_projection_failure_context

ADAPTER_ID = "bvbrc_comparative_systems"
ADAPTER_VERSION = "1"

# The exact transitive package closure is audited in P's retained test receipt.
# Configuration-time file reads never occur in parsing/projection/calculation.
_DEPENDENCIES = (
    "__init__.py",
    "bvbrc_appservice_contracts.py", "bvbrc_appservice_schemas.json",
    "bvbrc_comparative_systems_bundle_adapter.py", "bvbrc_comparative_systems_bundle_contracts.py",
    "bvbrc_comparative_systems_bundle_resolution.py", "bvbrc_comparative_systems_bundle_projection.py",
    "bvbrc_comparative_systems_fact_contracts.py", "bvbrc_comparative_systems_handoff_contracts.py",
    "bvbrc_comparative_systems_handoff_schemas.json", "bvbrc_comparative_systems_native.py",
    "bvbrc_comparative_systems_sheet.py", "bvbrc_comparative_systems_sheet_contracts.py",
    "bvbrc_comparative_systems_calculators.py", "bvbrc_comparative_systems_calculation_contracts.py",
    "bvbrc_comparative_systems_data_inputs.py", "bvbrc_comparative_systems_data_contracts.py",
    "acquisition.py", "execution_contracts.py", "bvbrc_data_fields.py", "bvbrc_data_query.py",
    "bvbrc_data_readers.py", "bvbrc_data_schema.py", "chemistry.py", "communication.py", "domain.py",
    "episode_bindings.py", "form_reference_validation.py", "launch_instructions.py", "literature_assets.py",
    "public_configuration.py", "rfam_discovery.py", "tool_knowledge.py",
)


def implementation_sha256():
    result = hashlib.sha256()
    for name in sorted(_DEPENDENCIES):
        raw = Path(__file__).with_name(name).read_bytes()
        result.update(name.encode("utf-8") + b"\0" + str(len(raw)).encode("ascii") + b"\0" + raw)
    return result.hexdigest()


__all__ = ["ADAPTER_ID", "ADAPTER_VERSION", "implementation_sha256", "parameters_schema",
           "validate_parameters", "validate_requested_form", "requested_form_schema", "consume_bundle",
           "validate_projection_failure_context"]
